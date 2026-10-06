# Jeu de test externe 2025 — Phase 3c-i

Généré le 2026-10-05 21:22 UTC par `src/data/build_external.py`. Aucun réapprentissage : règles 2b et lexique 3a appliqués tels quels.

## 1. Exports lus

| export_id | n_rows | n_with_narrative | pct_with_narrative |
|---|---|---|---|
| 9 | 811019 | 265405 | 32.72 |
| 10 | 803073 | 210147 | 26.17 |
| 11 | 827343 | 219632 | 26.55 |
| 12 | 968761 | 234404 | 24.2 |
| 13 | 1023636 | 157821 | 15.42 |
| 14 | 1009132 | 134641 | 13.34 |

## 2. Libellés produits et correspondance figée

| product | n_narratives | status |
|---|---|---|
| Credit reporting or other personal consumer reports | 912756 | excluded_frozen |
| Debt collection | 100609 | mapped |
| Money transfer, virtual currency, or money service | 64863 | mapped |
| Checking or savings account | 51448 | mapped |
| Credit card | 41516 | mapped |
| Mortgage | 14031 | mapped |
| Vehicle loan or lease | 11686 | mapped |
| Student loan | 10869 | mapped |
| Payday loan, title loan, personal loan, or advance loan | 7805 | mapped |
| Prepaid card | 3822 | mapped |
| Debt or credit management | 2645 | mapped |

## 3. Entonnoir

| étape | lignes |
|---|---|
| narratifs non vides | 1222050 |
| après correspondance figée | 309294 |
| après R8 | 309279 |
| après conflits (service) | 289030 |
| après conservation d'un exemplaire | 251745 |
| après retrait des textes identiques à 2026 | 251388 |

## 4. Règles de nettoyage (narratifs modifiés)

| rule | n_narratives |
|---|---|
| R1_bytes_prefix | 1171 |
| R2_literal_escapes | 1232 |
| R3_dates | 109986 |
| R4_amounts | 90784 |
| R5_glued_xseq_narratives | 9299 |
| R5_xseq | 190526 |
| R6_collapsed | 128931 |
| R8_dropped_no_letter | 15 |

## 5. Répartition par service (externe vs entraînement 2026)

| service | n_2025 | pct_2025 | pct_train_2026 |
|---|---|---|---|
| Comptes & Dépôts | 47251 | 18.8 | 20.03 |
| Crédit immobilier | 14023 | 5.58 | 7.31 |
| Crédits aux particuliers | 30088 | 11.97 | 13.42 |
| Monétique | 42960 | 17.09 | 20.38 |
| Recouvrement | 77124 | 30.68 | 29.68 |
| Transferts & Paiements | 39942 | 15.89 | 9.18 |

## 6. Répartition mensuelle

| received_month | n |
|---|---|
| 2025-01 | 46086 |
| 2025-02 | 17733 |
| 2025-03 | 17942 |
| 2025-04 | 17315 |
| 2025-05 | 18876 |
| 2025-06 | 18703 |
| 2025-07 | 21276 |
| 2025-08 | 20623 |
| 2025-09 | 19791 |
| 2025-10 | 18056 |
| 2025-11 | 18920 |
| 2025-12 | 16067 |

## 7. Couverture [COMPANY]

- Narratifs avec au moins un `[COMPANY]` : 43.45 %.

## 8. Critères de sortie de la 3c-i

| Critère | Statut |
|---|---|
| Exports externes disjoints de 2026 | OK |
| Schéma identique à la Phase 1 pour chaque export | OK |
| Dates converties avec le format de la Phase 1 (100 %) | OK |
| Aucun texte ni identifiant partagé avec 2026 | OK |
| Lexique 3a réutilisé sans modification (nombre de motifs contrôlé, sha256 enregistré) | OK |
| Libellés produits inconnus de la correspondance figée | aucun |
