# Seuil de routage et impact métier — Phase 5

Généré le 2026-10-05 21:50 UTC par `src/models/routing_threshold.py`. Première application : verrou créé (reports/phase5/ROUTING_LOCK.json).

Modèle : `company_masked` (verrouillé en Phase 3c). Protocole fixé avant calcul (config.yaml, section phase5).

## 1. Sélection sur la validation

Règles : `calibrated_argmax` (A, modèle évalué en 3c) ; `raw_svc_argmax` (B, classe du SVC brut, confiance = probabilité calibrée de cette classe). Seuil = plus petit seuil atteignant la précision cible.

| rule | target_precision | threshold | val_coverage | val_precision | val_macro_f1_no_threshold |
|---|---|---|---|---|---|
| calibrated_argmax | 0.95 | 0.79 | 0.6405 | 0.9507 | 0.8306 |
| calibrated_argmax | 0.9 | 0.585 | 0.855 | 0.9003 | 0.8306 |
| calibrated_argmax | 0.97 | 0.87 | 0.4948 | 0.971 | 0.8306 |
| raw_svc_argmax | 0.95 | 0.79 | 0.6405 | 0.9507 | 0.8318 |
| raw_svc_argmax | 0.9 | 0.585 | 0.855 | 0.9003 | 0.8318 |
| raw_svc_argmax | 0.97 | 0.87 | 0.4948 | 0.971 | 0.8318 |

**Règle retenue : `calibrated_argmax` ; seuil : 0.79** (couverture val maximale à précision ≥ 0.95). Le rappel de Transferts sous la règle A avait déjà été vu sur le test (3c) : le choix est donc fait par ce critère mécanique, fixé à l'avance.

## 2. Application unique (bootstrap 95 %)

| dataset | n | coverage | coverage_ci95 | precision_auto | precision_ci95 | macro_f1_no_threshold | accuracy_human_queue_if_model_kept |
|---|---|---|---|---|---|---|---|
| val_2026 | 15945 | 0.6405 | [0.6336 ; 0.6485] | 0.9507 | [0.9465 ; 0.9550] | 0.8306 | 0.6494 |
| test_2026 | 15947 | 0.6377 | [0.6301 ; 0.6449] | 0.9468 | [0.9427 ; 0.9513] | 0.8283 | 0.65 |
| external_2025 | 251388 | 0.6449 | [0.6431 ; 0.6467] | 0.948 | [0.9469 ; 0.9491] | 0.8423 | 0.6541 |

`accuracy_human_queue_if_model_kept` : exactitude qu'aurait eue le modèle sur les réclamations envoyées en revue humaine (montre ce que le seuil évite).

## 3. Par service

| dataset | service | share_auto_routed_pct | precision_auto_pred_as_service | n_true |
|---|---|---|---|---|
| test_2026 | Comptes & Dépôts | 51.44 | 0.9094 | 3194 |
| test_2026 | Crédit immobilier | 71.27 | 0.9728 | 1166 |
| test_2026 | Crédits aux particuliers | 62.38 | 0.9437 | 2140 |
| test_2026 | Monétique | 62.38 | 0.9501 | 3251 |
| test_2026 | Recouvrement | 81.17 | 0.969 | 4732 |
| test_2026 | Transferts & Paiements | 33.61 | 0.8436 | 1464 |
| external_2025 | Comptes & Dépôts | 55.3 | 0.923 | 47251 |
| external_2025 | Crédit immobilier | 67.6 | 0.9739 | 14023 |
| external_2025 | Crédits aux particuliers | 60.74 | 0.939 | 30088 |
| external_2025 | Monétique | 59.93 | 0.9469 | 42960 |
| external_2025 | Recouvrement | 76.34 | 0.9522 | 77124 |
| external_2025 | Transferts & Paiements | 59.09 | 0.9637 | 39942 |

## 4. Impact métier (illustratif)

Volume **illustratif** de 1,000 réclamations par mois (pas un chiffre Afriland). Temps de tri manuel **supposé** (hypothèse du cadrage, non mesurée). Aucun coût de réacheminement n'est chiffré : seul le nombre de réclamations mal routées est donné ; le taux d'erreur du tri manuel actuel n'est pas connu.

| dataset | triage_minutes_assumed | auto_routed_per_month | human_review_per_month | misrouted_auto_per_month | triage_hours_saved_per_month |
|---|---|---|---|---|---|
| test_2026 | 1 | 638 | 362 | 34 | 10.6 |
| test_2026 | 2 | 638 | 362 | 34 | 21.3 |
| test_2026 | 3 | 638 | 362 | 34 | 31.9 |
| test_2026 | 5 | 638 | 362 | 34 | 53.1 |
| external_2025 | 1 | 645 | 355 | 34 | 10.7 |
| external_2025 | 2 | 645 | 355 | 34 | 21.5 |
| external_2025 | 3 | 645 | 355 | 34 | 32.2 |
| external_2025 | 5 | 645 | 355 | 34 | 53.7 |

Figure : `reports/figures/phase5_coverage_precision.png`.

## 5. Critères de sortie de la Phase 5

| Critère | Statut |
|---|---|
| Modèle identique à celui verrouillé en 3c ; données et probabilités vérifiées | OK |
| Règle et seuil choisis sur la validation uniquement, par critère fixé à l'avance | OK |
| Précision cible atteinte sur le test (≥ 0.95) | KO — voir intervalle |
| Précision cible atteinte sur external_2025 | KO — voir intervalle |
| Impact métier calculé avec hypothèses explicites | OK |
| Verrou de routage enregistré | OK |
