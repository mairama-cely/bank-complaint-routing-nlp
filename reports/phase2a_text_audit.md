# Audit du texte — Phase 2a

Généré le 2026-10-05 12:56 UTC par `src/data/audit_text.py`. Mesures uniquement : aucune ligne modifiée ni supprimée.

Périmètre : narratifs reçus de 2026-01 à 2026-07, produits de `config/label_mapping.yaml` (figé) — **116,449 lignes**.

Motifs mesurés (expressions régulières RE2) :
- date : `[X0-9]{2}/[X0-9]{2}/[X0-9]{2,4}` ; séquence de X hors date : `\bX{2,}\b` ; accolades : `\{[^}]{0,40}\}`.

## A4 — Couverture des motifs

| n_narratives | pct_with_date_pattern | pct_with_other_xseq | pct_with_brace |
|---|---|---|---|
| 116449 | 26.83 | 81.83 | 42.26 |

## A1 — Formes des motifs de date (chiffres → 9)

| shape | n_occurrences |
|---|---|
| XX/XX/XXXX | 117896 |
| XX/XX/9999 | 4663 |
| XX/XX/99 | 535 |
| 99/99/9999 | 38 |
| 99/99/99 | 26 |
| XX/XX/9XXX | 5 |
| XX/XX/999 | 5 |
| XX/XX/999X | 2 |
| 99/99/XXXX | 1 |
| XX/XX/99XX | 1 |
| XX/XX/XX | 1 |

## A2 — Séquences de X hors dates (longueur)

| n_x | n_occurrences |
|---|---|
| 4 | 1070079 |
| 2 | 120838 |
| 8 | 21455 |
| 6 | 245 |
| 12 | 98 |
| 3 | 7 |
| 5 | 4 |
| 11 | 1 |
| 17 | 1 |
| 7 | 1 |

## A3 — Formes entre accolades (chiffres → 9)

| shape | n_occurrences |
|---|---|
| {$999.99} | 51367 |
| {$9999.99} | 48650 |
| {$99.99} | 19544 |
| {$99999.99} | 16712 |
| {$9.99} | 7612 |
| {$999999.99} | 3530 |
| {>= $9,999,999} | 137 |
| {$.99} | 43 |
| {$XXXX} | 41 |
| { XXXX } | 13 |
| { ChatWindowButton : 9. Yes, 9. No } | 5 |
| { XXXX : XXXX } | 4 |
| { case number } | 3 |
| {XXXX} | 3 |
| { / collections. } | 3 |
| { " status '' => " unavailable '' } | 2 |
| { s } | 2 |
| { b } | 2 |
| { Date } | 2 |
| { List Account here } | 2 |
| { Your Full Name } | 2 |
| { {$9999.99} | 2 |
| { Your Address } | 2 |
| { City, State, ZIP Code } | 2 |
| { Account Number } | 2 |
| { " type '' => " XXXX '' } | 1 |
| {$9
999.99} | 1 |
| { SELF FINANCIAL/LEAD BANK } | 1 |
| { Creditor or Credit Bureau Name } | 1 |
| { Creditor Name } | 1 |

## A5 — Longueur par service

`n_only_masks` = narratifs sans aucun mot une fois dates, X et accolades retirés.

| service | n | min_words | p5 | median | p95 | max_words | n_lt10 | n_lt20 | n_only_masks |
|---|---|---|---|---|---|---|---|---|---|
| Recouvrement | 41306 | 5 | 28.0 | 131.0 | 476.0 | 4643 | 102 | 1170 | 3 |
| Monétique | 21897 | 6 | 35.0 | 205.0 | 615.0 | 4950 | 66 | 387 | 0 |
| Comptes & Dépôts | 21335 | 7 | 37.0 | 190.0 | 601.0 | 5347 | 23 | 332 | 3 |
| Crédits aux particuliers | 14332 | 5 | 34.0 | 200.0 | 603.0 | 4997 | 25 | 269 | 0 |
| Transferts & Paiements | 9807 | 8 | 39.0 | 186.0 | 571.7 | 4324 | 5 | 121 | 0 |
| Crédit immobilier | 7772 | 9 | 58.0 | 247.0 | 860.4 | 4792 | 3 | 51 | 0 |

## A6 — 15 narratifs les plus courts (200 premiers caractères)

| complaint_id | service | n_words | narrative_200 |
|---|---|---|---|
| 18671898 | Crédits aux particuliers | 5 | XX/XX/year>.  Incorrect collection financial amount. |
| 22451956 | Recouvrement | 5 | Reference complaint XXXX New documentation |
| 18667393 | Recouvrement | 6 | XXXX account ending XXXX information inaccurate |
| 18876396 | Monétique | 6 | personal information forwarded without my consent. |
| 21287658 | Monétique | 6 | b'Defendant lack sufficient knowledge therefore denies' |
| 21291481 | Monétique | 6 | Credit builder card unauthorized transaction {$1500.00} |
| 22354405 | Recouvrement | 6 | False collection attempts and inaccurate reporting |
| 23073083 | Recouvrement | 6 | Creditor-Trueaccord corp Account-XXXX Opened-XXXX Balance- {$170.00} |
| 18444568 | Comptes & Dépôts | 7 | See attached dispute timeline and supporting documentation |
| 18587826 | Crédits aux particuliers | 7 | Account was in forbearance/deferment and reported inaccurately. |
| 19878820 | Recouvrement | 7 | JEFFERSON CAPITAL SYST Balance {$2200.00} on XX/XX/year> |
| 20109370 | Recouvrement | 7 | b'Requested information didnt receive still on credit' |
| 20173244 | Recouvrement | 7 | XXXX XXXX XXXX Last reported XX/XX/year> {$2000.00} |
| 21854474 | Recouvrement | 7 | b'These cards were closed in XXXXXXXX XXXX |
| 22236759 | Recouvrement | 7 | Non communication under laws governing debt collection |

## A7 — Effet de la règle de dédoublonnage dans le périmètre

| n_rows_scope | n_texts_duplicated | n_rows_duplicated | n_texts_multi_product | n_rows_multi_product | n_texts_multi_service | n_rows_multi_service | n_rows_after_rule |
|---|---|---|---|---|---|---|---|
| 116449 | 1286 | 10781.0 | 22 | 111.0 | 20 | 106.0 | 106932 |

La règle validée porte sur les **produits** (Phase 1 : 43 textes / 245 lignes, mesurés hors périmètre, Credit reporting et août inclus). Les colonnes `multi_service` indiquent combien de ces conflits subsistent si deux produits du même service (ex. Credit card / Prepaid card) ne sont pas considérés comme un conflit.

## A8 — Effectifs par service après la règle (conflits au niveau `service`), et découpage attendu

| service | n_after_rule | train_approx | val_approx | test_approx |
|---|---|---|---|---|
| Recouvrement | 32139 | 22497 | 4821 | 4821 |
| Monétique | 21683 | 15178 | 3252 | 3253 |
| Comptes & Dépôts | 21303 | 14912 | 3195 | 3196 |
| Crédits aux particuliers | 14276 | 9993 | 2141 | 2142 |
| Transferts & Paiements | 9763 | 6834 | 1464 | 1465 |
| Crédit immobilier | 7770 | 5439 | 1166 | 1165 |

Lignes conservées après la règle : **106,934** sur 116,449.

## A9 — Artefacts non captés par A1 à A3

### A9c — Couverture

| n_narratives | n_bytes_prefix | n_bytes_prefix_and_quote_end | n_with_date_letters | n_with_angle_bracket | n_with_literal_escape |
|---|---|---|---|---|---|
| 116449 | 741 | 543 | 30096 | 29805 | 757 |

### A9a — Formes date + lettres (chiffres → 9)

| shape | n_occurrences |
|---|---|
| XX/XX/year> | 59074 |
| XX/XX/year>XXXX | 663 |
| XX/XX/scrub> | 387 |
| XX/XX/scrub>XXXX | 273 |
| XX/XX/XXXXe | 119 |
| XX/XX/XXXXdays | 110 |
| XX/XX/XXXXand | 66 |
| XX/XX/XXXXyears | 32 |
| XX/XX/XXXXmonths | 31 |
| XX/XX/XXXXcredit | 22 |
| XX/XX/XXXXThe | 18 |
| XX/XX/XXXXaccount | 17 |
| XX/XX/XXXXday | 16 |
| XX/XX/XXXXtime | 15 |
| XX/XX/XXXXto | 14 |
| XX/XX/XXXXfor | 14 |
| XX/XX/XXXXyear | 11 |
| XX/XX/XXXXwith | 10 |
| XX/XX/XXXXon | 10 |
| XX/XX/XXXXmonth | 10 |
| XX/XX/XXXXof | 9 |
| XX/XX/XXXXes | 9 |
| XX/XX/XXXXwas | 8 |
| XX/XX/XXXXthat | 8 |
| XX/XX/year>XX | 8 |
| XX/XX/XXXXfrom | 7 |
| XX/XX/XXXXas | 7 |
| XX/XX/XXXXhas | 7 |
| XX/XX/XXXXOn | 7 |
| XX/XX/XXXXThis | 6 |

### A9b — Jetons contenant < ou > (chiffres → 9)

| shape | n_occurrences |
|---|---|
| XX/XX/year> | 25384 |
| XX/XX/year>, | 22145 |
| XX/XX/year>. | 10656 |
| XX/XX/year>XXXX | 654 |
| XX/XX/scrub> | 294 |
| XX/XX/year>9999 | 270 |
| > | 261 |
| XX/XX/scrub>XXXX | 254 |
| XXXXXX/XX/year> | 190 |
| XX/XX/year>9999, | 161 |
| {>= | 140 |
| XX/XX/scrub>, | 89 |
| XX/XX/year>9999. | 87 |
| -> | 84 |
| XX/XX/year>- | 39 |
| XXXXXX/XX/year>, | 27 |
| => | 18 |
| XXXXXX/XX/year>. | 17 |
| XX/XX/year>.. | 15 |
| XX/XX/year>! | 11 |
| < | 11 |
| XX/XX/year>? | 10 |
| XXXXXX/XX/year>XXXX | 8 |
| XX/XX/scrub>XXXX/9999 | 6 |
| <> | 5 |
| XXXXXX/XX/XXXXXX/XX/year> | 5 |
| XX/XX/year>99 | 4 |
| XXXX/9999XX/XX/year>. | 4 |
| >Collection< | 4 |
| <image999.png> | 4 |

### A9d — Narratifs commençant par b' ou b" (10 exemples)

| complaint_id | service | start_120 | end_40 |
|---|---|---|---|
| 18399889 | Monétique | b'Formal Complaint Regarding Closed Credit Account Handling\nDispute of JP Morgan Chase Banks Procedures and Legal Actio | XXX\nXXXX XXXX XXXX\nXXXX XXXX XXXX XXXX |
| 18401401 | Transferts & Paiements | b"Date of incident that occurred regarding claimant victim that was victim of identity theft and that I was eligible to  |  XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX |
| 18403037 | Monétique | b'I was deceived by XXXX XXXX  to take cash in advance from my credit cards in the amount of XXXX  dollars.  $XXXX  from | et my money back.  \n\nSee attachments.' |
| 18404939 | Recouvrement | b'DATA REMOVAL DIRECTIVE\nInformation Improperly Used and Required to Be Permanently Deleted\n\nNationstar Mortgage LLC  | within the CFPBs supervisory authority.' |
| 18411351 | Transferts & Paiements | b"Cash App\nXXXX XXXXn\nRouting number: XXXX XXXX XXXXAccount number: XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXXEmail: | ontacting them no one will tell me why." |
| 18416680 | Crédits aux particuliers | b'Illegally took my information around the credit report without my regards' | nd the credit report without my regards' |
| 18422667 | Monétique | b'Compr una tarjeta nespend visa starter  en walgreens pero no la pude activar ya que perd el plstico fsico antes de abr | e $110 \nEl da 01/01/2026 a las 8:25 PM' |
| 18425644 | Recouvrement | b'I received a bogus call from someone saying they are with Advance Financial XXXX XXXX XXXX, as a collection agency. Ca | machine, but left info.with fraud dept.' |
| 18431499 | Monétique | b'American Express gift card - keeps getting declined' | ress gift card - keeps getting declined' |
| 18432900 | Comptes & Dépôts | b'Dear CFPB,\n\nI am submitting a complaint regarding charges that appeared on my account between XXXX XXXX and XXXX XXX | XXX XXXX XXXXEmail: XXXXPhone: XXXX XXXX |

## Décisions attendues pour la Phase 2b

1. Expressions régulières définitives des jetons `[DATE]` et `[REDACTED]` (à partir de A1 et A2).
2. Traitement des formes entre accolades (A3).
3. Conflit au niveau produit (règle validée) ou au niveau service (A7).
4. Narratifs sans aucun mot hors masques (A5, `n_only_masks`).
