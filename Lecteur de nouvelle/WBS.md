# WBS — Work Breakdown Structure

> Découpage du système Lecteur de nouvelle en 6 domaines fonctionnels. Chaque domaine est la responsabilité exclusive d'un [[Ingénieur Système]].  
> **Créé** : 2026-05-18

---

## Arbre WBS

```
Lecteur de nouvelle
│
├── 1. Agents & Collecte                          [[Agents/Ingénieur-Agents]]
│   ├── 1.1 Orchestration parallèle               core/orchestrator.py
│   ├── 1.2 Agents RSS                            agents/rss_generic.py
│   │                                             agents/events_montreal.py
│   │                                             agents/local_contrecoeur.py
│   └── 1.3 Agents YouTube                        agents/youtube_subs.py
│                                                 agents/youtube_trending.py
│                                                 agents/viral_trending.py
│
├── 2. Pipeline & Traitement                      [[Agents/Ingénieur-Pipeline]]
│   ├── 2.1 Déduplication                         core/deduplicator.py
│   ├── 2.2 Scoring & Sélection                   processors/scorer.py
│   └── 2.3 Assemblage                            core/pipeline.py
│                                                 processors/feed_assembler.py
│
├── 3. IA & Contenu                               [[Agents/Ingénieur-IA]]
│   ├── 3.1 Résumés IA                            processors/summarizer.py
│   ├── 3.2 Audio TTS                             processors/tts_generator.py
│   └── 3.3 Images                               processors/image_extractor.py
│
├── 4. Backend & Données                          [[Agents/Ingénieur-Backend]]
│   ├── 4.1 Modèle de données                     core/models.py
│   ├── 4.2 API REST                              backend/app.py
│   │                                             backend/api/feed.py
│   │                                             backend/api/feedback.py
│   │                                             backend/api/comments.py
│   │                                             backend/api/bugs.py
│   │                                             backend/api/settings.py
│   │                                             backend/api/health.py
│   │                                             backend/api/aftersales.py
│   └── 4.3 Authentification                      backend/auth.py
│                                                 backend/api/auth.py
│
├── 5. Frontend Mobile                            [[Agents/Ingénieur-Frontend]]
│   ├── 5.1 Interface & navigation                frontend/js/app.js
│   │                                             frontend/js/feed.js
│   │                                             frontend/js/ui.js
│   │                                             frontend/css/app.css
│   │                                             frontend/index.html
│   ├── 5.2 Lecteur audio                         frontend/js/player.js
│   └── 5.3 Saisie vocale & PWA                   frontend/js/speech.js
│                                                 frontend/js/api.js
│                                                 frontend/sw.js
│                                                 frontend/manifest.json
│
└── 6. Infrastructure & Déploiement               [[Agents/Ingénieur-Infra]]
    ├── 6.1 Serveur                               deploy/gunicorn.conf.py
    │                                             deploy/newsfeed.service
    ├── 6.2 Automatisation                        deploy/newsfeed-cron.service
    │                                             deploy/newsfeed-cron.timer
    │                                             run_pipeline.py
    ├── 6.3 Configuration                         config/config.yaml
    │                                             core/config.py
    └── 6.4 Monitoring & logs                     core/logger.py
                                                  backend/api/health.py
                                                  deploy/logrotate.conf
```

---

## Ingénieurs Système

| IS | Spécialité | ECRs actifs |
|----|-----------|-------------|
| [[Agents/Ingénieur-Agents\|IS-1]] | Agents & Collecte | ECR-003, ECR-004, ECR-005 |
| [[Agents/Ingénieur-Pipeline\|IS-2]] | Pipeline & Traitement | ECR-003, ECR-004 |
| [[Agents/Ingénieur-IA\|IS-3]] | IA & Contenu | ECR-004, ECR-006 |
| [[Agents/Ingénieur-Backend\|IS-4]] | Backend & Données | ECR-007 |
| [[Agents/Ingénieur-Frontend\|IS-5]] | Frontend Mobile | ECR-006, ECR-007 |
| [[Agents/Ingénieur-Infra\|IS-6]] | Infrastructure & Déploiement | — |

---

## Interfaces critiques entre domaines

| Interface | Producteur | Consommateur | Contrat |
|-----------|------------|--------------|---------|
| `RawNewsItem` | IS-1 Agents | IS-2 Pipeline | dataclass — `core/models.py` |
| `NewsItem` (DB) | IS-2 Pipeline | IS-4 Backend | SQLAlchemy — `core/models.py` |
| `DailyFeed` (DB) | IS-2 Pipeline | IS-4 Backend | JSON array d'IDs — `core/models.py` |
| `Feedback` (DB) | IS-4 Backend | IS-2 Pipeline | boost scoring — `core/models.py` |
| `audio_path` | IS-3 IA | IS-5 Frontend | chemin `/static/audio/*.mp3` |
| `image_path` | IS-3 IA | IS-5 Frontend | chemin `/static/images/*.jpg` |
| JSON REST | IS-4 Backend | IS-5 Frontend | `api.js` fetch wrapper |
| `config.yaml` | IS-6 Infra | Tous | dict Python via `core/config.py` |

---

## Matrice de responsabilités

| Domaine | Responsable de | Pas responsable de |
|---------|---------------|-------------------|
| IS-1 Agents | Collecte brute + orchestration parallèle | Déduplication, scoring, résumés, images, audio |
| IS-2 Pipeline | Dédup + scoring + sélection + assemblage | Collecte brute, API HTTP, frontend |
| IS-3 IA | Claude API + Google TTS + images | Pipeline logique, API, frontend |
| IS-4 Backend | DB schema + API REST + auth | Pipeline, agents, frontend |
| IS-5 Frontend | UI/UX mobile + PWA + audio player | Logique métier backend, infra |
| IS-6 Infra | Config + déploiement + monitoring | Logique métier, API, frontend |

---

## Liens

- [[Agents/Architecte Produit]] — utilise ce WBS pour analyser l'impact des ECRs
- [[Milestones/Phase 8 — Cycle en V — Plan]] — processus d'ingénierie
- [[Bugs/Backlog]] — ECRs ouverts par domaine

#wbs #architecture #ingenierie #phase8
