# Base de données

> **Moteur** : SQLite 3  
> **ORM** : SQLAlchemy 2.0  
> **Fichier** : `data/newsfeed.db`  
> **Tables** : 11  
> **Migrations** : `Base.metadata.create_all()` au démarrage du pipeline

---

## Vue d'ensemble

```
data/newsfeed.db
│
├── Pipeline ──────────────────────────────────────────
│   ├── news_items          (553 lignes)  ← cœur du système
│   ├── daily_feeds          (20 lignes)  ← feed publié chaque jour
│   └── agent_runs          (237 lignes)  ← logs d'exécution
│
├── Interactions utilisateur ──────────────────────────
│   ├── feedbacks            (57 lignes)  ← like / dislike / skip
│   ├── news_comments        (43 lignes)  ← notes personnelles
│   └── bug_reports          (10 lignes)  ← rapports de bugs
│
└── Aftersales ────────────────────────────────────────
    ├── ecr                   (0 lignes)  ← Engineering Change Records
    ├── mca                   (0 lignes)  ← Mises à jour Contexte Agent
    ├── investigations         (0 lignes)  ← logs d'investigation
    ├── ecr_status_history     (0 lignes)  ← audit trail ECR
    └── mca_status_history     (0 lignes)  ← audit trail MCA
```

---

## Pipeline

### `news_items` — 553 lignes

**But** : Mémoire centrale du système. Contient tous les articles jamais traités par le pipeline depuis le démarrage.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | Integer PK | Identifiant unique |
| `title` | String | Titre de l'article |
| `source_url` | String (unique) | URL originale — contrainte d'unicité = déduplication |
| `source_name` | String | Nom de la source (ex: "Radio-Canada") |
| `category` | String | Catégorie normalisée (tech_ai, politique_qc, etc.) |
| `published_at` | DateTime | Date de publication sur la source originale |
| `description` | Text | Extrait brut de la source |
| `image_url` | String | URL image distante |
| `video_url` | String | URL embed vidéo |
| `video_type` | String | `short` ou `long` |
| `raw_content` | Text | Contenu brut pour génération du résumé |
| `popularity_score` | Float | Score brut de popularité (vues, partages) |
| `summary_fr` | Text | Résumé en français généré par le Summarizer |
| `image_path` | String | Chemin local du fichier image téléchargé |
| `audio_path` | String | Chemin local du fichier MP3 généré |
| `final_score` | Float | Score final pondéré (fraîcheur + popularité + feedback) |
| `created_at` | DateTime UTC | Date d'ingestion dans le système |
| `updated_at` | DateTime UTC | Dernière modification |

> **Note architecture** : `published_at` = date source originale. `created_at` = date d'ingestion pipeline. Ces deux dates peuvent différer d'un jour si la source publie en soirée et le pipeline tourne le lendemain matin.

---

### `daily_feeds` — 20 lignes

**But** : Enregistre le fil de nouvelles publié chaque jour. Contient la liste ordonnée des IDs d'articles sélectionnés pour ce jour.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | Integer PK | Identifiant |
| `date` | String (unique) | Date au format `YYYY-MM-DD` |
| `status` | String | `pending` / `ready` / `partial` / `failed` |
| `item_count` | Integer | Nombre d'articles dans le feed |
| `item_ids` | Text (JSON) | Array JSON des IDs `news_items` ordonnés |
| `created_at` | DateTime UTC | Date de création |
| `updated_at` | DateTime UTC | Dernière modification |

> **Lien ECR-003** : Cette table est au cœur de la solution architecturale. L'agent [[Agents/Chef de presse]] n'aura accès qu'aux `news_items` dont `created_at` correspond à aujourd'hui — rendant les doublons cross-journées structurellement impossibles.

---

### `agent_runs` — 237 lignes

**But** : Journal d'exécution de chaque agent. Permet de diagnostiquer les pannes, mesurer les performances et suivre la collecte dans le temps.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | Integer PK | Identifiant |
| `agent_name` | String | Nom de l'agent (`rss_tech_ai`, `youtube_subs`, etc.) |
| `status` | String | `success` / `partial` / `failed` |
| `items_collected` | Integer | Nombre d'items retournés |
| `duration_seconds` | Float | Durée d'exécution |
| `error_message` | Text | Message d'erreur si échec |
| `created_at` | DateTime UTC | Timestamp de l'exécution |

---

## Interactions utilisateur

### `feedbacks` — 57 lignes

**But** : Capture les réactions de l'utilisateur sur chaque article. Alimente directement le `final_score` des articles via le Scorer.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | Integer PK | Identifiant |
| `news_item_id` | Integer FK → `news_items` | Article concerné |
| `action` | String | `like` / `dislike` / `skip` |
| `comment` | Text | Commentaire optionnel attaché à la réaction |
| `created_at` | DateTime UTC | Timestamp |

---

### `news_comments` — 43 lignes

**But** : Notes personnelles de l'utilisateur sur un article. Différent de `feedbacks` : pas d'impact sur le scoring, usage purement personnel et analytique (source [[Agents/Aftersales]]).

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | Integer PK | Identifiant |
| `news_item_id` | Integer FK → `news_items` | Article commenté |
| `body` | Text | Texte de la note (max 2000 car.) |
| `created_at` | DateTime UTC | Timestamp |

---

### `bug_reports` — 10 lignes

**But** : Rapports de bugs soumis depuis le menu ⋮ de l'interface. Inclut le contexte capturé automatiquement au moment de la soumission.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | Integer PK | Identifiant |
| `description` | Text | Description du problème (max 5000 car.) |
| `context` | Text (JSON) | `article_id`, `article_title`, `user_agent`, `timestamp` |
| `created_at` | DateTime UTC | Timestamp de soumission |

---

## Aftersales

> Ces 5 tables sont vides — le seed n'a pas encore été appliqué. Les ECR et MCA sont actuellement gérés uniquement via les fichiers markdown dans `ECR/` et `Bugs/`.

### `ecr` — Engineering Change Records

**But** : Version base de données des ECR (modifications de code requises). Miroir structuré des fichiers `ECR/ECR-XXX.md`.

| Colonne | Type | Description |
|---------|------|-------------|
| `ecr_number` | String (unique) | Ex: `ECR-003` |
| `title` | String | Titre court |
| `status` | String | `a_transmettre` / `en_cours` / `corrige` / `annule` |
| `priority` | String | `haute` / `normale` / `basse` |
| `severity` | String | `critique` / `haute` / `normale` / `basse` |
| `symptom` | Text | Description du symptôme observé |
| `root_cause` | Text | Cause racine identifiée |
| `proposed_fix` | Text | Correction proposée |
| `created_at` / `updated_at` / `closed_at` | DateTime | Cycle de vie |

---

### `mca` — Mises à jour Contexte Agent

**But** : Version base de données des MCA (changements de configuration sans code). Miroir des fichiers `Bugs/MCA-XXX.md`.

| Colonne | Type | Description |
|---------|------|-------------|
| `mca_number` | String (unique) | Ex: `MCA-001` |
| `title` | String | Titre court |
| `status` | String | `a_appliquer` / `applique` / `en_attente` |
| `target_agent` | String | Agent visé par la mise à jour |
| `description` | Text | Ce qui doit changer |
| `justification` | Text | Pourquoi ce changement |
| `blocking_ecr_id` | Integer FK → `ecr` | ECR bloquant si applicable |

---

### `investigations` — Logs Aftersales

**But** : Trace chaque cycle d'investigation mené par [[Agents/Aftersales]]. Une entrée par cycle : hypothèse, plan de données, résultats, décision.

| Colonne | Type | Description |
|---------|------|-------------|
| `trigger_type` | String | `comment` / `bug_report` / `feedback` / `manual` |
| `trigger_id` | Integer | ID de l'élément déclencheur |
| `hypothesis` | Text | Hypothèse formulée |
| `data_plan` | Text | Plan de collecte de données |
| `data_collected` | Text | Données brutes collectées |
| `conclusion` | Text | Résultat de l'analyse |
| `decision` | String | `journalisation` / `mca` / `ecr` / `business` |
| `ecr_id` | FK → `ecr` | ECR créé si décision = ecr |
| `mca_id` | FK → `mca` | MCA créé si décision = mca |

---

### `ecr_status_history` et `mca_status_history` — Audit trails

**But** : Enregistrent chaque changement de statut d'un ECR ou MCA avec la date, l'ancien statut, le nouveau statut et une note. Permet de retracer l'historique complet d'un ticket.

---

## Relations clés

```
news_items ──< feedbacks
news_items ──< news_comments
ecr        ──< ecr_status_history
ecr        ──< investigations
mca        ──< mca_status_history
mca        ──< investigations
mca        >── ecr (blocking_ecr_id)
```

---

## Liens

- [[Architecture/Modèle de données]] — structure des objets Python (RawNewsItem, catégories)
- [[Architecture/Pipeline de traitement]] — flux qui alimente `news_items` et `daily_feeds`
- [[Agents/Aftersales]] — consomme `feedbacks`, `news_comments`, `bug_reports`, `ecr`, `mca`
- [[DB Viewer — SQLite Web]] — outil d'inspection en temps réel

#architecture #base-de-données #sqlite
