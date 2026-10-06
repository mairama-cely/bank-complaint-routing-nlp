"""Re-read the 2026 exports (selected_exports) in strict sequential mode and compare with Phase 1 output.

Context (2026-10-05): with DuckDB's default reading (parallel, auto-detected dialect), 5 rows of the 2025 exports
9 and 13 were mis-split next to narratives spanning several lines with blank lines (exact cause not established;
not reproduced on synthetic data). Phase 1 read the 2026 exports with the same default mode. This script checks, for each selected export, that the strict sequential read gives exactly the same rows:
  - row count per export
  - set of complaint ids
  - sha256 of every (complaint_id, narrative) pair
Result: reports/csv_parsing_check.md. Exit code 1 if any difference is found (Phase 2 sets would then need rebuilding).
"""
from __future__ import annotations

import hashlib
import sys

import duckdb
import pandas as pd

from common import ROOT, load_config, read_json, stop
from profile_report import md_table


def pair_hash(ids: pd.Series, narr: pd.Series) -> pd.Series:
    return (ids.astype(str) + "\x1f" + narr.fillna("\x00")).map(lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest())


def main() -> int:
    cfg = load_config()
    if "csv_strict_options" not in cfg:
        stop("csv_strict_options absent de config.yaml.")
    cols = read_json(ROOT / cfg["paths"]["interim"] / "columns.json")
    o2n, keys = cols["original_to_normalized"], cols["keys"]
    n2o = {n: o for o, n in o2n.items()}
    cid_n, nar_n = keys["complaint_id"], keys["narrative"]
    all_pq = (ROOT / cfg["paths"]["interim"] / "complaints_all.parquet").as_posix()
    con = duckdb.connect()
    ref = con.execute(f'SELECT source_export_id, CAST("{cid_n}" AS VARCHAR) AS cid, "{nar_n}" AS nar '
                      f"FROM read_parquet('{all_pq}')").df()

    raw = ROOT / cfg["paths"]["raw"]
    by_id = {e["id"]: e for e in cfg["exports"]}
    rows, problems = [], []
    for eid in cfg["selected_exports"]:
        f = raw / by_id[eid]["csv"]
        print(f"[export {eid}] lecture séquentielle stricte…", flush=True)
        expr = f"read_csv('{f.as_posix()}', {cfg['csv_strict_options']})"
        header = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM {expr}").fetchall()]
        if header != list(o2n.keys()):
            stop(f"Schéma de l'export {eid} différent de la Phase 1 en lecture stricte : {header}")
        new = con.execute(f'SELECT CAST("{n2o[cid_n]}" AS VARCHAR) AS cid, "{n2o[nar_n]}" AS nar FROM {expr}').df()
        old = ref[ref["source_export_id"] == eid]
        ids_new, ids_old = set(new["cid"]), set(old["cid"])
        h_new = set(pair_hash(new["cid"], new["nar"]))
        h_old = set(pair_hash(old["cid"], old["nar"]))
        r = {"export_id": eid, "rows_phase1": len(old), "rows_strict": len(new),
             "ids_only_phase1": len(ids_old - ids_new), "ids_only_strict": len(ids_new - ids_old),
             "pair_hashes_differing": len(h_old ^ h_new)}
        r["status"] = "OK" if (r["rows_phase1"] == r["rows_strict"] and not r["ids_only_phase1"]
                              and not r["ids_only_strict"] and h_new == h_old) else "KO"
        rows.append(r)
        if r["status"] == "KO":
            diff_ids = sorted((ids_old ^ ids_new))[:10]
            problems.append(f"export {eid} : exemples d'identifiants en écart {diff_ids}")
        print(f"           {r['status']} (lignes Phase 1 {r['rows_phase1']:,} / strict {r['rows_strict']:,})", flush=True)

    res = pd.DataFrame(rows)
    ok = (res["status"] == "OK").all()
    lines = ["# Vérification de la lecture CSV des exports 2026", "",
             "Relecture des exports sélectionnés en mode séquentiel strict "
             f"(`{cfg['csv_strict_options']}`) et comparaison avec la sortie de la Phase 1 "
             "(`data/interim/complaints_all.parquet`).", "", md_table(res), "",
             "**Conclusion : lectures identiques — les jeux de la Phase 2 restent valides.**" if ok else
             "**Conclusion : ÉCARTS détectés — la Phase 1 doit être relancée en lecture stricte, puis les Phases 2 et 3.**"]
    lines += [f"- {p}" for p in problems]
    (ROOT / "reports" / "csv_parsing_check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n" + ("TOUS LES EXPORTS 2026 : OK" if ok else "ÉCARTS DÉTECTÉS : voir reports/csv_parsing_check.md"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
