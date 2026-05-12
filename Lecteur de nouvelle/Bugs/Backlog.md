# Backlog — ECR & MCA

> Table de bord centrale du triage Aftersales. Mise à jour à chaque cycle d'investigation.
> Dernière mise à jour : 2026-05-11 · Source : [[Analyse Aftersales — Mai 2026]]

---

## ECR — Engineering Change Requests (code requis)

| ID | Titre | Statut | Priorité | Sévérité | Créé | Dernière activité |
|----|-------|--------|----------|----------|------|------------------|
| [[ECR/ECR-003 — Déduplication étendue 7 jours\|ECR-003]] | Déduplication étendue 7 jours (scorer.py) | 🔵 À transmettre | 🔴 Haute | Haute | 2026-05-11 | 2026-05-11 |
| [[ECR/ECR-004 — Gate qualité contenu et blacklist sources\|ECR-004]] | Gate qualité contenu + blacklist The Verge + filtre live | 🔵 À transmettre | 🔴 Haute | Haute | 2026-05-11 | 2026-05-11 |
| [[ECR/ECR-005 — Resserrer catégories vehicules_ev et evenements_mtl\|ECR-005]] | Resserrer catégories `vehicules_ev` et `evenements_mtl` | 🔵 À transmettre | 🟡 Normale | Normale | 2026-05-11 | 2026-05-11 |
| [[ECR/ECR-006 — Bug stabilité lecteur audio\|ECR-006]] | Bug stabilité lecteur audio | 🔵 À transmettre | 🟡 Normale | Normale | 2026-05-11 | 2026-05-11 |
| [[ECR/ECR-007 — Afficher Pourquoi ce contenu\|ECR-007]] | Afficher "Pourquoi ce contenu" dans l'interface | 🔵 À transmettre | 🟢 Basse | Basse | 2026-05-11 | 2026-05-11 |
| [[ECR/ECR-001 — Bouton calendrier dupliqué au re-login\|ECR-001]] | Bouton calendrier dupliqué au re-login | ✅ Corrigé | — | Normale | antérieur | antérieur |
| [[ECR/ECR-002 — App non fonctionnelle sur navigateur desktop\|ECR-002]] | App non fonctionnelle sur navigateur desktop | ✅ Corrigé | — | Normale | antérieur | antérieur |

### Statuts ECR
- `🔵 À transmettre` — confirmé par investigation, pas encore remis à l'Architecte Produit
- `🟡 En cours` — V-cycle en marche (Architecte Produit → Ingénierie)
- `✅ Corrigé` — fermé par l'ingénierie, déployé en production
- `❌ Annulé` — décision de ne pas corriger (avec justification)

---

## MCA — Mises à jour Contexte Agent (sans code)

| ID | Changement | Agent ciblé | Statut | Créé | Dernière activité |
|----|-----------|-------------|--------|------|------------------|
| [[Bugs/MCA-001\|MCA-001]] | Géographie locale → Contrecoeur / Sorel / Grand MTL | Agent Scraping (local) | 🔵 À appliquer | 2026-05-11 | 2026-05-11 |
| [[Bugs/MCA-002\|MCA-002]] | `vehicules_ev` → exclure vélos, trottinettes, énergie solaire | Chef de nouvelle / Scorer | 🔵 À appliquer | 2026-05-11 | 2026-05-11 |
| [[Bugs/MCA-003\|MCA-003]] | `musique_electro` → exclure rap/hip-hop/R&B/Bollywood | Agent RSS (musique) | 🔵 À appliquer | 2026-05-11 | 2026-05-11 |
| [[Bugs/MCA-004\|MCA-004]] | `viral_trending` → contenu nord-américain, profil 35 ans Québec | Agent YouTube / Scraping | 🔵 À appliquer | 2026-05-11 | 2026-05-11 |
| [[Bugs/MCA-005\|MCA-005]] | Scorer à 0 : sport, jeux vidéo, contenu jeunesse | Chef de nouvelle / Scorer | 🔵 À appliquer | 2026-05-11 | 2026-05-11 |

### Statuts MCA
- `🔵 À appliquer` — validé par investigation, pas encore intégré au contexte
- `✅ Appliqué` — contexte agent mis à jour, effectif au prochain cycle
- `⏸ En attente` — bloqué (dépend d'un ECR ou d'une décision)

---

## Signaux Business (à transmettre)

| Signal | Source | Date |
|--------|--------|------|
| Fort appétit pour politique américaine à fort enjeu | 11 feedbacks "Très intéressant" | 2026-05-11 |
| Intérêt pour contenu partageable (divertissement grand public) | Notes #15, #16 | 2026-05-11 |
| Électro/EDM = niche forte mais mal servie | Note #12 + MCA-003 | 2026-05-11 |

---

## Journalisation (fermés sans action)

| Date | Item | Raison |
|------|------|--------|
| 2026-05-11 | 7 labels de confirmation de catégorie | Utilisateur confirme implicitement — aucune action requise |

---

## Liens

- [[Analyse Aftersales — Mai 2026]] — investigation source de ce cycle
- [[Agents/Aftersales]] — processus de triage et d'investigation
- [[Phase 8 — Cycle en V — Plan]] — processus ingénierie pour les ECRs

#backlog #triage #ecr #mca
