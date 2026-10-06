# Note — Routage automatique des réclamations clients

**Destinataire :** Direction Qualité / Relation client · **Auteure :** Mohamadou Maïrama Cely · **Date :** 05/10/2026
**Statut :** étude de faisabilité sur données publiques américaines (CFPB), non sur des données Afriland.

## 1. Question posée

Une part des réclamations écrites peut-elle être affectée automatiquement au bon service, sans tri manuel, avec au moins 95 % de bonnes affectations ?

## 2. Ce que montre l'étude

- **Près des deux tiers du flux peuvent être routés automatiquement.** Au seuil de confiance retenu (0,79), le modèle route 63,8 % des réclamations du jeu de test, avec 94,7 % de bonnes affectations. Le reste (36,2 %) part en revue humaine.
- **Le résultat tient dans le temps.** Sur 251 388 réclamations d'une autre année (2025), jamais vues à l'entraînement : 64,5 % routées, 94,8 % de bonnes affectations.
- **Le seuil fait l'essentiel du travail.** Sur les réclamations qu'il envoie en revue humaine, le modèle ne serait juste que dans 65 % des cas : ce sont bien les cas difficiles qui restent aux agents.
- **Ordre de grandeur, à titre illustratif.** Pour 1 000 réclamations par mois : environ 640 routées automatiquement, 360 en revue humaine, 34 mal routées, et de 11 à 53 heures de tri économisées selon le temps de tri réel (1 à 5 minutes par réclamation, hypothèse non mesurée).

## 3. Points de vigilance

- **Tous les services ne sont pas égaux.** Les affectations automatiques sont fiables pour le Recouvrement et le Crédit immobilier (96 à 97 %), moins pour les Transferts & Paiements (84 %) et les Comptes & Dépôts (91 %), souvent confondus entre eux.
- **La cible de 95 % est approchée, pas garantie** : 94,7 % sur le test, 94,8 % sur 2025.
- **Une partie des erreurs vient de l'étiquette, pas du modèle** : le client choisit lui-même le produit concerné, ce qui crée des incohérences (par exemple une plainte de recouvrement classée « carte de crédit »).

## 4. Recommandation

1. **Mesurer d'abord l'existant :** volume mensuel, temps de tri et taux d'erreur du tri manuel actuel. Sans ces trois chiffres, le gain réel ne peut pas être chiffré.
2. **Réentraîner sur des réclamations Afriland en français**, avec le même pipeline. Les résultats ci-dessus valident la méthode, pas un modèle directement réutilisable.
3. **Démarrer par un pilote limité aux services les plus fiables** (Recouvrement, Crédit immobilier), en gardant la revue humaine pour les Transferts & Paiements et les Comptes & Dépôts tant qu'un seuil propre à chaque service n'a pas été validé.
4. **Conserver un journal de chaque décision automatique** (service proposé, niveau de confiance), pour la traçabilité exigée par la Conformité.

*Méthode, chiffres détaillés et limites : README du dépôt `bank-complaint-routing-nlp` et rapports `reports/phase3c_evaluation.md`, `reports/phase5_routing.md`.*
