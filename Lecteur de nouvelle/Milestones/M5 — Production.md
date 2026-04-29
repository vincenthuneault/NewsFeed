# M5 — Production + monitoring continu

> Le système tourne tout seul chaque jour sans intervention. Monitoring, alertes, logs rotatifs, robustesse.

---

## Tâches

- [ ] 5.1 — Config Nginx → `deploy/nginx.conf`
- [ ] 5.2 — Gunicorn multi-worker → `deploy/gunicorn.conf.py`
- [ ] 5.3 — Systemd service (Flask) → `deploy/newsfeed.service`
- [ ] 5.4 — Systemd timer (cron 6h00) → `deploy/newsfeed-cron.timer`
- [ ] 5.5 — Log rotation → `deploy/logrotate.conf`
- [ ] 5.6 — Endpoint `/api/health` complet
- [ ] 5.7 — Script monitoring quotidien → `scripts/daily_monitor.py`
- [ ] 5.8 — Notification par email si échec (optionnel)

---

## POC M5 : 7 jours sans intervention

Le cron tourne à 6h00, le monitoring vérifie chaque soir.
Critère de succès : **7/7 jours avec feed généré automatiquement**, max 1 warning non-bloquant.

---

## Gate 5 — Critères

- [ ] 7 jours consécutifs avec feed auto
- [ ] `pytest tests/` : 100% (régression complète M0→M4)
- [ ] `/api/health` retourne un rapport correct
- [ ] Logs rotatifs (aucun > 10MB)
- [ ] Serveur redémarre proprement après reboot
- [ ] Coûts mensuels < $10
- [ ] Aucune intervention manuelle pendant la semaine test

---

## Liens

- Précédent : [[M4 — Frontend complet]]
- Suivant : Projet terminé !
- Retour : [[Vue d'ensemble]]
- Composant : [[Infrastructure et déploiement]]

#milestone #m5
