# Projet bancaire 3 — Routage automatique des réclamations clients (NLP)

**Phase 1 : cadrage métier et acquisition des données**
Version du 26/09/2026. Cible : candidature Afriland First Bank (clôture 20/10/2026).

---

## 0. Correction critique sur la source de données

Le plan initial prévoyait de télécharger la base CFPB « Consumer Complaint Database » en direct. **Ce n'est plus valable pour un projet NLP.**

- Le **14 août 2026**, le CFPB a cessé de publier les narratifs de réclamation (le texte écrit par le client) dans la base en ligne.
- Les narratifs déjà publiés ont été transférés dans la salle de lecture FOIA du CFPB, sous forme d'archive téléchargeable.
- **Source retenue :** *CFPB Consumer Complaint Database Narratives Archive*. Elle contient 21 exports couvrant les réclamations reçues du 1er décembre 2011 au 14 août 2026.
  Page : https://www.consumerfinance.gov/foia-requests/foia-electronic-reading-room/cfpb-consumer-complaint-database-narratives-archive/
- **Correction du 05/10/2026 (profilage Phase 1) :** l'export 21 contient des réclamations reçues jusqu'au **31 août 2026**, et non jusqu'au 14 août. Il ne contient qu'**un seul narratif** pour le mois d'août 2026.
- **Statut de vérification :** la page et les liens ont été consultés le 26/09/2026. La taille des fichiers, leur format interne (CSV ou autre) et le schéma des colonnes **n'ont pas été vérifiés**. C'est la première tâche de la Phase 1.
- **Avantage pour le portfolio :** le corpus est désormais figé, donc tes résultats sont reproductibles. Mentionne ce contexte dans le README, car il montre que tu suis l'actualité réglementaire de tes sources.

---

## 1. Problème métier

**Contexte.** Une banque de détail reçoit des réclamations par plusieurs canaux : agences, centre d'appels, e-mail, application mobile. Le tri manuel, qui consiste à lire chaque réclamation puis à l'affecter au bon service, pose trois problèmes :
- il prend du temps ;
- il produit des erreurs d'affectation ;
- chaque réclamation mal routée perd des jours avant d'arriver au bon service.

**Question analytique.** Peut-on affecter automatiquement une réclamation écrite au bon service interne, avec une confiance suffisante pour supprimer le tri manuel sur une part mesurable du flux ?

**Décision appuyée.** Le livrable principal n'est pas un score F1. C'est un **seuil de confiance** accompagné de son impact :
- au-dessus du seuil, la réclamation est routée automatiquement ;
- en dessous, elle part en revue humaine ;
- pour chaque seuil possible, on chiffre le volume traité automatiquement, le taux d'erreur et le temps économisé.

### Parties prenantes

| Acteur | Besoin | Ce que le projet lui fournit |
|---|---|---|
| Direction Qualité / Relation client | Réduire les délais de traitement | Part du flux routable automatiquement, temps économisé |
| Chefs de service (Monétique, Crédits…) | Recevoir uniquement leurs dossiers | Précision par service, matrice de confusion |
| Conformité | Traçabilité des décisions automatiques | Journal des prédictions, score de confiance, revue humaine sous le seuil |
| DSI / Data | Déployabilité | Latence d'inférence, taille du modèle, pipeline reproductible |

---

## 2. Périmètre

**Inclus**
- Réclamations dont le narratif est non vide.
- Produits correspondant à un service de banque de détail (voir section 3).
- Une fenêtre temporelle récente où la taxonomie des produits reste stable. Elle sera fixée au profilage.

**Exclu, avec justification**

| Élément exclu | Raison |
|---|---|
| *Credit reporting* (bureaux de crédit US) | Pas d'équivalent direct dans l'organisation d'une banque camerounaise, et ce produit domine le volume de la base, ce qui fausserait l'évaluation. Son volume sera tout de même mesuré au profilage pour documenter la décision. |
| Prédiction de la réponse de l'entreprise | Ce n'est pas le problème de routage. |
| Analyse de sentiment | Hors sujet : toutes les réclamations sont négatives par nature. |
| Données synthétiques | Pour un recruteur bancaire, un corpus réel a beaucoup plus de valeur. |

---

## 3. Variable cible : correspondance produits CFPB → services internes

> **Tous les libellés CFPB ci-dessous doivent être confirmés au profilage.** Ils sont donnés de mémoire et la taxonomie a changé plusieurs fois depuis 2011. Le fichier de correspondance définitif (`config/label_mapping.yaml`) ne sera figé qu'après lecture des valeurs réellement présentes dans les données.

| Service interne (classe cible) | Produits CFPB probables (à confirmer) |
|---|---|
| Comptes & Dépôts | Checking or savings account |
| Monétique | Credit card ; Prepaid card |
| Transferts & Paiements | Money transfer, virtual currency, or money service |
| Crédits aux particuliers | Vehicle loan or lease ; Payday / title / personal loan ; Student loan (option, car spécifique aux US) |
| Crédit immobilier | Mortgage |
| Recouvrement | Debt collection |

**Cible secondaire (optionnelle, après la candidature).** Le champ *Issue* permet un routage plus fin à l'intérieur de chaque service, par exemple « frais contestés » ou « fraude sur carte ».

---

## 4. Indicateurs de succès (définis avant de modéliser)

### KPI modèle

| KPI | Rôle | Pourquoi ce choix |
|---|---|---|
| **Macro-F1** | Indicateur principal | Les classes sont déséquilibrées : une moyenne pondérée masquerait les petits services. |
| Rappel par service | Contrôle | Un service oublié par le modèle devient un problème opérationnel. |
| Accuracy top-2 | Complément | Mesure l'intérêt d'une suggestion de deux services à l'agent humain. |
| Écart DistilBERT vs baseline TF-IDF | Justification du coût | Le Transformer ne se justifie que s'il apporte un gain mesurable. |

### KPI métier (le chiffre qui intéresse la banque)

- **Couverture au seuil de précision 95 %.** Part des réclamations routables automatiquement tout en gardant une précision d'au moins 95 %.
- **Temps de tri économisé.** Formule :
  `volume mensuel × couverture × temps de tri manuel par réclamation`
  Le temps de tri manuel est une **hypothèse**, pas une mesure. On la présente avec une analyse de sensibilité entre 1 et 5 minutes.
- **Coût des erreurs.** Nombre de réclamations mal routées au-dessus du seuil, multiplié par le délai de re-routage.

### KPI de déployabilité

- Latence d'inférence par réclamation sur CPU.
- Taille du modèle sur disque.

---

## 5. Hypothèses et risques

| Risque | Impact | Mesure prévue |
|---|---|---|
| Corpus en anglais, alors que les clients d'Afriland écrivent en français | Le modèle entraîné n'est pas directement transférable | C'est le pipeline qui se transfère, pas les poids du modèle : un réentraînement sur des réclamations françaises serait nécessaire. Test multilingue possible en option. |
| Taxonomie des produits modifiée dans le temps | Étiquettes incohérentes d'une période à l'autre | Profil de la distribution produit × mois, puis choix d'une fenêtre stable |
| Données personnelles masquées par « XXXX » | Bruit dans le texte | Mesure en Phase 1, traitement en Phase 2 |
| Seuls les narratifs dont le client a consenti à la publication sont présents | Échantillon non représentatif | Documenté comme limite dans le README |
| Doublons entre exports | Fuite entre jeux d'entraînement et de test | Contrôle d'unicité sur l'identifiant de réclamation, puis sur le texte |
| Volume important et entraînement du Transformer | Temps de calcul | Échantillon stratifié ; GPU gratuit (Colab ou Kaggle) en Phase 4 |
| Classes déséquilibrées | Petits services mal appris | Macro-F1, pondération des classes, échantillonnage stratifié |

---

## 6. Stratégie d'acquisition des données

1. **Sonder les sources.** Envoyer une requête HEAD sur les 21 URL pour relever le statut HTTP, la taille et la date de modification. Aucun téléchargement à ce stade.
2. **Télécharger les exports récents.** Commencer par les exports 15 à 21 (janvier à août 2026).
3. **Profiler :** volume de narratifs par produit, stabilité de la taxonomie, doublons.
4. **Vérifier le critère de volume.** Il faut au moins 2 000 narratifs par classe retenue. Si ce n'est pas atteint, étendre la fenêtre vers le passé, export par export, tant que la taxonomie reste stable.

Démarre le téléchargement dès maintenant, même si le projet 3 est planifié du 12 au 16 octobre. Il tourne en arrière-plan pendant que tu avances sur les projets 1 et 2.

### Liste complète des exports (lien direct, vérifiés sur la page le 26/09/2026)

| n° | Période | URL |
|---|---|---|
| 21 | Août 2026 | https://files.consumerfinance.gov/f/documents/CCDB_Export_21_August_2026.zip |
| 20 | Juillet 2026 | https://files.consumerfinance.gov/f/documents/CCDB_Export_20_July_2026.zip |
| 19 | Juin 2026 | https://files.consumerfinance.gov/f/documents/CCDB_Export_19_June_2026.zip |
| 18 | Mai 2026 | https://files.consumerfinance.gov/f/documents/CCDB_Export_18_May_2026.zip |
| 17 | Avril 2026 | https://files.consumerfinance.gov/f/documents/CCDB_Export_17_April_2026.zip |
| 16 | Mars 2026 | https://files.consumerfinance.gov/f/documents/CCDB_Export_16_March_2026.zip |
| 15 | Janv.–févr. 2026 | https://files.consumerfinance.gov/f/documents/CCDB_Export_15_January_2026_through_February_2026.zip |
| 14 | Nov.–déc. 2025 | https://files.consumerfinance.gov/f/documents/CCDB_Export_14_November_2025_through_December_2025.zip |
| 13 | Sept.–oct. 2025 | https://files.consumerfinance.gov/f/documents/CCDB_Export_13_September_2025_through_October_2025.zip |
| 12 | Juil.–août 2025 | https://files.consumerfinance.gov/f/documents/CCDB_Export_12_July_2025_through_August_2025.zip |
| 11 | Mai–juin 2025 | https://files.consumerfinance.gov/f/documents/CCDB_Export_11_May_2025_through_June_2025.zip |
| 10 | Mars–avr. 2025 | https://files.consumerfinance.gov/f/documents/CCDB_Export_10_March_2025_through_April_2025.zip |
| 9 | Janv.–févr. 2025 | https://files.consumerfinance.gov/f/documents/CCDB_Export_9_January_2025_through_February_2025.zip |
| 8 | Nov.–déc. 2024 | https://files.consumerfinance.gov/f/documents/CCDB_Export_8_November_2024_through_December_2024.zip |
| 7 | Août–oct. 2024 | https://files.consumerfinance.gov/f/documents/CCDB_Export_7_August_2024_through_October_2024.zip |
| 6 | Avr.–juil. 2024 | https://files.consumerfinance.gov/f/documents/CCDB_Export_6_April_2024_through_July_2024.zip |
| 5 | Sept. 2023–mars 2024 | https://files.consumerfinance.gov/f/documents/CCDB_Export_5_September_2023_through_March_2024.zip |
| 4 | Nov. 2022–août 2023 | https://files.consumerfinance.gov/f/documents/CCDB_Export_4_November_2022_through_August_2023.zip |
| 3 | Mai 2021–oct. 2022 | https://files.consumerfinance.gov/f/documents/CCDB_Export_3_May_2021_through_October_2022.zip |
| 2 | Mai 2018–avr. 2021 | https://files.consumerfinance.gov/f/documents/CCDB_Export_2_May_2018_through_April_2021.zip |
| 1 | Déc. 2011–avr. 2018 | https://files.consumerfinance.gov/f/documents/CCDB_Export_1_December_2011_through_April_2018.zip |

**Référence officielle des champs** (écrite pour la base en ligne ; sa correspondance avec l'archive reste à vérifier) : https://cfpb.github.io/api/ccdb/fields.html

**Licence.** Données publiques du gouvernement américain.

---

## 7. Arborescence du dépôt GitHub

> Mise à jour du 05/10/2026 : arborescence alignée sur l'état réel du dépôt (acquisition manuelle des CSV, scripts ajoutés en Phase 1 et 2a).

```
bank-complaint-routing-nlp/
├── README.md
├── requirements.txt
├── .gitignore
├── config/
│   ├── config.yaml              # URL, exports sélectionnés, chemins
│   └── label_mapping.yaml       # produits CFPB → services (figé en fin de Phase 1)
├── data/                        # non versionné
│   ├── raw/                     # 21 CSV extraits manuellement + MANIFEST.json (sha256 des CSV)
│   ├── interim/                 # parquet typé, non nettoyé
│   └── processed/               # Phase 2+
├── sql/
│   └── 01_profiling.sql
├── src/
│   └── data/
│       ├── common.py
│       ├── probe_sources.py
│       ├── register_local.py    # remplace download.py + extract.py (zip non conservés)
│       ├── build_interim.py
│       ├── profile_report.py
│       └── audit_text.py        # Phase 2a
├── notebooks/
│   └── 01_data_acquisition_profiling.ipynb
├── docs/
│   ├── 01_cadrage.md            # ce document, version dépôt
│   └── data_dictionary.md       # généré à partir des colonnes réelles
├── reports/
│   ├── source_probe.csv
│   ├── phase1_profile.md
│   └── figures/
└── models/                      # Phase 3+, non versionné
```

---

## 8. Critères de sortie de la Phase 1

Aucune de ces conditions n'est optionnelle. La Phase 2 ne démarre que lorsqu'elles sont toutes remplies.

- [ ] Les 21 URL sont sondées, et les statuts et tailles sont enregistrés dans `reports/source_probe.csv`.
- [ ] Les exports sélectionnés sont téléchargés, avec leur empreinte sha256 dans `MANIFEST.json`.
- [ ] Le format interne des zip est identifié, et le schéma réel des colonnes est documenté dans `data_dictionary.md`.
- [ ] Le taux de narratifs non vides est mesuré, globalement et par produit.
- [ ] La stabilité de la taxonomie est vérifiée (distribution produit × mois) et la fenêtre temporelle est choisie avec sa justification.
- [ ] L'absence de doublons est vérifiée : identifiant de réclamation d'abord, texte ensuite.
- [ ] Il y a au moins 2 000 narratifs par classe retenue, sinon la fenêtre est étendue.
- [ ] `label_mapping.yaml` est figé à partir des libellés réellement observés.

---

## 9. Feuille de route du projet

| Phase | Contenu | Date cible | Version candidature |
|---|---|---|---|
| 1 | Cadrage et acquisition (ce document) | Lancer maintenant | Oui |
| 2 | Nettoyage du texte (masques XXXX, doublons), exploration textuelle, découpage train/val/test stratifié et figé | 12 oct. | Oui |
| 3 | Baseline TF-IDF + régression logistique et LinearSVC, analyse des erreurs | 13–14 oct. | Oui |
| 4 | Fine-tuning DistilBERT sur GPU Colab ou Kaggle, comparaison avec la baseline | Après le 20 oct. | Non (mention « en cours ») |
| 5 | Courbe couverture/précision, choix du seuil, estimation du temps économisé | 15 oct. (sur la baseline) | Oui, version légère |
| 6 | Tableau de bord Power BI, README final, note d'une page pour la direction Qualité | 16 oct. | README et note seulement |

---
