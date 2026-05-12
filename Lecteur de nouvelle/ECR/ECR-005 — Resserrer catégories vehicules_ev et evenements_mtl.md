# ECR-005 — Resserrer catégories `vehicules_ev` et `evenements_mtl`

> **Statut** : 🔵 À transmettre
> **Priorité** : 🟡 Normale
> **Sévérité** : Normale — mauvaise catégorisation dégrade la pertinence du feed
> **Source** : [[Analyse Aftersales — Mai 2026]] · Cycle 1 (30 avril – 4 mai 2026)
> **Créé** : 2026-05-11

---

## Symptôme

Des articles atterrissent dans des catégories qui ne correspondent pas à leur contenu, réduisant la pertinence du feed et la confiance de l'utilisateur dans le système de catégorisation.

**Articles mal catégorisés identifiés :**
| # | Article | Catégorie actuelle | Problème |
|---|---------|-------------------|----------|
| #40 | Electric bikes — best at every price level | `vehicules_ev` | Vélos ≠ voitures/camions électriques |
| #35 | Solar farm — cattle under moving panels | `vehicules_ev` | Énergie solaire ≠ véhicules |
| #17 | Piste cyclable rue Hochelaga | `evenements_mtl` | Infrastructure ≠ spectacles/sorties |
| #6 | Œuvres de Luc Plamondon aux enchères | `politique_qc` | Culture/art hors scope |
| #22 | Spirit Airlines shuts down — jet fuel prices | non précisé | Mal routé |

**Clarification explicite de l'utilisateur (note #17) :**
> `evenements_mtl` = spectacles, théâtre, humour, événements spéciaux, popup, DJ, fêtes. **Pas de politique, pas d'infrastructure.**

---

## Cause racine

Les prompts de classification utilisés par le système (probablement dans les agents ou le scorer) ne définissent pas assez précisément les périmètres de chaque catégorie. Les frontières floues permettent à des contenus hors scope d'être acceptés.

---

## Correction proposée

**Resserrer les définitions de catégorie dans les prompts de classification :**

**`vehicules_ev` — nouvelle définition :**
> Voitures, camions, SUV, fourgonnettes, véhicules autonomes, électriques ou hybrides. Actualités de constructeurs (Tesla, GM, Stellantis, BYD…). **Exclure explicitement** : vélos, trottinettes, panneaux solaires, éoliennes, énergie renouvelable sans lien direct avec un véhicule.

**`evenements_mtl` — nouvelle définition :**
> Spectacles, concerts, festivals, théâtre, humour, sorties culturelles, événements popup, DJ sets, marchés spéciaux sur l'île de Montréal et rive sud immédiate. **Exclure explicitement** : politique municipale, infrastructure (pistes cyclables, travaux), transport.

---

## Cas de test à couvrir

| ID | Scénario | Résultat attendu |
|----|----------|-----------------|
| T-ECR005-01 | Article "meilleur vélo électrique 2026" | Exclu de `vehicules_ev` |
| T-ECR005-02 | Article "Tesla Model Y — nouvelle version" | Inclus dans `vehicules_ev` |
| T-ECR005-03 | Article "piste cyclable Hochelaga fermée" | Exclu de `evenements_mtl` |
| T-ECR005-04 | Article "Festival Jazz Montréal — programmation" | Inclus dans `evenements_mtl` |
| T-ECR005-05 | Article "ferme solaire en Ontario" | Exclu de `vehicules_ev` |

---

## Liens

- [[Bugs/Backlog]] — statut global
- [[Analyse Aftersales — Mai 2026]] — investigation complète (section 4)
- [[Bugs/MCA-002]] — mise à jour contexte complémentaire (sans code)

#ecr #categorisation #vehicules-ev #evenements-mtl #normale-priorite
