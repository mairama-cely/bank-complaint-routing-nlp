# Évaluation finale — Phase 3c-ii

Généré le 2026-10-05 21:37 UTC par `src/models/evaluate_final.py`. **Première évaluation du test** : verrou créé (reports/phase3c/TEST_LOCK.json).

Variante de référence : `company_masked`. Intervalles : bootstrap percentile, 1000 tirages.

## 1. Métriques globales

| dataset | variant | n | macro_f1 | macro_f1_ci95 | accuracy | top2_accuracy |
|---|---|---|---|---|---|---|
| test_2026 | as_is | 15947 | 0.8434 | [0.8373 ; 0.8495] | 0.8519 | 0.9512 |
| test_2026 | company_masked | 15947 | 0.8283 | [0.8219 ; 0.8346] | 0.8393 | 0.9435 |
| external_2025 | as_is | 251388 | 0.8517 | [0.8503 ; 0.8532] | 0.8515 | 0.9498 |
| external_2025 | company_masked | 251388 | 0.8423 | [0.8408 ; 0.8438] | 0.8436 | 0.9446 |

## 2. Écart dû aux noms d'entreprises (as_is − company_masked, bootstrap apparié)

| dataset | gap_as_is_minus_masked | gap_ci95 |
|---|---|---|
| test_2026 | 0.0152 | [0.0115 ; 0.0186] |
| external_2025 | 0.0093 | [0.0085 ; 0.0101] |

Le masquage étant incomplet (décision 3a), cet écart est une borne basse de la dépendance aux noms.

## 3. Rappel par service — `company_masked`

| service | external_2025 | test_2026 |
|---|---|---|
| Comptes & Dépôts | 0.8323 | 0.8118 |
| Crédit immobilier | 0.8794 | 0.9091 |
| Crédits aux particuliers | 0.8068 | 0.828 |
| Monétique | 0.7818 | 0.8216 |
| Recouvrement | 0.9165 | 0.9169 |
| Transferts & Paiements | 0.7978 | 0.6482 |

Détail précision / rappel / F1 : `reports/phase3c/per_service.csv`.

## 4. Calibrage (confiance de la classe prédite)

| dataset | variant | ece | brier |
|---|---|---|---|
| test_2026 | as_is | 0.0332 | 0.2256 |
| test_2026 | company_masked | 0.0338 | 0.2414 |
| external_2025 | as_is | 0.0359 | 0.225 |
| external_2025 | company_masked | 0.0381 | 0.2358 |

ECE sur 15 intervalles égaux ; Brier multiclasse. Le LinearSVC a été calibré sur la validation (Phase 3b). Figure : `reports/figures/phase3c_reliability.png`.

### Table de fiabilité — test_2026, `company_masked`

| bin | n | mean_confidence | accuracy | gap |
|---|---|---|---|---|
| 0.20-0.27 | 13 | 0.2471 | 0.3077 | 0.0605 |
| 0.27-0.33 | 96 | 0.3091 | 0.3438 | 0.0346 |
| 0.33-0.40 | 282 | 0.3694 | 0.3652 | -0.0042 |
| 0.40-0.47 | 432 | 0.4366 | 0.4977 | 0.0611 |
| 0.47-0.53 | 811 | 0.5019 | 0.5253 | 0.0234 |
| 0.53-0.60 | 899 | 0.5675 | 0.6096 | 0.042 |
| 0.60-0.67 | 975 | 0.6339 | 0.6821 | 0.0482 |
| 0.67-0.73 | 1129 | 0.7012 | 0.7626 | 0.0614 |
| 0.73-0.80 | 1381 | 0.7686 | 0.7972 | 0.0287 |
| 0.80-0.87 | 1948 | 0.8356 | 0.885 | 0.0494 |
| 0.87-0.93 | 3191 | 0.903 | 0.9436 | 0.0406 |
| 0.93-1.00 | 4790 | 0.9652 | 0.9797 | 0.0145 |

## 5. Matrices de confusion — `company_masked` (lignes = vrai, colonnes = prédit)

### test_2026

| vrai \ prédit | Comptes & Dépôts | Crédit immobilier | Crédits aux particuliers | Monétique | Recouvrement | Transferts & Paiements |
|---|---|---|---|---|---|---|
| Comptes & Dépôts | 2593 | 7 | 28 | 234 | 49 | 283 |
| Crédit immobilier | 15 | 1060 | 58 | 17 | 15 | 1 |
| Crédits aux particuliers | 55 | 11 | 1772 | 100 | 187 | 15 |
| Monétique | 256 | 8 | 54 | 2671 | 194 | 68 |
| Recouvrement | 59 | 25 | 156 | 138 | 4339 | 15 |
| Transferts & Paiements | 391 | 6 | 14 | 89 | 15 | 949 |

### external_2025

| vrai \ prédit | Comptes & Dépôts | Crédit immobilier | Crédits aux particuliers | Monétique | Recouvrement | Transferts & Paiements |
|---|---|---|---|---|---|---|
| Comptes & Dépôts | 39329 | 121 | 446 | 2912 | 858 | 3585 |
| Crédit immobilier | 232 | 12332 | 731 | 293 | 398 | 37 |
| Crédits aux particuliers | 721 | 184 | 24276 | 1413 | 3306 | 188 |
| Monétique | 3309 | 74 | 755 | 33586 | 4219 | 1017 |
| Recouvrement | 806 | 446 | 2415 | 2585 | 70687 | 185 |
| Transferts & Paiements | 6154 | 69 | 254 | 1121 | 479 | 31865 |

## 6. Paires les plus confondues — test_2026, `company_masked`

| service | pred | n_errors | share_of_true_service_pct |
|---|---|---|---|
| Transferts & Paiements | Comptes & Dépôts | 391 | 26.71 |
| Comptes & Dépôts | Transferts & Paiements | 283 | 8.86 |
| Monétique | Comptes & Dépôts | 256 | 7.87 |
| Comptes & Dépôts | Monétique | 234 | 7.33 |
| Monétique | Recouvrement | 194 | 5.97 |
| Crédits aux particuliers | Recouvrement | 187 | 8.74 |

### Exemples (3 par paire, 300 premiers caractères)

| true | pred | complaint_id | confidence | text_300 |
|---|---|---|---|---|
| Transferts & Paiements | Comptes & Dépôts | 18399447 | 0.669 | Basically, my Cashapp account was hacked and used to complete fraudulent transaction. Funds were being taken from my account without my permission. When I finally notified customer service, they would ask me if I had proof that it was not me completing the transaction. Well, I did not have any proof |
| Transferts & Paiements | Comptes & Dépôts | 18401397 | 0.449 | Sometime around [REDACTED] of [REDACTED] disputed every transaction we ever had with [REDACTED] . [REDACTED] purchased many items from me for his new place. He also received each of these items. [REDACTED] issued the refund without allowing me to explain that each of the charges was very valid and I |
| Transferts & Paiements | Comptes & Dépôts | 18402258 | 0.442 | On the [REDACTED] of [DATE] i erroneously zelle [AMOUNT] to a contact from phone whom i have no connection ftom my citbank account. Upon noticing this error i sent the unintended receipient a text asking for the erroneous funds to be returned. This request was denied. I called my bank ( [REDACTED] ) |
| Comptes & Dépôts | Transferts & Paiements | 18399899 | 0.593 | Issue : Unauthorized transaction and account takeover [COMPANY] refused reimbursement I am filing a complaint regarding an unauthorized transaction on my [COMPANY] account and [COMPANY] refusal to reimburse the funds despite clear evidence of account takeover fraud. Summary of the problem I live in  |
| Comptes & Dépôts | Transferts & Paiements | 18400256 | 0.806 | On [DATE] 2025, I was messaged through [REDACTED] from someone claiming to be an agent from [REDACTED] ( not a typo, and the only [REDACTED] with the blue checkmark in the profile ) who runs an online gaming casino and wanted me to play on their platforms, I agreed to give them a shot and they sent  |
| Comptes & Dépôts | Transferts & Paiements | 18401135 | 0.793 | In 2025 my cash app was permanently closed due to terms of violation they said they send me a email to respond but I never received an email |
| Monétique | Comptes & Dépôts | 18404906 | 0.738 | On [DATE] Ive mistakenly made two [REDACTED] payments of [REDACTED] right after each other I called [REDACTED] for both refunds only [REDACTED] payment of [REDACTED] was refunded to me I called [REDACTED] I was told they released the other [AMOUNT] to [COMPANY] then I was given a date [DATE] my mone |
| Monétique | Comptes & Dépôts | 18413897 | 0.786 | On or around [REDACTED] unauthorized ACH withdrawals were taken from my account by [REDACTED] ( also known as [REDACTED] / [REDACTED] ) and Fizz. I did not authorize these charges and did not consent to any recurring withdrawals from these companies. I contacted both companies to request an explanat |
| Monétique | Comptes & Dépôts | 18422195 | 0.516 | I am submitting a new complaint because U.S. Bank has failed to resolve an issue that resulted from repeated misinformation provided by its own representatives and has not provided any effective escalation channel to address the harm caused. I applied for a U.S. Bank [REDACTED] and fully met the pro |
| Comptes & Dépôts | Monétique | 18408691 | 0.608 | It is unacceptable for [COMPANY] to display third-party commercial advertising within a clients private online banking portal. Both a [REDACTED] advertisement and a [REDACTED] advertisement have individually appeared at the top of my checking account page, above transactions and below account totals |
| Comptes & Dépôts | Monétique | 18425773 | 0.609 | I am filing a complaint regarding [COMPANY] handling of a debit card dispute involving merchant impersonation. I made a [AMOUNT] debit card payment through an online form that represented itself as an official booking desk or authorized agent of [REDACTED] . The merchant was later revealed to be [RE |
| Comptes & Dépôts | Monétique | 18446455 | 0.358 | I was attempting to use [COMPANY] to make a " Pay-in-four '' purchase of approximately [AMOUNT] from [REDACTED] . I was in the checkout section of an online purchase with the [COMPANY] app. I went to complete my purchase with [REDACTED] and my transaction was declined. It was at this point that I re |
| Monétique | Recouvrement | 18399448 | 0.987 | I was contacted by a collection agency and I sent a cease and desist with a debt validation letter. the account is still reporting and there has been no change for what is reporting on my credit report |
| Monétique | Recouvrement | 18407798 | 0.454 | [REDACTED] : [REDACTED] dba [REDACTED] Lines hired [REDACTED] from [REDACTED] , RI [REDACTED] , Florida. The move occurred on [DATE] . The moving company required me to take photos of the paperwork instead of giving me a hard copy. When the movers arrived in [REDACTED] , it was raining. requested th |
| Monétique | Recouvrement | 18409505 | 0.338 | Re : Credit Report Dispute [COMPANY] Late Payment ( [AMOUNT] Balance ) To Whom It May Concern, I am writing to formally dispute a late payment reported by [COMPANY] on my credit report relating to an alleged [AMOUNT] outstanding balance. This negative reporting is inaccurate and incomplete. Prior to |
| Crédits aux particuliers | Recouvrement | 18424974 | 0.699 | To Whom It May Concern, I am writing to formally dispute inaccurate information being reported on my consumer credit report, pursuant to the Fair Credit Reporting Act ( FCRA ), specifically 15 U.S.C. 1681s-2, which imposes a duty on furnishers to provide accurate and complete information. The accoun |
| Crédits aux particuliers | Recouvrement | 18425277 | 0.749 | [REDACTED] continues to send communications reflecting incorrect and inconsistent amounts owed despite a confirmed settlement agreement. Continued Use of Incorrect Balance After Settlement On [REDACTED] and I agreed to settle the account for a total of [AMOUNT] , payable in three biweekly installmen |
| Crédits aux particuliers | Recouvrement | 18444786 | 0.984 | Product : Credit Reporting / Debt Collection Issue : Incorrect information on credit report Desired Resolution : Immediate deletion of collection account I am filing this complaint against Credit Central for reporting a collection account on my credit report without lawful verification, documentatio |

## 7. Erreurs à forte confiance (≥ 0.9) — test_2026, `company_masked`

189 erreurs sur 2,563 (7.4 %). Candidates au bruit d'étiquetage : à confirmer par lecture, pas par le score.

| complaint_id | service | pred | confidence | text_300 |
|---|---|---|---|---|
| 19693624 | Monétique | Recouvrement | 0.989644517579444 | I am filing this complaint against Midland Credit Management [REDACTED] regarding an alleged debt currently showing a balance of [AMOUNT] . The original debt for [AMOUNT] , as you can that i made payments. Midland Credit Management is not the original creditor. This debt appears to have been purchas |
| 18634912 | Recouvrement | Crédit immobilier | 0.9893122461149552 | On [REDACTED] I bought my home [REDACTED] bought the mortgage from [REDACTED] I have proof misapplied funds causing late fees misplaced escrow, funds in suspension etc. my mortgage is a 30 year fixed mortgage. Now its a 40 year mortgage I did not consent to this extra 10 years. Because of the misapp |
| 19022949 | Recouvrement | Monétique | 0.9891717456362108 | I am submitting this complaint to formally dispute the inaccurate and unverified reporting of a closed, charged-off [COMPANY] credit card account currently appearing on my consumer credit reports. Creditor : [COMPANY] Bank , N.A . Account Type : Credit Card Status Reported : Closed / Charged-Off Rep |
| 18399448 | Monétique | Recouvrement | 0.9874648963805372 | I was contacted by a collection agency and I sent a cease and desist with a debt validation letter. the account is still reporting and there has been no change for what is reporting on my credit report |
| 19287451 | Crédits aux particuliers | Recouvrement | 0.9858669588203969 | Balance Reported : [AMOUNT] Account Type : Debt Buyer Date Opened : [DATE] This account is being reported as a valid collection ; however, I dispute this account in its entirety. The information provided is incomplete and unverified. As a debt buyer, Jefferson Capital Systems has not provided eviden |
| 18953809 | Monétique | Recouvrement | 0.9837293503083092 | first national collections bureau is trying to collect a debt that is [REDACTED] or more years old. i have called and they will not stop. You can pay approximately 60 % in 12 payments. Current Creditor : [REDACTED] Original Creditor : [REDACTED] , [REDACTED] . Debt Description : [REDACTED] Original  |
| 18444786 | Crédits aux particuliers | Recouvrement | 0.9835317149670516 | Product : Credit Reporting / Debt Collection Issue : Incorrect information on credit report Desired Resolution : Immediate deletion of collection account I am filing this complaint against Credit Central for reporting a collection account on my credit report without lawful verification, documentatio |
| 20701263 | Monétique | Recouvrement | 0.9835130012396277 | I am submitting this complaint regarding a collection account being reported by I.C. System, Inc. that I have formally disputed and requested validation for. I sent a written request for debt validation pursuant to the Fair Debt Collection Practices Act ( FDCPA 809 ), requesting documentation to sup |
| 24161825 | Recouvrement | Crédits aux particuliers | 0.9832329263611946 | FEDERAL DIRECT STUDENT EDUCATIONAL LOANS NEVER LATE NOR 120-DAYS DELINQUENT [REDACTED] AS [REDACTED] , LOAN SERVICER, FALSELY PURPORTS. THE FACTUALLY INACCURATE CREDIT REPORTING REQUIRES RETROACTIVE AND IMMEDIATE PERMANENT REMOVAL FROM [REDACTED] AND [REDACTED] CREDIT REPORT. I ATTEST, [REDACTED] ,  |
| 19985264 | Recouvrement | Crédits aux particuliers | 0.9827723636605159 | My vehicle was declared a total loss on [DATE] . At that time, the payoff balance on my auto loan with [COMPANY] was [AMOUNT] , which included interest accrued through the date of loss. The primary insurance company issued payment toward the loan, and a GAP claim was processed through the GAP admini |
| 21275236 | Monétique | Recouvrement | 0.982086141683832 | I am filing this complaint against Midland Credit Management ( MCM ) for violations of the Fair Debt Collection Practices Act ( FDCPA ) and the Fair Credit Reporting Act ( FCRA ). Within 30 days of receiving MCM 's initial collection notice, I submitted a written debt validation request asking MCM t |
| 20062026 | Monétique | Recouvrement | 0.9807635395134495 | LVNV FUNDING LLC Original creditor : [REDACTED] Balance details 0 % paid off Balance [AMOUNT] Balance updated [DATE] Original balance [AMOUNT] Account info Account number [REDACTED] Date opened [DATE] Account type Debt Buyer |
| 20173668 | Recouvrement | Crédits aux particuliers | 0.9792320567811074 | I am submitting this complaint as the victim of identity theft involving a personal loan opened with [COMPANY] Loans for approximately [AMOUNT] . I never applied for or authorized this loan. My former fianc used my personal information without my knowledge or permission [REDACTED] obtain the loan. T |
| 19103523 | Recouvrement | Crédits aux particuliers | 0.9785677118394793 | I entered into a transaction with [REDACTED] with the intent to receive an extension of my credit for the purchase of a vehicle. Unknown to me, the dealership converted the loan contract into a credit installment agreement and then assigned my promissory note to [COMPANY] , Inc . When I discovered i |
| 21837098 | Comptes & Dépôts | Monétique | 0.9775636764919983 | problems with [COMPANY] applying for credit card. How is my credit score....? |

## 8. Macro-F1 mensuel — external_2025, `company_masked`

| received_month | n | macro_f1 |
|---|---|---|
| 2025-01 | 46086 | 0.8567 |
| 2025-02 | 17733 | 0.8363 |
| 2025-03 | 17942 | 0.8254 |
| 2025-04 | 17315 | 0.8226 |
| 2025-05 | 18876 | 0.8244 |
| 2025-06 | 18703 | 0.8205 |
| 2025-07 | 21276 | 0.8211 |
| 2025-08 | 20623 | 0.8133 |
| 2025-09 | 19791 | 0.8018 |
| 2025-10 | 18056 | 0.8233 |
| 2025-11 | 18920 | 0.8213 |
| 2025-12 | 16067 | 0.8256 |

## 9. Critères de sortie de la 3c-ii

| Critère | Statut |
|---|---|
| sha256 des données et des modèles vérifiés | OK |
| Verrou du test respecté (première évaluation) | OK |
| Métriques avec intervalles de confiance (test et externe) | OK |
| Calibrage mesuré | OK |
| Analyse d'erreurs produite | OK |
| Prédictions sauvegardées pour la Phase 5 (data/processed/predictions/) | OK |
