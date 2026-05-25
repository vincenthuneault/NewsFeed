# PRD-001 — Requis produit — vhds-NewsFeed

> Document de référence produit. Synthèse exhaustive des requis fonctionnels et non fonctionnels
> ayant guidé la conception et le développement du système de fil de nouvelles personnalisé.
>
> **Auteur :** Architecte Produit · Claude Sonnet 4.6
> **Date :** 2026-05-18
> **Sources :** Milestones M0–M7 · Architecture · Agents · Analyse Aftersales · ECRs · MCAs

---

## Table des matières

1. [Vision produit](#1-vision-produit)
2. [Utilisateur cible](#2-utilisateur-cible)
3. [Requis de collecte — Journalistes](#3-requis-de-collecte--journalistes)
4. [Requis éditoriaux — Chef de nouvelles](#4-requis-éditoriaux--chef-de-nouvelles)
5. [Requis du pipeline de traitement](#5-requis-du-pipeline-de-traitement)
6. [Requis de l'API REST](#6-requis-de-lapi-rest)
7. [Requis du frontend mobile](#7-requis-du-frontend-mobile)
8. [Requis de feedback utilisateur](#8-requis-de-feedback-utilisateur)
9. [Requis d'infrastructure et de déploiement](#9-requis-dinfrastructure-et-de-déploiement)
10. [Requis non fonctionnels](#10-requis-non-fonctionnels)
11. [Requis de qualité éditoriale](#11-requis-de-qualité-éditoriale)
12. [Contraintes budgétaires](#12-contraintes-budgétaires)

---

## 1. Vision produit

### 1.1 Objectif
Produire quotidiennement un fil de nouvelles personnalisé, généré par des agents IA autonomes, présenté dans une interface mobile audio-first, accessible via VPN.

### 1.2 Proposition de valeur
L'utilisateur consomme en format audio et scroll un fil d'information dense, pertinent et sans bruit, sans avoir à naviguer entre sources hétérogènes. Le système apprend de ses préférences.

### 1.3 Principe fondateur
> "Rien n'avance tant que ce qui est derrière ne fonctionne pas encore."

Le système est conçu pour la fiabilité quotidienne avant l'étendue des fonctionnalités.

---

## 2. Utilisateur cible

### 2.1 Profil

| Dimension    | Valeur                                                       |
| ------------ | ------------------------------------------------------------ |
| Âge          | ~35 ans                                                      |
| Langue       | Francophone (fr-CA)                                          |
| Localisation | Contrecoeur / Sorel-Tracy / Grand Montréal                   |
| Usage        | Veille stratégique quotidienne — comprendre avant les autres |
| Comportement | Consomme en scroll audio, partage avec son entourage         |

### 2.2 Intérêts déclarés et confirmés

| Catégorie                                                        | Niveau |
| ---------------------------------------------------------------- | ------ |
| Politique américaine (procès, figures, conflits institutionnels) | Fort   |
| Technologie et intelligence artificielle                         | Fort   |
| Exploration spatiale (SpaceX, NASA, missions)                    | Fort   |
| Politique canadienne et québécoise                               | Fort   |
| Véhicules électriques (voitures, SUV, camions)                   | Fort   |
| Culture pop nord-américaine (films, trailers)                    | Modéré |
| Musique électronique (EDM, house, techno, trance)                | Modéré |
| Actualité locale (Contrecoeur, Sorel, Grand Montréal)            | Modéré |

### 2.3 Exclusions explicites

Sport professionnel · Hockey · Jeux vidéo et esports · Contenu jeunesse · Bollywood · K-pop · Tendances hors Amérique du Nord · Vélos électriques · Trottinettes · Énergie solaire résidentielle · Éolien · Politique municipale hors Grand Montréal · Articles sans substance · Teasers conçus pour faire cliquer

---

## 3. Requis de collecte — Journalistes

### 3.1 Structure générale

| Requis    | Valeur                                                                   |
| --------- | ------------------------------------------------------------------------ |
| R-COL-001 | Chaque journaliste couvre un seul sujet assigné                          |
| R-COL-002 | Quota quotidien maximum : 5 articles par journaliste                     |
| R-COL-003 | Fraîcheur : articles publiés le jour même uniquement                     |
| R-COL-004 | Déduplication par URL contre l'historique complet du journaliste         |
| R-COL-005 | Un article hors-scope ne doit jamais être soumis pour atteindre le quota |

### 3.2 Critères de sélection d'un article

| Critère   | Description                                                           |
| --------- | --------------------------------------------------------------------- |
| R-COL-010 | Publié dans les 24 dernière heures                                    |
| R-COL-011 | URL inédite dans l'historique de soumissions du journaliste           |
| R-COL-012 | Informationnel — l'essentiel est compréhensible sans ouvrir la source |
| R-COL-013 | Factuel — journalisme neutre, faits, chiffres, contexte concret       |
| R-COL-014 | Dans le périmètre exact du sujet assigné                              |

### 3.3 Articles jamais soumis

- Derrière paywall ou contenu < 300 caractères extractibles
- Live streams ou contenus éphémères sans valeur archivable
- Vidéos YouTube avec `🔴LIVE`, `#LIVE`, `LIVE |` dans le titre
- Articles appartenant à une autre catégorie

### 3.4 Sujets et périmètres des journalistes

#### `tech_ai` — Technologie & IA
- Plateformes IA majeures, annonces produits tech à fort impact, recherche IA, réglementation, impacts sociétaux
- Exclus : jeux vidéo, gadgets décoratifs, esports
- Sources à éviter : The Verge (paywall systématique) → préférer Ars Technica, MIT Technology Review, Wired

#### `evenements_mtl` — Événements Montréal
- Spectacles, concerts, festivals, théâtre, humour, DJ, soirées, expositions, marchés sur l'île de Montréal et rive sud immédiate
- Exclus : politique (municipale, provinciale, fédérale), infrastructure, travaux, événements hors zone

#### `vehicules_ev` — Véhicules électriques & autonomes
- Voitures, camions, SUV, fourgonnettes électriques ou hybrides; conduite autonome; recharge; réglementation VÉ
- Exclus : vélos électriques, trottinettes, panneaux solaires, éoliennes, énergie sans lien avec un véhicule

#### `spatial` — Espace & exploration
- Missions lunaires/martiennes/orbitales, SpaceX, NASA, ESA, satellites, découvertes astronomiques
- Note : vérification stricte anti-doublon (SpaceNews republie fréquemment)

#### `politique_ca` — Politique canadienne
- Politique fédérale et québécoise, économie canadienne, relations internationales du Canada
- Exclus : politique municipale (Ottawa, Toronto…), provinces autres que Québec, politique américaine pure

#### `youtube_trending` — Tendances YouTube
- Tendances nord-américaines, trailers films, contenu viral partageable, musique électronique, abonnements de l'utilisateur
- Exclus : gaming, esports, Bollywood, K-pop, live streams, rap/hip-hop/R&B/reggaeton, contenu jeunesse

#### `local_contrecoeur` — Local Contrecoeur & région
- Contrecoeur, Sorel-Tracy, Grand Montréal (île + rive sud immédiate)
- Exclus : Rimouski, Québec (ville), Ottawa, Toronto, autres provinces

### 3.5 Feedback reçu par le journaliste

| Signal | Signification |
|--------|---------------|
| ✅ Accepté | Article intégré au feed du jour |
| ❌ Rejeté | Flag qualité — l'article ne passe pas la gate éditoriale |
| (silence) | Feed complet — pas un signal négatif sur la qualité |

---

## 4. Requis éditoriaux — Chef de nouvelles

### 4.1 Rôle et périmètre

| Requis    | Valeur                                                                           |
| --------- | -------------------------------------------------------------------------------- |
| R-EDI-001 | Seul agent à décider de l'inclusion et de l'ordre du feed — aucun scorer externe |
| R-EDI-002 | Travaille uniquement avec les articles soumis le jour même                       |
| R-EDI-003 | Capacité maximale du feed : 30 articles                                          |
| R-EDI-004 | Aucune catégorie ne dépasse 40 % du feed                                         |
| R-EDI-005 | Tout article rejeté doit avoir une note dans `editorial_note`                    |

### 4.2 Gate de qualité informationnelle

Un article est **rejeté** si, après lecture du résumé, l'utilisateur ne peut pas comprendre ce que l'article voulait communiquer.

| Motif de rejet | Description                                            |
| -------------- | ------------------------------------------------------ |
| R-EDI-010      | Résumé vague ou sans substance (aucun fait concret)    |
| R-EDI-011      | Information tronquée — l'essentiel manque              |
| R-EDI-012      | Teaser conçu pour faire cliquer, pas pour informer     |
| R-EDI-013      | Contradictions internes non résolues dans le résumé    |
| R-EDI-014      | Article hors sujet par rapport à la catégorie déclarée |

La gate ne filtre **pas** : longueur du contenu brut (gate technique), domaines blacklistés (gate technique), pertinence pour l'utilisateur (influence l'ordre, pas le rejet).

### 4.3 Ordonnancement du feed

Critères appliqués dans l'ordre de priorité décroissante :

| Priorité | Critère                                                        |
| -------- | -------------------------------------------------------------- |
| 1        | Importance du jour — nouvelles chaudes en tête                 |
| 2        | Pertinence pour l'utilisateur — selon profil                   |
| 3        | Arc narratif — deux articles sur le même événement consécutifs |
| 4        | Diversité de format — alterner texte, vidéo, audio             |
| 5        | Variété de ton — ne pas finir sur des nouvelles pesantes       |

Règles fixes :
- Les deux premiers et deux derniers articles sont choisis avec soin
- Deux articles sur le même événement sont toujours consécutifs

### 4.4 Profil utilisateur vivant

Le Chef de nouvelles maintient un profil utilisateur mis à jour à chaque cycle à partir des `news_comments`. Ce profil est intégré dans son prompt et constitue sa boussole éditoriale.

---

## 5. Requis du pipeline de traitement

### 5.1 Orchestration

| Requis     | Valeur                                                        |
| ---------- | ------------------------------------------------------------- |
| R-PIPE-001 | Tous les agents s'exécutent en parallèle (ThreadPoolExecutor) |
| R-PIPE-002 | Timeout par agent : 5 minutes                                 |
| R-PIPE-003 | Si un agent échoue, les autres continuent                     |
| R-PIPE-004 | Un `AgentReport` est produit pour chaque agent                |

### 5.2 Gate technique (pré-éditorial)

| Requis     | Valeur                                                                           |
| ---------- | -------------------------------------------------------------------------------- |
| R-PIPE-010 | Longueur minimale du `raw_content` pour passer la sélection                      |
| R-PIPE-011 | Domaines blacklistés exclus avant soumission au Chef de nouvelles                |
| R-PIPE-012 | Vidéos YouTube live filtrées par pattern de titre (`🔴LIVE`, `#LIVE`, `LIVE \|`) |

### 5.3 Déduplication (responsabilité des Journalistes — pas du pipeline)

La déduplication est distribuée aux agents Journaliste. Il n'existe pas de composant `Deduplicator` dans le pipeline.

| Requis     | Valeur                                                                                     |
| ---------- | ------------------------------------------------------------------------------------------ |
| R-PIPE-020 | Chaque Journaliste vérifie l'URL contre l'historique complet de ses propres soumissions    |
| R-PIPE-021 | Filtre 24h : un article soumis hier ne peut pas être re-soumis aujourd'hui                 |
| R-PIPE-022 | La déduplication cross-journalistes (même article couvert par deux sources) est hors scope |

### 5.4 Résumé IA

| Requis     | Valeur                                            |
| ---------- | ------------------------------------------------- |
| R-PIPE-030 | Modèle : Claude Sonnet (dernière version stable)  |
| R-PIPE-031 | Input max : 2000 tokens · Output max : 300 tokens |
| R-PIPE-032 | Température : 0.3 (factuel)                       |
| R-PIPE-033 | Toujours en français, maximum 4 phrases           |
| R-PIPE-034 | Coût cible : < $0.01 par article                  |

### 5.5 Images

| Requis     | Valeur                                                                  |
| ---------- | ----------------------------------------------------------------------- |
| R-PIPE-040 | Priorité : `og:image` > thumbnail YouTube > première image de l'article |
| R-PIPE-041 | Redimensionnement : 720px max de large                                  |
| R-PIPE-042 | Format : JPEG qualité 85                                                |
| R-PIPE-043 | Fallback : image par défaut par catégorie                               |

### 5.6 TTS

| Requis     | Valeur                                                                   |
| ---------- | ------------------------------------------------------------------------ |
| R-PIPE-050 | Moteur : Google Cloud TTS — Gemini 2.5 Pro                               |
| R-PIPE-051 | Voix : tous les journaliste on leur voix (`fr-CA`), style journalistique |
| R-PIPE-052 | Format : MP3, max 90 secondes (~700 caractères)                          |


### 5.7 Assemblage du feed

| Requis     | Valeur                                               |
| ---------- | ---------------------------------------------------- |
| R-PIPE-060 | Crée l'entrée `daily_feed` avec liste ordonnée d'IDs |
| R-PIPE-061 | Statut possible : "ready", "partial", "failed"       |

---

## 6. Requis de l'API REST

### 6.1 Stack

| Composant     | Choix                         |
| ------------- | ----------------------------- |
| Framework     | Flask 3.1                     |
| WSGI          | Gunicorn (4 workers)          |
| Reverse proxy | Nginx (HTTPS via mkcert)      |
| Auth          | Cookie de session signé Flask |
| Format        | JSON, dates ISO 8601          |

### 6.2 Endpoints requis

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/api/feed/today` | Fil du jour |
| `GET` | `/api/feed/{date}` | Fil d'une date passée |
| `GET` | `/api/feed/dates` | Liste des dates disponibles |
| `GET` | `/api/news/{id}` | Détail d'un article |
| `POST` | `/api/news/{id}/feedback` | Like / dislike / skip |
| `GET` | `/api/settings` | Préférences utilisateur |
| `PUT` | `/api/settings` | Modifier les préférences |
| `POST` | `/api/auth/login` | Authentification |
| `POST` | `/api/auth/logout` | Déconnexion |
| `GET` | `/api/health` | Rapport de santé complet |
| `GET` | `/api/version` | Version de l'application |
| `POST` | `/api/news/{id}/comments` | Créer un commentaire personnel |
| `GET` | `/api/news/{id}/comments` | Lire les commentaires |
| `POST` | `/api/bugs` | Soumettre un rapport de bug |
| `POST` | `/api/speech/transcribe` | Audio → texte (Google STT V2, fr-CA) |

### 6.3 Convention d'erreur

```json
{
  "error": true,
  "message": "Description lisible",
  "code": "NOT_FOUND"
}
```

Codes HTTP : 200, 201, 400, 401, 404, 500.

### 6.4 Sécurité

| Requis | Valeur |
|--------|--------|
| R-API-010 | Toutes les routes (sauf login) protégées par cookie de session |
| R-API-011 | Cookie signé, persistant 7 jours |
| R-API-012 | Accès uniquement via VPN — SSL via mkcert (usage interne) |

---

## 7. Requis du frontend mobile

### 7.1 Choix techniques

| Aspect | Choix |
|--------|-------|
| JS | Vanilla ES2022+ modules — pas de build, pas de npm |
| CSS | Vanilla + custom properties — thème sombre par défaut |
| Layout | CSS scroll-snap natif — 1 carte par écran |
| PWA | manifest.json + service worker — expérience app-like Android |

### 7.2 Carte de nouvelle

| Requis   | Valeur                                                          |
| -------- | --------------------------------------------------------------- |
| R-FE-001 | Chaque carte occupe un écran complet                            |
| R-FE-002 | Image de couverture (ou vidéo inline pour les shorts)           |
| R-FE-003 | Titre + résumé en français (3-4 phrases)                        |
| R-FE-004 | Bouton TTS play/pause                                           |
| R-FE-005 | L'audio s'arrête automatiquement au scroll vers une autre carte |

### 7.3 Menu ⋮

| Requis   | Valeur                                                                            |
| -------- | --------------------------------------------------------------------------------- |
| R-FE-010 | Menu fixe, coin supérieur droit, accessible depuis toute carte                    |
| R-FE-011 | Feedback : 👍 J'aime / 👎 Je n'aime pas / ⏭ Ignorer                               |
| R-FE-012 | 💬 Commenter — note personnelle via texte ou dictée vocale                        |
| R-FE-013 | 🔗 Voir la source                                                                 |
| R-FE-014 | 📅 Historique — calendrier inline pour naviguer dans les dates passées            |
| R-FE-015 | 🐛 Signaler un bug — texte ou dictée vocale avec contexte capturé automatiquement |
| R-FE-016 | ⎋ Déconnexion                                                                     |
| R-FE-017 | Numéro de version affiché en bas du menu                                          |

### 7.4 Navigation

| Requis   | Valeur                                                       |
| -------- | ------------------------------------------------------------ |
| R-FE-020 | Scroll vertical avec snap — 1 carte = 1 écran                |
| R-FE-021 | Compteur de position (ex: "12/30") + barre de progression    |
| R-FE-022 | Calendrier inline dans le menu pour accéder aux feeds passés |

### 7.5 Authentification

| Requis | Valeur |
|--------|--------|
| R-FE-030 | Page de login (mot de passe unique) |
| R-FE-031 | Cookie de session signé, persistant 7 jours |
| R-FE-032 | Toutes les routes protégées — 401 redirige vers login |

### 7.6 Saisie vocale (M7)

| Requis | Valeur |
|--------|--------|
| R-FE-040 | Bouton 🎤 dans sections Commenter et Signaler un bug |
| R-FE-041 | Push-to-talk toggle : tap pour démarrer, re-tap pour arrêter |
| R-FE-042 | Status "🔴 Enregistrement…" + canvas barres rouges pendant la prise |
| R-FE-043 | Status "⏳ Transcription…" pendant l'appel Google STT V2 |
| R-FE-044 | Texte transcrit s'appende au textarea |
| R-FE-045 | Moteur : Google Cloud STT V2, modèle `latest_long`, `fr-CA` |
| R-FE-046 | Le blob audio est envoyé en entier après arrêt (pas de streaming) |

### 7.7 Cache et mises à jour

| Type de fichier | Stratégie service worker |
|-----------------|--------------------------|
| JS, HTML | Network only (toujours frais) |
| CSS | Network First + fallback cache |
| Images, audio (`/static/`) | Cache First (stable) |

---

## 8. Requis de feedback utilisateur

### 8.1 Feedback comportemental (scoring)

| Requis | Valeur |
|--------|--------|
| R-FB-001 | Actions : `like`, `dislike`, `skip` |
| R-FB-002 | Un like booste le score de la catégorie associée |
| R-FB-003 | Un dislike pénalise le score de la catégorie |
| R-FB-004 | Le poids du feedback décroît dans le temps |
| R-FB-005 | Les items ne sont jamais perdus — juste re-rankés |

### 8.2 Commentaires personnels (note de lecture)

| Requis | Valeur |
|--------|--------|
| R-FB-010 | Stockés dans `news_comments` — séparés du feedback de scoring |
| R-FB-011 | Un commentaire n'influence pas le scorer |
| R-FB-012 | Longueur max : 2000 caractères |
| R-FB-013 | Le commentaire vide ne peut pas être soumis |
| R-FB-014 | Les commentaires sont la source principale du profil utilisateur du Chef de nouvelles |

### 8.3 Rapports de bugs

| Requis | Valeur |
|--------|--------|
| R-FB-020 | Stockés dans `bug_reports` |
| R-FB-021 | Le contexte est capturé automatiquement (article actif, user agent, timestamp) |
| R-FB-022 | Longueur max description : 5000 caractères |
| R-FB-023 | Le rapport vide ne peut pas être soumis |

---

## 9. Requis d'infrastructure et de déploiement

### 9.1 Serveur

| Composant | Choix |
|-----------|-------|
| OS | Ubuntu 24.04 LTS |
| Reverse proxy | Nginx |
| WSGI | Gunicorn (4 workers, timeout 120s) |
| Process manager | systemd |

### 9.2 Automatisation

| Requis | Valeur |
|--------|--------|
| R-INF-001 | Pipeline quotidien déclenché par systemd timer à 6h00 |
| R-INF-002 | Timer persistant — rattrape si le serveur était éteint |
| R-INF-003 | Flask API redémarre automatiquement en cas de crash |
| R-INF-004 | Le serveur doit redémarrer proprement après reboot |

### 9.3 Monitoring

| Requis | Valeur |
|--------|--------|
| R-INF-010 | `GET /api/health` retourne statut global + détails du dernier run |
| R-INF-011 | Monitoring quotidien vérifie : feed généré, agents, API, espace disque, coûts |
| R-INF-012 | Alerte par email si le feed n'a pas été généré |

### 9.4 Logs

| Aspect | Choix |
|--------|-------|
| Format | JSON structuré (1 ligne/entrée) |
| Rotation | logrotate — 10 MB max par fichier, 7 fichiers conservés |
| Sortie | Fichier + stdout |

---

## 10. Requis non fonctionnels

### 10.1 Performance

| Requis | Seuil |
|--------|-------|
| R-NFN-001 | Pipeline complet (30 articles) | < 10 min |
| R-NFN-002 | Résumé par article | < 5s |
| R-NFN-003 | TTS par article | < 10s |
| R-NFN-004 | Collecte YouTube | < 30s |
| R-NFN-005 | First load frontend | < 2s |
| R-NFN-006 | Pipeline total toutes sources | < 5 min (orchestration parallèle) |

### 10.2 Fiabilité

| Requis | Valeur |
|--------|--------|
| R-NFN-010 | 7 jours consécutifs avec feed généré automatiquement sans intervention |
| R-NFN-011 | Max 1 warning non-bloquant par semaine acceptable |
| R-NFN-012 | Agents réussis en mode nominal : 100% (dégradé acceptable : n-1/n) |

### 10.3 Qualité du contenu

| Requis | Valeur |
|--------|--------|
| R-NFN-020 | Taux de doublons dans un feed : < 30% |
| R-NFN-021 | Aucune catégorie > 40% du feed |
| R-NFN-022 | Résumés toujours en français |
| R-NFN-023 | Aucun article présenté deux jours consécutifs (fenêtre 7 jours) |
| R-NFN-024 | Audio < 1 MB par article |

### 10.4 Stack technologique

| Couche | Choix obligatoire |
|--------|------------------|
| Langage | Python 3.11 + venv |
| Config | YAML + .env |
| DB | SQLite + SQLAlchemy 2.0 |
| LLM | Claude Sonnet (SDK `anthropic`) |
| TTS | Google Cloud TTS Gemini 2.5 Pro |
| STT | Google Cloud Speech-to-Text V2 |
| YouTube | `google-api-python-client` + OAuth 2.0 |
| RSS | `feedparser` |
| Scraping | `beautifulsoup4` + `requests` + `lxml` |
| Déduplication floue | `rapidfuzz` (seuil 80%) |
| Tests | pytest + pytest-asyncio + pytest-cov |

### 10.5 Conventions de code

| Convention | Règle |
|------------|-------|
| Style | PEP 8 strict |
| Type hints | Obligatoires sur fonctions publiques |
| Logs | JSON structuré uniquement — pas de `print()` |
| Taille fichier | ~300 lignes max |
| VCS | Commits en français : `[Mx] Ajoute/Corrige/Refactorise…` |

---

## 11. Requis de qualité éditoriale

Ces requis émergent de l'Analyse Aftersales (mai 2026) et des ECRs actifs.

### 11.1 Gate qualité pré-éditoriale (ECR-004)

| Requis | Valeur |
|--------|--------|
| R-QUAL-001 | `raw_content` < 300 caractères → article exclu avant soumission |
| R-QUAL-002 | Sources blacklistées (ex : The Verge) exclues automatiquement |
| R-QUAL-003 | Titres YouTube correspondant aux patterns live exclus automatiquement |

### 11.2 Suffisance informationnelle (Chef de nouvelles)

| Requis | Valeur |
|--------|--------|
| R-QUAL-010 | Question centrale : "L'utilisateur comprend-il l'essentiel sans ouvrir la source ?" |
| R-QUAL-011 | Tout rejet documenté dans `editorial_note` |
| R-QUAL-012 | Un article non-publié (capacité atteinte) n'est pas un rejet |

### 11.3 Traçabilité éditoriale

| Requis | Valeur |
|--------|--------|
| R-QUAL-020 | Chaque article a trois états possibles : Publié / Non-publié / Rejeté |
| R-QUAL-021 | L'état de rejet seul déclenche un feedback au journaliste |
| R-QUAL-022 | L'état non-publié n'envoie aucun signal négatif |

---

## 12. Contraintes budgétaires

| Poste | Cible |
|-------|-------|
| Claude API (30 résumés/jour) | < $0.12/jour · < $3.60/mois |
| Google TTS | < $2/mois (estimation) |
| Google STT V2 | ~$0.016/min — usage limité |
| YouTube API | Gratuit (quota 10k requêtes/jour) |
| Hébergement | Serveur existant — $0 marginal |
| **Total mensuel** | **< $10** |

---

## Annexe — Milestones de livraison

| Milestone | Objectif | Statut |
|-----------|----------|--------|
| M0 — Setup | APIs, DB, structure, config | ✅ Terminé |
| M1 — Vertical slice | 1 agent end-to-end | ✅ Terminé |
| M2 — Multi-agents | ~7 agents + orchestrateur + scoring | ✅ Terminé |
| M3 — Feedback | Agents locaux + système de feedback | ✅ Terminé |
| M4 — Frontend complet | UI mobile + auth + PWA | ✅ Terminé |
| M5 — Production | Automatisation + monitoring 7 jours | ✅ Terminé |
| M6 — Commentaires et bugs | Notes personnelles + rapports de bugs | ✅ Terminé |
| M7 — Feedback vocal | Dictée vocale fr-CA push-to-talk (Google STT V2) | ✅ Terminé |
| Phase 8 — Cycle en V | ECRs actifs + processus qualité | 🔄 En cours |

---

## Annexe — ECRs et MCAs issus de l'analyse terrain

| ID | Titre | Type | Priorité |
|----|-------|------|----------|
| ECR-001 | Déduplication étendue 7 jours | Bug systémique | Haute |
| ECR-002 | Gate qualité contenu + blacklist sources + filtre live | Qualité | Haute |
| ECR-003 | Resserrer catégories `vehicules_ev` et `evenements_mtl` | Éditorial | Normale |
| ECR-004 | Bug stabilité lecteur audio | Bug UX | Normale |
| ECR-005 | Bouton calendrier dupliqué au re-login | Bug UI | Normale |
| ECR-006 | App non fonctionnelle sur navigateur desktop | Bug compatibilité | Normale |
| ECR-007 | Afficher "Pourquoi ce contenu" | Feature UX | Faible |
| MCA-001 | Géographie locale : restreindre à Grand Montréal / rive sud | Prompt | Appliqué |
| MCA-002 | `vehicules_ev` : exclure vélos, trottinettes, solaire | Prompt | Appliqué |
| MCA-003 | `musique_electro` : exclure rap/hip-hop/R&B/Bollywood | Prompt | Appliqué |
| MCA-004 | `viral_trending` : filtrer pour contenu nord-américain | Prompt | Appliqué |
| MCA-005 | Scorer à 0 : sport, jeux vidéo, contenu jeunesse | Scoring | Appliqué |

---

*Document vivant — à mettre à jour à chaque cycle Aftersales et à chaque approbation d'ECR.*
