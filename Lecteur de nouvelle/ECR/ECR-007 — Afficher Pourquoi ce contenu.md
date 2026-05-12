# ECR-007 — Afficher "Pourquoi ce contenu"

> **Statut** : 🔵 À transmettre
> **Priorité** : 🟢 Basse
> **Sévérité** : Basse — amélioration UX, pas de bug fonctionnel
> **Source** : [[Analyse Aftersales — Mai 2026]] · Cycle 1 (30 avril – 4 mai 2026)
> **Créé** : 2026-05-11

---

## Symptôme / Besoin

L'utilisateur ne comprend pas pourquoi certains articles (surtout des vidéos) lui sont présentés. L'absence d'explication réduit la confiance dans le système et rend le feedback moins ciblé.

**Note utilisateur (#12, Fetty Wap) :**
> "ajouter l'information 'pourquoi ce contenu m'est présenté' — surtout pour les vidéos"

---

## Valeur attendue

Afficher dans l'interface, pour chaque article, la raison de sa présentation :
- `"Présenté car : trending Québec"`
- `"Source : abonnement YouTube"`
- `"Catégorie : tech_ai · Score : 0.87"`
- `"Nouvelle source — premier article de ce domaine"`

**Bénéfices :**
1. L'utilisateur comprend le système et lui fait plus confiance
2. Le feedback (like/dislike) devient plus ciblé — l'utilisateur sait si c'est la source, la catégorie ou le sujet qu'il rejette
3. Meilleure détection des problèmes de catégorisation (ECR-005) par l'utilisateur lui-même

---

## Correction proposée

**Backend :** Ajouter un champ `presentation_reason` (JSON) dans `news_items` ou le calculer à la volée lors de l'assemblage du feed.

```json
{
  "presentation_reason": {
    "category": "tech_ai",
    "score": 0.87,
    "source_type": "rss",
    "source_name": "Ars Technica",
    "freshness_hours": 6,
    "diversity_boost": false
  }
}
```

**Frontend :** Afficher un tooltip ou une ligne discrète sous le titre (ex : `📌 tech_ai · Ars Technica · il y a 6h`). Accessible via le menu ⋮ pour ne pas surcharger l'interface principale.

---

## Cas de test à couvrir

| ID | Scénario | Résultat attendu |
|----|----------|-----------------|
| T-ECR007-01 | Article YouTube dans le feed | Affiche "Source : YouTube · Catégorie : X" |
| T-ECR007-02 | Article RSS trending | Affiche "Trending · Score : Y" |
| T-ECR007-03 | `presentation_reason` absent en DB | Affiche rien (graceful degradation) |
| T-ECR007-04 | Interface sur mobile (petite taille) | Tooltip ou menu ⋮ — pas d'overflow |

---

## Liens

- [[Bugs/Backlog]] — statut global
- [[Analyse Aftersales — Mai 2026]] — investigation complète (section 7)
- [[Phase 8 — Cycle en V — Plan]] — processus ingénierie

#ecr #ux #transparence #basse-priorite
