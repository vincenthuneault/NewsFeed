# M3 — Agents locaux + événements + feedback

> Compléter les agents (Contrecoeur, Montréal, viral) et implémenter le système de feedback qui influence le scoring.

---

## Tâches

- [ ] 3.1 — Agent événements Montréal → `agents/events_montreal.py`
- [ ] 3.2 — Agent local Contrecoeur/Sorel → `agents/local_contrecoeur.py`
- [ ] 3.3 — Agent contenu viral (Google Trends + YT Shorts) → `agents/viral_trending.py`
- [ ] 3.4 — API feedback : `POST /api/news/<id>/feedback`
- [ ] 3.5 — API settings : `GET/PUT /api/settings`
- [ ] 3.6 — Feedback loop dans le scorer
- [ ] 3.7 — Frontend : bouton options + feedback

---

## POC M3 : `scripts/poc_m3_feedback.py`

Simule 3 jours de feedback et vérifie que :
- Les likes boostent la catégorie aimée
- Les dislikes pénalisent la catégorie
- Le feedback historique décroît dans le temps
- Les items ne sont jamais perdus, juste re-rankés

---

## Gate 3 — Critères

- [ ] POC M3 : feedback modifie visiblement le scoring
- [ ] `pytest tests/` : 100% (inclut M0→M2)
- [ ] Tous les agents (9+) fonctionnent
- [ ] API feedback fonctionne (POST + vérif DB)
- [ ] Rapport de santé inclut tous les agents
- [ ] Pas de régression

---

## Liens

- Précédent : [[M2 — Multi-agents]]
- Suivant : [[M4 — Frontend complet]]
- Retour : [[Vue d'ensemble]]

#milestone #m3
