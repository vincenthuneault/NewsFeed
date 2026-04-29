# Modèle de données

> Le contrat central du système. Tous les [[Agents de collecte|agents]] produisent des `RawNewsItem`. Tous les processeurs du [[Pipeline de traitement|pipeline]] les consomment.

---

## RawNewsItem (dataclass)

### Champs obligatoires (remplis par l'agent)
| Champ | Type | Description |
|-------|------|-------------|
| `title` | `str` | Titre de la nouvelle |
| `source_url` | `str` | URL de la source originale |
| `source_name` | `str` | Nom lisible (ex: "Radio-Canada") |
| `category` | `str` | Catégorie normalisée (voir ci-dessous) |
| `published_at` | `datetime` | Date de publication |

### Champs optionnels (remplis par l'agent si disponible)
| Champ | Type | Défaut | Description |
|-------|------|--------|-------------|
| `description` | `str \| None` | `None` | Description courte ou extrait |
| `image_url` | `str \| None` | `None` | URL image/thumbnail |
| `video_url` | `str \| None` | `None` | URL embed vidéo |
| `video_type` | `str \| None` | `None` | `"short"` (< 60s) ou `"long"` |
| `raw_content` | `str \| None` | `None` | Contenu brut pour le résumé |
| `popularity_score` | `float` | `0.0` | Score brut (vues, partages) |
| `metadata` | `dict \| None` | `None` | Données spécifiques à l'agent |

### Champs générés par le pipeline (jamais par l'agent)
| Champ | Ajouté par | Description |
|-------|-----------|-------------|
| `summary_fr` | Summarizer | Résumé en français |
| `image_path` | ImageExtractor | Chemin local JPEG |
| `audio_path` | TTSGenerator | Chemin local MP3 |
| `final_score` | Scorer | Score final pondéré |

---

## Catégories normalisées

| Clé | Label | Agent associé |
|-----|-------|---------------|
| `youtube_subs` | Mes abonnements YouTube | youtube_subs |
| `youtube_trending` | Tendances YouTube | youtube_trending |
| `viral` | Contenu viral | viral_trending |
| `tech_ai` | Tech & IA | rss_generic |
| `politique_intl` | Politique internationale | rss_generic |
| `politique_ca` | Politique canadienne | rss_generic |
| `politique_qc` | Politique québécoise | rss_generic |
| `evenements_mtl` | Événements Montréal | events_montreal |
| `musique_electro` | Musique électronique | events_montreal |
| `humour` | Humour | events_montreal |
| `local_contrecoeur` | Contrecoeur & Sorel | local_contrecoeur |
| `local_alerte` | Alertes locales | local_contrecoeur |
| `vehicules_ev` | Véhicules électriques & autonomes | rss_generic |
| `spatial` | Espace & exploration | rss_generic |

---

## Base de données

| Choix | Détail |
|-------|--------|
| Moteur | SQLite 3 |
| ORM | SQLAlchemy 2.0 (déclaratif) |
| Migrations | `Base.metadata.create_all()` au démarrage |
| Fichier | `/home/vhds/NewsFeed/data/newsfeed.db` |
| Config | `config.yaml` → `database.url: sqlite:///data/newsfeed.db` |

Convention : chaque table a `id` (autoincrement PK) et `created_at` (UTC).

### Tables existantes

| Table | Classe | Description |
|-------|--------|-------------|
| `news_items` | `NewsItem` | Nouvelles traitées par le pipeline |
| `daily_feeds` | `DailyFeed` | Fil quotidien assemblé (liste d'IDs ordonnés) |
| `feedbacks` | `Feedback` | Réactions utilisateur (`like`/`dislike`/`skip`) — alimente le scoring |
| `news_comments` | `NewsComment` | Notes personnelles sur une nouvelle — **pas de lien avec le scoring** |
| `bug_reports` | `BugReport` | Rapports de bugs soumis depuis l'interface |
| `agent_runs` | `AgentRun` | Logs d'exécution des agents (durée, items collectés, erreurs) |

### Détail des tables M6

**`news_comments`** — note perso liée à un article

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | Integer PK | Identifiant |
| `news_item_id` | Integer FK → `news_items.id` | Article commenté |
| `body` | Text | Texte du commentaire (max 2000 car.) |
| `created_at` | DateTime UTC | Date de saisie |

**`bug_reports`** — rapport de bug depuis le menu ⋮

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | Integer PK | Identifiant |
| `description` | Text | Description du problème (max 5000 car.) |
| `context` | Text (JSON) | Contexte capturé auto : `article_id`, `article_title`, `user_agent`, `timestamp` |
| `created_at` | DateTime UTC | Date de soumission |

---

## Sérialisation

| Frontière | Format |
|-----------|--------|
| Agent → Pipeline | Objets Python (en mémoire) |
| Pipeline → DB | SQLAlchemy ORM |
| Backend → Frontend | JSON REST (UTF-8) |
| Config → Tous | Dict Python (depuis YAML) |
| Logs → Fichiers | JSON structuré (1 ligne/entrée) |

Dates en ISO 8601. IDs en integer. Listes paginées si > 50 items.

---

## Liens

- Retour : [[Vue d'ensemble]]
- Produit par : [[Agents de collecte]]
- Transformé par : [[Pipeline de traitement]]
- Servi par : [[API REST]]

#architecture #données
