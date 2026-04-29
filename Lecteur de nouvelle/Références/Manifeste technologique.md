# Manifeste technologique — Choix définitifs

> Référence unique pour toutes les décisions technologiques. Aucune ambiguïté.

---

## Stack à un coup d'oeil

| Couche | Choix |
|--------|-------|
| Langage | Python 3.11 + venv + pip |
| Config | YAML + .env |
| DB | SQLite + SQLAlchemy 2.0 + Alembic |
| Data interne | Dataclass `RawNewsItem` |
| API | JSON REST via Flask 3.1 |
| WSGI | Gunicorn (4 workers) |
| Reverse proxy | Nginx |
| Auth | Cookie de session signé Flask |
| Frontend | Vanilla JS (ES2022), Vanilla CSS, pas de build |
| TTS | Edge TTS (`fr-CA-SylvieNeural`) |
| LLM | Claude Sonnet (`anthropic` SDK) |
| YouTube | `google-api-python-client` + OAuth 2.0 |
| RSS | `feedparser` |
| Scraping | `beautifulsoup4` + `requests` + `lxml` |
| Images | Pillow → JPEG 720px |
| Déduplication | `rapidfuzz` (seuil 80%) |
| Tests | pytest + pytest-asyncio + pytest-cov |
| Logs | JSON structuré (`python-json-logger`) |
| Scheduling | systemd timer (6h00) |
| VCS | Git (branches par milestone, tags par gate) |

---

## Conventions de code

| Convention | Règle |
|------------|-------|
| Style | PEP 8 strict |
| Docstrings | Google style |
| Type hints | Obligatoires (fonctions publiques) |
| Imports | stdlib → tiers → projet |
| Fichiers | snake_case |
| Classes | PascalCase |
| Constantes | UPPER_SNAKE_CASE |
| Pas de `print()` | Utiliser StructuredLogger |
| Max par fichier | ~300 lignes |

---

## Git

| Aspect | Choix |
|--------|-------|
| Branching | `main` + branches par milestone |
| Commits | Français : `[M1] Ajoute l'agent YouTube subs` |
| Tags | Par gate : `gate-0`, `gate-1`, etc. |
| .gitignore | `venv/`, `secrets/`, `data/`, `logs/`, `__pycache__/` |

---

> Le document complet avec toutes les dépendances épinglées et les exemples de code est dans les fichiers source du projet.

---

## Liens

- Retour : [[Vue d'ensemble]]
- Voir aussi : [[Modèle de données]], [[Plan de projet]]

#référence #tech
