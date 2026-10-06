# Routage automatique des réclamations clients bancaires (NLP)

Une banque reçoit des réclamations écrites qu'il faut trier puis affecter au bon service (comptes, cartes, crédits, recouvrement…).
Ce projet mesure dans quelle proportion ce routage peut être automatisé par un modèle de classification de texte, et à quel seuil de confiance, sans dégrader la précision.
Le livrable métier est un seuil de routage automatique chiffré : couverture, taux d'erreur et temps de tri économisé.

> **Source des données.** Archive FOIA du Consumer Financial Protection Bureau (CFPB, États-Unis) : *CFPB Consumer Complaint Database Narratives Archive*. Selon la page source, elle couvre les réclamations reçues du 1er décembre 2011 au 14 août 2026.
> Constat au profilage (Phase 1, 05/10/2026) : l'export 21 contient des réclamations reçues jusqu'au 31 août 2026, mais un seul narratif pour tout le mois d'août 2026.
> Le 14 août 2026, le CFPB a cessé de publier les narratifs de réclamation dans sa base en ligne ; les narratifs déjà publiés ont été transférés dans cette archive.
> Le corpus est donc **figé** : les résultats de ce dépôt sont reproductibles à l'identique.
> Page source : https://www.consumerfinance.gov/foia-requests/foia-electronic-reading-room/cfpb-consumer-complaint-database-narratives-archive/

## En bref

| | |
|---|---|
| **Question** | Quelle part des réclamations écrites peut être affectée automatiquement au bon service (6 services de banque de détail), avec environ 95 % de bonnes affectations ? |
| **Données** | 106 307 réclamations réelles de 2026 (découpage 70/15/15 figé) et 251 388 réclamations de 2025 utilisées comme test externe, jamais vues à l'entraînement. |
| **Modèle** | TF-IDF (mots et paires de mots) + LinearSVC calibré ; noms d'entreprises masqués pour limiter les raccourcis non transférables. |
| **Résultat** | **63,8 %** des réclamations du test routées automatiquement avec **94,7 %** de bonnes affectations ; **64,5 %** et **94,8 %** sur 2025. Macro-F1 du classifieur : 0,828 sur le test. |
| **Rigueur** | Choix du modèle, de la règle et du seuil sur la validation uniquement ; test évalué une seule fois (verrous `TEST_LOCK.json` et `ROUTING_LOCK.json`) ; intervalles de confiance par bootstrap ; test externe sur une autre année ; dépendance aux noms d'entreprises mesurée ; empreintes sha256 de chaque jeu et de chaque modèle. |
| **Limites principales** | Précision inégale selon les services (84 % pour Transferts & Paiements) ; cible de 95 % approchée mais non atteinte ; corpus anglais américain : c'est la méthode qui se transfère, pas le modèle. |

Note d'une page pour la direction Qualité : [`docs/note_direction_qualite.md`](docs/note_direction_qualite.md).

Cadrage complet : [`docs/01_cadrage.md`](docs/01_cadrage.md).

## Structure du dépôt

```
config/          config.yaml (sources, sélection, chemins) · label_mapping.yaml (figé le 2026-10-05)
data/            non versionné — raw/ (21 CSV + MANIFEST.json), interim/ (parquet), processed/
sql/             01_profiling.sql (requêtes DuckDB de profilage)
src/data/        probe_sources.py · register_local.py · build_interim.py · profile_report.py · audit_text.py · clean_split.py · verify_csv_parsing.py · build_external.py · common.py
src/features/    build_company_mask.py (masquage [COMPANY], Phase 3a)
src/models/      train_baseline.py (Phase 3b) · evaluate_final.py (Phase 3c-ii) · routing_threshold.py (Phase 5)
notebooks/       00_Data_Acquisition · 01_EDA · 02_Data_Cleaning · 03_Text_Exploration · 04_Company_Masking · 05_Baseline_Models · 06_Final_Evaluation · 07_Routing_Threshold · 08_Final_Synthesis (générés par scripts/create_notebooks.py) · _archive/
scripts/         create_notebooks.py (génère les 9 notebooks)
output/          figures des notebooks (NN_nom.png, 300 dpi)
docs/            01_cadrage.md · data_dictionary.md (généré) · note_direction_qualite.md
reports/         source_probe.csv · local_inventory.csv · read_log.json · tables/ · figures/ · phase1_profile.md · phase2a_text_audit.md · phase2b_cleaning.md · phase2a/ · phase2b/ · phase2c/
models/          non versionné — as_is_best.joblib · company_masked_best.joblib · MANIFEST_models.json
```

## Reproduire la Phase 1

Prérequis : Python 3.13 (64 bits).

> Écart à la spécification initiale (Python 3.11) : le projet tourne sous Python 3.13, seule version installée sur le poste de développement. `pyarrow==17.0.0` ne publiant pas de wheel pour 3.13, la version épinglée est passée à `pyarrow==18.1.0`. Toutes les autres versions épinglées sont inchangées.

Acquisition des données : les 21 zip de l'archive ont été téléchargés manuellement depuis la page source, puis extraits dans `data/raw/` (21 fichiers CSV, 8,66 Go). Les zip d'origine ne sont pas conservés : `MANIFEST.json` contient donc l'empreinte sha256 des CSV locaux, pas celle des fichiers servis par le CFPB.

Windows (PowerShell), depuis la racine du dépôt :

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python src/data/probe_sources.py      # T3  HEAD sur les 21 URL, traçabilité des sources
python src/data/register_local.py     # T4/T5  inventaire des CSV locaux, sha256, détection du format
python src/data/build_interim.py      # T6/T9  parquet + dictionnaire de données
python src/data/profile_report.py     # T7/T10/T11  profilage SQL, brouillon de mapping, rapport
```

## Reproduire la Phase 2

```powershell
python src/data/audit_text.py         # 2a  audit des masques, dates, montants, artefacts (mesures seules)
python src/data/clean_split.py        # 2b  nettoyage R1-R8, dédoublonnage sur texte nettoyé, découpage 70/15/15
```

## Reproduire la Phase 3

```powershell
python src/features/build_company_mask.py   # 3a   lexique d'entreprises (train seul), variante [COMPANY]
python src/models/train_baseline.py         # 3b   TF-IDF + LogReg / LinearSVC, sélection sur val (test non lu)
python src/data/verify_csv_parsing.py       # 3c-i contrôle de la lecture CSV des exports 2026 (lecture stricte)
python src/data/build_external.py           # 3c-i jeu de test externe 2025 (aucun réapprentissage)
python src/models/evaluate_final.py         # 3c-ii évaluation unique du test (verrou TEST_LOCK.json) + externe 2025
```

## Reproduire la Phase 5

```powershell
python src/models/routing_threshold.py      # règle et seuil choisis sur val, appliqués une fois (verrou ROUTING_LOCK.json)
```

## Notebooks (00 à 08)

Les notebooks présentent les résultats produits par les scripts ci-dessus : ils lisent les rapports et les jeux figés, n'entraînent aucun modèle et ne réévaluent pas le jeu de test. Chaque figure est enregistrée dans `output/`.

```powershell
.venv\Scripts\python.exe scripts/create_notebooks.py
Get-ChildItem notebooks\0*.ipynb | ForEach-Object { .venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800 $_.FullName }
```

| Notebook | Contenu |
|---|---|
| 00_Data_Acquisition | Sources, fichiers locaux, schéma, intégrité sha256, contrôle de lecture CSV |
| 01_EDA | Profilage des exports 2026 : volumes, taux de narratifs, taxonomie, doublons, longueurs |
| 02_Data_Cleaning | Audit du texte, règles R1–R8, dédoublonnage, découpage 70/15/15 |
| 03_Text_Exploration | Exploration du jeu d'entraînement : longueurs, jetons, vocabulaire discriminant, bigrammes |
| 04_Company_Masking | Masquage des noms d'entreprises : couverture, marques captées et résiduelles |
| 05_Baseline_Models | Grille TF-IDF et sélection sur la validation |
| 06_Final_Evaluation | Test 2026 et externe 2025 : métriques, intervalles, calibrage, erreurs |
| 07_Routing_Threshold | Seuil de routage, couverture, précision par service, impact métier |
| 08_Final_Synthesis | Synthèse, tableau de bord, recommandations, limites |

Chaque script s'arrête avec un message `[STOP]` en cas d'écart par rapport à la spécification : export sélectionné absent, schéma différent, format non CSV, colonne clé introuvable, date non convertible. Ces écarts ne sont jamais contournés automatiquement.

## Résultats

- Phase 1 — Profilage : voir `reports/phase1_profile.md`.
- Phase 2 — Audit du texte : `reports/phase2a_text_audit.md` ; nettoyage et découpage : `reports/phase2b_cleaning.md` (106 307 narratifs, 6 services, jeux figés avec sha256 dans `data/processed/MANIFEST.json`) ; exploration : `notebooks/03_Text_Exploration.ipynb`.
- Phase 3 — Baseline TF-IDF (`reports/phase3b_selection.md`, `reports/phase3c_evaluation.md`). Modèle de référence : LinearSVC (C = 0,3, classes équilibrées, calibré), noms d'entreprises masqués.
  - Test 2026 (évalué une seule fois) : macro-F1 **0,828** [IC 95 % 0,822 ; 0,835], accuracy 0,839, top-2 0,944.
  - Test externe 2025 (251 388 narratifs, aucun réapprentissage) : macro-F1 **0,842** [0,841 ; 0,844] ; macro-F1 mensuel de 0,802 à 0,857, sans tendance régulière.
  - Dépendance aux noms d'entreprises (borne basse) : −1,5 point de macro-F1 sur le test [IC 1,2 ; 1,9], −0,9 point sur 2025.
  - Calibrage : ECE 0,034 ; modèle légèrement sous-confiant (exactitude observée ≥ confiance annoncée).
- Phase 4+ — DistilBERT : _à venir_.
- Phase 5 — Seuil de routage (`reports/phase5_routing.md`). Règle et seuil choisis sur la validation par un critère fixé à l'avance, appliqués une seule fois.
  - Seuil de confiance retenu : **0,79** (précision 95,1 % et couverture 64,1 % sur la validation).
  - Test 2026 : **63,8 %** des réclamations routées automatiquement [IC 63,0 ; 64,5], précision **94,7 %** [94,3 ; 95,1].
  - Test externe 2025 : couverture 64,5 % [64,3 ; 64,7], précision 94,8 % [94,7 ; 94,9].
  - Sur les réclamations laissées en revue humaine, le modèle n'aurait eu raison que dans 65 % des cas : le seuil écarte l'essentiel de ses erreurs.
  - Pour 1 000 réclamations par mois (volume illustratif) : 638 routées automatiquement, 362 en revue humaine, 34 mal routées ; de 10,6 à 53,1 heures de tri économisées selon le temps de tri supposé (1 à 5 minutes).
- Phase 6 — Note de synthèse d'une page pour la direction Qualité : `docs/note_direction_qualite.md`. Le tableau de bord Power BI prévu au cadrage n'est pas réalisé dans cette version (cadrage §9 : « README et note seulement » pour la candidature).

## Limites connues

- Le corpus est en anglais et provient de consommateurs américains. C'est le pipeline qui se transfère à une banque francophone, pas les poids du modèle.
- Seuls les narratifs dont le consommateur a consenti à la publication sont présents. L'échantillon n'est donc pas représentatif de l'ensemble des réclamations.
- Les données personnelles sont masquées dans les textes (motifs `XXXX`).
- 741 narratifs étaient stockés sous forme d'octets Python (`b'…'`) : leurs caractères non ASCII (accents) sont perdus à la source et ne sont pas récupérables.
- Phase 2b, défauts mineurs connus et non corrigés (les corriger changerait les sha256 des jeux figés) : une apostrophe isolée peut subsister en fin de texte (ex. réclamation 18491624) ; `en_stop_ratio` n'est pas arrondi dans le rapport.
- La détection de langue de la Phase 2b est une heuristique non validée : ses signalements ne sont pas fiables (faux positifs fréquents sur des textes anglais télégraphiques ou juridiques).
- Phase 3, effet du calibrage : le modèle a été sélectionné sur la décision du LinearSVC brut, mais il est déployé avec la décision calibrée (argmax des probabilités). Sur la validation, ce changement laisse le macro-F1 quasi inchangé (0,832 → 0,831) mais fait baisser le rappel de Transferts & Paiements de 0,728 à 0,669 ; sur le test, ce rappel vaut 0,648. Limite documentée ; réexaminée en Phase 5 (voir « Phase 5, règle de décision ») : a priori sans effet sur les routages automatiques.
- Phase 3, masquage des noms incomplet : les marques absentes de la colonne Company (ex. citi, cash app) restent visibles ; quelques mots courants sont masqués à tort (ex. january, express).
- Phase 3, comparabilité 2025 / 2026 : répartition des services, taux de publication des narratifs et volume de lettres types différents ; le test 2025 mesure l'absence de dégradation, pas une supériorité.
- Phase 3, bruit d'étiquetage : l'étiquette est le produit choisi par le consommateur ; plusieurs erreurs à forte confiance décrivent un autre service que l'étiquette. Non chiffré (nécessiterait une annotation manuelle).
- Lecture CSV : 5 lignes des exports 2025 étaient mal découpées en lecture par défaut ; la lecture stricte (séquentielle) est désormais utilisée pour 2025 et a été vérifiée identique à la lecture de la Phase 1 pour les 7 exports 2026. Cause exacte non établie.
- Phase 5, précision cible manquée de peu : le seuil a été fixé au plus petit niveau atteignant 95 % sur la validation, sans marge de sécurité. Sur le test, la précision vaut 94,7 % (95 % reste dans l'intervalle de confiance) ; sur 2025, 94,8 % (intervalle entièrement sous 95 %). Le seuil est verrouillé et n'a pas été réajusté ; une marge (par exemple exiger que la borne basse de l'intervalle sur la validation atteigne 95 %) aurait dû être prévue.
- Phase 5, précision hétérogène par service : sur le test 2026, la précision des routages automatiques vaut 84,4 % pour Transferts & Paiements (dont seulement 33,6 % sont routés automatiquement) et 90,9 % pour Comptes & Dépôts, contre 96 à 97 % pour Recouvrement et Crédit immobilier. Le seuil global de 95 % masque ces écarts.
- Phase 5, règle de décision : sur la validation, les règles A (calibrée) et B (SVC brut) donnent exactement la même couverture et la même précision aux trois seuils examinés (0,585, 0,79 et 0,87), alors que leur macro-F1 sans seuil diffère (0,831 contre 0,832). Leurs écarts se situent donc, selon toute vraisemblance (non vérifié prédiction par prédiction), sur des réclamations de confiance inférieure à 0,585, qui sont envoyées en revue humaine au seuil retenu. L'effet du calibrage relevé en Phase 3 ne semble donc pas modifier les routages automatiques.
- Phase 5, impact métier illustratif : volume et temps de tri sont des hypothèses, non des mesures chez Afriland ; le taux d'erreur du tri manuel actuel est inconnu, la comparaison avec le processus existant n'est donc pas faite.
