# Journaliste

> **Rôle** : Agent IA spécialisé dans la collecte quotidienne d'articles sur un sujet assigné. Il est le premier maillon de la salle de nouvelles.

---

## Responsabilités

1. Effectuer quotidiennement une recherche sur son **sujet assigné**
2. Identifier jusqu'à 5 articles pertinents, récents, et inédits publiés **aujourd'hui**
3. Vérifier qu'aucun article proposé n'a déjà été soumis dans le passé (par URL)
4. Soumettre ses articles au [[Agents/Chef de presse]] pour révision éditoriale
5. Consulter les feedbacks reçus pour améliorer ses sélections futures

---

## Contraintes

| Contrainte | Valeur |
|-----------|--------|
| Sujet | Un seul sujet par journaliste (ex: Politique québécoise, Tech/IA, Spatial) |
| Quota quotidien | Maximum 5 articles — moins acceptable les jours creux |
| Fraîcheur | Articles publiés le jour même uniquement |
| Déduplication | Vérification par URL contre l'historique complet de ses soumissions |

---

## Inputs

| Source | Contenu |
|--------|---------|
| Sujet assigné | Paramètre de configuration |
| `news_items` (historique) | Articles déjà soumis par ce journaliste — pour déduplication |
| Feedback éditorial | Flags qualité reçus du Chef de presse sur les jours précédents |

---

## Output

- `RawNewsItem` soumis au pipeline de traitement (résumé FR, image, audio)
- Un seul journaliste ne produit que des articles dans **sa catégorie**

---

## Feedback reçu

Le journaliste reçoit un feedback **binaire** du Chef de presse sur chaque article soumis :

| Signal | Signification |
|--------|--------------|
| ✅ Accepté | Article intégré au `daily_feeds` du jour |
| ❌ Rejeté | Flag qualité dans `news_items` — l'article ne correspond pas aux standards éditoriaux |

Ce mécanisme permet au journaliste d'ajuster ses critères de sélection au fil du temps. À terme, un système de review multi-agents évaluera plusieurs dimensions (pertinence, rédaction, profondeur) pour guider le journaliste plus précisément.

---

## Agents existants (migration)

Les agents de collecte actuels (`rss_generic.py`, `youtube_subs.py`, etc.) seront progressivement redéfinis comme journalistes avec sujet assigné. Voir [[Architecture/Agents de collecte]] pour l'état actuel.

---

## Développements futurs

- **Expertise interrogeable** : le journaliste pourra répondre à des questions sur son sujet (ex: "Quelle est la situation actuelle sur X?")
- **Mémoire de raisonnement** : capture du raisonnement derrière chaque sélection pour amélioration continue
- **Déduplication cross-journalistes** : éviter que deux journalistes sur des sujets proches proposent le même article

---

## Liens

- [[Agents/Chef de presse]] — destinataire de ses propositions
- [[Architecture/Agents de collecte]] — implémentation technique actuelle
- [[ECR/ECR-003 — Redéfinition architecturale]] — contexte de création de ce rôle

#agent #journaliste #collecte
