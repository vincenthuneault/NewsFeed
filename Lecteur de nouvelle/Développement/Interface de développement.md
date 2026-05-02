# Interface de développement

> Console interne pour inspecter les données de l'application en temps réel. Point d'entrée centralisé pour tous les outils d'analyse et de débogage.

**URL d'accès :** `/dev` (même serveur que l'application principale)
**Authentification :** session partagée avec l'application — connexion requise si `APP_PASSWORD` est défini

---

## Fonction

L'interface de développement permet d'explorer directement le contenu des bases de données sans passer par un client SQLite externe. Elle est conçue pour évoluer : chaque nouvelle source de données peut être ajoutée comme un onglet supplémentaire sans modifier l'architecture existante.

### Cas d'usage typiques

- Lire les commentaires laissés sur les articles pour analyser les retours utilisateur
- Consulter les rapports de bug soumis depuis l'app mobile avec leur contexte (article actif, user-agent, horodatage)
- Surveiller les exécutions des agents de collecte (statut, durée, erreurs)
- Parcourir la base d'articles avec filtres par catégorie ou titre

---

## Architecture

### Backend — `/backend/api/dev.py`

Blueprint Flask `dev_bp` enregistré avec le préfixe `/api`. Tous les endpoints sont protégés par le décorateur `@require_auth`.

| Endpoint | Description |
|----------|-------------|
| `GET /api/dev/stats` | Compteurs globaux et activité de la semaine |
| `GET /api/dev/comments` | Liste paginée des commentaires avec article associé |
| `GET /api/dev/bugs` | Liste paginée des rapports de bug avec contexte JSON |
| `GET /api/dev/agent-runs` | Historique des exécutions d'agents |
| `GET /api/dev/news` | Parcourir les articles avec filtres |

**Paramètres communs :** `page`, `per_page` (max 100), `q` (recherche texte), `category` (filtre articles), `agent` (filtre runs).

### Frontend

| Fichier | Rôle |
|---------|------|
| `frontend/dev.html` | Page principale — structure HTML des onglets et du modal |
| `frontend/css/dev.css` | Styles — thème sombre cohérent avec l'application principale |
| `frontend/js/dev.js` | Logique — appels API, rendu des tableaux, pagination, modal |

La route `/dev` dans `app.py` sert `dev.html` avec les en-têtes `no-cache`.

### Flux d'authentification

Le JS appelle directement `/api/dev/stats` au chargement. Si la réponse est `401`, la page redirige vers `/` (écran de connexion). En mode sans mot de passe (`APP_PASSWORD` non défini), tous les appels passent sans session.

---

## Onglets disponibles

### Tableau de bord
Cinq cartes de statistiques chargées depuis `/api/dev/stats` :
- Total articles en base
- Commentaires (total + ajouts cette semaine)
- Rapports de bug (total + cette semaine)
- Feedbacks (total, ventilés likes / dislikes / skips)
- Taux de succès des agents (% + horodatage du dernier run)

### Commentaires
Tableau paginé (20 par page) des `news_comments` avec l'article associé. Champ de recherche avec debounce 300 ms filtrant sur le corps du commentaire. Bouton « Voir » pour les commentaires longs — ouvre un modal plein texte.

### Rapports de bug
Tableau paginé des `bug_reports`. Chaque ligne expose : description tronquée, article actif au moment du signalement, date. Bouton « Voir » pour le texte complet, bouton « JSON » pour le contexte brut (article, user-agent, timestamp).

### Agents
Tableau paginé (50 par page) des `agent_runs`, avec filtre par agent. Affiche : statut coloré (success / partial / failed), nombre d'items collectés, durée, message d'erreur tronqué.

### Articles
Tableau paginé des `news_items` avec double filtre (titre + catégorie). Chaque ligne indique : score final, nombre de commentaires et feedbacks associés. Le titre est un lien cliquable vers la source originale.

---

## Extensibilité — ajouter une nouvelle source de données

1. **Backend** : ajouter un endpoint dans `backend/api/dev.py`
   ```python
   @dev_bp.route("/dev/ma-table")
   @require_auth
   def dev_ma_table():
       ...
   ```

2. **HTML** : ajouter un bouton dans `.tab-nav` et une section `.tab-panel`
   ```html
   <button class="tab-btn" data-tab="ma-table" role="tab">Ma table</button>
   ```

3. **JS** : ajouter un cas dans `loadTab()` et écrire la fonction de chargement correspondante

L'architecture en onglets paresseux (lazy load) garantit qu'une nouvelle source ne charge ses données que lorsque l'onglet est ouvert pour la première fois.

---

## Décisions de conception

- **Pas de framework JS** — cohérence avec le reste du frontend vanilla
- **Session partagée** — pas de second mot de passe ; l'accès dev implique l'accès app
- **Lecture seule** — aucun endpoint d'écriture dans le blueprint `dev_bp`
- **Pagination serveur** — évite de charger toute la table en mémoire côté navigateur
- **Modal JSON natif** — affichage `pre` avec `JSON.stringify(…, null, 2)` sans dépendance externe
