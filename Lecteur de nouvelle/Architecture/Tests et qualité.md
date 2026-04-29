# Tests et qualité

> Chaque composant a des tests. Chaque gate valide TOUT. La suite de régression complète roule à chaque gate.

---

## Philosophie

1. **Chaque milestone a un POC** — preuve tangible avant le code final
2. **Chaque composant a des tests** — unitaires, intégration et smoke
3. **Chaque gate valide TOUT** — régression complète, pas juste les nouveaux tests
4. **Tout est observable** — logs structurés, métriques, rapport de santé
5. **Les erreurs sont attendues** — chaque agent gère ses erreurs sans crasher les autres

> **Règle d'or** : Rien n'avance tant que ce qui est derrière ne fonctionne pas encore.

---

## Framework

| Aspect | Choix |
|--------|-------|
| Framework | pytest |
| Async | pytest-asyncio |
| Couverture | pytest-cov (objectif > 80%) |
| Mocks | `unittest.mock` (stdlib) |
| DB de test | SQLite en mémoire |

---

## Types de tests

### Unitaires (`tests/unit/`)
Tests isolés, pas de réseau ni de DB réelle. Utilisent des mocks pour les APIs externes (YouTube, Claude, Edge TTS).

### Intégration (`tests/integration/`)
Tests avec DB réelle (SQLite), mocks réseau. Vérifient les connexions entre composants.

### Smoke (`tests/smoke/`)
Tests end-to-end légers. Vérifient que "ça tourne" : le pipeline produit un feed, le frontend charge, l'audio est lisible.

### Régression (`tests/regression/`)
Lance TOUT. Rejoue les POC de chaque milestone. Génère un rapport complet.

---

## Convention de nommage

```
test_{milestone}_{composant}_{comportement}

Exemples :
test_m1_youtube_agent_selects_top_3_by_views
test_m2_orchestrator_continues_if_agent_fails
test_m3_feedback_liked_source_gets_boost
```

---

## Commandes

```bash
pytest                              # Tout
pytest tests/unit/                  # Unitaires
pytest tests/integration/           # Intégration
pytest --cov=. --cov-report=html    # Avec couverture
python scripts/run_regression.py    # Régression complète
```

---

## Structure des fichiers

```
tests/
├── conftest.py          # Fixtures : db_session, mock APIs, sample data
├── unit/
│   ├── test_base_agent.py
│   ├── test_scorer.py
│   ├── test_summarizer.py
│   ├── test_tts.py
│   ├── test_models.py
│   └── test_config.py
├── integration/
│   ├── test_youtube_agent.py
│   ├── test_rss_agent.py
│   ├── test_pipeline.py
│   ├── test_api_feed.py
│   └── test_api_feedback.py
├── smoke/
│   ├── test_full_pipeline.py
│   └── test_frontend_loads.py
└── regression/
    └── run_all.py
```

---

## Liens

- Retour : [[Vue d'ensemble]]
- Teste : [[Agents de collecte]], [[Pipeline de traitement]], [[API REST]], [[Frontend mobile]]

#architecture #tests
