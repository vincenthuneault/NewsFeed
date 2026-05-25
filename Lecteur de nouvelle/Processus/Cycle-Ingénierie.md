# Cycle d'Ingénierie — Guide de processus

> Ce document décrit chaque étape du pipeline d'ingénierie, comment consulter ce que chaque
> agent a produit, et comment donner des commentaires à chaque point d'accès.

---

## Vue d'ensemble du flux

```
Aftersales (22h quotidien)
  → ECRs créés [a_transmettre]
          ↓
Étape 1 — Package (Architecte Produit)
  → PKG proposé → USER ✅ approuve
          ↓
Étape 2 — Product Brief par ECR (Architecte Produit)
  → PB produit → USER lit → IS démarrent
          ↓
Étape 3 — SFD + ICD par IS (Ingénieurs Système — Round 1)
  → Drafts soumis
          ↓ (si multi-domaines)
Étape 4 — Arbitrage (Architecte Produit)
  → Décision contraignante sur les interfaces
          ↓
Étape 5 — REQ + DVP par IS (Ingénieurs Système — Round 2)
  → Documents finaux soumis
          ↓
Étape 6 — Design Review (Architecte Produit)
  → Validation vs PB → USER ✅ approuve ou 🔄 retourne
          ↓
Développeur → implémente
Testeur → exécute les cas DVP
Beta → USER ✅ → ECR [corrige]
```

---

## Statuts ECR

| Statut | Signification |
|--------|---------------|
| `a_transmettre` | Créé par Aftersales, en attente de package |
| `en_cours` | Approuvé dans un package, en ingénierie |
| `en_observation` | Fix présumé déployé, observation en cours |
| `corrige` | Beta validée par l'utilisateur |
| `annule` | Annulé lors du package (doublon, hors scope) |

---

## Étape 1 — Package (Architecte Produit)

### Ce que l'agent produit
Le PKG analyse tous les ECRs `a_transmettre` et propose :
- **Inclure** (max 3) : ECRs prioritaires avec IS assignés et responsabilités
- **Annuler** : doublons ou ECRs hors scope
- **Différer** : valides mais pas urgents

### Consulter
```bash
python scripts/run_architecte_produit.py --package
# Propose un nouveau package et l'affiche

python scripts/run_architecte_produit.py --show
# Affiche l'état global (packages, ECRs en cours, progression)
```

### Donner des commentaires / approuver
```bash
# Approuver tel quel
python scripts/run_architecte_produit.py --approve PKG-001

# Approuver avec rejet explicite d'un ECR
python scripts/run_architecte_produit.py --approve PKG-001 \
  --reject ECR-004 "doublon de ECR-001"

# Si tu veux modifier le package : relancer --package après avoir modifié
# manuellement les statuts ECR dans la DB, ou commenter ici pour qu'un
# nouveau package soit proposé avec des instructions précises.
```

---

## Étape 2 — Product Brief (Architecte Produit)

### Ce que l'agent produit
Le PB est le document de référence des IS. Il contient :
- **Intent** : ce qu'on veut obtenir du point de vue utilisateur
- **IS assignments** : quel IS est responsable de quoi (boundaries précises)
- **Constraints** : contraintes non-négociables (perf, rétrocompat, coût)
- **Success criteria** : comment on sait que c'est réglé
- **Out of scope** : ce qui n'est PAS dans ce fix

### Consulter
```bash
python scripts/run_architecte_produit.py --brief ECR-017
# Génère et affiche le PB pour ECR-017

python scripts/run_architecte_produit.py --show ECR-017
# Affiche tous les documents de ECR-017 (incluant le PB)
```

### Donner des commentaires
Si le PB ne correspond pas à ce que tu attends :
```bash
# Relancer avec des instructions supplémentaires :
# Modifier run_architecte_produit.py --brief pour passer un contexte additionnel,
# ou ajuster directement le contenu JSON dans la DB et marquer le doc 'approuve'.
```

---

## Étape 3 — SFD + ICD (Ingénieurs Système — Round 1)

### Ce que l'agent produit

**SFD — System Functional Description**
Comment le système fonctionnera APRÈS le fix :
- Description fonctionnelle narrative
- Comportements (trigger → action → outcome)
- Interfaces proposées avec les autres domaines

**ICD — Interface Control Document**
Contrats d'interface avec les autres domaines :
- Qui produit, qui consomme
- Format exact des données
- Déclencheur et gestion d'erreur

### Consulter
```bash
python scripts/run_ingenieur_systeme.py --ecr ECR-017
# Lance tous les IS assignés dans le PB (auto-détection)
# Si multi-domaines : Round 1 → Arbitrage → Round 2 automatiquement

python scripts/run_ingenieur_systeme.py --ecr ECR-017 --domain IS-6
# Lance uniquement IS-6 (utile pour relancer un domaine après révision)

python scripts/run_ingenieur_systeme.py --show ECR-017
# Affiche tous les documents produits pour ECR-017
```

### Donner des commentaires
```bash
# Retourner un document en révision
python scripts/run_ingenieur_systeme.py --return SFD-ECR017-IS6 \
  "La description fonctionnelle ne couvre pas le cas de redémarrage du service"

# Approuver un document
python scripts/run_ingenieur_systeme.py --approve SFD-ECR017-IS6

# Relancer un IS après révision
python scripts/run_ingenieur_systeme.py --ecr ECR-017 --domain IS-6
```

---

## Étape 4 — Arbitrage (Architecte Produit · multi-domaines uniquement)

### Ce que l'agent produit
L'Arbitre est lancé automatiquement après le Round 1 si plusieurs IS sont impliqués.
Il reçoit les SFDs et ICDs de tous les IS et produit :
- **Conflits résolus** : chaque contradiction avec une décision contraignante
- **Contrats d'interface finaux** : format, producteur, consommateur — sans ambiguïté
- **Contraintes par domaine** : ce que chaque IS doit respecter pour le Round 2

L'arbitrage est inclus dans le `--show ECR-017` et dans la sortie de `--ecr ECR-017`.

### Donner des commentaires
L'arbitrage est automatique. Si la décision d'arbitrage est incorrecte, tu peux :
1. Retourner l'ARB en révision (via update direct en DB)
2. Relancer `--ecr ECR-017` pour régénérer SFD+ICD+ARB+REQ+DVP

---

## Étape 5 — REQ + DVP (Ingénieurs Système — Round 2)

### Ce que l'agent produit

**REQ — Requis Système**
Exigences formelles dérivées du PB et du SFD/ICD/ARB :
- Condition (déclencheur)
- Critère d'acceptation (mesurable)
- Contrainte technique
- Interface affectée (fichier ou endpoint)

**DVP — Design Validation Plan**
Cas de test structurés :
- **Nominal** : le chemin heureux
- **Limite** : valeurs aux frontières
- **Dégradé** : que se passe-t-il si une dépendance échoue
- **Régression** : vérifier que les autres fonctionnalités ne sont pas cassées

### Consulter
```bash
python scripts/run_ingenieur_systeme.py --show ECR-017
```

### Donner des commentaires
```bash
python scripts/run_ingenieur_systeme.py --return REQ-ECR017-IS6 \
  "Le critère d'acceptation de REQ-001 n'est pas mesurable"

python scripts/run_ingenieur_systeme.py --return DVP-ECR017-IS6 \
  "Manque un cas de test pour la régression sur le pipeline"
```

---

## Étape 6 — Design Review (Architecte Produit)

### Ce que l'agent produit
L'AP lit l'ensemble des documents IS (PB, SFD, ICD, ARB, REQ, DVP) et évalue :
- SFD cohérent avec l'intent du PB ?
- ICD ferme toutes les interfaces ?
- REQs complets et testables ?
- DVP couvre cas nominaux + limites + régressions ?

Décision : **approuve** (développement peut démarrer) ou **retourne** (avec issues précises).

### Consulter
```bash
python scripts/run_architecte_produit.py --design-review ECR-017
```

### Donner des commentaires
```bash
# Si la Design Review retourne des IS en révision :
# 1. Corriger les documents IS retournés
python scripts/run_ingenieur_systeme.py --ecr ECR-017 --domain IS-6

# 2. Relancer la Design Review
python scripts/run_architecte_produit.py --design-review ECR-017
```

---

## Référence rapide — Toutes les commandes

| Action | Commande |
|--------|----------|
| État global du pipeline | `python scripts/run_architecte_produit.py --show` |
| Proposer un package | `python scripts/run_architecte_produit.py --package` |
| Approuver un package | `python scripts/run_architecte_produit.py --approve PKG-001` |
| Approuver + rejeter ECR | `python scripts/run_architecte_produit.py --approve PKG-001 --reject ECR-004 "raison"` |
| Générer Product Brief | `python scripts/run_architecte_produit.py --brief ECR-017` |
| Lancer les IS | `python scripts/run_ingenieur_systeme.py --ecr ECR-017` |
| Lancer un IS spécifique | `python scripts/run_ingenieur_systeme.py --ecr ECR-017 --domain IS-6` |
| Voir les docs d'un ECR | `python scripts/run_ingenieur_systeme.py --show ECR-017` |
| Approuver un document | `python scripts/run_ingenieur_systeme.py --approve SFD-ECR017-IS6` |
| Retourner un document | `python scripts/run_ingenieur_systeme.py --return SFD-ECR017-IS6 "commentaire"` |
| Design Review | `python scripts/run_architecte_produit.py --design-review ECR-017` |
| Voir un ECR complet | `python scripts/run_architecte_produit.py --show ECR-017` |

---

## Liens

- [[Agents/Architecte Produit]] — définition et runtime prompt de l'AP
- [[Agents/Ingénieur-Agents]] · [[Agents/Ingénieur-Pipeline]] · etc. — prompts IS par domaine
- [[Milestones/Phase 8 — Cycle en V — Plan]] — processus complet
- [[Bugs/Backlog]] — état courant des ECRs

#processus #ingenierie #cycle-en-v #architecte-produit #ingenieur-systeme
