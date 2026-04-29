# M0 — Setup + validation environnement

> Prouver que toutes les briques de base fonctionnent : APIs accessibles, DB créée, dépendances installées.

---

## Tâches

- [ ] 0.1 — Setup Google Cloud + YouTube API + OAuth → `secrets/youtube_oauth.json`
- [ ] 0.2 — Setup Anthropic API → `secrets/.env`
- [ ] 0.3 — Install dépendances serveur → `scripts/setup.sh`
- [ ] 0.4 — Créer le schéma DB → `backend/models.py` + migration
- [ ] 0.5 — Structure du projet → tous les dossiers + fichiers de base
- [ ] 0.6 — Config initiale → `config.yaml` avec valeurs par défaut
- [ ] 0.7 — Logger structuré → `core/logger.py`

---

## POC M0 : `scripts/poc_m0_apis.py`

Un script qui valide toutes les connexions :
- YouTube Data API (50 subscriptions listées)
- YouTube OAuth (token refresh)
- Claude API (résumé test)
- Edge TTS (fichier audio test)
- SQLite DB (tables créées, CRUD OK)
- Config (chargé depuis YAML)
- Logger (entrée JSON structurée)

Résultat attendu : **7/7 checks passed**

---

## Tests

```
tests/unit/test_config.py   — Config charge, valeurs par défaut, validation
tests/unit/test_models.py   — Modèles DB : CRUD sur chaque table
tests/unit/test_logger.py   — Format JSON correct, rotation
```

---

## Gate 0 — Critères

- [ ] POC script : 7/7 checks passent
- [ ] `pytest tests/unit/test_config.py tests/unit/test_models.py` : 100%
- [ ] Aucune erreur dans les logs
- [ ] `config.yaml` documenté et complet

---

## Liens

- Précédent : —
- Suivant : [[M1 — Vertical slice]]
- Retour : [[Vue d'ensemble]]

#milestone #m0
