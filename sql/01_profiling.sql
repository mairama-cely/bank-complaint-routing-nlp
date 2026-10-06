-- =====================================================================================
-- Phase 1 — Profilage (DuckDB)
-- Vues : all_c  = data/interim/complaints_all.parquet            (toutes les lignes)
--        narr_c = data/interim/complaints_with_narrative.parquet  (narratif non vide)
-- Les marqueurs "dollar + accolades" sont remplacés par src/data/profile_report.py avec les NOMS RÉELS
-- des colonnes, lus dans data/interim/columns.json. Aucun nom n'est supposé ici.
-- Chaque requête commence par "-- name: <id>".
-- =====================================================================================

-- name: Q1
-- Nombre de lignes par export et plage des dates de réception.
SELECT source_export_id,
       COUNT(*)                AS n_rows,
       MIN(${date_received})   AS min_date_received,
       MAX(${date_received})   AS max_date_received
FROM all_c
GROUP BY source_export_id
ORDER BY source_export_id;

-- name: Q2_global
-- Taux de narratifs non vides, global.
SELECT COUNT(*) AS n_rows,
       COUNT(*) FILTER (WHERE ${narrative} IS NOT NULL AND trim(${narrative}) <> '') AS n_with_narrative,
       ROUND(100.0 * COUNT(*) FILTER (WHERE ${narrative} IS NOT NULL AND trim(${narrative}) <> '')
             / COUNT(*), 2) AS pct_with_narrative
FROM all_c;

-- name: Q2_by_export
-- Taux de narratifs non vides, par export.
SELECT source_export_id,
       COUNT(*) AS n_rows,
       COUNT(*) FILTER (WHERE ${narrative} IS NOT NULL AND trim(${narrative}) <> '') AS n_with_narrative,
       ROUND(100.0 * COUNT(*) FILTER (WHERE ${narrative} IS NOT NULL AND trim(${narrative}) <> '')
             / COUNT(*), 2) AS pct_with_narrative
FROM all_c
GROUP BY source_export_id
ORDER BY source_export_id;

-- name: Q2_by_product
-- Taux de narratifs non vides, par produit.
SELECT ${product} AS product,
       COUNT(*) AS n_rows,
       COUNT(*) FILTER (WHERE ${narrative} IS NOT NULL AND trim(${narrative}) <> '') AS n_with_narrative,
       ROUND(100.0 * COUNT(*) FILTER (WHERE ${narrative} IS NOT NULL AND trim(${narrative}) <> '')
             / COUNT(*), 2) AS pct_with_narrative
FROM all_c
GROUP BY 1
ORDER BY n_with_narrative DESC;

-- name: Q3
-- Distribution produit x mois (lignes avec narratif) : stabilité de la taxonomie.
SELECT received_month, ${product} AS product, COUNT(*) AS n_narratives
FROM narr_c
GROUP BY 1, 2
ORDER BY 1, 2;

-- name: Q4_product
-- Valeurs distinctes de produit (lignes avec narratif).
SELECT ${product} AS product, COUNT(*) AS n_narratives
FROM narr_c
GROUP BY 1
ORDER BY n_narratives DESC;

-- name: Q4_product_subproduct
-- Valeurs distinctes produit x sous-produit (lignes avec narratif).
SELECT ${product} AS product, ${sub_product} AS sub_product, COUNT(*) AS n_narratives
FROM narr_c
GROUP BY 1, 2
ORDER BY 1, n_narratives DESC;

-- name: Q5_across_exports
-- Identifiants de réclamation présents dans plusieurs exports.
SELECT COUNT(*) AS n_ids_in_multiple_exports
FROM (SELECT ${complaint_id}
      FROM all_c
      GROUP BY ${complaint_id}
      HAVING COUNT(DISTINCT source_export_id) > 1);

-- name: Q5_within_export
-- Identifiants dupliqués à l'intérieur d'un même export.
SELECT e.source_export_id,
       COALESCE(d.n_duplicated_ids, 0)  AS n_duplicated_ids,
       COALESCE(d.n_rows_involved, 0)   AS n_rows_involved
FROM (SELECT DISTINCT source_export_id FROM all_c) e
LEFT JOIN (SELECT source_export_id, COUNT(*) AS n_duplicated_ids, SUM(c) AS n_rows_involved
           FROM (SELECT source_export_id, ${complaint_id}, COUNT(*) AS c
                 FROM all_c GROUP BY 1, 2 HAVING COUNT(*) > 1)
           GROUP BY 1) d USING (source_export_id)
ORDER BY 1;

-- name: Q6
-- Doublons exacts sur le texte du narratif.
SELECT COUNT(*)            AS n_texts_duplicated,
       COALESCE(SUM(c), 0) AS n_rows_involved
FROM (SELECT ${narrative}, COUNT(*) AS c FROM narr_c GROUP BY 1 HAVING COUNT(*) > 1);

-- name: Q6b
-- Textes dupliqués portant des produits différents (conflit d'étiquette potentiel).
SELECT COUNT(*)            AS n_texts_multi_product,
       COALESCE(SUM(c), 0) AS n_rows_involved
FROM (SELECT ${narrative}, COUNT(*) AS c
      FROM narr_c
      GROUP BY 1
      HAVING COUNT(*) > 1 AND COUNT(DISTINCT ${product}) > 1);

-- name: Q7
-- Longueur des narratifs en mots.
WITH w AS (
  SELECT len(string_split(trim(regexp_replace(${narrative}, '\s+', ' ', 'g')), ' ')) AS n_words
  FROM narr_c
)
SELECT MIN(n_words)                   AS min,
       quantile_cont(n_words, 0.05)   AS p5,
       quantile_cont(n_words, 0.25)   AS p25,
       quantile_cont(n_words, 0.50)   AS median,
       quantile_cont(n_words, 0.75)   AS p75,
       quantile_cont(n_words, 0.95)   AS p95,
       MAX(n_words)                   AS max
FROM w;

-- name: Q8
-- Masques de données personnelles (séquences de 4 X ou plus).
SELECT ROUND(100.0 * AVG(CASE WHEN regexp_matches(${narrative}, 'X{4,}') THEN 1 ELSE 0 END), 2)
         AS pct_narratives_with_mask,
       ROUND(AVG(len(regexp_extract_all(${narrative}, 'X{4,}'))), 2)
         AS avg_masks_per_narrative
FROM narr_c;

-- name: Q9
-- Produit(s) « credit reporting » : libellé réel repéré par motif, effectif et part des narratifs.
SELECT ${product} AS product,
       COUNT(*)   AS n_narratives,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM narr_c), 2) AS pct_of_narratives
FROM narr_c
WHERE lower(${product}) LIKE '%credit report%'
GROUP BY 1
ORDER BY 2 DESC;
