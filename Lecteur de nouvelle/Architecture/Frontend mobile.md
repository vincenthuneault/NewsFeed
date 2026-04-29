# Frontend mobile

> Interface style "shorts" pour consommer le fil de nouvelles sur mobile.

---

## Choix techniques

| Aspect | Choix | Justification |
|--------|-------|---------------|
| JS | Vanilla ES2022+ | Pas de build, pas de npm |
| CSS | Vanilla + custom properties | Thème sombre par défaut |
| Layout | CSS scroll-snap | Natif, 1 carte par écran |
| Vidéo | YouTube IFrame API | Standard pour embeds |
| Audio | HTML5 `<audio>` | Pas de lib externe |
| PWA | manifest.json + service worker | Optionnel, expérience app-like |

---

## Fonctionnalités

### Carte de nouvelle
Chaque carte occupe un écran complet et contient :
- **Image** de couverture (ou vidéo inline pour les shorts)
- **Titre** accrocheur
- **Résumé** en français (3-4 phrases)
- **Bouton TTS** play/pause
- **Bouton options** (⋮) : lien source, feedback, partage

### Navigation
- **Scroll vertical** avec snap (1 carte = 1 écran)
- **Compteur** de position (ex: "12/30")
- **Calendrier** pour accéder aux fils passés

### Vidéo
- **Shorts** (< 60s) : lecture inline auto-play
- **Vidéos longues** : résumé texte + lien vers YouTube

### Audio TTS
- Play/pause par carte
- L'audio s'arrête au changement de carte
- Voix : fr-CA-SylvieNeural

### Auth
- Page de login simple (mot de passe unique)
- Cookie de session signé
- Routes protégées

---

## Fichiers

```
frontend/
├── index.html        # Point d'entrée + login
├── manifest.json     # PWA
├── sw.js             # Service worker
├── css/
│   └── app.css       # Thème sombre, scroll-snap
└── js/
    ├── app.js        # Init, routing
    ├── api.js        # Fetch wrapper + auth
    ├── feed.js       # Scroll, navigation
    ├── player.js     # YouTube + audio TTS
    └── ui.js         # Carte, menu options, toast
```

---

## Critères de performance

- First load < 2s
- Pas de glitch en scroll rapide
- Fonctionne sur mobile via VPN

---

## Liens

- Retour : [[Vue d'ensemble]]
- Consomme : [[API REST]]
- Milestone principal : [[M4 — Frontend complet]]

#architecture #frontend
