# M7 — Feedback vocal transcrit en temps réel

> Ajouter un bouton microphone dans les sections de commentaire et de rapport de bug. L'utilisateur parle, le texte apparaît dans le champ en direct. Il peut corriger avant d'envoyer.

---

## Décision technologique : Google Cloud Speech-to-Text

| Critère | Web Speech API | **Google Cloud STT** ✅ | Whisper API | Azure Speech |
|---------|:---:|:---:|:---:|:---:|
| Temps réel (chunks) | Oui | **Oui** | Non (batch) | Oui |
| fr-CA natif | Oui | **Oui** | Partiel | Oui |
| Précision | Bonne | **Très bonne** | Excellente | Très bonne |
| Credentials existants | — | **Oui** | Non | Non |
| Contrôle backend | Non | **Oui** | Oui | Oui |
| Coût/min | Gratuit | ~$0.016 | ~$0.006 | ~$0.017 |

**Raison du choix :** les credentials Google (`GOOGLE_APPLICATION_CREDENTIALS`) sont déjà en place pour le TTS. Même infrastructure, même compte de facturation. Précision supérieure à la Web Speech API, contrôle côté serveur.

---

## Architecture : chunks audio via HTTP

```
[Navigateur]
  MediaRecorder → chunk audio/webm;opus toutes les 3s
       │
       ▼ POST /api/speech/transcribe  (base64 + mime_type)
[Backend Flask]
  google.cloud.speech → recognize() → transcript
       │
       ▼ {"transcript": "texte reconnu"}
[Navigateur]
  Append au textarea → affichage en direct
```

Pas de WebSocket. Chaque chunk de 3 secondes est traité indépendamment. Latence perçue : ~1-2s après la fin de chaque phrase.

---

## Comportement attendu

1. Ouvrir menu ⋮ → 💬 ou 🐛 → textarea apparaît
2. Bouton 🎤 visible à gauche du bouton Envoyer
3. Clic 🎤 → enregistrement démarre (bouton pulse rouge)
4. Toutes les 3 secondes → chunk envoyé → texte ajouté au textarea
5. Clic 🎤 à nouveau → arrêt (dernier chunk traité avant stop)
6. Le texte transcrit est éditable → Envoyer comme d'habitude
7. Si permission refusée → toast "Microphone non autorisé", pas de crash
8. Si navigateur sans `MediaRecorder` → bouton 🎤 absent (dégradation silencieuse)

---

## Stockage

Les transcriptions ne sont **pas stockées séparément**. Le texte dicté remplit le textarea, puis est sauvegardé via les routes existantes :
- Commentaire → `POST /api/news/<id>/comments` → table `news_comments`
- Rapport de bug → `POST /api/bugs` → table `bug_reports`

---

## Fichiers à créer / modifier

| Fichier | Action | Détail |
|---------|--------|--------|
| `requirements.txt` | Modifier | Ajouter `google-cloud-speech` |
| `backend/api/speech.py` | Créer | Blueprint `speech_bp` : `POST /api/speech/transcribe` |
| `backend/app.py` | Modifier | Enregistrer `speech_bp` |
| `frontend/js/speech.js` | Créer | `voiceSupported`, `createVoiceRecorder()` (MediaRecorder + fetch) |
| `frontend/js/ui.js` | Modifier | `_buildInputSection` : bouton 🎤, intégration speech.js |
| `frontend/css/app.css` | Modifier | `.btn-mic`, `.btn-mic--recording`, `@keyframes pulse-mic`, `.menu-textarea-actions` |

---

## Détail technique

### `backend/api/speech.py`

```
POST /api/speech/transcribe
Body : { "audio": "<base64>", "mime_type": "audio/webm;codecs=opus" }
Réponse : { "transcript": "texte reconnu" }
```

- Détecte l'encodage depuis le mime_type (`webm` → WEBM_OPUS, `ogg` → OGG_OPUS)
- Appelle `speech.SpeechClient().recognize()` avec `language_code="fr-CA"`
- Retourne le transcript concaténé de tous les segments

### `frontend/js/speech.js`

- `voiceSupported` — `true` si `MediaRecorder` + `getUserMedia` disponibles
- `createVoiceRecorder({ onTranscript, onStop, onError })` — démarre/arrête l'enregistrement, envoie les chunks, rappelle `onTranscript(texteAccumulé)` à chaque résultat

### `frontend/js/ui.js`

Mise à jour de `_buildInputSection` :
- Rangée boutons : `[🎤]  [Envoyer]` (mic à gauche si supporté)
- Clic mic : toggle recording + état visuel
- `onTranscript` : `textarea.value = texte`

---

## Tâches

- [ ] 7.1 — `requirements.txt` : ajouter `google-cloud-speech`
- [ ] 7.2 — `backend/api/speech.py` : blueprint POST /api/speech/transcribe
- [ ] 7.3 — `backend/app.py` : enregistrer speech_bp
- [ ] 7.4 — `frontend/js/speech.js` : MediaRecorder + chunks + fetch
- [ ] 7.5 — `frontend/js/ui.js` : bouton 🎤 dans _buildInputSection
- [ ] 7.6 — `frontend/css/app.css` : styles mic + animation pulse

---

## Tests manuels (gate de validation)

| ID | Scénario | Résultat attendu |
|----|----------|-----------------|
| T-VOC-01 | Chrome Android — clic 🎤 → parler en fr | Texte apparaît dans le textarea (délai ~3s) |
| T-VOC-02 | Parler, stopper, corriger, Envoyer | Texte final = transcription ± corrections |
| T-VOC-03 | Navigateur sans MediaRecorder | Bouton 🎤 absent, textarea seul |
| T-VOC-04 | Refus permission micro | Toast "Microphone non autorisé", pas de crash |
| T-VOC-05 | Vocal → commentaire Envoyer | Entrée en DB (table news_comments) |
| T-VOC-06 | Vocal → rapport de bug Envoyer | Entrée en DB (table bug_reports) avec contexte |
| T-REG-01 | Saisie manuelle sans micro | Aucune régression |

---

## Gate 7 — Critères

- [ ] T-VOC-01 à T-VOC-06 passent
- [ ] T-REG-01 : saisie manuelle non affectée
- [ ] Aucun crash sur permission refusée
- [ ] Dégradation silencieuse sur navigateur non supporté

---

## Liens

- Précédent : [[M6 — Commentaires et bugs]]
- Retour : [[Vue d'ensemble]]
- Composants : [[Frontend mobile]], [[API REST]]
- Routes utilisées : `POST /api/news/<id>/comments`, `POST /api/bugs`

#milestone #m7 #vocal #google-stt #frontend
