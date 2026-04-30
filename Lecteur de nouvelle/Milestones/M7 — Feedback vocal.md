# M7 — Feedback vocal transcrit en temps réel

> Bouton microphone dans les sections commentaire et rapport de bug. L'utilisateur appuie pour démarrer l'enregistrement, réappuie pour arrêter — la transcription complète arrive d'un coup via Google STT V2.

---

## Décision technologique : Google Cloud Speech-to-Text V2

| Critère | Web Speech API | **Google Cloud STT V2** ✅ | Whisper API | Azure Speech |
|---------|:---:|:---:|:---:|:---:|
| fr-CA natif | Oui | **Oui** | Partiel | Oui |
| Précision | Bonne | **Très bonne (latest_long)** | Excellente | Très bonne |
| Credentials existants | — | **Oui** | Non | Non |
| Détection auto encodage | Non | **Oui (AutoDetect)** | Non | Non |
| Contrôle backend | Non | **Oui** | Oui | Oui |
| Coût/min | Gratuit | ~$0.016 | ~$0.006 | ~$0.017 |

**Raison du choix V2 vs V1 :**
- Modèle `latest_long` — meilleure précision fr-CA
- `AutoDetectDecodingConfig` — Google détecte encoding + sample rate depuis les headers du fichier WebM, plus de risque d'erreur de configuration
- Inline recognizer (`recognizers/_`) — sans pré-création de ressource

---

## Comportement final (push-to-talk toggle)

1. Tap 🎤 → **"🔴 Enregistrement…"** + bouton rouge + canvas barres rouges
2. L'utilisateur parle (durée libre)
3. Re-tap 🎤 → enregistrement s'arrête → **"⏳ Transcription…"**
4. Google STT V2 retourne la transcription complète → texte apparaît dans le textarea → status disparaît

> **Note :** Le push-to-hold (maintenir enfoncé) a été abandonné — Chrome Android déclenche son menu contextuel natif après ~500ms, comportement OS non suppressible en contexte navigateur.

---

## Architecture

```
[Navigateur]
  Tap 🎤 → MediaRecorder.start() (NO timeslice)
  Re-tap → MediaRecorder.stop() → blob WebM complet
       │
       ▼ POST /api/speech/transcribe (base64 + mime_type)
[Backend Flask]
  Google STT V2 — AutoDetectDecodingConfig
  model="latest_long", language_codes=["fr-CA"]
  Inline recognizer: projects/{project}/locations/global/recognizers/_
       │
       ▼ {"transcript": "texte reconnu"}
[Navigateur]
  Texte appendé au textarea
```

---

## Stockage

Les transcriptions ne sont **pas stockées séparément**. Le texte dicté remplit le textarea, puis est sauvegardé via les routes existantes :
- Commentaire → `POST /api/news/<id>/comments` → table `news_comments`
- Rapport de bug → `POST /api/bugs` → table `bug_reports`

---

## Fichiers créés / modifiés

| Fichier | Action | Détail |
|---------|--------|--------|
| `requirements.txt` | Modifié | `google-cloud-speech==2.38.0` |
| `backend/api/speech.py` | Créé | Blueprint `speech_bp` — Google STT V2 |
| `backend/app.py` | Modifié | Enregistrement `speech_bp` |
| `frontend/js/speech.js` | Créé | `voiceSupported`, `createVoiceRecorder()` — MediaRecorder + fetch |
| `frontend/js/ui.js` | Modifié | Bouton 🎤 dans `_buildInputSection`, status "Enregistrement…" / "Transcription…" |
| `frontend/css/app.css` | Modifié | `.btn-mic`, `.btn-mic--recording`, `.voice-status`, `.voice-amplitude` |
| `frontend/sw.js` | Modifié | Cache v5 (invalidation forcée) |

---

## Permissions Google Cloud requises

Le compte de service doit avoir le rôle **Cloud Speech Editor** (`roles/speech.editor`) pour accéder à l'API V2.
- V1 utilisait des permissions différentes (`speech.googleapis.com` standard)
- V2 requiert `speech.recognizers.recognize` — inclus dans `roles/speech.editor`

---

## Tâches

- [x] 7.1 — `requirements.txt` : `google-cloud-speech==2.38.0`
- [x] 7.2 — `backend/api/speech.py` : Google STT V2, AutoDetectDecodingConfig, latest_long
- [x] 7.3 — `backend/app.py` : enregistrement `speech_bp`
- [x] 7.4 — `frontend/js/speech.js` : MediaRecorder sans timeslice, push-to-talk toggle
- [x] 7.5 — `frontend/js/ui.js` : bouton 🎤, status "Enregistrement…" / "Transcription…", canvas amplitude
- [x] 7.6 — `frontend/css/app.css` : styles mic, animation pulse, voice-status, voice-amplitude

---

## Gate 7 — Critères

- [x] Tap 🎤 → "🔴 Enregistrement…" visible
- [x] Re-tap → "⏳ Transcription…" puis texte dans le textarea
- [x] Aucune transcription pendant l'enregistrement (blob envoyé en une fois)
- [x] Saisie manuelle non affectée (aucune régression)
- [x] Google STT V2 (`latest_long`, `fr-CA`) opérationnel
- [x] Cache navigateur invalidé (SW v5 + Cache-Control: no-cache)

---

## Liens

- Précédent : [[M6 — Commentaires et bugs]]
- Retour : [[Vue d'ensemble]]
- Composants : [[Frontend mobile]], [[API REST]]
- Routes utilisées : `POST /api/news/<id>/comments`, `POST /api/bugs`

#milestone #m7 #vocal #google-stt-v2 #frontend #terminé
