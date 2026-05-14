# Chef de presse

> **Rôle** : Agent IA éditorial — sélectionne et valide le fil de nouvelles quotidien à partir des propositions des journalistes du jour. Il est le gardien de la qualité du feed.

---

## Responsabilités

1. Lire l'ensemble des articles proposés par les [[Agents/Journaliste|journalistes]] **ce jour même**
2. Assembler un fil de nouvelles de maximum 30 articles pour le `daily_feeds`
3. Appliquer les critères de sélection : préférences utilisateur, commentaires, feedbacks historiques
4. Rejeter les articles sous le seuil de qualité avec un flag binaire dans `news_items`
5. Transmettre le feed validé au Narrateur pour production audio

---

## Contraintes

| Contrainte | Valeur |
|-----------|--------|
| Périmètre temporel | Uniquement les articles soumis aujourd'hui — aucun article des jours précédents |
| Capacité du feed | Maximum 30 articles par journée |
| Traçabilité | Toute décision de rejet doit être tracée (flag dans `news_items`) |

---

## Inputs

| Source | Contenu |
|--------|---------|
| Articles du jour | `news_items` soumis aujourd'hui par les journalistes |
| Préférences utilisateur | Catégories favorites, sujets d'intérêt |
| `feedbacks` | Historique des likes / dislikes / skips |
| `news_comments` | Commentaires de l'utilisateur — signaux qualitatifs |

---

## Output

- `DailyFeed` — liste ordonnée d'IDs d'articles (max 30) pour le jour courant
- Flags qualité dans `news_items` pour les articles rejetés

---

## Gate qualité (décision éditoriale)

Le Chef de presse applique un **filtre binaire** sur chaque article proposé :

| Décision | Action |
|----------|--------|
| ✅ Accepté | Article inclus dans le `daily_feeds` |
| ❌ Rejeté | Flag qualité dans `news_items` → feedback transmis au journaliste |

La décision repose sur la combinaison des préférences de l'utilisateur, la pertinence du sujet du jour, et la qualité rédactionnelle de l'article soumis.

---

## Pourquoi les doublons sont impossibles avec ce design

Le Chef de presse n'a accès qu'aux articles soumis **aujourd'hui**. Un article d'hier ne peut pas être candidat au feed d'aujourd'hui — non pas parce qu'un algorithme le filtre, mais parce qu'il n'est simplement pas dans son périmètre de travail. La contrainte est architecturale, pas algorithmique.

---

## Développements futurs

- **Système multi-agents de review** : plusieurs agents spécialisés (rédaction, profondeur de recherche, expertise du sujet) évalueront indépendamment chaque article avant la sélection finale du Chef de presse
- **Justification des décisions** : le Chef de presse documentera son raisonnement pour chaque rejet, enrichissant le feedback aux journalistes

---

## Liens

- [[Agents/Journaliste]] — source des propositions d'articles
- [[Agents/Aftersales]] — fournit les signaux utilisateur (feedbacks, commentaires)
- [[Architecture/Pipeline de traitement]] — pipeline de traitement en aval
- [[ECR/ECR-003 — Redéfinition architecturale]] — contexte de création de ce rôle

#agent #chef-de-presse #editorial #curation
