# Masquage des noms d'entreprises — Phase 3a

Généré le 2026-10-05 19:35 UTC par `src/features/build_company_mask.py`. Lexique construit sur le **jeu d'entraînement uniquement**, appliqué tel quel à la validation et au test.

- Entreprises distinctes (nom normalisé) dans train : 2,037 ; retenues (≥ 20 réclamations) : 319.
- Motifs du lexique : 490 (noms complets : 324 ; mots isolés retenus : 166 sur 405 candidats).

## 1. Part des narratifs contenant au moins un `[COMPANY]` (%)

| service | train | val | test |
|---|---|---|---|
| Comptes & Dépôts | 65.52 | 65.62 | 64.9 |
| Crédit immobilier | 52.28 | 52.1 | 54.29 |
| Crédits aux particuliers | 49.6 | 48.93 | 49.3 |
| Monétique | 60.27 | 61.23 | 59.03 |
| Recouvrement | 28.77 | 29.56 | 29.8 |
| Transferts & Paiements | 49.8 | 49.8 | 48.22 |

## 2. 30 correspondances les plus fréquentes (tous jeux)

| matched_text | n_occurrences |
|---|---|
| chase | 18480 |
| wells fargo | 17540 |
| capital one | 13972 |
| paypal | 13851 |
| bank of america | 11948 |
| chime | 9117 |
| citibank | 8541 |
| synchrony | 6537 |
| american express | 5490 |
| mohela | 4555 |
| affirm | 3656 |
| truist | 3304 |
| sofi | 3032 |
| navy | 2716 |
| barclays | 2560 |
| ally | 2490 |
| rocket mortgage | 2275 |
| santander | 2053 |
| td bank | 1982 |
| shellpoint | 1946 |
| nelnet | 1877 |
| goldman sachs | 1787 |
| klarna | 1689 |
| coinbase | 1679 |
| robinhood | 1652 |
| resurgent | 1452 |
| citizens | 1448 |
| westlake | 1374 |
| freedom mortgage | 1338 |
| portfolio recovery associates | 1334 |

## 3. Mots isolés candidats (retenus en tête, puis rejetés)

Critère : ≥ 20 documents train et concentration ≥ 0.5 (part des documents contenant le mot dont l'entreprise visée contient ce mot) et mot présent dans les noms de ≤ 3 entreprises retenues (`n_company_names`). Liste complète : `reports/phase3a/single_token_candidates.csv`.

| token | n_docs | n_docs_company_match | concentration | n_company_names | selected |
|---|---|---|---|---|---|
| chase | 2786 | 2683 | 0.963 | 1 | True |
| fargo | 2607 | 2594 | 0.995 | 1 | True |
| wells | 2604 | 2589 | 0.994 | 1 | True |
| chime | 1850 | 1812 | 0.979 | 1 | True |
| paypal | 1848 | 1571 | 0.85 | 1 | True |
| citibank | 1402 | 1396 | 0.996 | 1 | True |
| express | 1332 | 966 | 0.725 | 1 | True |
| synchrony | 1263 | 1241 | 0.983 | 1 | True |
| mohela | 845 | 841 | 0.995 | 1 | True |
| navy | 740 | 731 | 0.988 | 1 | True |
| affirm | 620 | 541 | 0.873 | 1 | True |
| goldman | 536 | 536 | 1.0 | 1 | True |
| sachs | 522 | 522 | 1.0 | 1 | True |
| truist | 509 | 497 | 0.976 | 1 | True |
| rocket | 507 | 481 | 0.949 | 1 | True |
| ally | 480 | 468 | 0.975 | 1 | True |
| sofi | 479 | 474 | 0.99 | 1 | True |
| jpmorgan | 459 | 458 | 0.998 | 1 | True |
| resurgent | 385 | 367 | 0.953 | 1 | True |
| santander | 384 | 378 | 0.984 | 1 | True |
| barclays | 384 | 372 | 0.969 | 1 | True |
| freedom | 340 | 257 | 0.756 | 2 | True |
| global | 327 | 234 | 0.716 | 2 | True |
| nelnet | 324 | 321 | 0.991 | 1 | True |
| citizens | 320 | 246 | 0.769 | 2 | True |
| shellpoint | 316 | 307 | 0.972 | 1 | True |
| robinhood | 260 | 256 | 0.985 | 1 | True |
| fifth | 258 | 173 | 0.671 | 1 | True |
| westlake | 255 | 254 | 0.996 | 1 | True |
| huntington | 222 | 221 | 0.995 | 1 | True |
| klarna | 218 | 215 | 0.986 | 1 | True |
| coinbase | 204 | 191 | 0.936 | 1 | True |
| transworld | 192 | 192 | 1.0 | 1 | True |
| caine | 184 | 184 | 1.0 | 1 | True |
| weiner | 180 | 180 | 1.0 | 1 | True |
| karma | 174 | 149 | 0.856 | 1 | True |
| columbia | 174 | 167 | 0.96 | 1 | True |
| spring | 156 | 110 | 0.705 | 1 | True |
| regions | 155 | 141 | 0.91 | 1 | True |
| bilt | 155 | 141 | 0.91 | 1 | True |
| radius | 149 | 140 | 0.94 | 1 | True |
| harris | 146 | 122 | 0.836 | 1 | True |
| pennymac | 146 | 146 | 1.0 | 1 | True |
| bridgecrest | 141 | 141 | 1.0 | 1 | True |
| receivables | 137 | 76 | 0.555 | 2 | True |
| delaware | 133 | 76 | 0.571 | 1 | True |
| western | 130 | 104 | 0.8 | 1 | True |
| exeter | 129 | 126 | 0.977 | 1 | True |
| selene | 128 | 128 | 1.0 | 1 | True |
| loancare | 126 | 118 | 0.937 | 1 | True |
| aldous | 126 | 125 | 0.992 | 1 | True |
| sunrise | 125 | 120 | 0.96 | 1 | True |
| genesis | 123 | 113 | 0.919 | 1 | True |
| cooper | 113 | 67 | 0.593 | 1 | True |
| outsourcing | 112 | 99 | 0.884 | 2 | True |
| carrington | 110 | 110 | 1.0 | 1 | True |
| edfinancial | 108 | 108 | 1.0 | 1 | True |
| navient | 106 | 64 | 0.604 | 1 | True |
| onemain | 106 | 103 | 0.972 | 1 | True |
| eastern | 105 | 61 | 0.581 | 1 | True |
| netspend | 104 | 104 | 1.0 | 1 | True |
| toyota | 101 | 98 | 0.97 | 1 | True |
| oaks | 100 | 98 | 0.98 | 1 | True |
| acima | 90 | 88 | 0.978 | 1 | True |
| bread | 89 | 89 | 1.0 | 1 | True |
| trueaccord | 81 | 81 | 1.0 | 1 | True |
| planet | 75 | 63 | 0.84 | 1 | True |
| southwest | 74 | 65 | 0.878 | 1 | True |
| procollect | 73 | 73 | 1.0 | 1 | True |
| honda | 72 | 71 | 0.986 | 1 | True |
| sequium | 70 | 70 | 1.0 | 1 | True |
| velocity | 68 | 40 | 0.588 | 1 | True |
| hyundai | 68 | 68 | 1.0 | 1 | True |
| upstart | 67 | 60 | 0.896 | 1 | True |
| remitly | 66 | 61 | 0.924 | 1 | True |
| climb | 66 | 60 | 0.909 | 1 | True |
| waypoint | 65 | 62 | 0.954 | 1 | True |
| mosaic | 61 | 58 | 0.951 | 1 | True |
| moneylion | 61 | 60 | 0.984 | 1 | True |
| adjusters | 60 | 46 | 0.767 | 1 | True |
| avant | 58 | 55 | 0.948 | 1 | True |
| lakeview | 57 | 48 | 0.842 | 1 | True |
| cavalry | 57 | 53 | 0.93 | 1 | True |
| monterey | 55 | 55 | 1.0 | 1 | True |
| dave | 55 | 55 | 1.0 | 1 | True |
| halsted | 54 | 53 | 0.981 | 1 | True |
| imprint | 53 | 52 | 0.981 | 1 | True |
| sezzle | 52 | 51 | 0.981 | 1 | True |
| carmax | 49 | 47 | 0.959 | 1 | True |
| cherry | 48 | 40 | 0.833 | 1 | True |
| aargon | 48 | 47 | 0.979 | 1 | True |
| amerihome | 46 | 46 | 1.0 | 1 | True |
| morris | 45 | 45 | 1.0 | 1 | True |
| nissan | 43 | 43 | 1.0 | 1 | True |
| google | 43 | 25 | 0.581 | 1 | True |
| diversified | 42 | 38 | 0.905 | 1 | True |
| stanley | 42 | 42 | 1.0 | 1 | True |
| synergetic | 42 | 41 | 0.976 | 1 | True |
| village | 41 | 37 | 0.902 | 1 | True |
| hsbc | 41 | 41 | 1.0 | 1 | True |
| mercury | 41 | 38 | 0.927 | 2 | True |
| unifin | 41 | 38 | 0.927 | 1 | True |
| crosscountry | 41 | 40 | 0.976 | 1 | True |
| comerica | 40 | 39 | 0.975 | 1 | True |
| lockhart | 40 | 40 | 1.0 | 1 | True |
| ford | 39 | 38 | 0.974 | 1 | True |
| montgomery | 38 | 30 | 0.789 | 1 | True |
| january | 37 | 22 | 0.595 | 1 | True |
| golden | 36 | 27 | 0.75 | 1 | True |
| mountain | 35 | 24 | 0.686 | 1 | True |
| valon | 35 | 35 | 1.0 | 1 | True |
| axos | 35 | 34 | 0.971 | 1 | True |
| optum | 35 | 34 | 0.971 | 1 | True |
| roundpoint | 34 | 31 | 0.912 | 1 | True |
| zions | 34 | 34 | 1.0 | 2 | True |
| moneygram | 33 | 32 | 0.97 | 1 | True |
| kraken | 33 | 32 | 0.97 | 1 | True |
| kikoff | 33 | 32 | 0.97 | 1 | True |
| incomm | 33 | 30 | 0.909 | 1 | True |
| williams | 33 | 33 | 1.0 | 2 | True |

_285 lignes supplémentaires dans reports/tables/_

## 4. Mots les plus discriminants de la 2c : fréquence avant / après masquage (train)

Un `pct_removed` proche de 100 indique un mot masqué ; proche de 0, un mot non capté par le lexique.

| word | train_count_before | train_count_after | pct_removed |
|---|---|---|---|
| affirm | 2603 | 0 | 100.0 |
| barclays | 1894 | 0 | 100.0 |
| chime | 6313 | 0 | 100.0 |
| express | 4295 | 0 | 100.0 |
| fargo | 12369 | 0 | 100.0 |
| coinbase | 1195 | 0 | 100.0 |
| nelnet | 1203 | 0 | 100.0 |
| paypals | 706 | 0 | 100.0 |
| paypal | 9637 | 0 | 100.0 |
| rocket | 1976 | 0 | 100.0 |
| mohela | 3214 | 0 | 100.0 |
| synchrony | 4632 | 0 | 100.0 |
| shellpoint | 1305 | 0 | 100.0 |
| wells | 13110 | 0 | 100.0 |
| american | 4510 | 409 | 90.9 |
| capital | 13771 | 3397 | 75.3 |
| one | 22312 | 12916 | 42.1 |
| bank | 57193 | 45455 | 20.5 |
| mortgage | 15220 | 12447 | 18.2 |
| finance | 3968 | 3351 | 15.5 |
| servicing | 7162 | 6803 | 5.0 |
| credit | 102259 | 98089 | 4.1 |
| home | 6992 | 6783 | 3.0 |
| property | 7334 | 7294 | 0.5 |
| loan | 33655 | 33551 | 0.3 |
| collection | 33025 | 32921 | 0.3 |
| debt | 66487 | 66292 | 0.3 |
| payments | 25586 | 25572 | 0.1 |
| branch | 5832 | 5829 | 0.1 |
| car | 4869 | 4866 | 0.1 |
| auto | 3806 | 3806 | 0.0 |
| billing | 9524 | 9524 | 0.0 |
| app | 12322 | 12322 | 0.0 |
| atm | 3203 | 3203 | 0.0 |
| act | 19457 | 19457 | 0.0 |
| alleged | 16049 | 16049 | 0.0 |
| cash | 13395 | 13395 | 0.0 |
| card | 43394 | 43394 | 0.0 |
| checking | 7640 | 7640 | 0.0 |
| check | 16386 | 16386 | 0.0 |
| charges | 19362 | 19362 | 0.0 |
| charge | 17611 | 17611 | 0.0 |
| cashapp | 1479 | 1479 | 0.0 |
| cease | 6943 | 6943 | 0.0 |
| deposited | 4023 | 4023 | 0.0 |
| escrow | 6598 | 6598 | 0.0 |
| fcra | 9631 | 9631 | 0.0 |
| fair | 17693 | 17693 | 0.0 |
| creditor | 9892 | 9892 | 0.0 |
| deposit | 8046 | 8046 | 0.0 |
| debit | 7307 | 7307 | 0.0 |
| dealership | 1929 | 1929 | 0.0 |
| collect | 10517 | 10517 | 0.0 |
| citi | 4745 | 4745 | 0.0 |
| money | 22800 | 22800 | 0.0 |
| modification | 3182 | 3182 | 0.0 |
| mitigation | 2444 | 2444 | 0.0 |
| merchant | 15101 | 15101 | 0.0 |
| interest | 18351 | 18351 | 0.0 |
| loans | 5331 | 5331 | 0.0 |
| funds | 32506 | 32506 | 0.0 |
| insurance | 7810 | 7810 | 0.0 |
| fdcpa | 8419 | 8419 | 0.0 |
| fha | 1140 | 1140 | 0.0 |
| forgiveness | 1264 | 1264 | 0.0 |
| foreclosure | 4135 | 4135 | 0.0 |
| overdraft | 2369 | 2369 | 0.0 |
| original | 19658 | 19658 | 0.0 |
| repayment | 3735 | 3735 | 0.0 |
| recipient | 1715 | 1715 | 0.0 |
| rewards | 2121 | 2121 | 0.0 |
| repossession | 3341 | 3341 | 0.0 |
| reporting | 48832 | 48832 | 0.0 |
| report | 31394 | 31394 | 0.0 |
| scam | 3455 | 3455 | 0.0 |
| student | 3644 | 3644 | 0.0 |
| support | 7942 | 7942 | 0.0 |
| servicer | 5267 | 5267 | 0.0 |
| taxes | 2146 | 2146 | 0.0 |
| transaction | 24519 | 24519 | 0.0 |
| transfer | 14430 | 14430 | 0.0 |
| transactions | 18320 | 18320 | 0.0 |
| validation | 18481 | 18481 | 0.0 |
| vehicle | 10570 | 10570 | 0.0 |
| venmo | 803 | 803 | 0.0 |
| wire | 2979 | 2979 | 0.0 |

## 5. Limites

- Les marques absentes de la colonne Company (ex. une application détenue par une société au nom différent) ne sont pas captées.
- Un mot isolé rejeté (concentration insuffisante ou présent dans trop de noms) reste visible dans le texte, même s'il désigne parfois l'entreprise.
- Aucune liste d'alias écrite à la main (décision du 2026-10-05) : les formes courtes ou commerciales absentes de la colonne Company restent visibles (voir section 4, mots à `pct_removed` = 0).
- Un mot retenu peut aussi être un mot courant dans certains textes : la part de faux positifs d'un mot est au plus 1 − concentration (section 3).
