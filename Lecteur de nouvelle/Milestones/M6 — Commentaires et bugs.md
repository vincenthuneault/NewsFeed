# M6 — Commentaires sur les nouvelles + rapport de bugs

> Deux features de saisie utilisateur : noter ses pensées sur un article, et signaler un bug directement depuis l'interface.

---

## Vue d'ensemble des features

| Feature | Description |
|---------|-------------|
| **Commentaires** | Écrire une note personnelle sur un article, stockée en DB liée à la nouvelle |
| **Rapport de bugs** | Bouton dans le menu ⋮ pour décrire un problème, avec contexte capturé automatiquement |

---

## Décisions d'architecture

### Pourquoi une nouvelle table `news_comments` et non `Feedback.comment` ?

Le modèle `Feedback` a un champ `comment` (Text, nullable) mais il est couplé à une `action` (`like`/`dislike`/`skip`). Ces actions alimentent le **scoring** du pipeline. Un commentaire personnel est une note de lecture — il ne doit pas influer sur le scoring ni être traité comme un signal de préférence.

Séparation nette : `Feedback` = signal de scoring · `NewsComment` = note personnelle.

---

## Feature 1 — Commentaires sur les nouvelles

### 1.1 Modèle DB — `news_comments`

Ajouter dans `core/models.py` :

```python
class NewsComment(Base):
    __tablename__ = "news_comments"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    news_item_id = Column(Integer, ForeignKey("news_items.id"), nullable=False, index=True)
    body         = Column(Text, nullable=False)
    created_at   = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    news_item = relationship("NewsItem", back_populates="comments")
```

Ajouter la relation inverse sur `NewsItem` :

```python
comments = relationship("NewsComment", back_populates="news_item", cascade="all, delete-orphan")
```

### 1.2 API — `backend/api/comments.py` (nouveau blueprint)

| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/api/news/<id>/comments` | Crée un commentaire |
| `GET`  | `/api/news/<id>/comments` | Retourne les commentaires (ordre chronologique) |

Body POST : `{"body": "mon commentaire"}`  
Validation : `body` non vide, longueur max 2000 caractères.  
Réponse 201 : `{"success": true, "comment_id": 42}`

Enregistrement dans `backend/app.py` :
```python
from backend.api.comments import comments_bp
app.register_blueprint(comments_bp, url_prefix="/api")
```

### 1.3 Frontend — `ui.js`

Dans `_renderMenu()`, après la section feedback (après le lien source) :

```
_menuDivider(menu)
[💬] Commenter
      → affiche un textarea + bouton "Envoyer" inline dans le menu
      → POST /api/news/<id>/comments
      → ferme le menu + toast "💬 Commentaire enregistré"
```

Le textarea est injecté directement dans le menu (pas de modal séparé), cohérent avec le pattern du calendrier inline.

Ajouter dans `api.js` :
```js
export async function postComment(newsId, body) {
  const res = await apiFetch(`/api/news/${newsId}/comments`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
```

---

## Feature 2 — Rapport de bugs

### 2.1 Modèle DB — `bug_reports`

Ajouter dans `core/models.py` :

```python
class BugReport(Base):
    __tablename__ = "bug_reports"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(Text, nullable=False)
    context     = Column(Text, nullable=True)   # JSON : article actif, user_agent, url
    created_at  = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
```

Le champ `context` stocke un JSON capturé automatiquement côté frontend :
```json
{
  "article_id": 12,
  "article_title": "Mon titre",
  "user_agent": "Mozilla/5.0...",
  "timestamp": "2026-04-29T14:32:00"
}
```

### 2.2 API — `backend/api/bugs.py` (nouveau blueprint)

| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/api/bugs` | Soumet un rapport de bug |

Body POST : `{"description": "...", "context": {...}}`  
Validation : `description` non vide, longueur max 5000 caractères.  
Réponse 201 : `{"success": true, "bug_id": 7}`  
Pas de `GET /api/bugs` dans cette version (consultation directement en DB).

Enregistrement dans `backend/app.py` :
```python
from backend.api.bugs import bugs_bp
app.register_blueprint(bugs_bp, url_prefix="/api")
```

### 2.3 Frontend — `ui.js`

Dans `_renderMenu()`, après la section calendrier (avant logout) :

```
_menuDivider(menu)
[🐛] Signaler un bug
      → affiche un textarea + bouton "Envoyer" inline dans le menu
      → capture automatiquement : article actif, user agent, timestamp
      → POST /api/bugs
      → ferme le menu + toast "🐛 Bug signalé, merci !"
```

Ajouter dans `api.js` :
```js
export async function postBugReport(description, context) {
  const res = await apiFetch("/api/bugs", {
    method: "POST",
    body: JSON.stringify({ description, context }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
```

---

## Stockage

| Élément | Détail |
|---------|--------|
| Type de base de données | SQLite 3 |
| Fichier | `/home/vhds/NewsFeed/data/newsfeed.db` |
| Création des tables | Automatique au démarrage via `Base.metadata.create_all()` |
| Table commentaires | `news_comments` |
| Table rapports de bugs | `bug_reports` |

Les tables sont créées automatiquement — aucune migration manuelle nécessaire.  
Voir [[Modèle de données]] pour le schéma complet des colonnes.

---

## Fichiers à créer / modifier

| Fichier | Action | Détail |
|---------|--------|--------|
| `core/models.py` | Modifier | Ajouter `NewsComment`, `BugReport`, relation `NewsItem.comments` |
| `backend/api/comments.py` | Créer | Blueprint `comments_bp` avec `POST` + `GET` |
| `backend/api/bugs.py` | Créer | Blueprint `bugs_bp` avec `POST` |
| `backend/app.py` | Modifier | Enregistrer `comments_bp` et `bugs_bp` |
| `frontend/js/api.js` | Modifier | Ajouter `postComment()` et `postBugReport()` |
| `frontend/js/ui.js` | Modifier | Ajouter sections textarea dans `_renderMenu()` |
| `frontend/css/app.css` | Modifier | Styles pour le textarea inline dans le menu |

---

## Tâches

- [ ] 6.1 — `NewsComment` dans `core/models.py` + relation `NewsItem.comments`
- [ ] 6.2 — `BugReport` dans `core/models.py`
- [ ] 6.3 — `backend/api/comments.py` — blueprint POST + GET
- [ ] 6.4 — `backend/api/bugs.py` — blueprint POST
- [ ] 6.5 — `backend/app.py` — enregistrement des deux blueprints
- [ ] 6.6 — `api.js` — `postComment()` et `postBugReport()`
- [ ] 6.7 — `ui.js` — textarea inline commentaire dans le menu ⋮
- [ ] 6.8 — `ui.js` — textarea inline rapport de bug dans le menu ⋮
- [ ] 6.9 — `app.css` — styles textarea menu

---

## Tests manuels (gate de validation)

| ID | Scénario | Résultat attendu |
|----|----------|-----------------|
| T-COM-01 | Ouvrir menu ⋮ → cliquer 💬 | Textarea apparaît dans le menu |
| T-COM-02 | Écrire commentaire + Envoyer | Toast "Commentaire enregistré", entrée en DB |
| T-COM-03 | Envoyer commentaire vide | Pas de requête envoyée, bouton désactivé |
| T-COM-04 | Commentaire sur article 1, vérifier `GET /api/news/1/comments` | Retourne le commentaire |
| T-BUG-01 | Ouvrir menu ⋮ → cliquer 🐛 | Textarea apparaît dans le menu |
| T-BUG-02 | Écrire description + Envoyer | Toast "Bug signalé", entrée en DB avec contexte |
| T-BUG-03 | Vérifier contexte en DB | `context` contient article actif + user agent |
| T-BUG-04 | Envoyer rapport vide | Pas de requête envoyée, bouton désactivé |
| T-REG-01 | Feedback 👍👎⏭ existant | Aucune régression, fonctionne toujours |
| T-REG-02 | Menu calendrier | Aucune régression |

---

## Gate 6 — Critères

- [ ] Tests T-COM-01 à T-COM-04 passent
- [ ] Tests T-BUG-01 à T-BUG-04 passent
- [ ] Aucune régression (T-REG-01, T-REG-02)
- [ ] Les deux tables créées automatiquement par `init_db()`
- [ ] Textarea respecte `overflow: hidden` sur body (pas de scrollbar parasite)

---

## Liens

- Précédent : [[M5 — Production]]
- Retour : [[Vue d'ensemble]]
- Composants touchés : [[Frontend mobile]], [[API REST]], [[Modèle de données]]

#milestone #m6 #commentaires #bugs
