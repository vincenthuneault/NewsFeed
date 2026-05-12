# Aftersales — Triage & Investigation

> **Rôle** : Premier point de contact après réception d'un feedback utilisateur. Ne prend aucune décision sans investigation préalable. Applique la méthode scientifique avant toute action.

---

## Inputs reçus

| Type                   | Source                | Contenu                              |
| ---------------------- | --------------------- | ------------------------------------ |
| 👍👎⏭ Réaction         | `feedbacks` table     | like / dislike / skip sur un article |
| 💬 Commentaire article | `news_comments` table | note personnelle liée à un article   |
| 🐛 Rapport de bug      | `bug_reports` table   | description + contexte auto-capturé  |

---

## Étape 0 — Triage quotidien (avant toute investigation)

Avant d'appliquer la méthode scientifique, vérifier si le nouveau feedback se rattache à un item existant.

1. Ouvrir [[Bugs/Backlog]] — consulter les ECRs et MCAs ouverts (`🔵 À transmettre`, `🟡 En cours`, `🔵 À appliquer`)
2. Pour chaque nouveau commentaire ou feedback :
   - **Correspond à un item existant ?** → Ajouter le commentaire dans le fichier ECR ou MCA concerné, mettre à jour `Dernière activité` dans le Backlog
   - **Nouveau problème potentiel ?** → Passer à l'Étape 1 (méthode scientifique)
   - **Doublon déjà journalisé ?** → Journalisation directe, pas d'investigation

**Logging obligatoire :**
Toute décision — même "cas isolé → journalisation" — doit être tracée dans le Backlog avec :
`[date] · Commentaire reçu · Décision prise · Justification courte`

---

## Processus d'investigation (méthode scientifique)

### Étape 1 — Réception & Observation

- Enregistrer le feedback brut avec son contexte complet (article_id, timestamp, type, contenu)
- Lire littéralement : que dit le commentaire, sans interprétation
- Regrouper les feedbacks similaires reçus sur la même période
- Déterminer si le commentaire faire référence à un problème actif ou passé

### Étape 2 — Formulation de l'hypothèse

Transformer l'observation en une hypothèse **testable et falsifiable** :

> *"Le commentaire X suggère que Y se produit dans le système."*

Exemples :
| Observation | Hypothèse |
|-------------|-----------|
| "encore la même nouvelle" | Le système publie des articles au sujet similaire dans la même journée |
| "je comprends pas le résumé" | Les résumés générés dépassent le niveau de langue cible |
| "le bouton ne fonctionne pas" | Un élément UI est cassé dans un contexte spécifique |

### Étape 3 — Plan d'investigation

Définir **avant** de regarder les données :
- Quelles données sont nécessaires pour confirmer ou réfuter l'hypothèse ?
- Quel est le critère de confirmation (seuil, fréquence, corrélation) ?
- Sur quelle période analyser ?

*Ne pas chercher de pattern dans les données sans plan défini au préalable — biais de confirmation.*

### Étape 4 — Collecte & Analyse des données

Interroger la base de données selon le plan :
- Tables disponibles : `news_items`, `feedbacks`, `news_comments`, `bug_reports`, `agent_runs`
- Comparer les métriques calculées aux seuils du plan
- Documenter les résultats bruts, pas seulement la conclusion

### Étape 5 — Conclusion & Décision

| Résultat                                             | Action                            |
| ---------------------------------------------------- | --------------------------------- |
| Hypothèse **réfutée** — cas isolé                    | → [[Journalisation]]              |
| Hypothèse **confirmée** — réglable par configuration | → [[Mise à jour contexte agents]] |
| Hypothèse **confirmée** — nécessite du code          | → [[ECR]] → Ingénierie            |
| Pattern de fond — tendance utilisateur               | → Business (métriques)            |

---

## Exemple complet — Redondance de nouvelles

### Observation
Plusieurs commentaires mentionnent des doublons ou de la répétition dans le feed.

### Hypothèse
> *Le pipeline publie des articles traitant du même sujet dans un intervalle de 24h, perçus comme des doublons par l'utilisateur.*

### Plan d'investigation
**Données nécessaires :**
- Titres et résumés des articles publiés sur les 14 derniers jours
- Score de similarité calculé lors du pipeline (champ `final_score` + analyse de titre)
- Feedbacks `dislike` ou `skip` associés à ces articles
- Fréquence par catégorie (politique, sport, tech…)

**Critère de confirmation :**
Similarité sémantique > 0.70 entre deux articles publiés dans la même journée **ET** taux de skip > 40% sur ces articles.

**Critère de réfutation :**
Aucun cluster de similarité > 0.70, ou taux de skip dans la moyenne globale.

### Analyse
```sql
-- Articles similaires publiés le même jour
SELECT a.title, b.title, a.category, a.created_at
FROM news_items a
JOIN news_items b ON DATE(a.created_at) = DATE(b.created_at)
                 AND a.id < b.id
                 AND a.category = b.category
ORDER BY a.created_at DESC;

-- Taux de skip par article
SELECT n.title, COUNT(f.id) as feedbacks,
       SUM(CASE WHEN f.action = 'skip' THEN 1 ELSE 0 END) * 100.0 / COUNT(f.id) as skip_rate
FROM news_items n
JOIN feedbacks f ON f.news_item_id = n.id
GROUP BY n.id
HAVING skip_rate > 40
ORDER BY skip_rate DESC;
```

### Conclusions possibles

| Conclusion | Décision |
|------------|----------|
| Doublons confirmés (similarité haute + skip élevé) | ECR → ajuster le seuil de déduplication dans le pipeline |
| Sujet répété mais articles différents (score bas) | Mise à jour contexte → Chef de nouvelle préfère la diversité de sujets |
| Cas isolé, perception subjective | Journalisation |

---

## Liens

- [[Processus de revue des commentaires]] — vue d'ensemble du flux
- [[Phase 8 — Cycle en V — Plan]] — processus ingénierie pour les ECR
- [[Comment processing]] — impact des commentaires sur le comportement des agents
- [[Agents/Chef de nouvelle]] — destinataire des mises à jour de contexte

#agent #aftersales #triage #investigation #methode-scientifique
