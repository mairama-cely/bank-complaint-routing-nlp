# Baselines TF-IDF — sélection sur la validation (Phase 3b)

Généré le 2026-10-05 20:45 UTC par `src/models/train_baseline.py` (scikit-learn 1.6.1, durée 2269 s). **Le jeu de test n'a pas été lu.**

Train : 74,415 ; val : 15,945. TF-IDF ajusté sur train uniquement : {'ngram_range': [1, 2], 'min_df': 5, 'max_df': 0.9, 'max_features': 300000, 'sublinear_tf': True, 'token_pattern': '(?u)\\[\\w+\\]|\\b\\w\\w+\\b'}.

## 1. Meilleur modèle par variante (val)

| variant | model | C | class_weight | calibrated_on_val | val_macro_f1 | val_accuracy | val_top2_accuracy | val_min_recall |
|---|---|---|---|---|---|---|---|---|
| as_is | linear_svc | 0.3 | balanced | True | 0.8469 | 0.855 | 0.9541 | 0.7616 |
| company_masked | linear_svc | 0.3 | balanced | True | 0.8318 | 0.8425 | 0.9478 | 0.7281 |

Écart de macro-F1 val (as_is − company_masked) : **+0.0151**. Mesure préliminaire sur val ; la mesure retenue sera celle du test (Phase 3c). Le masquage étant incomplet (marques absentes de la colonne Company non masquées, décision 3a), cet écart est une **borne basse** de la dépendance aux noms d'entreprises.

## 2. Rappel par service du meilleur modèle (val)

| variant | recall_Comptes & Dépôts | recall_Crédit immobilier | recall_Crédits aux particuliers | recall_Monétique | recall_Recouvrement | recall_Transferts & Paiements |
|---|---|---|---|---|---|---|
| as_is | 0.8131 | 0.9193 | 0.8654 | 0.8206 | 0.9153 | 0.7616 |
| company_masked | 0.7974 | 0.903 | 0.843 | 0.8092 | 0.9159 | 0.7281 |

## 3. Grille complète (val)

| variant | model | C | class_weight | val_macro_f1 | val_accuracy | val_top2_accuracy | val_min_recall | fit_seconds |
|---|---|---|---|---|---|---|---|---|
| as_is | logreg | 1.0 | none | 0.8377 | 0.8487 | 0.9553 | 0.6755 | 136.6 |
| as_is | logreg | 1.0 | balanced | 0.8428 | 0.8499 | 0.955 | 0.7835 | 119.8 |
| as_is | logreg | 4.0 | none | 0.8397 | 0.8502 | 0.9559 | 0.6926 | 180.9 |
| as_is | logreg | 4.0 | balanced | 0.8436 | 0.8517 | 0.9571 | 0.7643 | 175.8 |
| as_is | logreg | 16.0 | none | 0.8383 | 0.8485 | 0.9555 | 0.6899 | 219.1 |
| as_is | logreg | 16.0 | balanced | 0.8399 | 0.8487 | 0.9562 | 0.7391 | 218.4 |
| as_is | linear_svc | 0.1 | none | 0.8417 | 0.8519 | 0.9531 | 0.6899 | 7.1 |
| as_is | linear_svc | 0.1 | balanced | 0.8455 | 0.8534 | 0.9527 | 0.7684 | 7.0 |
| as_is | linear_svc | 0.3 | none | 0.8432 | 0.8529 | 0.9541 | 0.7063 | 7.9 |
| as_is | linear_svc | 0.3 | balanced | 0.8469 | 0.855 | 0.9541 | 0.7616 | 8.5 |
| as_is | linear_svc | 1.0 | none | 0.84 | 0.8494 | 0.95 | 0.7049 | 12.3 |
| as_is | linear_svc | 1.0 | balanced | 0.8421 | 0.8509 | 0.9493 | 0.7384 | 13.2 |
| company_masked | logreg | 1.0 | none | 0.8234 | 0.8379 | 0.9482 | 0.6298 | 128.4 |
| company_masked | logreg | 1.0 | balanced | 0.8296 | 0.8384 | 0.9495 | 0.765 | 119.4 |
| company_masked | logreg | 4.0 | none | 0.8247 | 0.8377 | 0.9505 | 0.6489 | 164.8 |
| company_masked | logreg | 4.0 | balanced | 0.8287 | 0.8391 | 0.9508 | 0.7302 | 145.7 |
| company_masked | logreg | 16.0 | none | 0.8246 | 0.8374 | 0.9493 | 0.6551 | 225.2 |
| company_masked | logreg | 16.0 | balanced | 0.8262 | 0.8373 | 0.9498 | 0.707 | 167.1 |
| company_masked | linear_svc | 0.1 | none | 0.8238 | 0.8381 | 0.9479 | 0.6216 | 7.1 |
| company_masked | linear_svc | 0.1 | balanced | 0.8312 | 0.8412 | 0.9481 | 0.7404 | 8.8 |
| company_masked | linear_svc | 0.3 | none | 0.8306 | 0.8429 | 0.9495 | 0.6639 | 8.4 |
| company_masked | linear_svc | 0.3 | balanced | 0.8318 | 0.8425 | 0.9478 | 0.7281 | 8.7 |
| company_masked | linear_svc | 1.0 | none | 0.8237 | 0.8368 | 0.9444 | 0.6571 | 12.4 |
| company_masked | linear_svc | 1.0 | balanced | 0.8281 | 0.8399 | 0.9435 | 0.7029 | 13.8 |

## 4. Matrices de confusion du meilleur modèle (val ; lignes = vrai service, colonnes = prédit)

### as_is

| vrai \ prédit | Comptes & Dépôts | Crédit immobilier | Crédits aux particuliers | Monétique | Recouvrement | Transferts & Paiements |
|---|---|---|---|---|---|---|
| Comptes & Dépôts | 2639 | 4 | 32 | 202 | 49 | 268 |
| Crédit immobilier | 22 | 1065 | 46 | 12 | 20 | 0 |
| Crédits aux particuliers | 59 | 9 | 1801 | 72 | 185 | 14 |
| Monétique | 247 | 5 | 70 | 2691 | 164 | 73 |
| Recouvrement | 46 | 33 | 149 | 112 | 4379 | 13 |
| Transferts & Paiements | 334 | 5 | 17 | 58 | 14 | 1036 |

### company_masked

| vrai \ prédit | Comptes & Dépôts | Crédit immobilier | Crédits aux particuliers | Monétique | Recouvrement | Transferts & Paiements |
|---|---|---|---|---|---|---|
| Comptes & Dépôts | 2599 | 5 | 34 | 207 | 55 | 294 |
| Crédit immobilier | 18 | 1049 | 58 | 19 | 19 | 2 |
| Crédits aux particuliers | 63 | 12 | 1757 | 106 | 186 | 16 |
| Monétique | 269 | 3 | 71 | 2665 | 171 | 71 |
| Recouvrement | 47 | 32 | 144 | 116 | 4382 | 11 |
| Transferts & Paiements | 362 | 6 | 13 | 87 | 16 | 980 |

## 5. Critères de sortie de la Phase 3b

| Critère | Statut |
|---|---|
| Jeu de test non lu (aucune lecture de test.parquet dans ce script) | OK |
| sha256 de train, val et company_masked vérifiés | OK |
| Grille complète exécutée (24 ajustements) | OK |
| Meilleur modèle par variante sauvegardé avec sha256 (models/MANIFEST_models.json) | OK |
| Probabilités disponibles pour la Phase 5 (régression logistique ou LinearSVC calibré) | OK |

Note : si un LinearSVC est retenu, il est calibré sur la validation, qui a aussi servi à la sélection ; la qualité du calibrage sera mesurée sur le test en Phase 3c.
