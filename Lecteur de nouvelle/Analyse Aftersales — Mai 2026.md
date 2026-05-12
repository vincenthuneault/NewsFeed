# Analyse Aftersales — Cycle 1 (30 avril – 4 mai 2026)

**Rôle :** Aftersales (Triage)
**Source :** 42 notes personnelles + 11 feedbacks textuels
**Date d'analyse :** 2026-05-11

---

## Résumé exécutif

| Type                                           | Nb  | Destination               |
| ---------------------------------------------- | --- | ------------------------- |
| Redondance / Duplicata                         | 7   | ECR-001                   |
| Contenu tronqué / Source problématique         | 7   | ECR-002                   |
| Hors profil géographique ou démographique      | 10  | MCA-001, MCA-003, MCA-004 |
| Mauvaise catégorisation                        | 5   | ECR-003 / MCA-002         |
| Hors scope éditorial (sport, jeunesse, gaming) | 3   | MCA-005                   |
| Bug technique                                  | 1   | ECR-004                   |
| Suggestion UX                                  | 1   | ECR-005                   |
| Label de confirmation (bonne catégorie)        | 7   | Journalisation            |
| Contenu approuvé / positif                     | 2   | Business                  |
| Feedbacks "Très intéressant"                   | 10  | Business                  |

**Total traité : 53 items (42 notes + 11 feedbacks)**

---

## 1. Redondances — ECR-001

> Articles présentés plusieurs jours de suite. Problème systémique confirmé par investigation DB.

| #   | Article                                     | Note utilisateur                      | Confirmé DB         |
| --- | ------------------------------------------- | ------------------------------------- | ------------------- |
| #37 | DARPA — lunar orbiter studies               | redondance de l'article présenté hier | ✅ feed 02/05 + 03/05 |
| #36 | Amazon Leo — 300 satellites                 | redondance de l'article présenté hier | ✅ feed 02/05 + 03/05 |
| #34 | Trump nominates Schiess — Space Force       | redondance, déjà présentée            | ✅ feed 02/05 + 03/05 |
| #33 | Starcloud — orbital data center funding     | redondante les deux derniers jours    | ✅ feed 02/05 + 03/05 |
| #29 | The opportunity beyond orbital data centers | déjà présentée hier                   | ✅ feed 02/05 + 03/05 |
| #28 | Tesla Model 3 RWD Canada                    | déjà présentée hier                   | ✅ feed 02/05 + 03/05 |
| #27 | NASA CLPS contract value increase           | déjà présentée hier                   | ✅ feed 02/05 + 03/05 |

### Investigation DB — Ampleur réelle du problème

L'analyse complète des 13 feeds (28 avril → 11 mai) révèle un problème bien plus large :

| Fréquence                        | Nombre d'articles                                                                                      |
| -------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Présentés 1× (normal)            | 303                                                                                                    |
| Présentés 2× (répétition)        | **42**                                                                                                 |
| Présentés 3×+ (répétition grave) | **1** — #194 "The 40 best Mother's Day gift ideas" (The Verge) dans les feeds du 05/05, 07/05 et 09/05 |

**44 slots sur 390 gaspillés (11% du contenu présenté est du déjà-vu)**

### Cause racine identifiée

Le bug est dans `processors/scorer.py` — **pas dans le déduplicateur d'URL**.

Le `Scorer._select_with_diversity()` (ligne 141) sélectionne le top 30 par `final_score` sans jamais consulter les `daily_feeds` précédents. La fenêtre de fraîcheur est de 48h (`freshness_decay_hours: 48`), ce qui donne encore un score non-nul à des articles de la veille. Le `FeedAssembler` sauvegarde simplement ce qu'il reçoit — aucune mémoire non plus.

**→ ECR-001 :** Dans `Scorer._select_with_diversity()`, charger l'union des `item_ids` de tous les `DailyFeed` des 7 derniers jours et exclure ces IDs avant la sélection. Fix minimal : ~10 lignes dans `scorer.py`.

---

## 2. Contenu tronqué / Sources problématiques — ECR-002

> Articles illisibles ou insuffisants pour être présentés. The Verge est la source principale.

| # | Article | Note |
|---|---|---|
| #7 | All the evidence unveiled — Musk v. Altman | sujets tronqués à cause de The Verge |
| #5 | Google Search queries — all time high | The Verge, contenu pas disponible — trouver autres sources |
| #3 | Grindr won the WHCD party circuit | information tronquée |
| #2 | Elon Musk's worst enemy in court is Elon Musk | contenu tronqué — trouver autres sources |
| #30 | Mark Carney se rend en Arménie | article totalement incomplet |
| #10 | Supply-chain attack — Checkmarx/Bitwar | description insuffisante, ne devrait pas passer le filtre |
| #1 | 🔴LIVE ARC RAIDERS — Riven Tide | live stream, aucune information utilisable pour construire un article |

**Constat :** The Verge génère systématiquement du contenu inaccessible (paywall ou JS requis). Les live streams YouTube ne devraient jamais passer le filtre.

**→ ECR-002 :** Mettre en place un gate de qualité sur le contenu extrait :
- Longueur minimale du `raw_content` pour passer la sélection
- Blacklister The Verge ou trouver des sources alternatives de substitution (ex : Ars Technica, 9to5Mac, The Information)
- Filtrer les vidéos YouTube dont le titre contient `🔴LIVE`, `#LIVE`, `LIVE |`

---

## 3. Hors profil géographique ou démographique — MCA-001, MCA-003, MCA-004

### 3a. Géographie locale hors zone (MCA-001)

> La catégorie `local_contrecoeur` et `evenements_mtl` ramassent des contenus trop larges géographiquement.

| # | Article | Note |
|---|---|---|
| #41 | Marchethon de la dignité — Rimouski | marathon Rimouski ≠ Contrecoeur/Sorel |
| #32 | Hot-dogs, arts, cuisine — trottoirs torontois | politique torontoise, peu intéressant |
| #31 | Vote par anticipation — élections N.-B. | politique Nouveau-Brunswick, peu intéressant |
| #21 | Enrochement de Mont-Louis | ville inconnue, pas intéressé |
| #20 | Chantiers 2026 — Ville de Québec | politique municipale Québec, pas intéressé |
| #19 | Élection municipale Ottawa | politique municipale Ottawa, pas intéressé |

**→ MCA-001 :** Resserrer le périmètre géographique des agents locaux à : **Contrecoeur, Sorel-Tracy, Grand Montréal (île + rive sud immédiate)**. Exclure explicitement : Rimouski, Québec, Ottawa, Toronto, autres provinces.

### 3b. Musique hors style (MCA-003)

| # | Article | Note |
|---|---|---|
| #12 | Fetty Wap — I Remember (feat. G Herbo) | ne connaît pas cet artiste — écoute électro, EDM, techno |

**→ MCA-003 :** Pour `musique_electro`, le filtre doit favoriser exclusivement : électro, EDM, techno, house, trance. Exclure : rap, hip-hop, R&B, reggaeton, Bollywood.

### 3c. Contenu trending non-nord-américain (MCA-004)

| # | Article | Note |
|---|---|---|
| #9 | Drishyam 3 — Official Teaser (Bollywood) | pas le bon démographique — trending devrait être nord-américain, profil 35 ans Québec |

**→ MCA-004 :** L'agent `viral_trending` doit filtrer pour contenu nord-américain et francophone. Exclure les tendances internationales hors NA (Bollywood, K-pop, etc.).

---

## 4. Mauvaise catégorisation — ECR-003 + MCA-002

> Des articles atterrissent dans des catégories qui ne correspondent pas à leur contenu réel.

| # | Article | Catégorie actuelle | Devrait être |
|---|---|---|---|
| #40 | Electric bikes — best at every price level | `vehicules_ev` | À exclure (vélos ≠ auto/camion) |
| #35 | Solar farm — cattle under moving panels | `vehicules_ev` | `tech_ai` |
| #22 | Spirit Airlines shuts down — jet fuel prices | non précisé | `politique_intl` ou `tech_ai` |
| #17 | Piste cyclable rue Hochelaga | `evenements_mtl` | `politique_ca` ou `politique_qc` |
| #6 | Œuvres de Luc Plamondon aux enchères | `politique_qc` | Hors scope (culture/art) |

**Clarification explicite de l'utilisateur (#17) :** `evenements_mtl` = spectacles, théâtre, humour, événements spéciaux, popup, DJ, fêtes. **Pas de politique municipale.**

**→ ECR-003 :** Resserrer les prompts de classification :
- `vehicules_ev` → **voitures, camions, VUS, véhicules autonomes électriques uniquement** (exclure vélos, trottinettes, panneaux solaires)
- `evenements_mtl` → spectacles, sorties culturelles, festivals, DJ, popup (exclure politique, infrastructure)

**→ MCA-002 :** Mettre à jour le contexte de scoring pour pénaliser les articles "vélo électrique" dans `vehicules_ev`.

---

## 5. Hors scope éditorial — MCA-005

> Catégories de contenu que l'utilisateur ne souhaite pas du tout dans son feed.

| # | Article | Note |
|---|---|---|
| #13 | Le Rocket défait les Marlies | sport — pas ce que je veux couvrir |
| #11 | Tomodunkey Life (YouTube gaming) | jeux vidéo, pas intéressé |
| #4 | Splatoon Raiders — Switch 2 preorders | jeux vidéo, pas intéressé |
| #14 | Des ados mettent leur inventivité à l'épreuve | pas d'intérêt — focus politique, tech, business |
| #25 | The things we're building | article sans information, aucune valeur |

**→ MCA-005 :** Exclure ou scorer à zéro : sport, jeux vidéo, contenu jeunesse/éducation. Appliquer un filtre sur les articles avec `raw_content` < seuil minimum de substance.

---

## 6. Bug technique — ECR-004

| # | Article | Note |
|---|---|---|
| #8 | The new Razr Ultra — best-looking phone | bug lecteur audio : pris 3 tentatives avant lecture complète |

**→ ECR-004 :** Investiguer la stabilité du player TTS sur certains articles. Vérifier si le problème est lié à la longueur du fichier audio, au format du `audio_path`, ou à un timeout de chargement. Ajouter un log d'erreur de lecture côté frontend pour reproduire.

---

## 7. Suggestion UX — ECR-005

| # | Article | Note |
|---|---|---|
| #12 | Fetty Wap (aussi) | ajouter l'information "pourquoi ce contenu m'est présenté" — surtout pour les vidéos |

**→ ECR-005 :** Afficher dans l'interface la raison de présentation d'un article/vidéo (ex : "Présenté car : trending Québec", "Source : abonnement YouTube", "Catégorie : tech_ai"). Permet un feedback plus ciblé et rapide.

---

## 8. Labels de confirmation — Journalisation

> L'utilisateur confirme implicitement que la catégorie est correcte en la nommant dans sa note. Aucune action requise.

| # | Article | Label donné |
|---|---|---|
| #42 | Canada vulnérable aux cyberattaques | politique canadienne ✓ |
| #39 | RSF — liberté de presse | politique internationale ✓ |
| #38 | Victor Schwartz — importateur de vin | politique américaine ✓ |
| #26 | Mark Carney en Arménie | politique canadienne ✓ |
| #24 | Boulerice — gauche s'inspirer de Poilievre | politique québécoise ✓ |
| #23 | Appartements vacants Montréal | politique municipale MTL ✓ |
| #18 | Charles Milliard — nucléaire | politique québécoise ✓ |

---

## 9. Contenu approuvé / positif — Business

| # | Article | Note |
|---|---|---|
| #16 | Pilule abortive suspendue aux États-Unis | intéressant pour ses enjeux politiques |
| #15 | Office Romance — trailer Netflix | intéressant à partager (usage social, partage avec proche) |

**Signal :** L'utilisateur voit de la valeur dans le contenu de divertissement grand public **quand il peut le partager**. Cas d'usage "partage avec la blonde" = fonctionnalité sociale potentielle.

---

## 10. Feedbacks textuels — Business

Les 11 feedbacks avec texte sont presque tous des `like` avec "Très intéressant" sur :
- Complot politique / créateurs de vidéos conspirationnistes
- Procès Elon Musk vs Altman
- Taylor Swift et droits d'auteur IA
- James Comey / politique américaine

**Signal clair :** L'utilisateur est fortement attiré par le contenu **politique américain à fort enjeu**, **tech-légal**, et **personnalités controversées**. Ces catégories devraient avoir un boost de score.

---

## Récapitulatif des actions

### ECRs à créer

| ID | Titre | Priorité |
|---|---|---|
| ECR-001 | Étendre fenêtre déduplication à 7 jours + dédup sémantique | 🔴 Haute |
| ECR-002 | Gate de qualité sur contenu extrait + blacklist The Verge + filtre live streams | 🔴 Haute |
| ECR-003 | Resserrer définition catégories `vehicules_ev` et `evenements_mtl` | 🟡 Moyenne |
| ECR-004 | Bug stabilité lecteur audio — investiguer et logger | 🟡 Moyenne |
| ECR-005 | Afficher "Pourquoi ce contenu" dans l'interface | 🟢 Faible |

### Mises à jour contexte agents (sans code)

| ID | Changement |
|---|---|
| MCA-001 | Géographie locale : restreindre à Contrecoeur / Sorel / Grand Montréal |
| MCA-002 | `vehicules_ev` : exclure vélos, trottinettes, énergie solaire |
| MCA-003 | `musique_electro` : exclure rap/hip-hop/R&B/Bollywood |
| MCA-004 | `viral_trending` : filtrer pour contenu nord-américain, profil 35 ans Québec |
| MCA-005 | Scorer à 0 : sport, jeux vidéo, contenu jeunesse |

### Pour le Business

- Fort appétit pour **politique américaine** → envisager une sous-catégorie `politique_us` dédiée
- Intérêt pour contenu **partageable** (divertissement grand public, trailers) → réfléchir à un mode "partage"
- Contenu électro/EDM = niche forte mais actuellement mal servie
