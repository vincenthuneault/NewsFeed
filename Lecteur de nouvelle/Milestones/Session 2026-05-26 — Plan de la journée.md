# Session 2026-05-26 — Plan de la journée

> **Date** : 2026-05-26  
> **Statut** : Complété  
> **Objectif** : Expansion des sources de collecte — couverture complète de toutes les catégories de journalistes, intégration de l'actualité locale Contrecoeur, et mise en place d'un agent d'événements Montréal via Ticketmaster.

---

## Ce que nous avons fait

### 1. Expansion des sources — Véhicules électriques & autonomes

**Avant** : 5 sources RSS  
**Après** : 15 RSS + 1 sitemap

Sources ajoutées :
- InsideEVs, CleanTechnica, Green Car Reports, The Autopian
- Truck News, Transport Topics, FreightWaves (camionnage électrique)
- Aurora Innovation, Torc Robotics (autonomie poids lourd)
- SemiAnalysis, ServeTheHome (hardware embarqué)
- NVIDIA Blog, NVIDIA Developer Blog (DRIVE platform)
- arXiv Robotics (recherche conduite autonome)
- Waabi (sitemap — startup québécoise, camion autonome IA)

**Corrections** :
- Ars Technica Space : URL corrigée (`feeds.arstechnica.com` → `arstechnica.com/science/space/feed/`)
- Aurora : pas de sitemap nécessaire — RSS valide trouvé à `/rss.xml`

**Documentation** : [[Agents/Journaliste-VehiculeEV]] mise à jour (tableau RSS + sitemap + sources sans RSS)

---

### 2. Expansion des sources — Espace & Exploration spatiale

**Avant** : sources de base  
**Après** : 17 RSS

Sources ajoutées :
- SpaceNews, NASA (Image of the Day, Breaking News, Earth Observatory, Science)
- ESA Space Science, Space.com, NASASpaceflight
- Ars Technica Space, Universe Today, Sky & Telescope
- Astronomy Magazine, Live Science Space, ScienceDaily Space
- Nature Astronomy, arXiv Astrophysics
- In-The-Sky Montréal (événements visibles depuis lat 45.41°N)

**Note** : fenêtre de fraîcheur à 48h (news spatiale moins dense que tech).

**Documentation** : [[Agents/Journaliste-Spatial]] mise à jour (tableau RSS + sources sans RSS)

---

### 3. Agent local Contrecoeur — Intégration pipeline

**Contexte** : besoin de couvrir l'actualité de Contrecoeur et des alertes locales (météo, pannes, eau potable).

**Architecture retenue** : intégration dans `agents/local_contrecoeur.py` (pipeline principal), pas de système indépendant.

**Deux chemins de collecte** :
- **Actualité municipale** (sélection LLM) :
  - RSS : Le Soir, Les 2 Rives, Le Contrecourant
  - Scraping : `ville.contrecoeur.qc.ca/actualites`
  - Scraping avis publics (filtre 30 jours)
- **Alertes critiques** (bypass LLM — toujours incluses) :
  - Environnement Canada : scraping `meteo.gc.ca/warnings/report_f.html?qc12=`
  - Hydro-Québec : API GeoJSON Phase 1 (stub + fallback gracieux — site JS-only)
  - Québec.ca eau potable : scraping avec filtre région Contrecœur

**Corrections en cours de route** :
- URL Contrecoeur corrigée (`contrecoeur.ca` → `ville.contrecoeur.qc.ca/actualites`)
- EC RSS 404 → scraping HTML direct
- Préfixes visuels sur les alertes : ⚠️ EC / ⚡ HQ / 🚰 eau

---

### 4. Sources RSS — Montréal Événements

**Avant** : 5 sources (dont Voir.ca en erreur 500)  
**Après** : 8 sources actives

Voir.ca retiré (erreur 500 persistante). Sources ajoutées :
- Journal Métro (`journalmetro.com/feed/`) — actualité locale Montréal
- La Presse Spectacles (`lapresse.ca/arts/spectacles/rss`) — critiques et annonces culturelles majeures
- Le Bordel (`lebordel.ca/feed`) — comédie, variété
- L'Olympia (`olympiamontreal.com/feed`) — concerts, venue

---

### 5. Agent Ticketmaster — Événements Montréal

**Objectif** : compléter la couverture événementielle avec des listings directs (pas seulement des articles de presse).

**Implémentation** : `agents/ticketmaster_agent.py` — nouveau `BaseAgent`.

**3 requêtes API** (marché 522 — Montréal) :
1. Tous les événements Montréal (`marketId=522`)
2. Musique / concerts (`classificationName=music`)
3. Arts & Théâtre / humour (`classificationName=Arts & Theatre`)

**Mécanisme** :
- Déduplication par event ID Ticketmaster entre les 3 requêtes
- `raw_content` structuré construit à partir des données API (événement, artistes, date, lieu, prix, lien)
- `ticketmaster.com` ajouté à `_SKIP_DOMAINS` dans l'ArticleFetcher → le `raw_content` synthétique est préservé
- Sélection LLM via `_llm_select()`, quota 5 événements
- Clé API : `secrets/.env → TICKETMASTER_API_KEY`

**Intégration** : `TicketmasterAgent` ajouté dans `scripts/run_pipeline.py` aux côtés de `EventsMontrealAgent`.

**Documentation** : [[Agents/Journaliste-Montreal]] mise à jour — tableau sources API Ticketmaster.

---

### 6. Secrets

- `secrets/.env` : ajout de `TICKETMASTER_API_KEY` (clé déposée par l'utilisateur)
- Fichier protégé par `.gitignore` — non versionné

---

## Fichiers modifiés

| Fichier | Type | Description |
|---------|------|-------------|
| `config/config.yaml` | Modifié | +12 RSS vehicules_ev, +1 sitemap Waabi, +17 RSS spatial, URL Contrecoeur corrigée, RSS evenements_mtl nettoyés (+4, -1) |
| `agents/local_contrecoeur.py` | Modifié | Refonte complète — 3 alertes critiques + scraping avis publics |
| `agents/ticketmaster_agent.py` | Nouveau | Agent Ticketmaster Discovery v2 — événements Montréal |
| `agents/sitemap_agent.py` | Nouveau | Agent sitemap (Waabi, OpenAI, Anthropic, DeepMind) |
| `agents/hf_papers_agent.py` | Nouveau | Agent HuggingFace Daily Papers |
| `processors/article_fetcher.py` | Modifié | `ticketmaster.com` ajouté à `_SKIP_DOMAINS` |
| `scripts/run_pipeline.py` | Modifié | Import + instanciation `TicketmasterAgent` |
| `Lecteur de nouvelle/Agents/Journaliste-VehiculeEV.md` | Modifié | 15 RSS + 1 sitemap + tableau sources sans RSS |
| `Lecteur de nouvelle/Agents/Journaliste-Spatial.md` | Modifié | 17 RSS + tableau sources sans RSS |
| `Lecteur de nouvelle/Agents/Journaliste-Montreal.md` | Modifié | 8 RSS + section API Ticketmaster |

---

## Prochaines priorités

- [ ] Expansion sources — Politique Québec (4 → ~10)
- [ ] Expansion sources — Politique Canada (5 → ~10)
- [ ] Expansion sources — Politique Internationale (6 → ~10)
- [ ] Synchroniser doc Tech AI (config : 16 sources, doc : à jour)
- [ ] Hydro-Québec Phase 2 — trouver point d'accès alternatif aux pannes (API GeoJSON inaccessible)

---

## Liens

- [[Agents/Journaliste-Montreal]] · [[Agents/Journaliste-VehiculeEV]] · [[Agents/Journaliste-Spatial]]
- [[Architecture/Agents de collecte]]
- [[Milestones/Phase 8 — Cycle en V — Plan]]

#session #2026-05-26 #expansion-sources #ticketmaster #contrecoeur
