# ECR-003 — Déduplication étendue 7 jours

> **Statut** : 🔵 À transmettre
> **Priorité** : 🔴 Haute
> **Sévérité** : Haute — 11% du contenu présenté est du déjà-vu (44 slots gaspillés sur 390)
> **Source** : [[Analyse Aftersales — Mai 2026]] · Cycle 1 (30 avril – 4 mai 2026)
> **Créé** : 2026-05-11

---

## Symptôme

Des articles publiés la veille (ou les jours précédents) réapparaissent dans le feed du lendemain. L'utilisateur reçoit du contenu déjà vu, réduisant la valeur perçue du feed.

**Ampleur confirmée par investigation DB (28 avril → 11 mai 2026) :**
| Fréquence | Nombre d'articles |
|-----------|-----------------|
| Présentés 1× (normal) | 303 |
| Présentés 2× (répétition) | **42** |
| Présentés 3×+ (répétition grave) | **1** (#194 "The 40 best Mother's Day gift ideas") |

**44 slots gaspillés sur 390 = 11% du contenu est du déjà-vu.**

**Exemples confirmés (feed 02/05 → 03/05) :**
- DARPA — lunar orbiter studies
- Amazon Leo — 300 satellites
- Trump nominates Schiess — Space Force
- Starcloud — orbital data center funding
- The opportunity beyond orbital data centers
- Tesla Model 3 RWD Canada
- NASA CLPS contract value increase

---

## Cause racine

**Fichier** : `processors/scorer.py`
**Fonction** : `Scorer._select_with_diversity()` — ligne 141

Le scorer sélectionne le top 30 par `final_score` **sans jamais consulter les `daily_feeds` précédents**. La fenêtre de fraîcheur est configurée à 48h (`freshness_decay_hours: 48`), ce qui laisse encore un score non-nul aux articles de la veille. Le `FeedAssembler` sauvegarde simplement ce qu'il reçoit — aucune mémoire non plus.

Le déduplicateur d'URL existant (en amont) fonctionne correctement — il élimine les doublons exacts dans le même batch. Le problème est en aval, dans la **sélection cross-journées**.

---

## Correction proposée

Dans `Scorer._select_with_diversity()` :

1. Charger l'union des `item_ids` de tous les `DailyFeed` des **7 derniers jours**
2. Exclure ces IDs de la liste de candidats avant la sélection du top 30
3. Fix estimé : ~10 lignes dans `scorer.py`

```python
# Pseudo-code de la correction
recent_feeds = session.query(DailyFeed).filter(
    DailyFeed.date >= date.today() - timedelta(days=7)
).all()
already_seen_ids = set(
    item_id for feed in recent_feeds for item_id in feed.item_ids
)
candidates = [item for item in candidates if item.id not in already_seen_ids]
```

**Paramètre à ajouter dans `config.yaml` :**
```yaml
pipeline:
  dedup_window_days: 7   # Fenêtre de déduplication cross-journées (défaut : 7)
```

---

## Cas de test à couvrir

| ID | Scénario | Résultat attendu |
|----|----------|-----------------|
| T-ECR003-01 | Article publié hier → lancé dans le pipeline aujourd'hui | Exclu du feed du jour |
| T-ECR003-02 | Article publié il y a 8 jours → lancé dans le pipeline | Inclus (hors fenêtre) |
| T-ECR003-03 | Nouvel article sur le même sujet (URL différente) | Inclus (ce n'est pas un doublon) |
| T-ECR003-04 | Pipeline sur 2 semaines consécutives | Aucun article n'apparaît 2× dans la fenêtre de 7 jours |
| T-ECR003-05 | `dedup_window_days: 0` dans config | Comportement actuel restauré (régression intentionnelle) |

---

## Liens

- [[Bugs/Backlog]] — statut global
- [[Analyse Aftersales — Mai 2026]] — investigation complète (section 1)
- [[Phase 8 — Cycle en V — Plan]] — processus ingénierie

#ecr #deduplication #scorer #haute-priorite
