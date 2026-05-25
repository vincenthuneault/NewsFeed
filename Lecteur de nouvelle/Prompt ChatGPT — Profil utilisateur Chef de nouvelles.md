# Prompt ChatGPT — Génération du profil utilisateur pour le Chef de nouvelles

> Copier-coller ce prompt dans ChatGPT, avec le fichier `Chef de nouvelles.md` en pièce jointe.

---

## Prompt

Je travaille sur un projet appelé **Lecteur de nouvelle** : un fil d'information personnalisé, entièrement automatisé, généré quotidiennement par des agents IA.

Le système fonctionne comme une salle de nouvelles autonome :
- Des **Journalistes IA** collectent des articles chaque jour selon leur sujet assigné (YouTube, RSS, scraping)
- Un **Chef de nouvelles IA** — dont tu trouveras la définition complète dans le fichier joint — évalue la qualité de chaque article, sélectionne les meilleurs, et détermine l'ordre de diffusion
- Un **Narrateur IA** produit ensuite un résumé audio en français (voix canadienne-française)
- L'utilisateur consomme le fil sur une interface mobile style "shorts"

Le Chef de nouvelles est piloté par un **prompt** qui contient entre autres un **profil utilisateur** — une synthèse de ses préférences éditoriales, qui lui permet de classer et filtrer les articles de façon personnalisée. C'est ce profil que je te demande de générer.

---

### Ce que je sais de l'utilisateur

Ces données proviennent d'une analyse de 53 feedbacks réels (commentaires et réactions) sur les 13 premiers jours d'utilisation du système (30 avril – 11 mai 2026).

**Profil démographique**
- Homme, ~35 ans, francophone, basé au Québec (Contrecoeur / Sorel-Tracy / Grand Montréal)

**Sujets d'intérêt fort** (commentaires enthousiastes, likes "Très intéressant")
- Politique américaine à fort enjeu : procès, personnalités controversées (Musk vs Altman, James Comey), décisions à impact
- Tech & IA : actualité produit, recherche, droit autour de l'IA (Taylor Swift et droits IA)
- Espace & exploration spatiale
- Politique canadienne et québécoise (avec nuance — voir géographie ci-dessous)
- Véhicules électriques : voitures, camions, SUV, autonomes — **pas** vélos ni énergie solaire
- Musique électronique : électro, EDM, techno, house, trance
- Contenu grand public partageable (films, trailers, culture pop nord-américaine — usage social avec son entourage)

**Sujets à exclure** (commentaires négatifs explicites)
- Sport (hockey, etc.)
- Jeux vidéo et esports
- Contenu jeunesse / éducatif
- Bollywood, K-pop et tendances hors Amérique du Nord
- Vélos électriques, trottinettes, énergie solaire / éolienne
- Politique municipale hors Montréal (Ottawa, Toronto, Québec ville, autres provinces)
- Contenu sans information concrète (articles vides ou teasers)

**Préférences géographiques**
- Local accepté : Contrecoeur, Sorel-Tracy, Grand Montréal (île + rive sud immédiate)
- National : Canada et Québec — avec intérêt surtout si enjeu politique national ou économique
- International : États-Unis prioritaire, puis reste du monde si enjeu fort

**Ton et profondeur attendus**
- Journalisme factuel — chiffres, faits concrets, événements réels
- Pas d'opinion éditoriale, pas de contenu "réflexif" sans substance
- Articles qui informent, pas qui teasent
- Profondeur suffisante pour comprendre l'essentiel sans aller lire la source

**Format**
- Abonnements YouTube (contenu de chaînes suivies) avant les sources RSS génériques
- Contenu francophone préféré mais anglophone accepté si le sujet est fort
- Pas de live streams, pas de contenu éphémère sans valeur archivable

---

### Ce que je te demande

En t'appuyant sur la définition du Chef de nouvelles (fichier joint) et les données ci-dessus, génère la **section "Profil de l'utilisateur"** telle qu'elle apparaîtrait dans le prompt du Chef de nouvelles.

Ce profil doit :
1. Être rédigé à la deuxième personne, comme si tu t'adressais directement au Chef de nouvelles ("Tu sais que l'utilisateur…", "L'utilisateur préfère…")
2. Être structuré, concis et directement exploitable par un agent IA pour classer et filtrer des articles
3. Couvrir toutes les dimensions définies dans la section "Profil utilisateur" du fichier joint
4. Intégrer les nuances — par exemple, la politique québécoise est d'intérêt mais la politique municipale hors Montréal ne l'est pas
5. Se terminer par une ligne résumant le **fil directeur éditorial** — la phrase qui capture l'essence de cet utilisateur en une seule idée

---

#prompt #chatgpt #profil-utilisateur #chef-de-nouvelles
