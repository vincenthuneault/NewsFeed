"""Agent Hugging Face Daily Papers — papiers IA du jour via API publique.

Endpoint : https://huggingface.co/api/daily_papers
Retourne les papiers triés par upvotes avec résumé, mots-clés et date.
Catégorie : tech_ai — passe par le même journaliste que les autres sources IA.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

from agents.base_agent import BaseAgent
from core.logger import get_logger
from core.models import RawNewsItem

_API_URL = "https://huggingface.co/api/daily_papers"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NewsFeed/1.0)"}
_TIMEOUT = 15

_SYSTEM_PROMPT = """\
Tu es un journaliste spécialisé dans la recherche en intelligence artificielle.
Tu sélectionnes parmi les papiers de recherche du jour sur Hugging Face Papers
ceux qui ont un impact réel sur l'industrie ou des implications importantes
pour l'avenir de l'IA.

## Processus de sélection quotidien

### Étape 1 — Lecture exhaustive
Parcourir tous les papiers disponibles avant toute sélection.
Le nombre d'upvotes est un signal fort de pertinence communautaire — en tenir compte.

### Étape 2 — Veille de continuité (priorité absolue)
Si un papier fait suite à une recherche déjà couverte ce mois-ci
(même laboratoire, même thème, suite d'une série), c'est prioritaire.

### Étape 3 — Priorisation
1. Suite ou extension d'une recherche déjà couverte — priorité maximale
2. Papier de laboratoire majeur (OpenAI, Anthropic, DeepMind, Meta AI, Google, etc.)
3. Recherche avec fort engagement (upvotes élevés) ou code disponible

### Étape 4 — Règle d'or
Contextualiser avec les implications pratiques plutôt que les détails techniques.
Tu ne dis jamais "l'information est insuffisante".

## Périmètre accepté
- Nouvelles architectures ou techniques d'entraînement avec impact réel
- Agents IA, raisonnement, multimodal, vision, langage
- Recherches en sécurité IA, alignement, évaluation de modèles

## Exclure si
- Optimisation mineure sur un benchmark très spécialisé
- Papier sans résumé clair ni application prévisible

Quota : maximum 5 papiers par jour.\
"""


class HFPapersAgent(BaseAgent):
    """Collecte les papiers IA du jour depuis l'API Daily Papers de Hugging Face."""

    def __init__(self, config: dict) -> None:
        super().__init__("hf_papers", config)
        self._log = get_logger("agents.hf_papers", config.get("logging"))
        self._max_age_hours: int = config.get("rss", {}).get("max_age_hours", 48)
        self._max_items: int = config.get("app", {}).get("max_articles_per_agent", 5)

    def collect(self) -> list[RawNewsItem]:
        try:
            raw = self._fetch_papers()
        except Exception as exc:
            self._log.error(
                "Erreur API Hugging Face Papers",
                extra={"agent": self.name, "error": str(exc)},
            )
            return []

        submitted = self._load_submitted_urls()
        items = [i for i in raw if i.source_url not in submitted]

        items = self._filter_by_freshness(items, self._max_age_hours)

        if not items:
            self._log.info("Aucun papier frais disponible", extra={"agent": self.name})
            return []

        # Tri par upvotes décroissants avant sélection LLM
        items.sort(key=lambda x: x.popularity_score, reverse=True)

        selected = self._llm_select(items, _SYSTEM_PROMPT, "tech_ai", self._max_items)
        self._log.info(
            "Collecte HF Papers terminée",
            extra={"agent": self.name, "items": len(selected)},
        )
        return selected

    def _fetch_papers(self) -> list[RawNewsItem]:
        resp = requests.get(_API_URL, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        papers = resp.json()

        items: list[RawNewsItem] = []
        for entry in papers:
            paper = entry.get("paper", {})
            paper_id = paper.get("id", "")
            if not paper_id:
                continue

            title = entry.get("title") or paper.get("title", "")
            summary = paper.get("summary", "")
            ai_summary = paper.get("ai_summary", "")
            upvotes = paper.get("upvotes", 0)
            published_raw = paper.get("publishedAt") or entry.get("publishedAt", "")

            try:
                published_at = datetime.fromisoformat(
                    published_raw.replace("Z", "+00:00")
                ).astimezone(timezone.utc)
            except Exception:
                published_at = datetime.now(timezone.utc)

            description = (ai_summary or summary)[:500]

            # Métadonnées utiles pour le LLM de sélection
            authors = paper.get("authors", [])
            author_names = ", ".join(a.get("name", "") for a in authors[:3])
            keywords = paper.get("ai_keywords", [])
            keyword_str = ", ".join(keywords[:5])

            if author_names or keyword_str:
                description = description + f"\nAuteurs : {author_names}. Mots-clés : {keyword_str}."

            items.append(
                RawNewsItem(
                    title=title,
                    source_url=f"https://huggingface.co/papers/{paper_id}",
                    source_name="Hugging Face Papers",
                    category="tech_ai",
                    published_at=published_at,
                    description=description[:500],
                    raw_content=summary[:2000],
                    popularity_score=upvotes / 100,
                    metadata={"paper_id": paper_id, "upvotes": upvotes},
                )
            )

        return items
