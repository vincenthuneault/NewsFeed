# Plan de projet — Progression des milestones

> La feuille de route complète. Chaque milestone a un POC, des tests et une gate de validation.

---

## Règle d'or

> Rien n'avance tant que ce qui est derrière ne fonctionne pas encore.

---

## Progression

| De | Vers | Condition |
|----|------|-----------|
| — | [[M0 — Setup\|M0]] | On commence |
| M0 | [[M1 — Vertical slice\|M1]] | Gate 0 : POC APIs OK + tests unit M0 |
| M1 | [[M2 — Multi-agents\|M2]] | Gate 1 : POC vertical slice + tests M0+M1 |
| M2 | [[M3 — Feedback\|M3]] | Gate 2 : POC multi-agents + tests M0→M2 |
| M3 | [[M4 — Frontend complet\|M4]] | Gate 3 : POC feedback + tests M0→M3 |
| M4 | [[M5 — Production\|M5]] | Gate 4 : POC mobile + tests M0→M4 |
| M5 | Terminé | Gate 5 : 7 jours autonomes + régression complète |

**Chaque gate exécute la suite de régression complète. Pas de raccourci.**

---

## Estimation des coûts

| Poste | Coût estimé |
|-------|-------------|
| Claude API (30 résumés/jour) | ~$0.12/jour → ~$3.60/mois |
| Edge TTS | Gratuit |
| YouTube API | Gratuit (quota 10k/jour) |
| Hébergement | Serveur existant |
| **Total mensuel** | **< $10** |

---

## Liens

- Retour : [[Vue d'ensemble]]
- Voir aussi : [[Manifeste technologique]], [[Tests et qualité]]

#référence #plan
