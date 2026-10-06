"""Phase 2a — Text audit (measurement only, nothing is modified or deleted).

Scope (Phase 1 decisions): narratives received in analysis_window, products mapped by the frozen
config/label_mapping.yaml. Measures the real shapes of masks, dates and amounts, short texts, and the
effect of the validated dedup rule, so that Phase 2b cleaning rules rest on observed data.

Outputs: reports/phase2a/*.csv, reports/phase2a_text_audit.md
"""
from __future__ import annotations

from datetime import datetime, timezone

import duckdb
import pandas as pd
import yaml

from common import ROOT, load_config, read_json, stop
from profile_report import md_table

DATE_RE = r"[X0-9]{2}/[X0-9]{2}/[X0-9]{2,4}"
XSEQ_RE = r"\bX{2,}\b"
BRACE_RE = r"\{[^}]{0,40}\}"


def main() -> int:
    cfg = load_config()
    aw = cfg.get("analysis_window")
    if not aw:
        stop("analysis_window absent de config.yaml : Phase 1 non close.")
    mapping = yaml.safe_load((ROOT / "config" / "label_mapping.yaml").read_text(encoding="utf-8"))
    if not isinstance(mapping, dict) or mapping.get("status") != "frozen":
        stop("config/label_mapping.yaml n'est pas figé : Phase 1 non close.")
    cols = read_json(ROOT / cfg["paths"]["interim"] / "columns.json")
    k = {n: f'"{v}"' for n, v in cols["keys"].items() if v}
    nar_pq = (ROOT / cfg["paths"]["interim"] / "complaints_with_narrative.parquet").as_posix()

    out = ROOT / "reports" / "phase2a"
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.register("map_df", pd.DataFrame(list(mapping["product_to_service"].items()), columns=["product", "service"]))
    con.execute(f"""
        CREATE TABLE base AS
        SELECT n.{k['complaint_id']} AS complaint_id, n.{k['date_received']} AS date_received,
               n.received_month, n.{k['product']} AS product, m.service, n.{k['narrative']} AS narrative
        FROM read_parquet('{nar_pq}') n
        JOIN map_df m ON n.{k['product']} = m.product
        WHERE n.received_month BETWEEN '{aw['start']}' AND '{aw['end']}'
    """)
    n_base = con.execute("SELECT COUNT(*) FROM base").fetchone()[0]
    if n_base == 0:
        stop("Aucune ligne dans le périmètre (fenêtre × produits figés).")

    q = {}
    # A1 date-like patterns: shape (digits -> 9)
    q["A1_date_shapes"] = f"""
        SELECT regexp_replace(m, '[0-9]', '9', 'g') AS shape, COUNT(*) AS n_occurrences
        FROM (SELECT unnest(regexp_extract_all(narrative, '{DATE_RE}')) AS m FROM base)
        GROUP BY 1 ORDER BY 2 DESC LIMIT 30"""
    # A2 X-sequences outside date patterns: by length
    q["A2_xseq_lengths"] = f"""
        SELECT length(m) AS n_x, COUNT(*) AS n_occurrences
        FROM (SELECT unnest(regexp_extract_all(regexp_replace(narrative, '{DATE_RE}', ' ', 'g'), '{XSEQ_RE}')) AS m
              FROM base)
        GROUP BY 1 ORDER BY 2 DESC LIMIT 30"""
    # A3 brace patterns (amounts?) : shape (digits -> 9)
    q["A3_brace_shapes"] = f"""
        SELECT regexp_replace(m, '[0-9]', '9', 'g') AS shape, COUNT(*) AS n_occurrences
        FROM (SELECT unnest(regexp_extract_all(narrative, '{BRACE_RE}')) AS m FROM base)
        GROUP BY 1 ORDER BY 2 DESC LIMIT 30"""
    q["A4_pattern_coverage"] = f"""
        SELECT COUNT(*) AS n_narratives,
          ROUND(100.0 * AVG(CASE WHEN regexp_matches(narrative, '{DATE_RE}') THEN 1 ELSE 0 END), 2) AS pct_with_date_pattern,
          ROUND(100.0 * AVG(CASE WHEN regexp_matches(regexp_replace(narrative, '{DATE_RE}', ' ', 'g'), '{XSEQ_RE}') THEN 1 ELSE 0 END), 2) AS pct_with_other_xseq,
          ROUND(100.0 * AVG(CASE WHEN regexp_matches(narrative, '{BRACE_RE}') THEN 1 ELSE 0 END), 2) AS pct_with_brace
        FROM base"""
    # A5 lengths per service, raw words and words left once masks/dates/braces are removed
    con.execute(f"""
        CREATE TABLE lens AS
        SELECT complaint_id, service, narrative,
          len(string_split(trim(regexp_replace(narrative, '\\s+', ' ', 'g')), ' ')) AS n_words,
          len(list_filter(string_split(trim(regexp_replace(
              regexp_replace(regexp_replace(regexp_replace(narrative, '{DATE_RE}', ' ', 'g'), '{XSEQ_RE}', ' ', 'g'),
                             '{BRACE_RE}', ' ', 'g'), '\\s+', ' ', 'g')), ' '), x -> x <> '')) AS n_words_unmasked
        FROM base""")
    q["A5_length_by_service"] = """
        SELECT service, COUNT(*) AS n,
          MIN(n_words) AS min_words, ROUND(quantile_cont(n_words, 0.05), 1) AS p5,
          ROUND(median(n_words), 1) AS median, ROUND(quantile_cont(n_words, 0.95), 1) AS p95, MAX(n_words) AS max_words,
          COUNT(*) FILTER (WHERE n_words < 10) AS n_lt10, COUNT(*) FILTER (WHERE n_words < 20) AS n_lt20,
          COUNT(*) FILTER (WHERE n_words_unmasked = 0) AS n_only_masks
        FROM lens GROUP BY 1 ORDER BY n DESC"""
    q["A6_shortest_examples"] = """
        SELECT complaint_id, service, n_words, left(replace(narrative, chr(10), ' '), 200) AS narrative_200
        FROM lens ORDER BY n_words, complaint_id LIMIT 15"""
    # A7 dedup rule preview, product level (validated rule) and service level (information)
    q["A7_dedup_preview"] = """
        WITH g AS (SELECT narrative, COUNT(*) AS c, COUNT(DISTINCT product) AS np, COUNT(DISTINCT service) AS ns
                   FROM base GROUP BY 1)
        SELECT
          (SELECT COUNT(*) FROM base) AS n_rows_scope,
          COUNT(*) FILTER (WHERE c > 1)                     AS n_texts_duplicated,
          COALESCE(SUM(c) FILTER (WHERE c > 1), 0)          AS n_rows_duplicated,
          COUNT(*) FILTER (WHERE np > 1)                    AS n_texts_multi_product,
          COALESCE(SUM(c) FILTER (WHERE np > 1), 0)         AS n_rows_multi_product,
          COUNT(*) FILTER (WHERE ns > 1)                    AS n_texts_multi_service,
          COALESCE(SUM(c) FILTER (WHERE ns > 1), 0)         AS n_rows_multi_service,
          COUNT(*) FILTER (WHERE np = 1)                    AS n_rows_after_rule
        FROM g"""
    level = cfg.get("dedup_rule", {}).get("conflict_level", "product")
    if level not in ("product", "service"):
        stop(f"dedup_rule.conflict_level invalide : {level}")
    q["A8_after_rule_by_service"] = f"""
        WITH g AS (SELECT narrative, COUNT(DISTINCT {level}) AS nl FROM base GROUP BY 1),
        kept AS (SELECT b.* FROM base b JOIN g USING (narrative) WHERE g.nl = 1
                 QUALIFY row_number() OVER (PARTITION BY b.narrative ORDER BY b.date_received, b.complaint_id) = 1)
        SELECT service, COUNT(*) AS n_after_rule FROM kept GROUP BY 1 ORDER BY 2 DESC"""
    # A9 artefacts not captured by A1-A3 (added 2026-10-05 after the first 2a run)
    q["A9a_date_like_with_letters"] = r"""
        SELECT regexp_replace(m, '[0-9]', '9', 'g') AS shape, COUNT(*) AS n_occurrences
        FROM (SELECT unnest(regexp_extract_all(narrative, '[X0-9]{2}/[X0-9]{2}/[A-Za-z<>]*[a-z<>][A-Za-z<>]*')) AS m FROM base)
        GROUP BY 1 ORDER BY 2 DESC LIMIT 30"""
    q["A9b_angle_bracket_tokens"] = r"""
        SELECT regexp_replace(m, '[0-9]', '9', 'g') AS shape, COUNT(*) AS n_occurrences
        FROM (SELECT unnest(regexp_extract_all(narrative, '\S*[<>]\S*')) AS m FROM base)
        GROUP BY 1 ORDER BY 2 DESC LIMIT 30"""
    # SQL literals: quote doubled (''), no backslash escaping in DuckDB strings -> regexes passed verbatim to RE2
    q["A9c_artifact_coverage"] = r"""
        SELECT COUNT(*) AS n_narratives,
          COUNT(*) FILTER (WHERE regexp_matches(narrative, '^b[''"]'))                                 AS n_bytes_prefix,
          COUNT(*) FILTER (WHERE regexp_matches(narrative, '^b[''"]') AND regexp_matches(narrative, '[''"]\s*$'))
                                                                                                   AS n_bytes_prefix_and_quote_end,
          COUNT(*) FILTER (WHERE regexp_matches(narrative, '[X0-9]{2}/[X0-9]{2}/[A-Za-z<>]*[a-z<>][A-Za-z<>]*'))         AS n_with_date_letters,
          COUNT(*) FILTER (WHERE regexp_matches(narrative, '[<>]'))                                     AS n_with_angle_bracket,
          COUNT(*) FILTER (WHERE regexp_matches(narrative, '\\[nrtx]'))                                 AS n_with_literal_escape
        FROM base"""
    q["A9d_bytes_prefix_examples"] = r"""
        SELECT complaint_id, service, left(replace(narrative, chr(10), ' '), 120) AS start_120,
               right(replace(narrative, chr(10), ' '), 40) AS end_40
        FROM base WHERE regexp_matches(narrative, '^b[''"]') ORDER BY complaint_id LIMIT 10"""

    res = {}
    for name, sql in q.items():
        res[name] = con.execute(sql).df()
        res[name].to_csv(out / f"{name}.csv", index=False)
        print(f"[ok] {name} ({len(res[name])} lignes)")

    sp = cfg.get("phase2", {}).get("split", {})
    a8 = res["A8_after_rule_by_service"].copy()
    if sp:
        a8["train_approx"] = (a8["n_after_rule"] * sp["train"]).round().astype(int)
        a8["val_approx"] = (a8["n_after_rule"] * sp["val"]).round().astype(int)
        a8["test_approx"] = a8["n_after_rule"] - a8["train_approx"] - a8["val_approx"]

    d = res["A7_dedup_preview"].iloc[0]
    lines = [
        "# Audit du texte — Phase 2a",
        "",
        f"Généré le {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC par `src/data/audit_text.py`. Mesures uniquement : "
        "aucune ligne modifiée ni supprimée.",
        "",
        f"Périmètre : narratifs reçus de {aw['start']} à {aw['end']}, produits de `config/label_mapping.yaml` (figé) — "
        f"**{n_base:,} lignes**.",
        "",
        "Motifs mesurés (expressions régulières RE2) :",
        f"- date : `{DATE_RE}` ; séquence de X hors date : `{XSEQ_RE}` ; accolades : `{BRACE_RE}`.",
        "",
        "## A4 — Couverture des motifs", "", md_table(res["A4_pattern_coverage"]), "",
        "## A1 — Formes des motifs de date (chiffres → 9)", "", md_table(res["A1_date_shapes"]), "",
        "## A2 — Séquences de X hors dates (longueur)", "", md_table(res["A2_xseq_lengths"]), "",
        "## A3 — Formes entre accolades (chiffres → 9)", "", md_table(res["A3_brace_shapes"]), "",
        "## A5 — Longueur par service", "",
        "`n_only_masks` = narratifs sans aucun mot une fois dates, X et accolades retirés.", "",
        md_table(res["A5_length_by_service"]), "",
        "## A6 — 15 narratifs les plus courts (200 premiers caractères)", "", md_table(res["A6_shortest_examples"]), "",
        "## A7 — Effet de la règle de dédoublonnage dans le périmètre", "",
        md_table(res["A7_dedup_preview"]), "",
        "La règle validée porte sur les **produits** (Phase 1 : 43 textes / 245 lignes, mesurés hors périmètre, "
        "Credit reporting et août inclus). Les colonnes `multi_service` indiquent combien de ces conflits subsistent "
        "si deux produits du même service (ex. Credit card / Prepaid card) ne sont pas considérés comme un conflit.",
        "",
        f"## A8 — Effectifs par service après la règle (conflits au niveau `{level}`), et découpage attendu", "",
        md_table(a8), "",
        f"Lignes conservées après la règle : **{int(a8['n_after_rule'].sum()):,}** sur {int(d['n_rows_scope']):,}.",
        "",
        "## A9 — Artefacts non captés par A1 à A3", "",
        "### A9c — Couverture", "", md_table(res["A9c_artifact_coverage"]), "",
        "### A9a — Formes date + lettres (chiffres → 9)", "", md_table(res["A9a_date_like_with_letters"]), "",
        "### A9b — Jetons contenant < ou > (chiffres → 9)", "", md_table(res["A9b_angle_bracket_tokens"]), "",
        "### A9d — Narratifs commençant par b' ou b\" (10 exemples)", "", md_table(res["A9d_bytes_prefix_examples"]), "",
        "## Décisions attendues pour la Phase 2b", "",
        "1. Expressions régulières définitives des jetons `[DATE]` et `[REDACTED]` (à partir de A1 et A2).",
        "2. Traitement des formes entre accolades (A3).",
        "3. Conflit au niveau produit (règle validée) ou au niveau service (A7).",
        "4. Narratifs sans aucun mot hors masques (A5, `n_only_masks`).",
    ]
    (ROOT / "reports" / "phase2a_text_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nRapport : {ROOT / 'reports' / 'phase2a_text_audit.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
