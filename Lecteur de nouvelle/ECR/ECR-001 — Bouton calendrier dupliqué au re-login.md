# ECR-001 — Bouton calendrier dupliqué au re-login

> **Statut** : Corrigé (3e tentative)  
> **Sévérité** : Moyen — UX cassée, pas de perte de données  
> **Découvert** : 2026-04-29 (test mobile Android)  
> **Corrigé dans** : commit `[fix] Garde DOM + JS exclu du cache service worker`

---

## Symptômes observés

1. **Icône 📅 dupliquée** : à chaque login, un nouveau bouton d'historique s'ajoutait dans la barre supérieure. Après 3 logins → 3 boutons empilés.
2. **Bouton logout déplacé au centre** : le bouton ⎋ se retrouvait au milieu de la barre au lieu d'être à droite, car le bouton 📅 était inséré directement dans `#top-bar` (flex container) au lieu de `#top-bar-actions`.

---

## Cause racine (finale — 2 couches)

**Couche 1 — Absence de garde dans `startApp()`**
`startApp()` était appelé à chaque `showApp()` sans vérifier si le bouton existait déjà.

**Couche 2 — Cache service worker (plus subtile)**
La première correction utilisait un flag module (`_appStarted`). Ce flag se reset à `false` à chaque rechargement complet de la page (force kill PWA). Le service worker en Cache First servait l'ancien `app.js` même après un déploiement, masquant les correctifs.

**Leçon clé** : dans une PWA, un flag module n'est jamais une garde fiable entre sessions. Seul le DOM est persistant au sein d'une même page chargée.

```js
// AVANT (bug)
function showApp() {
  loginScreen.classList.add("hidden");
  appScreen.classList.remove("hidden");
  startApp(); // ← appelé à chaque login
}

function startApp() {
  const topBar = document.getElementById("top-bar");
  const calBtn = buildCalendarBtn(...);
  topBar?.appendChild(calBtn); // ← ajout sans garde, mauvais parent
}
```

---

## Correction appliquée

```js
// APRÈS (corrigé)
let _appStarted = false;

function startApp() {
  loadFeed("today"); // toujours relancer le feed au login

  if (_appStarted) return; // ← garde : initialise l'UI une seule fois
  _appStarted = true;

  setupProgressBar();
  const actions = document.getElementById("top-bar-actions");
  const calBtn = buildCalendarBtn(...);
  actions?.insertBefore(calBtn, actions.firstChild); // ← bon parent
}
```

---

## Point de vigilence pour les tests futurs

> ⚠️ **À couvrir dans les tests d'intégration frontend (M4+)**

Tout composant UI initialisé dans `startApp()` doit être **idempotent** : appelable plusieurs fois sans effet de bord visible.

### Cas de test à implémenter

| ID | Scénario | Résultat attendu |
|----|----------|-----------------|
| T-UI-01 | Login → Logout → Login | Un seul bouton 📅 dans la barre |
| T-UI-02 | Login → Logout → Login × 3 | Barre du haut identique à la première session |
| T-UI-03 | Session expirée (401 API) → re-login | Même comportement que T-UI-01 |
| T-UI-04 | Bouton ⎋ logout visible à droite | Toujours en position rightmost de `#top-bar-actions` |
| T-UI-05 | Bouton 📅 → modal calendrier → fermer → re-ouvrir | Un seul modal, pas d'empilement |

### Règle générale à appliquer

> Tout code qui modifie le DOM dans une fonction appelée au login **doit** utiliser :
> 1. **Vérification DOM** (`if (!document.getElementById('btn-calendar'))`) — seule garde fiable en PWA
> 2. **Supprimer avant de recréer** (`el.remove()` puis recréer) — alternative sûre
>
> ⚠️ **Ne pas utiliser** un flag module (`let _started = false`) comme garde unique dans une PWA — il se reset à chaque rechargement de page (force kill).

### Règle service worker

> Les fichiers JS ne doivent **jamais** être mis en Cache First dans le service worker. Utiliser Network First ou les exclure complètement du cache. Un JS caché bloque le déploiement de correctifs sans que l'utilisateur le sache.

---

## Liens

- [[Vue d'ensemble]]
- [[Frontend mobile]]
- [[M4 — Frontend complet]]

#ecr #bug #frontend #tests
