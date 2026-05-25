# Session 2026-05-18 — Plan de journée

> **Date** : 2026-05-18  
> **Statut** : En cours  
> **Objectif** : Compléter les fiches agents, structurer l'ingénierie Phase 8, valider le pipeline et préparer le passage Beta → Release.

---

## Bloc 1 — Agents du Processus de revue des commentaires

**Ordre de priorité : suivre le flux du canvas de gauche à droite**

Journaliste → Chef de presse → Éditeur → Narrateur → Aftersales → Architecte Produit → Ingénieurs Système → Développeur → Testeur → Business

- [ ] **1.1** Réviser [[Agents/Journaliste]] — valider rôle, contraintes, inputs/outputs, feedback loop
- [ ] **1.2** Réviser [[Agents/Chef de presse]] — valider gate qualité, périmètre temporel, lien avec Journaliste
- [ ] **1.3** Créer [[Agents/Éditeur]] — résumé FR via Claude, position dans le pipeline après Chef de presse
- [ ] **1.4** Créer [[Agents/Narrateur]] — TTS Google fr-CA, inputs, outputs audio
- [ ] **1.5** Réviser [[Agents/Aftersales]] — méthode scientifique, triage, routage ECR / journalisation / contexte
- [ ] **1.6** Créer [[Agents/Architecte Produit]] — classification ECR, approbation packages, arbitrage, rôle utilisateur vs agent IA
- [ ] **1.7** Créer [[Agents/Ingénieurs Système]] — fiche générique (les domaines viendront du WBS — Bloc 2)
- [ ] **1.8** Créer [[Agents/Développeur]] — implémentation, tests unitaires, boucle retry
- [ ] **1.9** Créer [[Agents/Testeur]] — régression, DVP, critères d'échec, escalade
- [ ] **1.10** Créer [[Agents/Business]] — métriques, tendances, lien vers roadmap Architecte Produit
- [ ] **1.11** Valider la cohérence globale du canvas `Processus de revue des commentaires` avec toutes les fiches

---

## Bloc 2 — Ingénierie : WBS et ingénieurs système

**But : décomposer le système en domaines, créer un ingénieur par domaine, formaliser les deux processus**

- [ ] **2.1** Faire le WBS du système — identifier les domaines candidats (ex : Frontend, Backend/API, Pipeline de traitement, Agents IA, Base de données, Infrastructure/Déploiement)
- [ ] **2.2** Valider la liste finale des domaines — un ingénieur système par domaine
- [ ] **2.3** Créer une fiche par ingénieur système avec : domaine, responsabilités, périmètre d'impact, liens vers les composants
- [ ] **2.4** Définir le **processus de modification** (bug fix / amélioration) — s'appuie sur le Cycle en V existant (Phase 8)
- [ ] **2.5** Définir le **processus de création de nouvelle feature** — distinguer clairement de la modification (périmètre, étapes, livrables différents)
- [ ] **2.6** Documenter comment un ECR est routé : modification existante vs nouvelle feature, critères de décision

---

## Bloc 3 — Test du processus : ECR pilote

**But : lancer un ECR réel pour valider que l'ingénierie réagit correctement**

- [ ] **3.1** Choisir un ECR candidat parmi les existants (ECR-003, ECR-004, ECR-007 sont de bons candidats)
- [ ] **3.2** Lancer le Cycle en V Phase 8 complet sur cet ECR — de la classification à la validation beta
- [ ] **3.3** Documenter les frictions, zones de flou et décisions prises en cours de route
- [ ] **3.4** Ajuster les fiches agents ou le plan Phase 8 en conséquence

---

## Bloc 4 — Sandbox et environnement de test contrôlé

**But : définir comment tester le processus complet sans toucher à la production**

- [ ] **4.1** Définir l'architecture sandbox — DB séparée? branche git dédiée? variable d'environnement `SANDBOX_MODE`?
- [ ] **4.2** Créer un jeu de données fictives : articles, commentaires, bugs représentatifs de cas réels
- [ ] **4.3** Documenter la procédure pour lancer un cycle complet en mode sandbox
- [ ] **4.4** Valider qu'un agent peut être tuné dans le sandbox (modification de prompt ou contexte) sans impact production
- [ ] **4.5** Définir le processus pour promouvoir un ajustement validé en sandbox vers la production

---

## Bloc 5 — Validation pipeline : passage en autonomie

**But : s'assurer que le système peut tourner par lui-même sans intervention manuelle**

- [ ] **5.1** Vérifier l'enchaînement de tous les agents du pipeline (collecte → traitement → publication → feedback → triage)
- [ ] **5.2** Valider les déclencheurs automatiques (cron, event-driven)
- [ ] **5.3** Confirmer que les erreurs sont loggées, tracées et notifiées correctement
- [ ] **5.4** S'assurer qu'aucune action manuelle n'est requise pour un cycle normal de bout en bout

---

## Bloc 6 — Beta → Release : dynamique de versioning

**But : définir et visualiser le chemin entre Beta et Production**

- [ ] **6.1** Définir les critères de passage Beta → Release (qui approuve, quels tests, quel délai minimum)
- [ ] **6.2** Définir la coexistence des deux versions (branches git, environnements, flag de déploiement)
- [ ] **6.3** Créer une vue de visualisation des deux versions (canvas ou tableau comparatif)
- [ ] **6.4** Documenter le processus de rollback : comment revenir à une release depuis une beta problématique

---

## Bloc 7 — Ménage documentation

**But : s'assurer que tout est à jour avant de clore la session**

- [ ] **7.1** Mettre à jour [[Vue d'ensemble]] — ajouter les nouveaux agents, Phase 8, et état du projet
- [ ] **7.2** Vérifier les liens inter-documents dans tous les fichiers modifiés aujourd'hui
- [ ] **7.3** Mettre à jour [[Références/Plan de projet]] — documenter la transition vers Phase 8 et au-delà
- [ ] **7.4** Revoir les ECR ouverts dans [[Bugs/Backlog]] — s'assurer que les statuts sont à jour

---

## Notes de session

> Espace pour les décisions, blocages et ajustements pris durant la journée.

---

## Liens

- [[Agents/Journaliste]] · [[Agents/Chef de presse]] · [[Agents/Aftersales]]
- [[Milestones/Phase 8 — Cycle en V — Plan]]
- [[Processus de revue des commentaires]]
- [[Vue d'ensemble]] · [[Références/Plan de projet]]

#session #plan-de-journée #2026-05-18
