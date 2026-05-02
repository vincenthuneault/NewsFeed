# Phase 8 — Cycle en V : Gestion des Changements

> **Statut** : Plan en révision — aucune modification au code autorisée
> **Canvas associé** : [[Phase 8 — Cycle en V — Gestion des changements]]

---

## Objectif

Mettre en place un processus d'ingénierie structuré (cycle en V) qui transforme les commentaires utilisateur et les rapports de bugs en modifications validées du système. Le processus est piloté par des agents IA avec l'utilisateur jouant le rôle d'Architecte Produit.

---

## Acteurs

| Agent | Rôle | Type |
|-------|------|------|
| 🏗️ **Architecte Produit** | Vision produit, approbations, arbitrage final | Agent IA assisté par l'utilisateur |
| ⚙️ **Ingénieurs Système** | Requis par domaine, DVP, analyse d'impact | Agents IA spécialisés (un par domaine) |
| 💻 **Développeur** | Implémentation, tests unitaires | Agent IA |
| 🧪 **Testeur** | Tests de régression, DVP, intégration | Agent IA |

---

## Déclencheurs d'entrée

1. **Commentaires utilisateur** — saisis lors de la lecture de nouvelles (texte ou vocal via M7)
2. **Rapports de bugs** — soumis via l'interface (M6)

---

## Flux du processus (bras gauche du V — Définition)

### 1. Analyse & Classification
- **Acteur** : Architecte Produit (+ Ing. Sys. si nécessaire)
- Identifier le sujet, catégoriser (bug / feature / amélioration)
- Évaluer si une modification système est requise
- Si **non** → journalisation uniquement
- Si **oui** → création d'un ECR

### 2. Création d'ECR (Engineering Change Record)
- N° ECR-XXX généré automatiquement
- Description, contexte de découverte, type, priorité initiale
- Ajouté à la liste des ECR (backlog d'ingénierie)
- Format : `[[ECR/ECR-XXX — titre.md]]`

### 3. Priorisation des ECR
- **Acteur** : Architecte Produit + Ingénieurs Système
- **Fréquence** : configurable dans `config.yaml` (défaut : quotidienne)
- Critères : impact utilisateur · urgence · complexité technique
- Résultat : package de mises à jour priorisé

### 4. Validation du Package
- **Acteur** : Architecte Produit
- Approuve le périmètre du package avant de lancer les travaux d'ingénierie

### 5. Analyse d'impact par domaine
- **Acteur** : Ingénieurs Système concernés
- Identification des systèmes affectés
- Désignation des Ing. Sys. responsables par domaine

### 6. Rédaction des Requis + DVP
- **Acteur** : Ingénieurs Système (en parallèle)
- **Requis** : fonctionnels, non-fonctionnels, critères d'acceptation, contraintes
- **DVP (Design Validation Plan)** : cas de test, conditions d'utilisation, critères de succès mesurables

---

## Fond du V — Conception & Implémentation

### 7. Design Review
- **Acteur** : Architecte Produit
- Valide requis + DVP avec vision produit complet
- Approbation requise avant tout développement

### 8. Développement + Tests Unitaires
- **Acteur** : Développeur
- Analyse des requis, implémentation du fix / feature
- Boucle interne jusqu'au passage complet des tests unitaires
- Validation dans les conditions d'utilisation définies par le DVP

---

## Flux du processus (bras droit du V — Vérification)

### 9. Création de branche & Intégration
- **Acteur** : Développeur
- Fork depuis `main`
- Code intégré dans la branche de modification
- Remis au Testeur

### 10. Tests de Régression + DVP
- **Acteur** : Testeur
- Tests standards existants (non-régression complète)
- DVP nouvellement créé intégré dans la suite de tests
- Vérification systématique à chaque cycle

### 11. Décision sur les résultats de test

#### Si les tests passent ✅
- Résultats transmis aux Ingénieurs Système (contexte)
- Passage au déploiement beta

#### Si les tests échouent ❌
- Notification Ing. Sys. + Développeur
- Ing. Sys. analysent les échecs et décident :
  - **Retry développeur** : le développeur refait un développement
  - **Modification des requis** : les requis sont mal définis

**Limites :**
- Développeur : **max 3 tentatives** de redéveloppement
- Modification des requis : **max 3 cycles** de révision
- Si 3 cycles épuisés → **ARRÊT** — Architecte Produit notifié, processus stoppé

> ⚠️ Les Ingénieurs Système peuvent intervenir à tout moment pour stopper le développement et réviser les requis.

---

### 12. Déploiement Beta
- Branche déployée en version beta
- Version `main` toujours disponible pour retour immédiat

### 13. Validation utilisateur (Architecte Produit)
- L'utilisateur dispose des droits Architecte Produit pour accéder à la beta
- Peut revenir à la version `main` à tout moment

#### Si beta approuvée ✅
- **Merge to Main** — version beta devient version de production

#### Si beta rejetée ❌
- Commentaires utilisateur analysés par les Ingénieurs Système
- Recommandations techniques transmises au Développeur
- Nouveau cycle de développement lancé

---

## Configuration

Paramètres à ajouter dans `config.yaml` :

```yaml
engineering_process:
  ecr_prioritization_frequency: "daily"   # daily, weekly, manual
  max_dev_retries: 3                       # tentatives développeur
  max_req_modifications: 3                 # cycles révision requis
  beta_enabled: true
  auto_ecr_from_comments: true
  auto_ecr_from_bugs: true
```

---

## Structure des fichiers à créer

```
Lecteur de nouvelle/
├── ECR/
│   ├── ECR-XXX — <titre>.md        (format existant)
│   └── Backlog ECR.md              (liste priorisée)
├── Requis/
│   └── REQ-XXX — <titre>.md        (à définir)
├── DVP/
│   └── DVP-XXX — <titre>.md        (à définir)
└── Phase 8 — Cycle en V — Plan.md  (ce document)
```

---

## Questions ouvertes pour la revue

1. **Domaines des Ingénieurs Système** : quels domaines/spécialités définir ? (ex: frontend, backend, pipeline, agents, infra ?)
2. **Fréquence de priorisation** : quotidienne est-elle suffisante ou veut-on un déclenchement sur seuil (ex: 5 ECR accumulés) ?
3. **Format ECR** : le format actuel (ECR-001, ECR-002) convient-il ou faut-il l'étendre ?
4. **Critères d'approbation beta** : comment l'utilisateur communique-t-il son approbation ? (commentaire texte, commande, feedback vocal ?)
5. **Traçabilité** : faut-il lier chaque ECR aux requis, au DVP et au commit git correspondant ?
6. **Scope Phase 8** : tout le processus en une seule phase ou découper en sous-milestones (M8a, M8b, ...) ?

---

## Liens

- [[Vue d'ensemble]]
- [[ECR/ECR-001 — Bouton calendrier dupliqué au re-login]]
- [[ECR/ECR-002 — App non fonctionnelle sur navigateur desktop]]
- [[Références/Plan de projet]]

#phase8 #cycle-en-v #processus #ingenierie #plan
