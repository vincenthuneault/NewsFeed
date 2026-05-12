# ECR-006 — Bug stabilité lecteur audio

> **Statut** : 🔵 À transmettre
> **Priorité** : 🟡 Normale
> **Sévérité** : Normale — UX dégradée, lecture audio nécessite plusieurs tentatives
> **Source** : [[Analyse Aftersales — Mai 2026]] · Cycle 1 (30 avril – 4 mai 2026)
> **Créé** : 2026-05-11

---

## Symptôme

Sur certains articles, le lecteur audio nécessite plusieurs tentatives avant de lire l'article en entier.

**Article confirmé :**
| # | Article | Note utilisateur |
|---|---------|-----------------|
| #8 | The new Razr Ultra — best-looking phone | "bug lecteur audio : pris 3 tentatives avant lecture complète" |

---

## Cause racine

Inconnue — investigation requise. Hypothèses à valider :
1. **Longueur du fichier audio** : les fichiers TTS longs (.mp3) dépassent un timeout de chargement côté frontend
2. **Format ou path audio** : le champ `audio_path` contient un chemin invalide ou relatif selon le contexte de déploiement
3. **Timeout réseau** : le fichier audio n'est pas encore généré au moment où le frontend tente de le charger (race condition entre pipeline et affichage)
4. **Cache service worker** : le service worker sert une version stale du fichier audio (pattern similaire à ECR-001)

---

## Investigation requise

**Données à collecter :**
- Logs d'erreur frontend au moment de la tentative de lecture échouée
- Valeur de `audio_path` dans `news_items` pour l'article #8
- Taille du fichier MP3 correspondant
- Timing entre `updated_at` de l'article et l'heure de première tentative de lecture

**À ajouter en urgence** : log d'erreur côté frontend pour capturer les échecs de lecture avec contexte (article_id, timestamp, erreur HTTP/JS, durée fichier).

---

## Correction proposée

**Étape 1 — Logging (immédiat, avant le fix)**
Ajouter dans `ui.js` un handler `onerror` sur l'élément `<audio>` :
```js
audioElement.onerror = (e) => {
  postBugReport(`Audio load failed: ${e.target.error?.code}`, {
    article_id: currentArticleId,
    audio_src: e.target.src,
    timestamp: new Date().toISOString()
  });
};
```

**Étape 2 — Fix selon cause identifiée**
À définir après analyse des logs. Pistes probables :
- Ajouter un retry automatique (max 3×, délai exponentiel)
- Vérifier que `audio_path` est un chemin absolu servi correctement par Nginx
- Ajouter un indicateur "audio en cours de génération" si le fichier n'est pas encore prêt

---

## Cas de test à couvrir

| ID | Scénario | Résultat attendu |
|----|----------|-----------------|
| T-ECR006-01 | Lecture normale d'un article court | Lecture immédiate, pas d'erreur |
| T-ECR006-02 | Lecture d'un article avec long fichier audio (>3 min) | Lecture complète sans interruption |
| T-ECR006-03 | `audio_path` invalide en DB | Message d'erreur clair, bug report automatique |
| T-ECR006-04 | Connexion lente (throttling réseau) | Retry automatique ou indicateur de chargement |

---

## Liens

- [[Bugs/Backlog]] — statut global
- [[Analyse Aftersales — Mai 2026]] — investigation complète (section 6)
- [[Phase 8 — Cycle en V — Plan]] — processus ingénierie

#ecr #audio #lecteur #ux #normale-priorite
