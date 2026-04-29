# M1 — Premier agent end-to-end

> Prouver qu'un seul agent peut traverser tout le pipeline : collecte → résumé → image → TTS → affichage dans le navigateur. C'est le **vertical slice** le plus critique.

---

## Tâches

- [ ] 1.1 — `BaseAgent` avec interface + contrat → `agents/base_agent.py`
- [ ] 1.2 — Agent YouTube Subscriptions → `agents/youtube_subs.py`
- [ ] 1.3 — `BaseProcessor` avec interface → `processors/base_processor.py`
- [ ] 1.4 — Processeur résumé IA (Claude) → `processors/summarizer.py`
- [ ] 1.5 — Processeur extraction d'images → `processors/image_extractor.py`
- [ ] 1.6 — Processeur TTS → `processors/tts_generator.py`
- [ ] 1.7 — Pipeline minimal (séquentiel) → `core/pipeline.py`
- [ ] 1.8 — API Flask minimale → `backend/app.py` + `GET /api/feed/today`
- [ ] 1.9 — Frontend : 1 carte avec image + texte + audio → `frontend/index.html`

---

## POC M1 : `scripts/poc_m1_vertical.py`

Pipeline complet pour 3 vidéos YouTube :
1. Agent YouTube → 3 vidéos sélectionnées par popularité
2. Summarizer → résumés en français (< 4 phrases)
3. ImageExtractor → thumbnails 720px JPEG
4. TTS → audio MP3 (< 60s, fr-CA-SylvieNeural)
5. Flask → `GET /api/feed/today` retourne les 3 items
6. Frontend → 3 cartes scrollables dans le navigateur

Résultat attendu : **3 items complets affichés**, coût < $0.02

---

## Métriques

| Métrique | Seuil |
|----------|-------|
| Collecte YouTube | < 30s |
| Résumé par item | < 5s |
| Coût Claude par item | < $0.01 |
| TTS par item | < 10s |
| Audio par item | < 1MB |
| Pipeline total (3 items) | < 60s |

---

## Gate 1 — Critères

- [ ] POC M1 : pipeline complet pour 3 vidéos
- [ ] `pytest tests/` : 100% (inclut M0)
- [ ] 3 cartes s'affichent dans le navigateur mobile
- [ ] Audio TTS audible et < 60s
- [ ] Résumé en français, < 4 phrases
- [ ] Logs structurés détaillés
- [ ] Rapport de santé "READY"

---

## Liens

- Précédent : [[M0 — Setup]]
- Suivant : [[M2 — Multi-agents]]
- Retour : [[Vue d'ensemble]]
- Composants : [[Agents de collecte]], [[Pipeline de traitement]], [[API REST]], [[Frontend mobile]]

#milestone #m1
