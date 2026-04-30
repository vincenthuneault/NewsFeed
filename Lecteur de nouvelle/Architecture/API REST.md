# API REST

> Sert le contenu traité au [[Frontend mobile]] via des endpoints JSON.

---

## Stack

| Composant | Choix |
|-----------|-------|
| Framework | Flask 3.1 |
| WSGI | Gunicorn (4 workers) |
| Reverse proxy | Nginx (HTTPS, mkcert) |
| Auth | Cookie de session signé Flask |
| Format | JSON, dates ISO 8601 |

---

## Endpoints

| Méthode | Route | Description | Milestone |
|---------|-------|-------------|-----------|
| `GET` | `/api/feed/today` | Fil du jour | [[M1 — Vertical slice\|M1]] |
| `GET` | `/api/feed/{date}` | Fil d'une date passée | [[M2 — Multi-agents\|M2]] |
| `GET` | `/api/feed/dates` | Liste des dates disponibles | [[M2 — Multi-agents\|M2]] |
| `GET` | `/api/news/{id}` | Détail d'une nouvelle | [[M1 — Vertical slice\|M1]] |
| `POST` | `/api/news/{id}/feedback` | Like / dislike / skip | [[M3 — Feedback\|M3]] |
| `GET` | `/api/settings` | Préférences utilisateur | [[M3 — Feedback\|M3]] |
| `PUT` | `/api/settings` | Modifier les préférences | [[M3 — Feedback\|M3]] |
| `POST` | `/api/auth/login` | Authentification | [[M4 — Frontend complet\|M4]] |
| `POST` | `/api/auth/logout` | Déconnexion | [[M4 — Frontend complet\|M4]] |
| `GET` | `/api/health` | Rapport de santé complet | [[M5 — Production\|M5]] |
| `GET` | `/api/version` | Version de l'application (sans DB) | [[M6 — Commentaires et bugs\|M6]] |
| `POST` | `/api/news/{id}/comments` | Créer un commentaire personnel | [[M6 — Commentaires et bugs\|M6]] |
| `GET` | `/api/news/{id}/comments` | Lire les commentaires d'une nouvelle | [[M6 — Commentaires et bugs\|M6]] |
| `POST` | `/api/bugs` | Soumettre un rapport de bug | [[M6 — Commentaires et bugs\|M6]] |
| `POST` | `/api/speech/transcribe` | Audio → texte (Google STT V2, fr-CA) | [[M7 — Feedback vocal\|M7]] |

---

## Convention d'erreur

```json
{
  "error": true,
  "message": "Description lisible",
  "code": "NOT_FOUND"
}
```

Codes HTTP : 200, 201, 400, 401, 404, 500.

---

## Fichiers

```
backend/
├── app.py          # Factory Flask — enregistre tous les blueprints
├── auth.py         # Login + middleware cookie
└── api/
    ├── feed.py     # Routes /api/feed/*
    ├── feedback.py # Routes feedback (like/dislike/skip)
    ├── comments.py # Routes /api/news/{id}/comments  ← M6
    ├── bugs.py     # Route  /api/bugs                ← M6
    ├── speech.py   # Route  /api/speech/transcribe   ← M7 (Google STT V2)
    ├── settings.py # Routes settings
    └── health.py   # Routes /api/health + /api/version
```

---

## Liens

- Retour : [[Vue d'ensemble]]
- Reçoit de : [[Pipeline de traitement]] (via DB)
- Sert vers : [[Frontend mobile]]
- Utilise : [[Modèle de données]]

#architecture #api
