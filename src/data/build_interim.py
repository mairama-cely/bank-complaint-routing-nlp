"""T6 + T9 — Read the CSVs in data/raw/ with DuckDB (all_varchar), check schema consistency,
normalise column names, type date columns only when 100 % convert, write interim parquet,
generate docs/data_dictionary.md.

Outputs:
  data/interim/complaints_all.parquet
  data/interim/complaints_with_narrative.parquet
  data/interim/columns.json          (real column names resolved from the data)
  reports/read_log.json              (CSV read options actually used)
  docs/data_dictionary.md
"""
from __future__ import annotations

import re
from pathlib import Path

import duckdb

from common import load_config, p, selected_exports, stop, write_json

READ_ATTEMPTS = [
    ("auto", "header=true, all_varchar=true"),
    ("quote_escape_explicit", "header=true, all_varchar=true, quote='\"', escape='\"', "
                              "parallel=false, max_line_size=20000000"),
]
DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%dT%H:%M:%S"]


def sql_str(path: Path) -> str:
    return "'" + path.as_posix().replace("'", "''") + "'"


def snake(name: str) -> str:
    s = re.sub(r"[^0-9a-zA-Z]+", "_", name.strip()).strip("_").lower()
    return re.sub(r"_+", "_", s)


def qi(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def read_expr(con, path: Path) -> tuple[str, str, list[str]]:
    errors = []
    for label, opts in READ_ATTEMPTS:
        expr = f"read_csv({sql_str(path)}, {opts})"
        try:
            cols = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM {expr}").fetchall()]
            con.execute(f"SELECT COUNT(*) FROM {expr}").fetchone()   # force a full parse
            return expr, label, cols
        except duckdb.Error as exc:
            errors.append(f"{label}: {exc}")
    stop(f"Lecture impossible de {path} :\n  " + "\n  ".join(errors))


def resolve_key(norm_cols: list[str], exact: str | None = None, contains: str | None = None,
                required: bool = True) -> str | None:
    if exact:
        hits = [c for c in norm_cols if c == exact]
    else:
        hits = [c for c in norm_cols if contains in c]
    if len(hits) == 1:
        return hits[0]
    if not hits and not required:
        return None
    stop(f"Colonne clé non identifiable sans ambiguïté ({exact or '*' + contains + '*'}) : "
         f"{hits or 'aucune'}. Colonnes réelles : {norm_cols}")


def main() -> int:
    cfg = load_config()
    raw, interim, reports, docs = (p(cfg, k) for k in ("raw", "interim", "reports", "docs"))
    con = duckdb.connect(str(interim / "phase1.duckdb"))

    # 1. read every CSV, collect headers
    files, read_log = [], []
    for e in selected_exports(cfg):
        f = raw / e["csv"]
        if not f.exists():
            stop(f"{e['csv']} absent de data/raw : exécuter register_local.py")
        expr, label, cols = read_expr(con, f)
        files.append((e["id"], f, expr, cols))
        read_log.append({"export_id": e["id"], "file": f.name, "read_options": label, "n_columns": len(cols)})
        print(f"[lu] export {e['id']:>2} — {len(cols)} colonnes (option : {label})")
    write_json(reports / "read_log.json", read_log)

    # 2. schema must be identical (names AND order)
    ref_id, ref_file, _, ref_cols = files[0]
    for eid, f, _, cols in files[1:]:
        if cols != ref_cols:
            stop("Schéma différent entre fichiers :\n"
                 f"  référence : export {ref_id} / {ref_file.name}\n"
                 f"  écart     : export {eid} / {f.name}\n"
                 f"  colonnes en plus : {[c for c in cols if c not in ref_cols]}\n"
                 f"  colonnes en moins : {[c for c in ref_cols if c not in cols]}\n"
                 f"  même ensemble, ordre différent : {set(cols) == set(ref_cols)}")

    # 3. normalise names
    mapping = {c: snake(c) for c in ref_cols}
    norm = list(mapping.values())
    if len(set(norm)) != len(norm):
        stop(f"Collision après normalisation snake_case : {mapping}")

    keys = {
        "complaint_id": resolve_key(norm, exact="complaint_id"),
        "date_received": resolve_key(norm, exact="date_received"),
        "product": resolve_key(norm, exact="product"),
        "sub_product": resolve_key(norm, exact="sub_product", required=False),
        "narrative": resolve_key(norm, contains="narrative"),
    }

    # 4. union all files
    select_cols = ", ".join(f"{qi(o)} AS {qi(n)}" for o, n in mapping.items())
    union = " UNION ALL ".join(f"SELECT {eid} AS source_export_id, {select_cols} FROM {expr}"
                               for eid, _, expr, _ in files)
    con.execute(f"CREATE OR REPLACE TABLE complaints_all AS {union}")
    n_rows = con.execute("SELECT COUNT(*) FROM complaints_all").fetchone()[0]
    print(f"Lignes chargées : {n_rows:,}")

    # 5. type date columns only if 100 % of non-empty values convert
    date_log = {}
    for col in [c for c in norm if "date" in c]:
        non_empty = con.execute(
            f"SELECT COUNT(*) FROM complaints_all WHERE {qi(col)} IS NOT NULL AND trim({qi(col)}) <> ''"
        ).fetchone()[0]
        chosen = None
        for fmt in DATE_FORMATS:
            ok = con.execute(
                f"SELECT COUNT(*) FROM complaints_all WHERE try_strptime(trim({qi(col)}), '{fmt}') IS NOT NULL"
            ).fetchone()[0]
            if non_empty and ok == non_empty:
                chosen = fmt
                break
        if chosen:
            con.execute(f"CREATE OR REPLACE TABLE complaints_all AS SELECT * REPLACE "
                        f"(CAST(try_strptime(trim({qi(col)}), '{chosen}') AS DATE) AS {qi(col)}) FROM complaints_all")
            date_log[col] = {"converted": True, "format": chosen, "non_empty": non_empty}
        else:
            date_log[col] = {"converted": False, "non_empty": non_empty,
                             "reason": "aucun format ne convertit 100 % des valeurs non vides"}
            print(f"[ALERTE] {col} laissée en texte : aucun format ne convertit 100 % des valeurs")

    if not date_log.get(keys["date_received"], {}).get("converted"):
        stop(f"{keys['date_received']} non convertible en DATE : profil mensuel (Q3) impossible. Détail : {date_log}")
    con.execute(f"ALTER TABLE complaints_all ADD COLUMN received_month VARCHAR")
    con.execute(f"UPDATE complaints_all SET received_month = strftime({qi(keys['date_received'])}, '%Y-%m')")

    # 6. parquet outputs
    nar = qi(keys["narrative"])
    all_pq, nar_pq = interim / "complaints_all.parquet", interim / "complaints_with_narrative.parquet"
    con.execute(f"COPY complaints_all TO {sql_str(all_pq)} (FORMAT parquet, COMPRESSION zstd)")
    con.execute(f"COPY (SELECT * FROM complaints_all WHERE {nar} IS NOT NULL AND trim({nar}) <> '') "
                f"TO {sql_str(nar_pq)} (FORMAT parquet, COMPRESSION zstd)")
    n_nar = con.execute(f"SELECT COUNT(*) FROM read_parquet({sql_str(nar_pq)})").fetchone()[0]
    print(f"Lignes avec narratif non vide : {n_nar:,}")

    write_json(interim / "columns.json", {
        "original_to_normalized": mapping,
        "keys": keys,
        "date_conversion": date_log,
        "n_rows_all": n_rows,
        "n_rows_with_narrative": n_nar,
    })

    # 7. data dictionary (T9) — measured facts only, no semantic description
    lines = [
        "# Dictionnaire de données — Phase 1",
        "",
        "Généré automatiquement par `src/data/build_interim.py` à partir des colonnes réelles des exports "
        f"sélectionnés {cfg['selected_exports']} ({n_rows:,} lignes).",
        "",
        f"Référence officielle des champs : {cfg['field_reference']}. Attention : cette référence documente "
        "la base en ligne ; sa correspondance avec l'archive FOIA n'est pas vérifiée.",
        "",
        "`% null` = valeurs NULL ; `% vide` = chaînes vides après suppression des espaces (colonnes texte).",
        "",
        "| Nom original | Nom normalisé | Type DuckDB | % null | % vide | Valeurs distinctes | Exemple (80 car.) |",
        "|---|---|---|---|---|---|---|",
    ]
    types = dict(con.execute("SELECT column_name, column_type FROM (DESCRIBE complaints_all)").fetchall())
    for orig, col in mapping.items():
        c = qi(col)
        is_text = types[col] == "VARCHAR"
        pct_null, pct_empty, n_dist = con.execute(
            f"SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE {c} IS NULL) / COUNT(*), 2), "
            + (f"ROUND(100.0 * COUNT(*) FILTER (WHERE trim({c}) = '') / COUNT(*), 2), " if is_text else "NULL, ")
            + f"COUNT(DISTINCT {c}) FROM complaints_all").fetchone()
        ex = con.execute(f"SELECT CAST({c} AS VARCHAR) FROM complaints_all WHERE {c} IS NOT NULL "
                         + (f"AND trim({c}) <> '' " if is_text else "") + "LIMIT 1").fetchone()
        ex = (ex[0] if ex else "").replace("\n", " ").replace("|", "\\|")[:80]
        lines.append(f"| {orig} | {col} | {types[col]} | {pct_null} | {pct_empty if pct_empty is not None else '—'} "
                     f"| {n_dist:,} | {ex} |")
    lines += ["", "Colonnes ajoutées par le pipeline : `source_export_id` (id de l'export d'origine), "
              "`received_month` (AAAA-MM dérivé de la date de réception).", "",
              "Conversions de dates :", ""]
    lines += [f"- `{k}` : " + (f"convertie en DATE (format `{v['format']}`)" if v["converted"]
                               else f"laissée en texte — {v['reason']}") for k, v in date_log.items()]
    (docs / "data_dictionary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Dictionnaire : {docs / 'data_dictionary.md'}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
