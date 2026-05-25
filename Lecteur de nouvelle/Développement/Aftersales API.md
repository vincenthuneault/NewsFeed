# Aftersales API — Guide d'utilisation

> API de suivi des ECR, MCA et investigations Aftersales.
> Base URL : `http://localhost:5000/api`

---

## État de la base de données

La DB `data/newsfeed.db` existe et contient déjà toutes les données de l'app (articles, commentaires, feedbacks, bug reports).

Les **nouvelles tables** (`ecr`, `mca`, `investigations`, `ecr_status_history`, `mca_status_history`) sont créées **automatiquement au prochain démarrage de l'app** — aucune action requise.

**La seule étape manuelle** est de charger les 5 ECRs et 5 MCAs identifiés lors de l'analyse Mai 2026. À faire **une seule fois** après le premier démarrage :

```bash
curl -X POST http://localhost:5000/api/aftersales/seed
```

```json
{
  "success": true,
  "created": {
    "ecr": ["ECR-003", "ECR-004", "ECR-005", "ECR-006", "ECR-007"],
    "mca": ["MCA-001", "MCA-002", "MCA-003", "MCA-004", "MCA-005"]
  }
}
```

Idempotent — si tu l'appelles une deuxième fois, `"created"` sera vide `{"ecr": [], "mca": []}` et rien ne sera écrasé.

---

## Vue d'ensemble (admin)

```bash
curl http://localhost:5000/api/dev/aftersales
```

Retourne les ECRs ouverts, les MCAs en attente, et les 10 dernières investigations.

---

## ECR — Engineering Change Requests

### Statuts

| Code | Signification |
|------|--------------|
| `a_transmettre` | 🔵 Confirmé, pas encore transmis à l'ingénierie |
| `en_cours` | 🟡 V-cycle en marche |
| `corrige` | ✅ Fermé par l'ingénierie |
| `annule` | ❌ Décision de ne pas corriger |

### Lister les ECRs

```bash
# Tous les ECRs
curl http://localhost:5000/api/aftersales/ecr

# Filtrer par statut
curl "http://localhost:5000/api/aftersales/ecr?status=a_transmettre"
```

### Créer un ECR

```bash
curl -X POST http://localhost:5000/api/aftersales/ecr \
  -H "Content-Type: application/json" \
  -d '{
    "ecr_number": "ECR-008",
    "title": "Titre du problème",
    "priority": "haute",
    "severity": "haute",
    "symptom": "Description de ce que l'\''utilisateur observe",
    "root_cause": "Cause identifiée par investigation",
    "proposed_fix": "Solution proposée"
  }'
```

**Champs :**

| Champ | Requis | Valeurs |
|-------|--------|---------|
| `ecr_number` | ✅ | ECR-XXX |
| `title` | ✅ | Texte libre |
| `priority` | — | `haute` / `normale` / `basse` |
| `severity` | — | `critique` / `haute` / `normale` / `basse` |
| `symptom` | — | Ce que l'utilisateur observe |
| `root_cause` | — | Cause identifiée |
| `proposed_fix` | — | Solution proposée |

### Transmettre à l'ingénierie

```bash
curl -X PATCH http://localhost:5000/api/aftersales/ecr/1/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "en_cours",
    "note": "Transmis à l'\''Architecte Produit le 2026-05-11"
  }'
```

### Fermer un ECR (corrigé)

```bash
curl -X PATCH http://localhost:5000/api/aftersales/ecr/1/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "corrige",
    "note": "Déployé en production — scorer.py:141 corrigé"
  }'
```

### Voir l'historique d'un ECR

```bash
curl http://localhost:5000/api/aftersales/ecr/1/history
```

```json
{
  "ecr_number": "ECR-003",
  "history": [
    {
      "old_status": "a_transmettre",
      "new_status": "en_cours",
      "note": "Transmis à l'Architecte Produit le 2026-05-11",
      "changed_at": "2026-05-11T14:32:00"
    }
  ]
}
```

---

## MCA — Mises à jour Contexte Agent

### Statuts

| Code | Signification |
|------|--------------|
| `a_appliquer` | 🔵 Validé, pas encore intégré au contexte |
| `applique` | ✅ Contexte agent mis à jour |
| `en_attente` | ⏸ Bloqué (dépend d'un ECR) |

### Lister les MCAs

```bash
# Tous les MCAs
curl http://localhost:5000/api/aftersales/mca

# MCAs à appliquer
curl "http://localhost:5000/api/aftersales/mca?status=a_appliquer"
```

### Créer un MCA

```bash
curl -X POST http://localhost:5000/api/aftersales/mca \
  -H "Content-Type: application/json" \
  -d '{
    "mca_number": "MCA-006",
    "title": "Description courte du changement",
    "target_agent": "Chef de nouvelle / Scorer",
    "description": "Détail du changement à appliquer",
    "justification": "Commentaires utilisateurs qui justifient ce changement"
  }'
```

### Marquer un MCA comme appliqué

```bash
curl -X PATCH http://localhost:5000/api/aftersales/mca/1/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "applique",
    "note": "Contexte mis à jour dans config.yaml — effectif au prochain cycle"
  }'
```

---

## Investigations

### Lister les investigations

```bash
# 50 dernières (défaut)
curl http://localhost:5000/api/aftersales/investigations

# Limiter
curl "http://localhost:5000/api/aftersales/investigations?limit=10"
```

### Logger une investigation complète

Après avoir suivi la méthode scientifique, documenter le résultat :

```bash
curl -X POST http://localhost:5000/api/aftersales/investigations \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_type": "comment",
    "trigger_id": 42,
    "hypothesis": "Le pipeline publie des articles similaires dans la même journée",
    "data_plan": "Analyser les titres des 7 derniers jours + taux de skip associé",
    "data_collected": "42 articles présentés 2x, 1 présenté 3x sur 13 feeds analysés",
    "conclusion": "Hypothèse confirmée — 11% de doublons cross-journées",
    "decision": "ecr",
    "ecr_id": 1
  }'
```

**Valeurs de `trigger_type` :**
- `comment` — déclenché par un commentaire utilisateur (`news_comments`)
- `bug_report` — déclenché par un rapport de bug (`bug_reports`)
- `feedback` — déclenché par un pattern de like/dislike
- `manual` — investigation manuelle (analyse périodique)

**Valeurs de `decision` :**
- `journalisation` — cas isolé, aucune action
- `mca` — mise à jour de contexte agent
- `ecr` — engineering requis
- `business` — signal transmis au Business

### Logger une investigation en cours (sans conclusion)

```bash
curl -X POST http://localhost:5000/api/aftersales/investigations \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_type": "comment",
    "trigger_id": 55,
    "hypothesis": "Les résumés sont trop longs pour certaines catégories",
    "data_plan": "Mesurer la longueur moyenne des résumés par catégorie + comparer au taux de skip"
  }'
```

Sans `decision`, `completed_at` reste `null` — l'investigation est en cours.

---

## Workflow typique — Triage quotidien

### 1. Nouveau commentaire reçu

```bash
# Voir les investigations ouvertes pour vérifier si c'est un doublon
curl "http://localhost:5000/api/aftersales/investigations?limit=20"

# Voir les ECRs ouverts sur le même sujet
curl "http://localhost:5000/api/aftersales/ecr?status=a_transmettre"
```

### 2. Si c'est un nouveau problème — investigation

```bash
# Ouvrir l'investigation
curl -X POST http://localhost:5000/api/aftersales/investigations \
  -d '{"trigger_type": "comment", "trigger_id": 99, "hypothesis": "..."}'

# ... investigation ...

# Clore avec décision
curl -X POST http://localhost:5000/api/aftersales/investigations \
  -d '{"trigger_type": "comment", "decision": "ecr", "ecr_id": 3, ...}'
```

### 3. Transmettre ECR à l'ingénierie

```bash
curl -X PATCH http://localhost:5000/api/aftersales/ecr/3/status \
  -d '{"status": "en_cours", "note": "Transmis 2026-05-11"}'
```

### 4. L'ingénierie corrige — fermer l'ECR

```bash
curl -X PATCH http://localhost:5000/api/aftersales/ecr/3/status \
  -d '{"status": "corrige", "note": "Déployé en prod v1.2.3"}'
```

---

## Liens

- [[Agents/Aftersales]] — processus d'investigation (méthode scientifique)
- [[Bugs/Backlog]] — vue d'ensemble statique (Obsidian)
- [[Phase 8 — Cycle en V — Plan]] — processus ingénierie complet
- [[API REST]] — architecture API générale

#api #aftersales #ecr #mca #investigation #developpement
