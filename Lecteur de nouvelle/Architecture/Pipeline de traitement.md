# Pipeline de traitement

> Le pipeline prend les nouvelles brutes des [[Agents de collecte]], les transforme et produit un fil quotidien prêt à consommer.

---

## Orchestrateur (`core/orchestrator.py`)

Lance tous les agents activés **en parallèle** via `ThreadPoolExecutor`.
- Timeout : 5 min par agent
- Si un agent échoue, les autres continuent
- Génère un `AgentReport` pour chaque agent

Introduit au [[M2 — Multi-agents]].

---

## Étapes du pipeline (séquentielles)

### 1. Déduplication (`core/deduplicator.py`)
- **Exacte** : URL normalisée identique
- **Floue** : `rapidfuzz` sur les titres, seuil > 80%
- Seuil acceptable : < 30% de doublons (sinon sources trop similaires)

### 2. Scoring (`processors/scorer.py`)
Calcule un `final_score` pour chaque item basé sur :
- **Fraîcheur** — décroissance temporelle
- **Fiabilité source** — poids par source
- **Diversité** — pénalité si trop d'items de la même catégorie
- **Feedback utilisateur** — boost/pénalité basé sur les likes/dislikes historiques (décroissance dans le temps)

Sélection des **top 30** items. Aucune catégorie ne dépasse 40% du fil.

### 3. Résumé IA (`processors/summarizer.py`)
- Modèle : Claude Sonnet (`claude-sonnet-4-20250514`)
- Max 2000 tokens input, 300 tokens output
- Température 0.3 (factuel)
- Toujours en français, max 4 phrases
- Coût cible : < $0.01 par item

### 4. Extraction d'images (`processors/image_extractor.py`)
- Priorité : `og:image` > thumbnail YouTube > première image de l'article
- Redimensionnement : 720px max de large
- Format : JPEG qualité 85
- Fallback : image par défaut par catégorie

### 5. TTS (`processors/tts_generator.py`)
- Moteur : Google Cloud TTS — Gemini 2.5 Pro (`gemini-2.5-pro-tts`)
- Voix : `Achernar` (`fr-CA`), style journalistique via prompt
- Format : MP3, max 60 secondes (~700 caractères)
- Si texte trop long → tronquer avant génération

### 6. Assemblage (`processors/feed_assembler.py`)
- Crée l'entrée `daily_feed` en DB avec la liste ordonnée d'IDs
- Statut : "ready", "partial" ou "failed"

---

## Métriques clés

| Métrique | Seuil |
|----------|-------|
| Pipeline complet (30 items) | < 10 min |
| Résumé par item | < 5s |
| TTS par item | < 10s |
| Coût Claude par item | < $0.01 |
| Coût mensuel total | < $10 |

---

## Fichiers

```
core/
├── orchestrator.py      # Parallélisme agents
├── deduplicator.py      # URL + titre flou
└── pipeline.py          # Enchaîne les processeurs

processors/
├── base_processor.py    # Classe abstraite
├── scorer.py
├── summarizer.py
├── image_extractor.py
├── tts_generator.py
└── feed_assembler.py
```

---

## Liens

- Retour : [[Vue d'ensemble]]
- Reçoit de : [[Agents de collecte]]
- Produit vers : [[API REST]]
- Stocke dans : [[Modèle de données]]
- Testé dans : [[Tests et qualité]]

#architecture #pipeline
