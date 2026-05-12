# ECR-004 — Gate qualité contenu + blacklist sources

> **Statut** : 🔵 À transmettre
> **Priorité** : 🔴 Haute
> **Sévérité** : Haute — contenu inutilisable présenté à l'utilisateur (paywalls, live streams, articles tronqués)
> **Source** : [[Analyse Aftersales — Mai 2026]] · Cycle 1 (30 avril – 4 mai 2026)
> **Créé** : 2026-05-11

---

## Symptôme

Des articles avec un contenu insuffisant ou inaccessible passent le filtre et sont présentés à l'utilisateur :
- Articles derrière paywall (The Verge) → `raw_content` quasi vide
- Live streams YouTube actifs → aucune information utilisable
- Articles tronqués → résumé Claude incomplet ou sans substance

**Articles identifiés :**
| # | Article | Problème |
|---|---------|----------|
| #7 | All the evidence unveiled — Musk v. Altman | The Verge — contenu tronqué |
| #5 | Google Search queries — all time high | The Verge — contenu pas disponible |
| #3 | Grindr won the WHCD party circuit | Information tronquée |
| #2 | Elon Musk's worst enemy in court is Elon Musk | The Verge — contenu tronqué |
| #30 | Mark Carney se rend en Arménie | Article totalement incomplet |
| #10 | Supply-chain attack — Checkmarx/Bitwar | Description insuffisante |
| #1 | 🔴LIVE ARC RAIDERS — Riven Tide | Live stream — zéro information utilisable |

---

## Cause racine

Trois causes distinctes :

1. **The Verge** : paywall ou JavaScript requis → le scraper récupère un contenu minimal. Aucun gate ne vérifie la longueur ou la qualité du `raw_content` avant de passer à Claude.

2. **Live streams YouTube** : les titres contenant `🔴LIVE`, `#LIVE`, `LIVE |` indiquent un live en cours → aucune information statique disponible. Aucun filtre sur ce pattern.

3. **Absence de gate de qualité** : il n'existe pas de seuil minimum sur `raw_content` avant la génération du résumé. Claude reçoit du contenu vide et génère un résumé vague.

---

## Correction proposée

**Gate 1 — Longueur minimale du `raw_content`**
Avant la génération du résumé, vérifier que `len(raw_content) >= MIN_CONTENT_LENGTH` (valeur suggérée : 300 caractères). Si insuffisant → article exclu du feed ou marqué `low_quality`.

**Gate 2 — Blacklist de sources**
Ajouter une liste de domaines blacklistés dans `config.yaml` :
```yaml
pipeline:
  blacklisted_domains:
    - "theverge.com"       # paywall systématique
```
Les articles de ces domaines sont exclus avant même la génération du résumé. Alternative : chercher des sources de substitution (Ars Technica, 9to5Mac, The Information).

**Gate 3 — Filtre live streams YouTube**
Dans l'agent YouTube, avant de soumettre un article au pipeline, vérifier si le titre contient l'un des patterns suivants (insensible à la casse) :
- `🔴live`, `#live`, `live |`, `| live`, `[live]`
→ Exclure l'article.

---

## Cas de test à couvrir

| ID | Scénario | Résultat attendu |
|----|----------|-----------------|
| T-ECR004-01 | Article The Verge avec `raw_content` < 300 chars | Exclu du feed |
| T-ECR004-02 | Article The Verge avec contenu complet (> 300 chars) | Inclus normalement |
| T-ECR004-03 | Vidéo YouTube avec titre "🔴LIVE Gaming Stream" | Exclue par le filtre live |
| T-ECR004-04 | Vidéo YouTube avec titre "LIVE at the summit — recap" (post-live) | À définir : inclure si post-live ? |
| T-ECR004-05 | `blacklisted_domains: []` dans config | Aucun domaine blacklisté |
| T-ECR004-06 | Article court (150 chars) d'une source fiable | Exclu — qualité insuffisante |

---

## Liens

- [[Bugs/Backlog]] — statut global
- [[Analyse Aftersales — Mai 2026]] — investigation complète (section 2)
- [[Phase 8 — Cycle en V — Plan]] — processus ingénierie

#ecr #qualite-contenu #blacklist #live-stream #haute-priorite
