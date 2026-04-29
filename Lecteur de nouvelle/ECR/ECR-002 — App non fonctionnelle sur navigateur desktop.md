# ECR-002 — Scrollbar parasite au clic ⋮ sur navigateur desktop

> **Statut** : Corrigé  
> **Sévérité** : Moyen — mobile fonctionnel, desktop dégradé  
> **Découvert** : 2026-04-29  
> **Plateforme touchée** : Navigateur desktop (Chrome, Firefox, Edge)  
> **Plateforme OK** : Android (PWA via VPN)

---

## Symptôme observé

Sur desktop, quand l'utilisateur appuie sur le bouton `⋮`, une nouvelle barre de défilement apparaît à côté de la barre de défilement principale de la page au lieu d'afficher le menu de feedback/options.

---

## Cause racine

Le `.main-menu` est un élément `position: fixed` injecté dans `document.body`. Sur desktop, `html` et `body` n'avaient pas `overflow: hidden` — le navigateur calculait donc un `scrollHeight` plus grand que le `clientHeight` et affichait une scrollbar de niveau page.

Sur mobile (PWA), ce comportement est masqué car `overscroll-behavior: none` et le mode standalone suppriment la scrollbar native. Sur desktop browser, la scrollbar apparaît systématiquement.

```css
/* AVANT — body pouvait scroller */
html, body {
  height: 100%;
  overscroll-behavior: none;
  /* pas de overflow: hidden */
}

/* APRÈS — body ne scrolle jamais, tout le scroll est dans #feed */
html, body {
  height: 100%;
  overflow: hidden;
  overscroll-behavior: none;
}
```

---

## Correction appliquée

Ajout de `overflow: hidden` sur `html` et `body` dans `app.css`. Le scroll de contenu se fait exclusivement dans `#feed` (déjà `overflow-y: scroll`), donc aucune perte fonctionnelle.

---

## Point de vigilence pour les tests futurs

> ⚠️ **À couvrir dans les tests cross-platform**

| ID | Scénario | Résultat attendu |
|----|----------|-----------------|
| T-UI-06 | Clic ⋮ sur desktop Chrome | Menu ouvert, aucune scrollbar parasite |
| T-UI-07 | Clic ⋮ sur desktop Firefox | Même comportement que Chrome |
| T-UI-08 | Scroll du feed sur desktop | Seul le feed scrolle, le body reste fixe |
| T-DEPLOY-01 | Validation cross-platform avant gate | Mobile ET desktop testés systématiquement |

### Règle générale

> Tout composant injecté dans `document.body` (menu, modal, toast) doit être `position: fixed` **et** le `body` doit avoir `overflow: hidden` pour éviter les scrollbars parasites sur desktop.  
> Toute gate de milestone doit être validée sur **au moins deux plateformes** avant d'être marquée complète.

---

## Liens

- [[ECR-001 — Bouton calendrier dupliqué au re-login]]
- [[Frontend mobile]]
- [[M4 — Frontend complet]]

#ecr #bug #desktop #css #overflow
