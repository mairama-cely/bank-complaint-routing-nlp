"""Phase 2b — Clean narratives, deduplicate on cleaned text, stratified train/val/test split.

Rules validated by the user on 2026-10-05 (from the 2a audit), applied in this order:
  R1 bytes artefact  : leading b' / b" removed; matching trailing quote removed only if present
  R2 literal escapes : \\n \\r \\t (as text) -> space
  R3 dates           : [X0-9]{1,2}/[X0-9]{1,2}/(year>|scrub>|[X0-9]{2,4}) -> [DATE]
  R4 amounts         : {$...} and {>= $...} -> [AMOUNT]
  R5 X-sequences     : X{2,} (no word boundary required) -> [REDACTED]
  R6 consecutive identical tokens collapsed
  R7 whitespace normalised
  R8 rows with no letter outside tokens dropped
Then: dedup on cleaned text (conflict level from config), stratified split by service (seed from config).
Language: measured only (stopword heuristic), never filtered.

Outputs: data/processed/*.parquet, data/processed/MANIFEST.json, reports/phase2b/*.csv, reports/phase2b_cleaning.md
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

import duckdb
import numpy as np
import pandas as pd
import yaml

from common import ROOT, load_config, read_json, stop, write_json
from profile_report import md_table

R1 = re.compile(r"^b(['\"])")
R2 = re.compile(r"\\[nrt]")
R3 = re.compile(r"[X0-9]{1,2}/[X0-9]{1,2}/(?:year>|scrub>|[X0-9]{2,4})")
R4 = re.compile(r"\{\s*(?:>=\s*)?\$[0-9.,X]*\s*\}")
R5 = re.compile(r"X{2,}")
R5_GLUED = re.compile(r"(?<=[A-WYZa-z])X{2,}|X{2,}(?=[A-WYZa-z])")
R6 = re.compile(r"(\[(?:REDACTED|DATE|AMOUNT)\])(?:\s*\1)+")
R7 = re.compile(r"\s+")
TOKENS = re.compile(r"\[(?:REDACTED|DATE|AMOUNT)\]")
WORD = re.compile(r"[a-z']+")
EN_STOP = set("the a an and or but to of in on at for with from by is was were are be been have has had i my me "
              "you your it this that they them their not no do did does as so if we our he she his her".split())
ES_STOP = set("el la los las de del y que en un una por para con no se su sus mi es lo al pero como".split())


def clean(text: str, tok: dict, counts: dict) -> str:
    t = text
    m = R1.match(t)
    if m:
        q = m.group(1)
        t = t[2:]
        if t.rstrip().endswith(q):
            t = t.rstrip()[:-1]
        counts["R1_bytes_prefix"] += 1
    t2 = R2.sub(" ", t); counts["R2_literal_escapes"] += t2 != t; t = t2
    t2 = R3.sub(f" {tok['date']} ", t); counts["R3_dates"] += t2 != t; t = t2
    t2 = R4.sub(f" {tok['amount']} ", t); counts["R4_amounts"] += t2 != t; t = t2
    if R5_GLUED.search(t):
        counts["R5_glued_xseq_narratives"] += 1
    t2 = R5.sub(f" {tok['generic']} ", t); counts["R5_xseq"] += t2 != t; t = t2
    t2 = R6.sub(r"\1", t); counts["R6_collapsed"] += t2 != t; t = t2
    return R7.sub(" ", t).strip()


def lang_flags(text: str, min_words: int, max_en: float) -> tuple[float, float, str]:
    words = WORD.findall(TOKENS.sub(" ", text.lower()))
    if len(words) < min_words:
        return np.nan, np.nan, "too_short_to_judge"
    en = sum(w in EN_STOP for w in words) / len(words)
    es = sum(w in ES_STOP for w in words) / len(words)
    if en >= max_en:
        return en, es, "english_likely"
    return en, es, "spanish_suspect" if es > en else "non_english_suspect"


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(8 * 1024**2), b""):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    cfg = load_config()
    aw, p2, dd = cfg.get("analysis_window"), cfg.get("phase2"), cfg.get("dedup_rule")
    if not (aw and p2 and dd):
        stop("analysis_window, phase2 ou dedup_rule absent de config.yaml.")
    mapping = yaml.safe_load((ROOT / "config" / "label_mapping.yaml").read_text(encoding="utf-8"))
    if not isinstance(mapping, dict) or mapping.get("status") != "frozen":
        stop("config/label_mapping.yaml n'est pas figé.")
    level = dd["conflict_level"]
    if level not in ("product", "service") or p2.get("dedup_on") != "cleaned_text":
        stop(f"Paramètres de dédoublonnage inattendus : conflict_level={level}, dedup_on={p2.get('dedup_on')}")
    sp = p2["split"]
    if abs(sp["train"] + sp["val"] + sp["test"] - 1) > 1e-9:
        stop("Les proportions du découpage ne somment pas à 1.")
    tok = {"date": p2["mask_tokens"]["date"], "generic": p2["mask_tokens"]["generic"], "amount": p2["amount_token"]}

    cols = read_json(ROOT / cfg["paths"]["interim"] / "columns.json")
    k = {n: f'"{v}"' for n, v in cols["keys"].items() if v}
    nar_pq = (ROOT / cfg["paths"]["interim"] / "complaints_with_narrative.parquet").as_posix()
    con = duckdb.connect()
    con.register("map_df", pd.DataFrame(list(mapping["product_to_service"].items()), columns=["product", "service"]))
    df = con.execute(f"""
        SELECT CAST(n.{k['complaint_id']} AS VARCHAR) AS complaint_id, n.{k['date_received']} AS date_received,
               n.received_month, n.{k['product']} AS product, m.service, n.{k['narrative']} AS narrative_raw
        FROM read_parquet('{nar_pq}') n JOIN map_df m ON n.{k['product']} = m.product
        WHERE n.received_month BETWEEN '{aw['start']}' AND '{aw['end']}'
        ORDER BY complaint_id""").df()
    n_scope = len(df)
    print(f"Périmètre : {n_scope:,} lignes")

    # --- cleaning R1-R7
    counts = dict.fromkeys(["R1_bytes_prefix", "R2_literal_escapes", "R3_dates", "R4_amounts",
                            "R5_glued_xseq_narratives", "R5_xseq", "R6_collapsed"], 0)
    df["text_clean"] = [clean(t, tok, counts) for t in df["narrative_raw"]]
    # --- R8 drop rows without any letter outside tokens
    has_letter = df["text_clean"].map(lambda t: bool(re.search(r"[A-Za-z]", TOKENS.sub(" ", t))))
    r8 = df.loc[~has_letter, ["complaint_id", "service", "narrative_raw"]]
    counts["R8_dropped_no_letter"] = int((~has_letter).sum())
    df = df[has_letter].copy()
    print("Règles :", counts)

    # --- dedup on cleaned text
    g = df.groupby("text_clean")[level].nunique()
    conflict_texts = set(g[g > 1].index)
    n_conflict_rows = int(df["text_clean"].isin(conflict_texts).sum())
    df = df[~df["text_clean"].isin(conflict_texts)]
    n_before_keep_one = len(df)
    df = (df.sort_values(["date_received", "complaint_id"])
            .drop_duplicates("text_clean", keep="first")
            .sort_values("complaint_id").reset_index(drop=True))
    dedup = {"n_after_R8": int(has_letter.sum()), "conflict_texts": len(conflict_texts),
             "conflict_rows_dropped": n_conflict_rows, "keep_one_rows_dropped": n_before_keep_one - len(df),
             "n_after_dedup": int(len(df))}
    print("Dédoublonnage :", dedup)

    # --- language measurement (no filtering)
    lc = p2["language_check"]
    lang = [lang_flags(t, lc["min_words"], lc["max_english_stopword_ratio"]) for t in df["text_clean"]]
    df["en_stop_ratio"] = [x[0] for x in lang]
    df["es_stop_ratio"] = [x[1] for x in lang]
    df["lang_flag"] = [x[2] for x in lang]
    df["n_words_clean"] = df["text_clean"].str.split().str.len()

    # --- stratified split, deterministic
    rng = np.random.default_rng(sp["seed"])
    df["split"] = ""
    for svc in sorted(df["service"].unique()):
        idx = df.index[df["service"] == svc].to_numpy()          # already sorted by complaint_id
        idx = idx[rng.permutation(len(idx))]
        n = len(idx); n_tr = int(round(n * sp["train"])); n_va = int(round(n * sp["val"]))
        df.loc[idx[:n_tr], "split"] = "train"
        df.loc[idx[n_tr:n_tr + n_va], "split"] = "val"
        df.loc[idx[n_tr + n_va:], "split"] = "test"

    # --- checks
    split_tab = pd.crosstab(df["service"], df["split"])[["train", "val", "test"]]
    split_tab["total"] = split_tab.sum(axis=1)
    prop = split_tab[["train", "val", "test"]].div(split_tab["total"], axis=0)
    max_dev = float((prop - pd.Series({"train": sp["train"], "val": sp["val"], "test": sp["test"]})).abs().max().max())
    leak_text = int(df.groupby("text_clean")["split"].nunique().gt(1).sum())
    leak_id = int(df.groupby("complaint_id")["split"].nunique().gt(1).sum())
    tok_left = int(df["text_clean"].str.contains(r"X{2,}|year>|scrub>", regex=True).sum())

    # --- outputs
    proc = ROOT / "data" / "processed"; proc.mkdir(parents=True, exist_ok=True)
    rep = ROOT / "reports" / "phase2b"; rep.mkdir(parents=True, exist_ok=True)
    keep_cols = ["complaint_id", "date_received", "received_month", "product", "service", "narrative_raw",
                 "text_clean", "n_words_clean", "lang_flag", "en_stop_ratio", "es_stop_ratio", "split"]
    files = {"all": proc / "complaints_clean.parquet"}
    df[keep_cols].to_parquet(files["all"], index=False)
    for s in ("train", "val", "test"):
        files[s] = proc / f"{s}.parquet"
        df.loc[df["split"] == s, keep_cols].to_parquet(files[s], index=False)
    manifest = {name: {"file": f.name, "rows": int(len(df) if name == "all" else (df["split"] == name).sum()),
                       "sha256": sha256(f)} for name, f in files.items()}
    manifest["_created_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest["_config"] = {"split": sp, "dedup_rule": dd, "tokens": tok}
    write_json(proc / "MANIFEST.json", manifest)

    rules_df = pd.DataFrame([{"rule": r, "n_narratives": v} for r, v in counts.items()])
    rules_df.to_csv(rep / "rules_counts.csv", index=False)
    split_tab.reset_index().to_csv(rep / "split_by_service.csv", index=False)
    lang_tab = pd.crosstab(df["service"], df["lang_flag"]).reset_index()
    lang_tab.to_csv(rep / "language_by_service.csv", index=False)
    len_tab = df.groupby("service")["n_words_clean"].describe(percentiles=[.05, .5, .95]).round(1).reset_index()
    len_tab.to_csv(rep / "length_clean_by_service.csv", index=False)
    lang_ex = (df[df["lang_flag"].isin(["spanish_suspect", "non_english_suspect"])]
               .assign(text_150=lambda d: d["text_clean"].str[:150])
               [["complaint_id", "service", "lang_flag", "en_stop_ratio", "text_150"]].head(15))
    clean_ex = (df[df["narrative_raw"] != df["text_clean"]].head(5)
                .assign(raw_150=lambda d: d["narrative_raw"].str.replace("\n", " ").str[:150],
                        clean_150=lambda d: d["text_clean"].str[:150])[["complaint_id", "raw_150", "clean_150"]])

    a8_path = ROOT / "reports" / "phase2a" / "A8_after_rule_by_service.csv"
    a8_total = int(pd.read_csv(a8_path)["n_after_rule"].sum()) if a8_path.exists() else None
    thr = cfg["min_narratives_per_class"]
    checklist = [
        ("Règles R1 à R8 appliquées, comptées par règle", "OK"),
        ("Aucun motif résiduel (X{2,}, year>, scrub>) dans le texte nettoyé", "OK" if tok_left == 0 else f"KO ({tok_left})"),
        ("Dédoublonnage sur texte nettoyé : aucun texte partagé entre jeux", "OK" if leak_text == 0 else f"KO ({leak_text})"),
        ("Aucun identifiant partagé entre jeux", "OK" if leak_id == 0 else f"KO ({leak_id})"),
        (f"Stratification : écart max aux proportions cibles ≤ 0,5 point (observé {max_dev * 100:.3f})",
         "OK" if max_dev <= 0.005 else "KO"),
        (f"Chaque service ≥ {thr} narratifs après nettoyage", "OK" if (split_tab['total'] >= thr).all() else "KO"),
        ("Jeux écrits avec sha256 (data/processed/MANIFEST.json)", "OK"),
        ("Langue mesurée (heuristique, sans filtrage)", "OK"),
    ]
    lines = [
        "# Nettoyage, dédoublonnage et découpage — Phase 2b", "",
        f"Généré le {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC par `src/data/clean_split.py`.", "",
        f"Périmètre : {aw['start']} → {aw['end']}, correspondance figée — **{n_scope:,} lignes** en entrée.", "",
        "## 1. Narratifs modifiés par règle", "",
        "`R5_glued_xseq_narratives` = narratifs contenant une séquence de X collée à une lettre (remplacée par R5, "
        "faute de séparateur). `R8_dropped_no_letter` = lignes supprimées.", "",
        md_table(rules_df), "",
        "### Lignes supprimées par R8", "", md_table(r8.assign(narrative_raw=r8["narrative_raw"].str[:120])), "",
        "### 5 exemples avant / après", "", md_table(clean_ex), "",
        "## 2. Dédoublonnage sur texte nettoyé", "",
        f"Niveau de conflit : `{level}`. Conservation : plus ancienne date de réception, puis plus petit identifiant.", "",
        md_table(pd.DataFrame([dedup])), "",
        (f"Pour comparaison, l'audit 2a (texte brut, niveau `{level}`) conservait {a8_total:,} lignes."
         if a8_total is not None else "Audit 2a (A8) introuvable : pas de comparaison."), "",
        "## 3. Découpage stratifié par service", "",
        f"Proportions cibles {sp['train']}/{sp['val']}/{sp['test']}, graine {sp['seed']}.", "",
        md_table(split_tab.reset_index()), "",
        "## 4. Longueur après nettoyage (mots)", "", md_table(len_tab), "",
        "## 5. Langue (heuristique, aucun filtrage)", "",
        f"Méthode : part des mots outils anglais parmi les mots du texte (≥ {lc['min_words']} mots). Sous "
        f"{lc['max_english_stopword_ratio']}, le texte est signalé ; `spanish_suspect` si la part de mots outils "
        "espagnols est supérieure. Heuristique non validée : les signalements sont des indices, pas des étiquettes.", "",
        md_table(lang_tab), "", "### Exemples signalés (15 premiers)", "", md_table(lang_ex), "",
        "## 6. Critères de sortie de la Phase 2b", "", "| Critère | Statut |", "|---|---|",
    ]
    lines += [f"| {c} | {s} |" for c, s in checklist]
    (ROOT / "reports" / "phase2b_cleaning.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\nCRITÈRES DE SORTIE PHASE 2B")
    for c, s in checklist:
        print(f"  [{s:^9}] {c}")
    print(f"\nRapport : {ROOT / 'reports' / 'phase2b_cleaning.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
