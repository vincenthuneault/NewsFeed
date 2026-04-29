# M4 — Frontend complet + auth + PWA

> Interface mobile complète : shorts scroll, TTS, options, historique, authentification.

---

## Tâches

- [ ] 4.1 — UI shorts scrollable complète
- [ ] 4.2 — Lecteur vidéo inline (Shorts/Reels) → `frontend/js/player.js`
- [ ] 4.3 — Bouton TTS avec play/pause
- [ ] 4.4 — Menu options (⋮) avec liens, feedback → `frontend/js/ui.js`
- [ ] 4.5 — Indicateur de position (barre + compteur)
- [ ] 4.6 — Navigation historique (calendrier/dates)
- [ ] 4.7 — Authentification (login + cookie) → `backend/auth.py`
- [ ] 4.8 — PWA manifest + service worker

---

## POC M4 : Test sur mobile réel

Checklist manuelle (téléphone via VPN) :
- [ ] Page de login s'affiche
- [ ] Connexion réussie → fil
- [ ] Première carte avec image + texte
- [ ] Scroll snap fonctionne (1 carte/écran)
- [ ] Vidéo short en auto-play
- [ ] Vidéo longue : résumé + lien
- [ ] Bouton TTS lance l'audio
- [ ] Audio s'arrête au scroll
- [ ] Bouton ⋮ ouvre le menu
- [ ] Like/dislike fonctionne
- [ ] Compteur "12/30" se met à jour
- [ ] Calendrier → dates → ancien fil
- [ ] Performance < 2s
- [ ] Pas de glitch en scroll rapide

---

## Gate 4 — Critères

- [ ] POC M4 : checklist mobile 100%
- [ ] `pytest tests/` : 100% (inclut M0→M3)
- [ ] Auth fonctionne (login/logout/protection)
- [ ] Performance mobile < 2s first load
- [ ] Pas de régression backend/pipeline

---

## Liens

- Précédent : [[M3 — Feedback]]
- Suivant : [[M5 — Production]]
- Retour : [[Vue d'ensemble]]
- Composant principal : [[Frontend mobile]]

#milestone #m4
