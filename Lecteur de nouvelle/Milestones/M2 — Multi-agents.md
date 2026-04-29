# M2 — Multi-agents + orchestrateur + scoring

> Passer de 1 agent à ~7 agents, avec exécution parallèle, déduplication, scoring et sélection des top 30.

---

## Tâches

- [ ] 2.1 — Agent RSS générique → `agents/rss_generic.py`
- [ ] 2.2 — Config RSS (tech/IA, politique x3, véhicules, spatial) → `config.yaml`
- [ ] 2.3 — Agent YouTube Trending → `agents/youtube_trending.py`
- [ ] 2.4 — Orchestrateur avec parallélisme → `core/orchestrator.py`
- [ ] 2.5 — Dédupliqueur → `core/deduplicator.py`
- [ ] 2.6 — Scorer → `processors/scorer.py`
- [ ] 2.7 — Assembleur de fil → `processors/feed_assembler.py`
- [ ] 2.8 — API : `GET /feed/<date>`, `GET /feed/dates`

---

## POC M2 : `scripts/poc_m2_multi.py`

7 agents en parallèle → déduplication → scoring → pipeline complet :
- ~33 items bruts → ~28 après dédup → 28 avec résumés, images, audio
- Distribution des catégories diversifiée (aucune > 40%)
- Durée totale < 5 min

---

## Métriques

| Métrique | Seuil |
|----------|-------|
| Orchestrateur total | < 5 min |
| Agents réussis | 100% (dégradé : 6/7) |
| Taux de déduplication | < 30% |
| Distribution catégories | Aucune > 40% |
| Pipeline complet (30 items) | < 10 min |

---

## Gate 2 — Critères

- [ ] POC M2 : fil de ~30 nouvelles diversifiées
- [ ] `pytest tests/` : 100% (inclut M0 + M1)
- [ ] Chaque agent logge correctement
- [ ] Rapport de santé montre tous les agents
- [ ] Distribution des catégories raisonnable
- [ ] Résumés tous en français
- [ ] Pipeline total < 10 min

---

## Liens

- Précédent : [[M1 — Vertical slice]]
- Suivant : [[M3 — Feedback]]
- Retour : [[Vue d'ensemble]]

#milestone #m2
