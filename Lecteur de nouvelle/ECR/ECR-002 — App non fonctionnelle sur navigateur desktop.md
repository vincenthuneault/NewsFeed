# ECR-002 — App non fonctionnelle sur navigateur desktop

> **Statut** : Sous investigation  
> **Sévérité** : Moyen — mobile fonctionnel, desktop non  
> **Découvert** : 2026-04-29  
> **Plateforme touchée** : Navigateur desktop (Chrome, Firefox, Edge)  
> **Plateforme OK** : Android (PWA via VPN)

---

## Symptômes observés

L'application fonctionne correctement sur Android (PWA installée, connexion VPN).  
Sur navigateur desktop, l'app est non fonctionnelle — comportement exact à préciser lors du prochain test.

---

## Causes probables (par ordre de vraisemblance)

### 1. Certificat SSL mkcert non installé sur le desktop ← PROBABLE

Le certificat SSL est auto-signé par mkcert. Sur Android, le CA root (`rootCA.crt`) a été installé manuellement dans les paramètres de sécurité. Cette étape **n'a pas été faite sur le desktop**.

Sans ce certificat, Chrome/Firefox affiche une erreur SSL et refuse de charger l'app, ou charge en HTTP (sans service worker, sans PWA).

**Vérification :** Ouvrir `https://10.8.0.8` sur le desktop — y a-t-il un avertissement SSL ("Votre connexion n'est pas privée") ?

### 2. Ancien service worker avec JS en cache

Le navigateur desktop a visité le site depuis M1. Le service worker v1/v2 peut encore servir d'anciennes versions de `app.js` incompatibles avec le code actuel.

**Vérification :** Ouvrir les DevTools → Application → Service Workers — quelle version est active ?

### 3. Erreur JS runtime silencieuse

Une exception dans un module ES peut faire échouer silencieusement le chargement sans message visible.

**Vérification :** DevTools → Console — y a-t-il des erreurs rouges ?

---

## Procédure de diagnostic

1. Ouvrir `https://10.8.0.8` sur le desktop
2. Regarder si une erreur SSL s'affiche → si oui, cause #1
3. Si la page charge : ouvrir DevTools (F12) → onglet Console → noter les erreurs
4. DevTools → Application → Service Workers → voir la version active et vider si nécessaire

---

## Correction selon la cause

### Cause #1 — Installer le certificat CA sur desktop

**Windows :**
1. Télécharger `https://10.8.0.8/static/rootCA.crt`
2. Double-cliquer → "Installer le certificat"
3. Choisir "Ordinateur local" → "Placer tous les certificats dans le magasin suivant"
4. Sélectionner "Autorités de certification racines de confiance" → Terminer
5. Redémarrer Chrome

**macOS :**
1. Télécharger `https://10.8.0.8/static/rootCA.crt`
2. Double-cliquer → s'ouvre dans Trousseaux
3. Double-cliquer sur le certificat → "Se fier" → "Toujours approuver"

**Linux (Chrome) :**
```bash
certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n "NewsFeed mkcert" -i rootCA.crt
```

### Cause #2 — Vider le cache service worker sur desktop

Dans Chrome : `chrome://settings/privacy` → "Effacer les données de navigation"  
→ cocher "Images et fichiers en cache" + "Données de sites" → "Effacer les données"

Ou via DevTools → Application → Storage → "Clear site data"

### Cause #3 — Erreur JS

À diagnostiquer via la console DevTools avant de corriger.

---

## Point de vigilence pour les tests futurs

> ⚠️ **À couvrir dans les tests de déploiement**

| ID | Scénario | Résultat attendu |
|----|----------|-----------------|
| T-DEPLOY-01 | Accès desktop Chrome sans cert CA | Page SSL warning visible (comportement attendu) |
| T-DEPLOY-02 | Accès desktop après install cert CA | Login fonctionnel, feed chargé |
| T-DEPLOY-03 | Accès desktop après clear site data | Nouveau SW installé, app fonctionnelle |
| T-DEPLOY-04 | Vérification cross-platform | Mobile ET desktop fonctionnels avant gate |

### Règle générale

> Toute gate de milestone doit être validée sur **au moins deux plateformes** (mobile + desktop) avant d'être marquée complète.

---

## Liens

- [[ECR-001 — Bouton calendrier dupliqué au re-login]]
- [[M4 — Frontend complet]]
- [[M5 — Production]]
- [[Infrastructure et déploiement]]

#ecr #bug #desktop #ssl #deploiement
