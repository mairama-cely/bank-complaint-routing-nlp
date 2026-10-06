# Dictionnaire de données — Phase 1

Généré automatiquement par `src/data/build_interim.py` à partir des colonnes réelles des exports sélectionnés [15, 16, 17, 18, 19, 20, 21] (4,851,531 lignes).

Référence officielle des champs : https://cfpb.github.io/api/ccdb/fields.html. Attention : cette référence documente la base en ligne ; sa correspondance avec l'archive FOIA n'est pas vérifiée.

`% null` = valeurs NULL ; `% vide` = chaînes vides après suppression des espaces (colonnes texte).

| Nom original | Nom normalisé | Type DuckDB | % null | % vide | Valeurs distinctes | Exemple (80 car.) |
|---|---|---|---|---|---|---|
| Date received | date_received | DATE | 0.0 | — | 243 | 2026-02-08 |
| Product | product | VARCHAR | 0.0 | 0.0 | 11 | Credit reporting or other personal consumer reports |
| Sub-product | sub_product | VARCHAR | 0.0 | 0.0 | 55 | Credit reporting |
| Issue | issue | VARCHAR | 0.0 | 0.0 | 88 | Problem with a company's investigation into an existing problem |
| Sub-issue | sub_issue | VARCHAR | 1.15 | 0.0 | 209 | Problem with personal statement of dispute |
| Consumer complaint narrative | consumer_complaint_narrative | VARCHAR | 97.5 | 0.0 | 109,631 | I requested a refund of a payment ( {$40000.00} ). I requested this refund becau |
| Company public response | company_public_response | VARCHAR | 45.75 | 0.0 | 10 | Company has responded to the consumer and the CFPB and chooses not to provide a  |
| Company | company | VARCHAR | 0.0 | 0.0 | 3,682 | CITIBANK, N.A. |
| State | state | VARCHAR | 0.1 | 0.0 | 61 | NY |
| ZIP code | zip_code | VARCHAR | 0.05 | 0.0 | 22,576 | 11727 |
| Tags | tags | VARCHAR | 97.87 | 0.0 | 3 | Servicemember |
| Submitted via | submitted_via | VARCHAR | 0.0 | 0.0 | 4 | Web |
| Date sent to company | date_sent_to_company | DATE | 0.0 | — | 252 | 2026-02-08 |
| Company response to consumer | company_response_to_consumer | VARCHAR | 0.0 | 0.0 | 5 | Closed with non-monetary relief |
| Timely response? | timely_response | VARCHAR | 0.0 | 0.0 | 2 | Yes |
| Complaint ID | complaint_id | VARCHAR | 0.0 | 0.0 | 4,851,531 | 19343334 |

Colonnes ajoutées par le pipeline : `source_export_id` (id de l'export d'origine), `received_month` (AAAA-MM dérivé de la date de réception).

Conversions de dates :

- `date_received` : convertie en DATE (format `%Y-%m-%d`)
- `date_sent_to_company` : convertie en DATE (format `%Y-%m-%d`)
