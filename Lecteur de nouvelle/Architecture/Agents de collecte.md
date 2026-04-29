# Agents de collecte

> Chaque agent est responsable d'une source de données. Tous produisent des objets [[Modèle de données|RawNewsItem]].

---

## Principe

- Chaque agent hérite de `BaseAgent` (classe abstraite)
- Un agent ne remplit **jamais** les champs du pipeline (summary, image_path, audio_path, score)
- Chaque agent gère ses erreurs sans crasher les autres
- L'[[Pipeline de traitement|orchestrateur]] les lance en parallèle

---

## Liste des agents

### YouTube
| Agent | Source | Catégorie | Auth | Milestone |
|-------|--------|-----------|------|-----------|
| `youtube_subs.py` | Mes abonnements | `youtube_subs` | OAuth 2.0 | [[M1 — Vertical slice\|M1]] |
| `youtube_trending.py` | Tendances YouTube | `youtube_trending` | Clé API | [[M2 — Multi-agents\|M2]] |

### RSS (agent générique réutilisé)
| Config | Source | Catégorie | Milestone |
|--------|--------|-----------|-----------|
| `rss_tech_ai` | Feeds tech/IA | `tech_ai` | [[M2 — Multi-agents\|M2]] |
| `rss_politique_ca` | Feeds politique Canada | `politique_ca` | [[M2 — Multi-agents\|M2]] |
| `rss_politique_qc` | Feeds politique Québec | `politique_qc` | [[M2 — Multi-agents\|M2]] |
| `rss_vehicules` | Feeds VE/autonomes | `vehicules_ev` | [[M2 — Multi-agents\|M2]] |
| `rss_spatial` | Feeds espace | `spatial` | [[M2 — Multi-agents\|M2]] |

### Agents spécialisés
| Agent | Source | Catégorie | Milestone |
|-------|--------|-----------|-----------|
| `events_montreal.py` | Scraping événements | `evenements_mtl` | [[M3 — Feedback\|M3]] |
| `local_contrecoeur.py` | Avis municipaux | `local_contrecoeur` / `local_alerte` | [[M3 — Feedback\|M3]] |
| `viral_trending.py` | Google Trends + YT Shorts | `viral` | [[M3 — Feedback\|M3]] |

---

## Interface BaseAgent

```python
class BaseAgent(ABC):
    @abstractmethod
    def collect(self) -> list[RawNewsItem]:
        """Retourne les nouvelles brutes de cette source."""
        pass
```

Chaque agent reçoit sa section de config depuis `config.yaml`.

---

## Fichiers

```
agents/
├── base_agent.py           # Classe abstraite
├── youtube_subs.py          # M1
├── youtube_trending.py      # M2
├── rss_generic.py           # M2 (réutilisé pour 5+ feeds)
├── events_montreal.py       # M3
├── local_contrecoeur.py     # M3
└── viral_trending.py        # M3
```

---

## Liens

- Retour : [[Vue d'ensemble]]
- Produit des : [[Modèle de données|RawNewsItem]]
- Lancé par : [[Pipeline de traitement|Orchestrateur]]
- Testé dans : [[Tests et qualité]]

#architecture #agents
