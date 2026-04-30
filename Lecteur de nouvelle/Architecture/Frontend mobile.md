# Frontend mobile

> Interface style "shorts" pour consommer le fil de nouvelles sur mobile.

---

## Choix techniques

| Aspect | Choix | Justification |
|--------|-------|---------------|
| JS | Vanilla ES2022+ modules | Pas de build, pas de npm |
| CSS | Vanilla + custom properties | Thème sombre par défaut |
| Layout | CSS scroll-snap | Natif, 1 carte par écran |
| Vidéo | YouTube IFrame API | Standard pour embeds |
| Audio TTS | HTML5 `<audio>` | Pas de lib externe |
| Audio vocal | `MediaRecorder` + Google STT V2 | Dictée fr-CA |
| PWA | manifest.json + service worker v5 | Expérience app-like Android |

---

## Fonctionnalités

### Carte de nouvelle
Chaque carte occupe un écran complet :
- **Image** de couverture (ou vidéo inline pour les shorts)
- **Titre** + **Résumé** en français (3-4 phrases)
- **Bouton TTS** play/pause

### Menu ⋮ (fixe, coin supérieur droit)
Un seul menu accessible depuis n'importe quelle carte :
- Feedback : 👍 J'aime / 👎 Je n'aime pas / ⏭ Ignorer
- **💬 Commenter** — note personnelle, saisie texte ou dictée vocale → `news_comments`
- 🔗 Voir la source
- 📅 Historique (calendrier inline)
- **🐛 Signaler un bug** — saisie texte ou dictée vocale → `bug_reports`
- ⎋ Déconnexion
- `v1.7.x` — numéro de version (bas du menu)

### Saisie vocale (M7)
Dans les sections Commenter et Signaler un bug :
- Bouton 🎤 → tap pour démarrer, re-tap pour arrêter
- Status **"🔴 Enregistrement…"** + canvas barres rouges pendant la prise
- Status **"⏳ Transcription…"** pendant l'appel Google STT V2
- Texte transcrit s'appende au textarea

### Navigation
- Scroll vertical avec snap (1 carte = 1 écran)
- Compteur de position (ex: "12/30") + barre de progression
- Calendrier inline dans le menu ⋮

### Auth
- Page de login (mot de passe unique)
- Cookie de session signé, persistant 7 jours
- Routes protégées

---

## Fichiers

```
frontend/
├── index.html        # Point d'entrée SPA + login
├── manifest.json     # PWA (icônes 192/512px)
├── sw.js             # Service worker v5 (JS/HTML réseau, static cache)
├── css/
│   └── app.css       # Thème sombre, scroll-snap, menu, vocal
└── js/
    ├── app.js        # Init, auth check, routing
    ├── api.js        # Fetch wrapper (401 → login, postComment, postBugReport, postBugReport, getAppVersion)
    ├── feed.js       # Scroll-snap, compteur, IntersectionObserver
    ├── player.js     # HTML5 <audio> TTS, auto-stop au scroll
    ├── ui.js         # Carte, menu ⋮, _buildInputSection (textarea + 🎤)
    └── speech.js     # MediaRecorder push-to-talk → Google STT V2  ← M7
```

---

## Cache et mises à jour

| Type de fichier | Stratégie SW |
|-----------------|-------------|
| JS, HTML | Network only (toujours frais) |
| CSS | Network First + fallback cache |
| Images, audio (`/static/`) | Cache First (stable) |

Flask sert JS/CSS/HTML avec `Cache-Control: no-cache, must-revalidate` pour forcer la revalidation du cache HTTP navigateur à chaque restart serveur.

---

## Critères de performance

- First load < 2s
- Pas de glitch en scroll rapide
- Fonctionne sur Android via VPN (HTTPS mkcert)

---

## Liens

- Retour : [[Vue d'ensemble]]
- Consomme : [[API REST]]
- Milestones : [[M4 — Frontend complet]], [[M6 — Commentaires et bugs]], [[M7 — Feedback vocal]]

#architecture #frontend
