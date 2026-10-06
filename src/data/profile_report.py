"""T7 + T10 + T11 — Run sql/01_profiling.sql, save every result to reports/tables/,
derive the recommended time window (Q3), draft config/label_mapping.yaml (Q4) and write
reports/phase1_profile.md with the exit-criteria checklist.

Importable by the notebook: connect(), load_queries().
"""
from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from string import Template

import duckdb
import pandas as pd
import yaml

from common import ROOT, load_config, p, read_json, selected_exports, stop

# Keyword rules applied to REAL product labels (lower-case). First match wins.
# Output is a DRAFT: the user validates and freezes it.
RULES = [
    ("excluded", r"credit report", "Bureaux de crédit US : pas d'équivalent direct (cadrage §2)"),
    ("Comptes & Dépôts", r"checking|savings|bank account", None),
    ("Monétique", r"credit card|prepaid", None),
    ("Transferts & Paiements", r"money transfer|virtual currency|money service", None),
    ("Crédit immobilier", r"mortgage", None),
    ("Crédits aux particuliers", r"vehicle|payday|personal loan|student loan|consumer loan|title loan|advance loan", None),
    ("Recouvrement", r"debt collection", None),
    # User decision 2026-10-05: "Debt or credit management" attached to Recouvrement.
    ("Recouvrement", r"debt or credit management", None),
]


def connect() -> duckdb.DuckDBPyConnection:
    cfg = load_config()
    interim = ROOT / cfg["paths"]["interim"]
    for f in ("complaints_all.parquet", "complaints_with_narrative.parquet"):
        if not (interim / f).exists():
            stop(f"{f} absent : exécuter build_interim.py")
    con = duckdb.connect()
    con.execute(f"CREATE VIEW all_c AS SELECT * FROM read_parquet('{(interim / 'complaints_all.parquet').as_posix()}')")
    con.execute(f"CREATE VIEW narr_c AS SELECT * FROM read_parquet('{(interim / 'complaints_with_narrative.parquet').as_posix()}')")
    return con


def load_queries() -> dict[str, str]:
    cfg = load_config()
    cols = read_json(ROOT / cfg["paths"]["interim"] / "columns.json")
    if cols is None:
        stop("data/interim/columns.json absent : exécuter build_interim.py")
    k = cols["keys"]
    subs = {name: (f'"{v}"' if v else "NULL") for name, v in k.items()}
    text = Template((ROOT / "sql" / "01_profiling.sql").read_text(encoding="utf-8")).substitute(subs)
    queries = {}
    for block in re.split(r"^-- name: ", text, flags=re.M)[1:]:
        name, body = block.split("\n", 1)
        queries[name.strip()] = body.strip().rstrip(";")
    return queries


def md_table(df: pd.DataFrame, max_rows: int = 60) -> str:
    if df.empty:
        return "_(aucune ligne)_"
    d = df.head(max_rows).astype(str)
    out = ["| " + " | ".join(d.columns) + " |", "|" + "---|" * len(d.columns)]
    out += ["| " + " | ".join(v.replace("|", "\\|") for v in row) + " |" for row in d.values]
    if len(df) > max_rows:
        out.append(f"\n_{len(df) - max_rows} lignes supplémentaires dans reports/tables/_")
    return "\n".join(out)


def recommend_window(q3: pd.DataFrame, min_ratio: float) -> dict:
    """Longest trailing run of months whose set of product labels equals the last retained month's set.

    Months whose narrative volume is below min_ratio x median monthly volume are excluded first
    (rule decided 2026-10-05 after a 1-narrative month produced a degenerate 1-month window).
    """
    totals = q3.groupby("received_month")["n_narratives"].sum().sort_index()
    median = float(totals.median())
    floor = min_ratio * median
    low = {m: int(v) for m, v in totals.items() if v < floor}
    kept = q3[~q3["received_month"].isin(low)]
    sets = kept.groupby("received_month")["product"].apply(lambda s: frozenset(s.dropna())).sort_index()
    months = list(sets.index)
    if not months:
        stop("Aucun mois au-dessus du seuil de volume : fenêtre impossible à déterminer.")
    last = sets.iloc[-1]
    start = len(months) - 1
    while start > 0 and sets.iloc[start - 1] == last:
        start -= 1
    changes = []
    for i in range(1, len(months)):
        if sets.iloc[i] != sets.iloc[i - 1]:
            changes.append({"month": months[i],
                            "added": sorted(sets.iloc[i] - sets.iloc[i - 1]),
                            "removed": sorted(sets.iloc[i - 1] - sets.iloc[i])})
    return {"months_observed": list(totals.index), "monthly_totals": {m: int(v) for m, v in totals.items()},
            "median": median, "floor": floor, "min_ratio": min_ratio, "excluded_low_volume": low,
            "window_start": months[start], "window_end": months[-1],
            "n_months": len(months) - start, "label_set_changes": changes}


def draft_mapping(q4: pd.DataFrame, services: list[str], threshold: int) -> dict:
    by_service = {s: {"n_narratives": 0, "products": []} for s in services}
    excluded = []
    for _, r in q4.iterrows():
        label, n = r["product"], int(r["n_narratives"])
        target, reason = None, None
        for svc, pattern, why in RULES:
            if label is not None and re.search(pattern, str(label).lower()):
                target, reason = svc, why
                break
        if target is None:
            excluded.append({"label": label, "n_narratives": n, "status": "draft",
                             "reason": "Aucune règle ne correspond — à revoir manuellement"})
        elif target == "excluded":
            excluded.append({"label": label, "n_narratives": n, "status": "draft", "reason": reason})
        else:
            by_service[target]["products"].append({"label": label, "n_narratives": n, "status": "draft"})
            by_service[target]["n_narratives"] += n
    for s in by_service.values():
        s["below_threshold"] = s["n_narratives"] < threshold
    return {"status": "draft",
            "note": "Brouillon généré automatiquement à partir des libellés réels (Q4). À valider et figer par l'utilisatrice.",
            "counts_scope": "tous les narratifs des exports sélectionnés, sans restriction à la fenêtre recommandée",
            "min_narratives_per_class": threshold,
            "services": by_service, "excluded": excluded}


def main() -> int:
    cfg = load_config()
    reports, tables = p(cfg, "reports"), p(cfg, "tables")
    con, queries = connect(), load_queries()

    res = {}
    for name, q in queries.items():
        res[name] = con.execute(q).df()
        res[name].to_csv(tables / f"{name}.csv", index=False)
        print(f"[ok] {name} ({len(res[name])} lignes)")

    window = recommend_window(res["Q3"], cfg["window_min_volume_ratio"])
    threshold = cfg["min_narratives_per_class"]
    mapping = draft_mapping(res["Q4_product"], cfg["target_services"], threshold)
    # A frozen label_mapping.yaml is never overwritten: the draft goes to label_mapping.draft.yaml instead.
    frozen_path = ROOT / "config" / "label_mapping.yaml"
    existing = yaml.safe_load(frozen_path.read_text(encoding="utf-8")) if frozen_path.exists() else None
    frozen = existing if isinstance(existing, dict) and existing.get("status") == "frozen" else None
    draft_path = ROOT / "config" / ("label_mapping.draft.yaml" if frozen else "label_mapping.yaml")
    draft_path.write_text(
        "# BROUILLON — status: draft. Ne pas utiliser avant validation.\n"
        + yaml.safe_dump(mapping, allow_unicode=True, sort_keys=False), encoding="utf-8")

    # window-restricted counts per service (informative)
    wq = res["Q3"][(res["Q3"]["received_month"] >= window["window_start"])
                   & (res["Q3"]["received_month"] <= window["window_end"])]
    win_counts = wq.groupby("product")["n_narratives"].sum()
    svc_rows = []
    for svc, v in mapping["services"].items():
        n_win = int(sum(win_counts.get(pr["label"], 0) for pr in v["products"]))
        svc_rows.append({"service": svc, "n_narratives_all": v["n_narratives"], "n_narratives_window": n_win,
                         "products": "; ".join(str(pr["label"]) for pr in v["products"]) or "—",
                         "seuil_atteint_all": "oui" if not v["below_threshold"] else "NON",
                         "seuil_atteint_window": "oui" if n_win >= threshold else "NON"})
    svc_df = pd.DataFrame(svc_rows)

    # exit criteria
    probe = pd.read_csv(reports / "source_probe.csv")
    sel = [e["id"] for e in selected_exports(cfg)]
    manifest = read_json(ROOT / cfg["paths"]["raw"] / "MANIFEST.json", default={})
    inventory = pd.read_csv(reports / "local_inventory.csv")
    inv_sel = inventory[inventory["selected"]]
    dups = int(res["Q5_across_exports"].iloc[0, 0]) + int(res["Q5_within_export"]["n_duplicated_ids"].sum())
    txt_dups = int(res["Q6"]["n_texts_duplicated"].iloc[0])
    txt_conflicts = int(res["Q6b"]["n_texts_multi_product"].iloc[0])
    all_ok = all(r["seuil_atteint_window"] == "oui" for r in svc_rows)

    # validated decisions (config.yaml / frozen mapping) turn "À décider" into OK, or flag a mismatch
    aw = cfg.get("analysis_window") or {}
    if not aw:
        window_status = "À décider"
    elif (aw.get("start"), aw.get("end")) == (window["window_start"], window["window_end"]):
        window_status = "OK"
    else:
        window_status = f"ÉCART (config : {aw.get('start')} → {aw.get('end')})"
    dedup = cfg.get("dedup_rule")
    dedup_status = "OK" if (dups == 0 and txt_dups == 0) or (dups == 0 and dedup) else "À décider"
    observed = set(res["Q4_product"]["product"].dropna())
    if frozen is None:
        mapping_status = "À décider"
    else:
        covered = set(frozen.get("product_to_service", {})) | {e["label"] for e in frozen.get("excluded", [])}
        mapping_status = "OK" if observed <= covered else f"KO (produits non couverts : {sorted(observed - covered)})"
    checklist = [
        ("source_probe.csv complet (21 URL, sélection en HTTP 200)",
         "OK" if len(probe) == 21 and (probe[probe["selected"]]["http_status"].astype(str) == "200").all() else "KO"),
        ("MANIFEST.json avec sha256 pour chaque export sélectionné (empreinte des CSV locaux, pas des zip CFPB)",
         "OK" if all(str(i) in manifest and manifest[str(i)].get("sha256") for i in sel) else "KO"),
        ("Format interne et schéma documentés",
         "OK" if (inv_sel["detected_format"] == "csv").all() and (ROOT / "docs" / "data_dictionary.md").exists() else "KO"),
        ("Taux de narratifs mesuré (global, export, produit)", "OK"),
        (f"Stabilité de la taxonomie évaluée — fenêtre recommandée {window['window_start']} → {window['window_end']}",
         window_status),
        (f"Doublons contrôlés (id : {dups} ; textes identiques : {txt_dups} ; dont multi-produits : {txt_conflicts})",
         dedup_status),
        (f"Effectifs par service ≥ {threshold} dans la fenêtre recommandée", "OK" if all_ok else "KO"),
        ("Correspondance config/label_mapping.yaml figée et couvrant tous les produits observés", mapping_status),
    ]

    g = res["Q2_global"].iloc[0]
    lines = [
        "# Rapport de profilage — Phase 1",
        "",
        f"Généré le {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC par `src/data/profile_report.py`. "
        "Chiffres observés uniquement, aucune interprétation de modélisation.",
        "",
        "## 1. Sources sondées",
        "",
        md_table(probe[["id", "selected", "http_status", "content_length_mb", "last_modified"]]),
        "",
        "## 2. Fichiers locaux (téléchargement manuel, zip non conservés)",
        "",
        md_table(inventory[["id", "selected", "file", "present", "size_mb", "sha256"]]),
        "",
        "## 3. Format et schéma réels",
        "",
        md_table(inventory[["id", "selected", "detected_format", "n_header_fields"]]),
        "",
        "Schéma complet : `docs/data_dictionary.md`. Options de lecture CSV : `reports/read_log.json`.",
        "",
        "## 4. Chiffres clés",
        "",
        f"- Lignes totales : **{int(g['n_rows']):,}** ; avec narratif : **{int(g['n_with_narrative']):,}** "
        f"({g['pct_with_narrative']} %).",
        "",
        "### Q1 — Lignes et dates par export", "", md_table(res["Q1"]), "",
        "### Q2 — Taux de narratifs par export", "", md_table(res["Q2_by_export"]), "",
        "### Q2 — Taux de narratifs par produit", "", md_table(res["Q2_by_product"]), "",
        "### Q4 — Produits (lignes avec narratif)", "", md_table(res["Q4_product"]), "",
        "Produit × sous-produit : `reports/tables/Q4_product_subproduct.csv`.", "",
        "### Q5 — Doublons d'identifiant", "",
        f"- Identifiants présents dans plusieurs exports : **{int(res['Q5_across_exports'].iloc[0, 0]):,}**", "",
        md_table(res["Q5_within_export"]), "",
        "### Q6 — Doublons exacts de texte", "", md_table(res["Q6"]), "",
        "### Q6b — Textes dupliqués portant des produits différents", "", md_table(res["Q6b"]), "",
        "### Q7 — Longueur des narratifs (mots)", "", md_table(res["Q7"]), "",
        "### Q8 — Masques XXXX", "", md_table(res["Q8"]), "",
        "### Q9 — Credit reporting", "", md_table(res["Q9"]), "",
        "## 5. Stabilité de la taxonomie (Q3) et fenêtre recommandée",
        "",
        f"Mois observés : {window['months_observed'][0]} → {window['months_observed'][-1]} "
        f"({len(window['months_observed'])} mois).",
        "",
        "Règle appliquée (décidée le 2026-10-05) : (1) exclure les mois dont le volume de narratifs est inférieur à "
        f"{window['min_ratio']:.0%} du volume mensuel médian ({window['median']:,.0f} → seuil {window['floor']:,.0f}) ; "
        "(2) retenir la plus longue séquence finale de mois dont l'ensemble des libellés produit est identique "
        "à celui du dernier mois retenu.",
        "",
        "Volume de narratifs par mois : "
        + " ; ".join(f"{m} = {v:,}" for m, v in window["monthly_totals"].items()) + ".",
        "",
        "Mois exclus pour volume insuffisant : "
        + (", ".join(f"{m} ({v:,} narratif(s))" for m, v in window["excluded_low_volume"].items()) or "aucun") + ".",
        "",
        f"**Fenêtre recommandée : {window['window_start']} → {window['window_end']} ({window['n_months']} mois).**",
        "",
        "Changements d'ensemble de libellés d'un mois à l'autre :",
        "",
    ]
    lines += ([f"- {c['month']} : ajoutés {c['added'] or '—'} ; retirés {c['removed'] or '—'}"
               for c in window["label_set_changes"]] or ["- aucun changement"])
    lines += [
        "",
        "Détail produit × mois : `reports/tables/Q3.csv` et `reports/figures/heatmap_product_month.png`.",
        "",
        "## 6. Effectifs par service candidat (brouillon de correspondance)",
        "",
        md_table(svc_df),
        "",
        "Produits exclus ou non classés : voir `config/label_mapping.yaml` (section `excluded`).",
        "",
        "## 7. Critères de sortie de la Phase 1",
        "",
        "| Critère | Statut |",
        "|---|---|",
    ]
    lines += [f"| {c} | {s} |" for c, s in checklist]
    pending = [c for c, st in checklist if st != "OK"]
    lines += ["", "## 8. Décisions", ""]
    if aw:
        lines.append(f"- Fenêtre validée (config.yaml) : {aw.get('start')} → {aw.get('end')}.")
    if dedup:
        lines.append(f"- Règle de dédoublonnage validée (config.yaml, appliquée en Phase 2) : {dedup}.")
    if frozen:
        lines.append(f"- Correspondance figée le {frozen.get('frozen_on')} : `config/label_mapping.yaml`.")
        lines += [f"  - {d}" for d in frozen.get("decisions", [])]
    lines += ["", "Critères restant à traiter : " + ("; ".join(pending) if pending else "aucun — Phase 1 close.")]
    (reports / "phase1_profile.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\nCRITÈRES DE SORTIE")
    for c, s in checklist:
        print(f"  [{s:^9}] {c}")
    print(f"\nRapport : {reports / 'phase1_profile.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
