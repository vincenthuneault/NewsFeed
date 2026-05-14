# ECR-003 — Redéfinition architecturale : Agent Journaliste et Chef de presse

> **Statut** : 🔵 À transmettre
> **Priorité** : 🔴 Haute
> **Sévérité** : Haute — 11% du contenu présenté est du déjà-vu (44 slots gaspillés sur 390) + absence de gate éditorial
> **Source** : [[Analyse Aftersales — Mai 2026]] · Cycle 1 (30 avril – 4 mai 2026)
> **Créé** : 2026-05-11
> **Révisé** : 2026-05-14 — portée élargie suite à analyse architecturale

---

## Symptôme

Des articles scrappés la veille réapparaissent dans le feed du lendemain. L'utilisateur reçoit du contenu déjà vu, réduisant la valeur perçue du feed.

**Ampleur confirmée par investigation DB (28 avril → 11 mai 2026) :**
| Fréquence | Nombre d'articles |
|-----------|-----------------|
| Présentés 1× (normal) | 303 |
| Présentés 2× (répétition) | **42** |
| Présentés 3×+ (répétition grave) | **1** (#194 "The 40 best Mother's Day gift ideas") |

**44 slots gaspillés sur 390 = 11% du contenu est du déjà-vu.**

---

## Analyse de la cause racine

### Investigation initiale (2026-05-11)

Le `Scorer` sélectionne le top 30 par `final_score` sans jamais consulter les `daily_feeds` précédents. La fenêtre de fraîcheur à 48h (`freshness_decay_hours: 48`) laisse un score non-nul aux articles de la veille, qui peuvent donc être resélectionnés le lendemain.

### Cause racine réelle (2026-05-14)

La correction par fenêtre de 7 jours dans le scorer était un **patch sur les symptômes**, pas sur la cause racine. L'investigation architecturale a révélé que le problème fondamental est l'**absence de séparation entre collecte et curation** :

1. **Pas de concept de journaliste** — les agents RSS scrappent sans sujet assigné ni quota quotidien. Ils peuvent remonter des articles de plusieurs jours.
2. **Pas de gate éditorial** — le feed est assemblé automatiquement sans qu'aucun agent ne valide "cet article est-il pertinent pour aujourd'hui?".
3. **Mémoire inexistante** — aucun agent ne sait ce qu'il a déjà proposé dans le passé.

Si l'architecture distingue "journaliste qui propose aujourd'hui" de "chef de presse qui sélectionne parmi les propositions d'aujourd'hui", les doublons cross-journées deviennent **structurellement impossibles** : on ne peut pas sélectionner un article d'hier si seuls les articles d'aujourd'hui sont candidats.

---

## Solution architecturale

Remplacer le pipeline de scraping générique par deux agents IA distincts :

### Agent Journaliste
- Sujet assigné (ex: Politique québécoise, Tech/IA, Événements MTL)
- Soumet jusqu'à 5 articles **publiés aujourd'hui** sur son sujet
- Vérifie contre son historique complet qu'il ne repropose jamais une URL déjà soumise
- Reçoit un feedback binaire (✅ / ❌) du Chef de presse après chaque journée

→ Voir [[Agents/Journaliste]] pour la description complète

### Agent Chef de presse
- Ne voit que les articles soumis **aujourd'hui** par les journalistes
- Sélectionne jusqu'à 30 articles pour le `daily_feeds` du jour
- Applique les préférences utilisateur, commentaires et feedbacks historiques
- Rejette les articles sous le seuil de qualité avec un flag binaire dans `news_items`
- Transmet le feed validé au Narrateur

→ Voir [[Agents/Chef de presse]] pour la description complète

---

## Décisions de conception

| Décision | Choix retenu | Raison |
|----------|-------------|--------|
| Déduplication cross-journalistes | ❌ Différé | Complexité vs. valeur — risque accepté en date du 2026-05-14 |
| Feedback éditorial | ✅ Binaire (pass/fail) | Simple à vérifier, base pour amélioration future |
| Quota journaliste | ≤ 5 articles/jour | Pas de minimum strict — les jours creux produisent moins |
| Nature du Chef de presse | Agent IA | Tout le système est AI — pas d'interface humaine |
| Fenêtre de 7 jours (solution initiale) | ❌ Abandonnée | Patch sur symptôme, remplacé par gate éditorial |

---

## Développements futurs hors scope

- Déduplication cross-journalistes (deux journalistes sur sujets proches)
- Système multi-agents de review (rédaction, profondeur, expertise sujet)
- Mémoire de raisonnement des journalistes
- Expertise interrogeable : le journaliste répond à des questions sur son domaine

---

## Cas de test à couvrir

| ID | Scénario | Résultat attendu |
|----|----------|-----------------|
| T-ECR003-01 | Journaliste soumet un article avec une URL déjà dans `news_items` | Article rejeté avant soumission |
| T-ECR003-02 | Chef de presse voit les articles soumis hier | Aucun — seul aujourd'hui est accessible |
| T-ECR003-03 | Journaliste A et B proposent la même URL le même jour | Un seul apparaît dans le feed (dédup pipeline existant) |
| T-ECR003-04 | Journaliste ne trouve que 2 articles un jour creux | Feed du jour contient moins de 30 articles — comportement normal |
| T-ECR003-05 | Article rejeté par le Chef de presse | Flag binaire dans `news_items`, visible au journaliste le lendemain |
| T-ECR003-06 | Pipeline sur 2 semaines consécutives | Aucun article n'apparaît 2× |

---

## Historique de la réflexion

| Date | Événement |
|------|-----------|
| 2026-05-11 | Création de l'ECR — solution proposée : fenêtre de dédup 7 jours dans le scorer |
| 2026-05-14 | Révision architecturale — session Claude Code du 2026-05-14. La conversation a établi que le pipeline est entièrement automatisé (pas de journalistes humains), que la solution 7 jours était un patch sur les symptômes, et que la vraie correction est architecturale : agents Journaliste + Chef de presse. Décisions clés documentées dans la section "Décisions de conception". |

---

## Liens

- [[Bugs/Backlog]] — statut global
- [[Analyse Aftersales — Mai 2026]] — investigation complète (section 1)
- [[Agents/Journaliste]] — description de l'agent journaliste
- [[Agents/Chef de presse]] — description de l'agent chef de presse
- [[Phase 8 — Cycle en V — Plan]] — processus ingénierie

#ecr #architecture #journaliste #chef-de-presse #haute-priorite
