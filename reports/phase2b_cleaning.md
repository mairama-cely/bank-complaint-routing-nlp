# Nettoyage, dédoublonnage et découpage — Phase 2b

Généré le 2026-10-05 13:03 UTC par `src/data/clean_split.py`.

Périmètre : 2026-01 → 2026-07, correspondance figée — **116,449 lignes** en entrée.

## 1. Narratifs modifiés par règle

`R5_glued_xseq_narratives` = narratifs contenant une séquence de X collée à une lettre (remplacée par R5, faute de séparateur). `R8_dropped_no_letter` = lignes supprimées.

| rule | n_narratives |
|---|---|
| R1_bytes_prefix | 741 |
| R2_literal_escapes | 756 |
| R3_dates | 56336 |
| R4_amounts | 49182 |
| R5_glued_xseq_narratives | 4621 |
| R5_xseq | 92131 |
| R6_collapsed | 61595 |
| R8_dropped_no_letter | 11 |

### Lignes supprimées par R8

| complaint_id | service | narrative_raw |
|---|---|---|
| 18451540 | Recouvrement | XXXX XXXX XXXX XXXX XXXX  XXXX  XXXX XXXX XXXX XXXX XXXX |
| 19515270 | Recouvrement | XXXX XX/XX/year> {$540.00} XXXX XXXX XXXXXX/XX/year> {$42000.00} XXXX XX/XX/year> {$61000.00} |
| 20808661 | Recouvrement | XX/XX/year> XXXX {$75.00}, XXXX XXXX {$470.00}, XXXX, {$700.00}, XXXX {$440.00}, XXXX {$0.00}, XXXX XXXX {$0.00}, XXXX X |
| 22406388 | Recouvrement | XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX  |
| 22977991 | Recouvrement | XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX |
| 23038975 | Comptes & Dépôts | XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX  |
| 23059115 | Comptes & Dépôts | XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX  |
| 24116967 | Recouvrement | XXXX XXXX - XX/XX/year> XXXX XXXX - XX/XX/year> 2023 |
| 24117012 | Recouvrement | XXXX XXXX XXXX - XX/XX/year> XXXX XXXX XXXX - XX/XX/year> 2023 |
| 24123757 | Comptes & Dépôts | XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX  |
| 24513554 | Comptes & Dépôts | XX/XX/year> XXXX XXXX XXXX XX/XX/year> XXXX XXXX XXXX XX/XX/year> XXXX XXXX XXXX XX/XX/year> XXXX XXXX XXXX XX/XX/year>  |

### 5 exemples avant / après

| complaint_id | raw_150 | clean_150 |
|---|---|---|
| 18398362 | I was notified by my management that my company card had been charged for something they nor I recognized. It was for a XXXX subscription which utiliz | I was notified by my management that my company card had been charged for something they nor I recognized. It was for a [REDACTED] subscription which  |
| 18398377 | CONSUMER COMPLAINT TO THE CONSUMER FINANCIAL PROTECTION BUREAU ( CFPB ) Parties Involved Creditor : Discover Bank Debt Collector / Law Firm XXXX XXXX  | CONSUMER COMPLAINT TO THE CONSUMER FINANCIAL PROTECTION BUREAU ( CFPB ) Parties Involved Creditor : Discover Bank Debt Collector / Law Firm [REDACTED] |
| 18398392 | This company is violating my rights they have not provided validation Information Under 12 CFR 1006.34 ( b ) ( 5 ) yet they have placed a collection o | This company is violating my rights they have not provided validation Information Under 12 CFR 1006.34 ( b ) ( 5 ) yet they have placed a collection o |
| 18398408 | My information was heisted and this accounts are fraudulent and do not belong to me. I would like these accounts completely removed from all XX/XX/XXX | My information was heisted and this accounts are fraudulent and do not belong to me. I would like these accounts completely removed from all [DATE] cr |
| 18398430 | In XX/XX/year> I came to Bank of America I applied for XXXX of there credit cards which I got approved for XXXX credit card I had a limit of XXXX XXXX | In [DATE] I came to Bank of America I applied for [REDACTED] of there credit cards which I got approved for [REDACTED] credit card I had a limit of [R |

## 2. Dédoublonnage sur texte nettoyé

Niveau de conflit : `service`. Conservation : plus ancienne date de réception, puis plus petit identifiant.

| n_after_R8 | conflict_texts | conflict_rows_dropped | keep_one_rows_dropped | n_after_dedup |
|---|---|---|---|---|
| 116438 | 24 | 123 | 10008 | 106307 |

Pour comparaison, l'audit 2a (texte brut, niveau `service`) conservait 106,934 lignes.

## 3. Découpage stratifié par service

Proportions cibles 0.7/0.15/0.15, graine 42.

| service | train | val | test | total |
|---|---|---|---|---|
| Comptes & Dépôts | 14906 | 3194 | 3194 | 21294 |
| Crédit immobilier | 5438 | 1165 | 1166 | 7769 |
| Crédits aux particuliers | 9987 | 2140 | 2140 | 14267 |
| Monétique | 15169 | 3250 | 3251 | 21670 |
| Recouvrement | 22084 | 4732 | 4732 | 31548 |
| Transferts & Paiements | 6831 | 1464 | 1464 | 9759 |

## 4. Longueur après nettoyage (mots)

| service | count | mean | std | min | 5% | 50% | 95% | max |
|---|---|---|---|---|---|---|---|---|
| Comptes & Dépôts | 21294.0 | 239.1 | 217.3 | 7.0 | 37.0 | 190.0 | 599.3 | 5300.0 |
| Crédit immobilier | 7769.0 | 326.3 | 315.9 | 9.0 | 58.0 | 247.0 | 855.0 | 4754.0 |
| Crédits aux particuliers | 14267.0 | 246.1 | 224.4 | 6.0 | 34.0 | 200.0 | 600.0 | 5021.0 |
| Monétique | 21670.0 | 251.9 | 221.4 | 4.0 | 38.0 | 206.0 | 612.0 | 4994.0 |
| Recouvrement | 31548.0 | 199.5 | 193.5 | 5.0 | 24.0 | 153.0 | 520.0 | 4830.0 |
| Transferts & Paiements | 9759.0 | 231.1 | 208.7 | 8.0 | 39.0 | 187.0 | 565.1 | 4267.0 |

## 5. Langue (heuristique, aucun filtrage)

Méthode : part des mots outils anglais parmi les mots du texte (≥ 10 mots). Sous 0.15, le texte est signalé ; `spanish_suspect` si la part de mots outils espagnols est supérieure. Heuristique non validée : les signalements sont des indices, pas des étiquettes.

| service | english_likely | non_english_suspect | spanish_suspect | too_short_to_judge |
|---|---|---|---|---|
| Comptes & Dépôts | 21231 | 37 | 0 | 26 |
| Crédit immobilier | 7752 | 14 | 0 | 3 |
| Crédits aux particuliers | 14211 | 28 | 0 | 28 |
| Monétique | 21560 | 51 | 1 | 58 |
| Recouvrement | 31255 | 167 | 2 | 124 |
| Transferts & Paiements | 9740 | 13 | 1 | 5 |

### Exemples signalés (15 premiers)

| complaint_id | service | lang_flag | en_stop_ratio | text_150 |
|---|---|---|---|---|
| 18399180 | Comptes & Dépôts | non_english_suspect | 0.058823529411764705 | [DATE] Charges - Disputed [REDACTED] [AMOUNT] [REDACTED] [AMOUNT] [REDACTED] [AMOUNT] [REDACTED] transactions TOTAL denied by US Bank [REDACTED] |
| 18403438 | Monétique | non_english_suspect | 0.1366906474820144 | Customer paid [REDACTED] for some items from our online store. Decided to sell his vehicle and he doesnt need the products anymore. When he was told b |
| 18422667 | Monétique | spanish_suspect | 0.06060606060606061 | Compr una tarjeta nespend visa starter en walgreens pero no la pude activar ya que perd el plstico fsico antes de abrirla El monto recargado es de $11 |
| 18425342 | Comptes & Dépôts | non_english_suspect | 0.125 | Acct. # [REDACTED] ...... Acct. opened [REDACTED] Acct. closed [DATE] does not give amount owed. Hancock Whitney Bank |
| 18427285 | Crédits aux particuliers | non_english_suspect | 0.125 | [DATE] : excessive hold times, followed by calls just being disconnected, Inability to access statutory rehabilitation rights. |
| 18437662 | Recouvrement | non_english_suspect | 0.125 | Violations FDCPA 809 ( b ) : No validation provided ( contract, payment history, original creditor ). FCRA 623 ( a ) ( 3 ) : Must correct or delete af |
| 18441121 | Monétique | non_english_suspect | 0.14782608695652175 | Consumer Financial Protection Bureau [REDACTED] . [REDACTED] DC [REDACTED] Date : [DATE] Re : Identity Theft Credit Reporting and Inquiry Violations D |
| 18491624 | Recouvrement | non_english_suspect | 0.09090909090909091 | [REDACTED] I am getting repeated phone calls nonstop every single day' |
| 18507542 | Recouvrement | non_english_suspect | 0.1 | Midland Credit Management [REDACTED] ( FCRA + FDCPA [DATE] [REDACTED] FCRA [REDACTED] , [REDACTED] , [REDACTED] Violacin FDCPA [REDACTED] [DATE] DELET |
| 18535731 | Recouvrement | non_english_suspect | 0.14035087719298245 | Experian [REDACTED] . [REDACTED] , [REDACTED] Re : FCRA Dispute Request I am disputing inaccurate and unverifiable information appearing on my Experia |
| 18539883 | Recouvrement | spanish_suspect | 0.03353658536585366 | Presento esta queja formal contra NCB Management Services, Inc. (NCB) por violaciones a la Fair Credit Reporting Act (FCRA) y a la Fair Debt Collectio |
| 18551885 | Recouvrement | non_english_suspect | 0.075 | Aldous & Associates collecting [AMOUNT] [REDACTED] gym debt ( # [REDACTED] , Aldous # [REDACTED] ) without FDCPA validation notice. Demanded proof ( c |
| 18552922 | Comptes & Dépôts | non_english_suspect | 0.1 | Up Dating An File Case # [REDACTED] Case Currently Under Investigation |
| 18555806 | Recouvrement | non_english_suspect | 0.1282051282051282 | [REDACTED] Payment Plan Other [AMOUNT] Status Date Reported [REDACTED] , [REDACTED] Payment Status Payment Plan Account Status Derogatory Account Deta |
| 18578750 | Crédit immobilier | non_english_suspect | 0.07936507936507936 | CFPB Formal Complaint : Auto Loan Payment Processing Failure Complainant : [REDACTED] Phone : [REDACTED] Email : [REDACTED] Address : [REDACTED] , [RE |

## 6. Critères de sortie de la Phase 2b

| Critère | Statut |
|---|---|
| Règles R1 à R8 appliquées, comptées par règle | OK |
| Aucun motif résiduel (X{2,}, year>, scrub>) dans le texte nettoyé | OK |
| Dédoublonnage sur texte nettoyé : aucun texte partagé entre jeux | OK |
| Aucun identifiant partagé entre jeux | OK |
| Stratification : écart max aux proportions cibles ≤ 0,5 point (observé 0.008) | OK |
| Chaque service ≥ 2000 narratifs après nettoyage | OK |
| Jeux écrits avec sha256 (data/processed/MANIFEST.json) | OK |
| Langue mesurée (heuristique, sans filtrage) | OK |
