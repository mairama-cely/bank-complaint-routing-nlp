"""Phase 3c-i — External temporal test set (2025), built with exactly the Phase 2b / 3a rules.

Pipeline (no re-fitting of anything):
  raw CSV (exports in phase3.external_test) -> same schema checks as Phase 1 -> non-empty narratives
  -> frozen product->service mapping (unknown labels excluded and reported)
  -> clean() R1-R7 from clean_split.py, R8 -> dedup on cleaned text (same rule as 2b)
  -> removal of texts identical to any 2026 cleaned text (train/val/test) -> [COMPANY] masking with the
     3a lexicon (reports/phase3a/lexicon_patterns.csv, unchanged).

Outputs: data/processed/external_<label>.parquet, data/processed/MANIFEST_external.json,
         reports/phase3c/external_*.csv, reports/phase3c_external_<label>.md
"""
from __future__ import annotations

import hashlib
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "features"))
from build_company_mask import make_masker  # noqa: E402
from clean_split import TOKENS, clean  # noqa: E402
from common import ROOT, load_config, read_json, stop, write_json  # noqa: E402
from profile_report import md_table  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(8 * 1024**2), b""):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    cfg = load_config()
    p2, p3, dd = cfg.get("phase2"), cfg.get("phase3"), cfg.get("dedup_rule")
    ext = (p3 or {}).get("external_test")
    if not (p2 and p3 and dd and ext):
        stop("phase2, phase3.external_test ou dedup_rule absent de config.yaml.")
    overlap = set(ext["exports"]) & set(cfg["selected_exports"])
    if overlap:
        stop(f"Exports externes déjà utilisés pour 2026 : {sorted(overlap)}")
    label = ext["label"]
    if "csv_strict_options" not in cfg:
        stop("csv_strict_options absent de config.yaml.")
    mapping = yaml.safe_load((ROOT / "config" / "label_mapping.yaml").read_text(encoding="utf-8"))
    if mapping.get("status") != "frozen":
        stop("config/label_mapping.yaml n'est pas figé.")
    cols = read_json(ROOT / cfg["paths"]["interim"] / "columns.json")
    o2n = cols["original_to_normalized"]
    keys = cols["keys"]
    date_fmt = cols["date_conversion"][keys["date_received"]]["format"]

    proc = ROOT / "data" / "processed"
    manifest = read_json(proc / "MANIFEST.json")
    mman = read_json(proc / "MANIFEST_company_masked.json")
    if manifest is None or mman is None:
        stop("Manifeste 2b ou 3a absent.")
    if sha256(proc / "complaints_clean.parquet") != manifest["all"]["sha256"]:
        stop("complaints_clean.parquet ne correspond pas à son sha256.")
    lex_path = ROOT / "reports" / "phase3a" / "lexicon_patterns.csv"
    patterns = pd.read_csv(lex_path, keep_default_na=False)["pattern"].tolist()
    if len(patterns) != mman["_n_patterns"]:
        stop(f"Lexique 3a incohérent : {len(patterns)} motifs lus, {mman['_n_patterns']} attendus.")

    # --- 1. read raw CSVs with the Phase 1 schema
    print("[1/5] Lecture des exports externes (schéma Phase 1)…", flush=True)
    raw = ROOT / cfg["paths"]["raw"]
    by_id = {e["id"]: e for e in cfg["exports"]}
    con = duckdb.connect()
    parts, per_export = [], []
    for eid in ext["exports"]:
        f = raw / by_id[eid]["csv"]
        if not f.exists():
            stop(f"{f.name} absent de data/raw.")
        expr = f"read_csv('{f.as_posix()}', {cfg['csv_strict_options']})"
        header = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM {expr}").fetchall()]
        if header != list(o2n.keys()):
            stop(f"Schéma de l'export {eid} différent de la Phase 1 : {header}")
        n2o = {n: o for o, n in o2n.items()}
        nar_o = n2o[keys["narrative"]]
        cond = f'"{nar_o}" IS NOT NULL AND trim("{nar_o}") <> \'\''
        n_rows, n_nar = con.execute(f"SELECT COUNT(*), COUNT(*) FILTER (WHERE {cond}) FROM {expr}").fetchone()
        per_export.append({"export_id": eid, "n_rows": int(n_rows), "n_with_narrative": int(n_nar)})
        need = [keys["complaint_id"], keys["date_received"], keys["product"], keys["narrative"]]
        sel = ", ".join(f'"{n2o[n]}" AS "{n}"' for n in need)
        parts.append(con.execute(f"SELECT {eid} AS source_export_id, {sel} FROM {expr} WHERE {cond}").df())
    df = pd.concat(parts, ignore_index=True)
    parsed = pd.to_datetime(df[keys["date_received"]], format=date_fmt, errors="coerce")
    if parsed.isna().any():
        bad = df.loc[parsed.isna(), ["source_export_id", keys["complaint_id"], keys["date_received"]]]
        detail = "\n".join(f"  export {r.iloc[0]} | id {r.iloc[1]} | valeur brute {r.iloc[2]!r}"
                           for _, r in bad.head(20).iterrows())
        stop(f"{len(bad)} dates non convertibles avec le format Phase 1 {date_fmt} :\n{detail}")
    df["date_received"] = parsed
    df = df.rename(columns={keys["complaint_id"]: "complaint_id", keys["product"]: "product",
                            keys["narrative"]: "narrative_raw"})
    df["received_month"] = df["date_received"].dt.strftime("%Y-%m")
    n_narr = len(df)

    # --- 2. frozen mapping
    print("[2/5] Correspondance produits → services (figée)…", flush=True)
    p2s = mapping["product_to_service"]
    excl = {e["label"] for e in mapping.get("excluded", [])}
    lab = df["product"].value_counts().rename_axis("product").reset_index(name="n_narratives")
    lab["status"] = lab["product"].map(lambda p: "mapped" if p in p2s else ("excluded_frozen" if p in excl
                                                                            else "unknown_excluded"))
    df["service"] = df["product"].map(p2s)
    df = df[df["service"].notna()].copy()
    n_mapped = len(df)

    # --- 3. same cleaning and dedup as 2b
    print(f"[3/5] Nettoyage R1-R8 et dédoublonnage ({n_mapped:,} narratifs)…", flush=True)
    tok = {"date": p2["mask_tokens"]["date"], "generic": p2["mask_tokens"]["generic"], "amount": p2["amount_token"]}
    counts = dict.fromkeys(["R1_bytes_prefix", "R2_literal_escapes", "R3_dates", "R4_amounts",
                            "R5_glued_xseq_narratives", "R5_xseq", "R6_collapsed"], 0)
    df["text_clean"] = [clean(t, tok, counts) for t in df["narrative_raw"]]
    has_letter = df["text_clean"].map(lambda t: bool(re.search(r"[A-Za-z]", TOKENS.sub(" ", t))))
    counts["R8_dropped_no_letter"] = int((~has_letter).sum())
    df = df[has_letter]
    level = dd["conflict_level"]
    g = df.groupby("text_clean")[level].nunique()
    conflicts = set(g[g > 1].index)
    n_conf = int(df["text_clean"].isin(conflicts).sum())
    df = df[~df["text_clean"].isin(conflicts)]
    n_before = len(df)
    df = (df.sort_values(["date_received", "complaint_id"]).drop_duplicates("text_clean", keep="first"))
    n_keep_one = n_before - len(df)

    # --- 4. no text shared with 2026
    print("[4/5] Retrait des textes identiques à 2026…", flush=True)
    t2026 = set(pd.read_parquet(proc / "complaints_clean.parquet", columns=["text_clean"])["text_clean"])
    shared = df["text_clean"].isin(t2026)
    n_shared = int(shared.sum())
    df = df[~shared].copy()
    id2026 = set(pd.read_parquet(proc / "complaints_clean.parquet", columns=["complaint_id"])["complaint_id"])
    if df["complaint_id"].astype(str).isin(id2026).any():
        stop("Des identifiants de réclamation 2025 existent aussi dans les jeux 2026.")

    # --- 5. company masking with the unchanged 3a lexicon
    print("[5/5] Masquage [COMPANY] (lexique 3a inchangé) et écriture…", flush=True)
    mask, hits = make_masker(patterns, p3["company_mask"]["token"])
    df["text_company_masked"] = df["text_clean"].map(mask)
    df["n_company_tokens"] = df["text_company_masked"].str.count(re.escape(p3["company_mask"]["token"]))
    df["n_words_clean"] = df["text_clean"].str.split().str.len()
    df = df.sort_values("complaint_id").reset_index(drop=True)
    keep = ["complaint_id", "date_received", "received_month", "product", "service", "narrative_raw",
            "text_clean", "text_company_masked", "n_company_tokens", "n_words_clean"]
    out = proc / f"external_{label}.parquet"
    df[keep].to_parquet(out, index=False)
    write_json(proc / "MANIFEST_external.json", {
        "file": out.name, "rows": int(len(df)), "sha256": sha256(out), "label": label, "exports": ext["exports"],
        "_created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "_lexicon_sha256": sha256(lex_path), "_source_2026_sha256": manifest["all"]["sha256"]})

    rep = ROOT / "reports" / "phase3c"; rep.mkdir(parents=True, exist_ok=True)
    pe = pd.DataFrame(per_export); pe["pct_with_narrative"] = (100 * pe["n_with_narrative"] / pe["n_rows"]).round(2)
    pe.to_csv(rep / f"external_{label}_per_export.csv", index=False)
    lab.to_csv(rep / f"external_{label}_product_labels.csv", index=False)
    rules = pd.DataFrame([{"rule": r, "n_narratives": v} for r, v in counts.items()])
    tr = pd.read_parquet(proc / "train.parquet", columns=["service"])
    dist = pd.DataFrame({
        f"n_{label}": df["service"].value_counts(),
        f"pct_{label}": (100 * df["service"].value_counts(normalize=True)).round(2),
        "pct_train_2026": (100 * tr["service"].value_counts(normalize=True)).round(2)}).reset_index(names="service")
    dist.to_csv(rep / f"external_{label}_distribution.csv", index=False)
    funnel = pd.DataFrame([
        {"étape": "narratifs non vides", "lignes": n_narr},
        {"étape": "après correspondance figée", "lignes": n_mapped},
        {"étape": "après R8", "lignes": n_mapped - counts["R8_dropped_no_letter"]},
        {"étape": f"après conflits ({level})", "lignes": n_mapped - counts["R8_dropped_no_letter"] - n_conf},
        {"étape": "après conservation d'un exemplaire", "lignes": n_before - n_keep_one},
        {"étape": "après retrait des textes identiques à 2026", "lignes": len(df)}])
    months = df["received_month"].value_counts().sort_index().reset_index()
    months.columns = ["received_month", "n"]
    checklist = [
        ("Exports externes disjoints de 2026", "OK"),
        ("Schéma identique à la Phase 1 pour chaque export", "OK"),
        ("Dates converties avec le format de la Phase 1 (100 %)", "OK"),
        ("Aucun texte ni identifiant partagé avec 2026", "OK"),
        ("Lexique 3a réutilisé sans modification (nombre de motifs contrôlé, sha256 enregistré)", "OK"),
        ("Libellés produits inconnus de la correspondance figée",
         "aucun" if not (lab["status"] == "unknown_excluded").any()
         else f"{int(lab.loc[lab['status'] == 'unknown_excluded', 'n_narratives'].sum()):,} narratifs exclus — à examiner"),
    ]
    lines = [
        f"# Jeu de test externe {label} — Phase 3c-i", "",
        f"Généré le {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC par `src/data/build_external.py`. "
        "Aucun réapprentissage : règles 2b et lexique 3a appliqués tels quels.", "",
        "## 1. Exports lus", "", md_table(pe), "",
        "## 2. Libellés produits et correspondance figée", "", md_table(lab), "",
        "## 3. Entonnoir", "", md_table(funnel), "",
        "## 4. Règles de nettoyage (narratifs modifiés)", "", md_table(rules), "",
        "## 5. Répartition par service (externe vs entraînement 2026)", "", md_table(dist), "",
        "## 6. Répartition mensuelle", "", md_table(months), "",
        "## 7. Couverture [COMPANY]", "",
        f"- Narratifs avec au moins un `[COMPANY]` : {100 * (df['n_company_tokens'] > 0).mean():.2f} %.", "",
        "## 8. Critères de sortie de la 3c-i", "", "| Critère | Statut |", "|---|---|",
    ]
    lines += [f"| {c} | {s} |" for c, s in checklist]
    (ROOT / "reports" / f"phase3c_external_{label}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nJeu externe {label} : {len(df):,} narratifs ; textes identiques à 2026 retirés : {n_shared:,}")
    print(f"Rapport : {ROOT / 'reports' / f'phase3c_external_{label}.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
