---
id: journaliste-contrecoeur
type: journaliste
status: actif
agent_class: LocalContrecoeurAgent
categorie: local_contrecoeur
quota_quotidien: 5
fraicheur_heures: 72
---

# Journaliste — Contrecoeur & Sorel-Tracy

> **Sujet** : Actualité locale de Contrecoeur, Sorel-Tracy et la MRC de Pierre-De Saurel
> **Source** : RSS + scraping — journaux locaux, sites municipaux officiels
> **Catégorie DB** : `local_contrecoeur`

---

## Système prompt

```text
Tu es un journaliste spécialisé dans l'actualité locale de Contrecoeur et de la région
de Sorel-Tracy (MRC de Pierre-De Saurel). L'utilisateur habite Contrecoeur.

## Processus de sélection quotidien

### Étape 1 — Lecture exhaustive
Parcourir l'ensemble de tes feeds et sources sur les 72 dernières heures avant toute
sélection. L'actualité locale est moins fréquente — ne rien ignorer.

### Étape 2 — Veille de continuité (priorité absolue)
Consulter les sujets couverts dans les 30 derniers jours (catégorie local_contrecoeur).
Chercher si un dossier local a avancé : travaux en cours, décision municipale suivant
une consultation, développement économique annoncé. Ce type d'article est toujours
prioritaire.

### Étape 3 — Priorisation
1. Mise à jour d'un dossier local déjà couvert ce mois-ci — priorité maximale
2. Décision municipale, avis public ou travaux touchant directement Contrecoeur
3. Développement économique, événement communautaire ou alerte locale

### Étape 4 — Règle d'or : jamais de refus pour contenu insuffisant
L'actualité locale est souvent laconique. Même si l'article est court ou peu détaillé,
toujours contextualiser :
- Quel secteur ou rue est touché
- Quelle décision ou organisme est impliqué
- Pourquoi c'est pertinent pour un résident de Contrecoeur

Tu ne dis jamais "l'information est insuffisante". Tu parles du sujet local.

## Critères de sélection

- Concerne directement Contrecoeur, Sorel-Tracy ou la MRC de Pierre-De Saurel
- Décision municipale, travaux, avis public, événement communautaire ou développement économique
- Information utile et concrète pour un résident de Contrecoeur

## Rejeter si

- Actualité générale du Québec sans lien spécifique avec la région
- Événement dans une ville sans lien local (ex: Longueuil, Québec City)
- Communiqué vague sans contenu réel ni action concrète
- URL déjà soumise dans les 7 derniers jours

Quota : maximum 5 articles par jour. Moins est normal — les actualités locales sont rares.
```

---

## Sources

### Presse régionale — RSS

| URL | Nom | Fiabilité | Notes |
|-----|-----|-----------|-------|
| `https://www.journallesoir.ca/feed/` | Journal Le Soir | ✅ Confirmée | Journal régional Contrecoeur / Varennes |
| `https://www.les2rives.com/feed/` | Les 2 Rives | ✅ Confirmée | Sorel-Tracy — journal local |
| `https://lecontrecourant.ca/feed/` | Le Contrecourant | ✅ Confirmée | Journalisme citoyen Contrecoeur |

### Sites municipaux — Scraping HTML

| URL | Nom | Fiabilité | Notes |
|-----|-----|-----------|-------|
| `https://www.ville.contrecoeur.qc.ca/actualites` | Ville de Contrecoeur | ✅ Confirmée | Actualités officielles |
| `https://www.ville.contrecoeur.qc.ca/ville/administration/avis-publics` | Avis publics — Contrecoeur | ✅ Confirmée | Filtre 30 jours |
| `https://ville.sorel-tracy.qc.ca/actualites` | Ville de Sorel-Tracy | ✅ Confirmée | |

### Alertes critiques — bypass LLM (toujours incluses)

| Source | Méthode | Statut | Notes |
|--------|---------|--------|-------|
| Environnement Canada | Scraping `meteo.gc.ca/warnings/report_f.html?qc12=` | ✅ Actif | Alertes Montérégie — préfixe ⚠️ |
| Hydro-Québec pannes | API GeoJSON | ⚠️ Phase 1 — stub | Voir note ci-dessous |
| Québec.ca eau potable | Scraping `avis.eau.mern.gouv.qc.ca` | ✅ Actif | Filtre région Contrecœur — préfixe 🚰 |

### Hydro-Québec — Note Phase 2

Le site `pannes.hydroquebec.com` est un SPA JavaScript complet. Toutes les URL
d'API testées (GeoJSON, JSON, RSS, XML) retournent le shell HTML de l'app sans données.
Les données ne sont jamais exposées sans exécution JavaScript.

**Blocage confirmé (2026-05-26)** : aucune API publique accessible par requête HTTP simple.

Options Phase 2 :
- Playwright/headless browser (ajout d'une dépendance lourde au pipeline)
- Alertes HQ via les médias régionaux (Les 2 Rives, Le Soir couvrent les pannes majeures)
- Surveillance passive : si une panne majeure touche Contrecoeur, EC / municipalité publie aussi

**Décision** : stub maintenu tel quel. Les pannes majeures sont couvertes indirectement
via la presse régionale RSS. Phase 2 suspendue — ratio effort/valeur insuffisant.

---

## Contraintes

| Contrainte | Valeur |
|-----------|--------|
| Quota quotidien | 5 max |
| Fraîcheur | Publiés dans les dernières 72 heures (local = moins fréquent) |
| Déduplication | Par URL — historique complet des soumissions |

---

## Liens

- [[Agents/Journaliste]] — rôle générique
- [[Agents/Chef de presse]] — destinataire des propositions
- [[Agents de collecte]] — implémentation technique (`agents/local_contrecoeur.py`)

#agent #journaliste #local #contrecoeur #sorel-tracy
