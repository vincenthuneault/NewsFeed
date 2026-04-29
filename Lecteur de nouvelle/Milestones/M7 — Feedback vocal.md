# M7 — Feedback vocal transcrit en temps réel

> Ajouter un bouton microphone dans les sections de commentaire et de rapport de bug. L'utilisateur parle, le texte apparaît dans le champ en direct. Il peut corriger avant d'envoyer.

---

## Décision technologique

### Web Speech API (browser-native) — choix retenu

| Critère | Web Speech API | Google Cloud STT | Whisper API |
|---------|---------------|-----------------|------------|
| Temps réel | Oui (interimResults) | Oui (streaming WebSocket) | Non (batch) |
| Coût | Gratuit | ~$0.006/15s | ~$0.006/min |
| Backend requis | Non | Oui (WebSocket) | Oui (POST) |
| Langue fr-CA | Oui | Oui | Partiel |
| Support Android PWA | Chrome ✅ | Tous | Tous |
| Complexité | Faible | Élevée | Moyenne |

**Raison du choix** : la cible principale est l'Android PWA (Chrome). La Web Speech API donne du temps réel natif, zéro coût, zéro backend, en une vingtaine de lignes JS. Le projet a déjà des credentials Google (TTS), mais ajouter un WebSocket de streaming STT serait une sur-ingénierie pour ce cas d'usage.

**Fallback** : si le navigateur ne supporte pas `SpeechRecognition` (Firefox, vieux Safari), le bouton micro est simplement masqué — le textarea reste utilisable normalement.

---

## Comportement attendu

1. L'utilisateur ouvre le menu ⋮ et clique 💬 ou 🐛 → le textarea apparaît
2. À côté du bouton Envoyer, un bouton 🎤 est visible
3. Clic sur 🎤 → enregistrement démarre
   - Bouton devient rouge avec animation de pulsation
   - Les mots apparaissent dans le textarea au fur et à mesure
   - Le texte intermédiaire (en cours de reconnaissance) s'affiche en italique/gris
   - Le texte confirmé s'affiche normalement
4. Clic sur 🎤 à nouveau → enregistrement s'arrête
5. L'utilisateur peut modifier le texte transcrit avant d'envoyer
6. Clic Envoyer → fonctionne exactement comme sans vocal

---

## Architecture technique

### Nouveau module `frontend/js/speech.js`

Wrapper isolé autour de `SpeechRecognition` :

```js
// Vérifie la disponibilité
export const speechSupported =
  !!(window.SpeechRecognition || window.webkitSpeechRecognition);

// Crée un recognizer configuré fr-CA
// Callbacks : onInterim(texte_partiel), onFinal(texte_confirmé), onStop(), onError(msg)
export function createSpeechRecognizer({ onInterim, onFinal, onStop, onError }) { ... }
```

Paramètres de configuration :
- `lang = 'fr-CA'` — cohérent avec le TTS
- `interimResults = true` — affichage en direct
- `continuous = true` — ne s'arrête pas après une pause

Gestion des résultats (`onresult`) :
- Parcourt `event.results` depuis `event.resultIndex`
- Accumule les résultats `isFinal` dans un buffer
- Passe le texte intermédiaire via `onInterim`
- Passe le texte confirmé (avec buffer précédent) via `onFinal`

### Modifications `frontend/js/ui.js`

Mettre à jour `_buildInputSection` pour accepter un paramètre `withVoice: true` (ou toujours activer si supporté) :

```
[ textarea 3 lignes                    ]
[ 🎤 Micro ]  [ Envoyer ]   ← boutons en ligne
```

- Import `speechSupported`, `createSpeechRecognizer` depuis `speech.js`
- Si `!speechSupported` → bouton 🎤 non ajouté (dégradation silencieuse)
- Clic 🎤 :
  - Si pas en cours → `recognizer.start()`, bouton passe en état `.btn-mic--recording`
  - Si en cours → `recognizer.stop()`
- `onInterim` → `textarea.value = confirmedText + ' ' + interimText` (italic via data-attr ou span overlay — voir note ci-dessous)
- `onFinal` → `textarea.value = fullText`, met à jour `confirmedText`
- `onStop` → retire l'état `.btn-mic--recording`

> **Note sur l'italic** : le textarea HTML ne permet pas de style inline partiel. Deux approches :
> - **Simple** : texte intermédiaire en minuscules dans le textarea, texte confirmé en normal → indiqué par la casse
> - **Visuelle** : afficher un `div` overlay transparent par-dessus le textarea pour le texte intermédiaire stylisé
>
> → **Retenu : approche simple**. Texte intermédiaire suffixé de `…` dans le textarea. Zéro complexité DOM.

### Modifications `frontend/css/app.css`

```css
/* Bouton micro */
.btn-mic { ... }                        /* même style que .menu-send-btn */
.btn-mic--recording { color: red; }    /* état actif */
@keyframes pulse-mic { ... }           /* pulsation douce */
.btn-mic--recording { animation: pulse-mic 1s ease-in-out infinite; }

/* Rangée boutons sous le textarea */
.menu-textarea-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}
```

---

## Fichiers à créer / modifier

| Fichier | Action | Détail |
|---------|--------|--------|
| `frontend/js/speech.js` | Créer | Wrapper `SpeechRecognition` : `speechSupported`, `createSpeechRecognizer()` |
| `frontend/js/ui.js` | Modifier | `_buildInputSection` : bouton 🎤, intégration speech.js |
| `frontend/css/app.css` | Modifier | `.btn-mic`, `.btn-mic--recording`, `@keyframes pulse-mic`, `.menu-textarea-actions` |

**Aucun changement backend.** Les données transcrites sont envoyées via les routes existantes (`POST /api/news/<id>/comments` et `POST /api/bugs`).

---

## Tâches

- [ ] 7.1 — `speech.js` : wrapper `SpeechRecognition` avec `speechSupported` + `createSpeechRecognizer()`
- [ ] 7.2 — `ui.js` : bouton 🎤 dans `_buildInputSection`, état recording, callbacks interim/final
- [ ] 7.3 — `app.css` : `.btn-mic`, animation pulse, `.menu-textarea-actions`

---

## Tests manuels (gate de validation)

| ID | Scénario | Résultat attendu |
|----|----------|-----------------|
| T-VOC-01 | Chrome Android — clic 🎤 → parler en fr | Texte apparaît dans le textarea en direct |
| T-VOC-02 | Parler, stopper, corriger manuellement, Envoyer | Texte final = transcription ± corrections |
| T-VOC-03 | Firefox — ouvrir menu ⋮ | Bouton 🎤 absent, textarea seul visible |
| T-VOC-04 | Clic 🎤, parler, recliquer 🎤 | Enregistrement s'arrête, texte reste dans le textarea |
| T-VOC-05 | Refus de permission micro | Toast "Microphone non autorisé", pas de crash |
| T-VOC-06 | Vocal + Envoyer commentaire | Commentaire enregistré en DB (même vérification que T-COM-02) |
| T-VOC-07 | Vocal + Envoyer rapport de bug | Rapport enregistré en DB (même vérification que T-BUG-02) |
| T-REG-01 | Envoyer texte saisi manuellement | Aucune régression — fonctionne toujours sans micro |

---

## Gate 7 — Critères

- [ ] T-VOC-01 à T-VOC-07 passent
- [ ] T-REG-01 : aucune régression sur la saisie manuelle
- [ ] Aucun crash si permission micro refusée
- [ ] Bouton 🎤 absent sur navigateur non supporté (dégradation silencieuse)

---

## Liens

- Précédent : [[M6 — Commentaires et bugs]]
- Retour : [[Vue d'ensemble]]
- Composants touchés : [[Frontend mobile]]
- Utilise les routes de : [[M6 — Commentaires et bugs]]

#milestone #m7 #vocal #speech #frontend
