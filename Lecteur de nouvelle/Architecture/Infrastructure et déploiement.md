# Infrastructure et déploiement

> Configuration serveur pour que le système tourne de façon autonome.

---

## Stack serveur

| Composant | Choix |
|-----------|-------|
| OS | Ubuntu 24.04 LTS |
| Reverse proxy | Nginx (port 80 → Gunicorn 5000) |
| WSGI | Gunicorn (4 workers, timeout 120s) |
| Process manager | systemd (2 services) |
| SSL | Non requis (accès via VPN) |

---

## Services systemd

### Flask API (`newsfeed.service`)
- Lance Gunicorn avec l'app Flask
- Restart automatique en cas de crash
- Logs via journalctl

### Cron quotidien (`newsfeed-cron.timer`)
- Exécution : **6h00 chaque jour**
- Lance le pipeline complet (orchestrateur → processeurs → feed)
- Persistant (rattrape si le serveur était éteint)

---

## Monitoring (`scripts/daily_monitor.py`)

Vérifie chaque soir :
- Le feed du jour existe
- Nombre d'items dans le feed
- Statut de chaque agent
- API responsive
- Espace disque
- Taille de la DB
- Coûts Claude (jour + mois)

Alerte par email si le feed n'a pas été généré.

---

## Endpoint `/api/health`

Retourne un JSON complet avec :
- Statut global (healthy/degraded/unhealthy)
- Détails du dernier run (durée, items, agents)
- Coûts (aujourd'hui + mois)
- Stockage (DB, images, audio, disque libre)
- Uptime

---

## Logging

| Aspect | Choix |
|--------|-------|
| Format | JSON structuré (1 ligne/entrée) |
| Librairie | `logging` stdlib + `python-json-logger` |
| Sortie | Fichier + stdout |
| Rotation | logrotate (10MB max, 7 fichiers) |

---

## Fichiers

```
deploy/
├── nginx.conf
├── gunicorn.conf.py
├── newsfeed.service        # systemd Flask
├── newsfeed-cron.service   # systemd cron job
├── newsfeed-cron.timer     # systemd timer 6h00
└── logrotate.conf
```

---

## Liens

- Retour : [[Vue d'ensemble]]
- Milestone : [[M5 — Production]]
- Sert : [[API REST]]

#architecture #infrastructure
