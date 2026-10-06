# Vérification de la lecture CSV des exports 2026

Relecture des exports sélectionnés en mode séquentiel strict (`header=true, all_varchar=true, parallel=false, quote='"', escape='"', max_line_size=20000000`) et comparaison avec la sortie de la Phase 1 (`data/interim/complaints_all.parquet`).

| export_id | rows_phase1 | rows_strict | ids_only_phase1 | ids_only_strict | pair_hashes_differing | status |
|---|---|---|---|---|---|---|
| 15 | 1038383 | 1038383 | 0 | 0 | 0 | OK |
| 16 | 614945 | 614945 | 0 | 0 | 0 | OK |
| 17 | 618293 | 618293 | 0 | 0 | 0 | OK |
| 18 | 619940 | 619940 | 0 | 0 | 0 | OK |
| 19 | 620794 | 620794 | 0 | 0 | 0 | OK |
| 20 | 672036 | 672036 | 0 | 0 | 0 | OK |
| 21 | 667140 | 667140 | 0 | 0 | 0 | OK |

**Conclusion : lectures identiques — les jeux de la Phase 2 restent valides.**
