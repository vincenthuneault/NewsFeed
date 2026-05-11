# Lecteur de nouvelle — Vue d'ensemble

> Fil de nouvelles personnalisé, généré quotidiennement par des agents autonomes, avec résumés IA et lecture audio TTS.

---

## Concept

Un système qui collecte automatiquement des nouvelles de multiples sources (YouTube, RSS, scraping), les déduplique, les score selon mes préférences, génère des résumés en français via Claude, et les présente dans une interface mobile style "shorts" avec lecture audio.

---

## Documents de référence

- [[Manifeste technologique]] — Tous les choix techniques définitifs
- [[Plan de projet]] — Les 6 milestones (M0→M5) avec POC et gates

---

## Architecture haut niveau

Le système se divise en 4 grandes couches :

1. **[[Agents de collecte]]** — Récupèrent les nouvelles brutes de chaque source
2. **[[Pipeline de traitement]]** — Déduplique, score, résume, génère images et audio
3. **[[API REST]]** — Sert le contenu au frontend via Flask
4. **[[Frontend mobile]]** — Interface scroll-snap style shorts

Voir aussi : [[Modèle de données]], [[Infrastructure et déploiement]], [[Tests et qualité]]

---

## Flow général

```
Sources (YouTube, RSS, scraping)
        │
        ▼
  [[Agents de collecte]] (en parallèle)
        │
        ▼  List[RawNewsItem]
  [[Pipeline de traitement]]
    1. Déduplication (URL + titre flou)
    2. Scoring (fraîcheur, fiabilité, diversité, feedback)
    3. Résumé IA (Claude Sonnet → français, 4 phrases max)
    4. Images (og:image / thumbnail → JPEG 720px)
    5. TTS (Google Cloud TTS Gemini 2.5 Pro → MP3, voix Achernar fr-CA)
    6. Assemblage du fil quotidien
        │
        ▼  SQLite + fichiers statiques
  [[API REST]] (Flask + Gunicorn + Nginx)
        │
        ▼  JSON + images + audio
  [[Frontend mobile]] (Vanilla JS, CSS scroll-snap)
```

---

## Progression des milestones

| Milestone | Objectif | Statut |
|-----------|----------|--------|
| [[M0 — Setup]] | Valider les APIs et l'environnement | Terminé |
| [[M1 — Vertical slice]] | 1 agent end-to-end (YouTube → affichage) | Terminé |
| [[M2 — Multi-agents]] | ~7 agents + orchestrateur + scoring | Terminé |
| [[M3 — Feedback]] | Agents locaux + système de feedback | Terminé |
| [[M4 — Frontend complet]] | UI mobile + auth + PWA | Terminé |
| [[M5 — Production]] | Automatisation + monitoring 7 jours | Terminé |
| [[M6 — Commentaires et bugs]] | Commentaires sur les nouvelles + rapport de bugs | Terminé |
| [[M7 — Feedback vocal]] | Transcription vocale en temps réel (micro → textarea) | Terminé |

---

## Tags

#projet #lecteur-nouvelle #vue-ensemble
