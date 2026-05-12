# DB Viewer — SQLite Web

Outil de visualisation et d'édition de la base de données `newsfeed.db` directement dans le navigateur.

## Prérequis

`sqlite-web` doit être installé (une seule fois) :

```bash
pip install sqlite-web --break-system-packages
```

## Lancer le serveur

```bash
sqlite_web /home/vhminiverse/Documents/NewsFeed/data/newsfeed.db --port 8080 --host 0.0.0.0
```

Ouvrir ensuite : **http://localhost:8080**

## Arrêter le serveur

`Ctrl+C` dans le terminal où le serveur tourne.

Si lancé en arrière-plan, trouver et tuer le processus :

```bash
pkill -f sqlite_web
```

## Ce qu'on peut faire

| Action | Comment |
|--------|---------|
| Voir les entrées | Cliquer sur une table dans le panneau gauche |
| Filtrer | Bouton **Filters** en haut de la table |
| Créer une entrée | Bouton **+ New row** |
| Modifier une entrée | Cliquer sur la ligne → **Edit** |
| Changer un statut | Même chose — modifier le champ `status` |
| Supprimer | Sélectionner la ligne → **Delete** |

## Tables Aftersales

| Table | Description |
|-------|-------------|
| `ecr` | Engineering Change Records |
| `mca` | Mises à jour Contexte Agent |
| `investigations` | Cycles d'investigation |
| `ecr_status_history` | Audit trail des statuts ECR |
| `mca_status_history` | Audit trail des statuts MCA |

## Tables NewsFeed

| Table | Description |
|-------|-------------|
| `news_items` | Nouvelles traitées |
| `daily_feeds` | Fils quotidiens assemblés |
| `feedbacks` | Like / dislike / skip par article |
| `news_comments` | Notes personnelles |
| `agent_runs` | Logs d'exécution des agents |
| `bug_reports` | Rapports de bugs |
