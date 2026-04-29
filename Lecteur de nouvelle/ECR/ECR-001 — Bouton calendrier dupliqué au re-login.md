# ECR-001 — Bouton calendrier dupliqué au re-login

> **Statut** : Corrigé  
> **Sévérité** : Moyen — UX cassée, pas de perte de données  
> **Découvert** : 2026-04-29 (test mobile Android)  
> **Corrigé dans** : commit `[fix] startApp() idempotent + calendrier dans top-bar-actions`

---

## Symptômes observés

1. **Icône 📅 dupliquée** : à chaque login, un nouveau bouton d'historique s'ajoutait dans la barre supérieure. Après 3 logins → 3 boutons empilés.
2. **Bouton logout déplacé au centre** : le bouton ⎋ se retrouvait au milieu de la barre au lieu d'être à droite, car le bouton 📅 était inséré directement dans `#top-bar` (flex container) au lieu de `#top-bar-actions`.

---

## Cause racine

`startApp()` était appelé à chaque `showApp()` (donc à chaque login réussi), sans garde. Chaque appel créait un nouveau `buildCalendarBtn()` et l'appendait au DOM sans vérifier si un bouton existait déjà.

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

> Tout code qui modifie le DOM dans une fonction appelée au login **doit** utiliser l'une de ces stratégies :
> 1. **Garde par flag** (`if (_started) return`)
> 2. **Vérification d'existence** (`if (!document.getElementById('btn-calendar'))`)
> 3. **Supprimer avant de recréer** (`el.remove()` puis recréer)

---

## Liens

- [[Vue d'ensemble]]
- [[Frontend mobile]]
- [[M4 — Frontend complet]]

#ecr #bug #frontend #tests
