"""Classe abstraite pour tous les agents de collecte."""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from core.models import RawNewsItem


class BaseAgent(ABC):
    """Chaque agent hérite de BaseAgent et implémente collect().

    Un agent ne remplit JAMAIS les champs du pipeline
    (summary_fr, image_path, audio_path, final_score).
    """

    def __init__(self, name: str, config: dict) -> None:
        self.name = name
        self.config = config

    @abstractmethod
    def collect(self) -> list[RawNewsItem]:
        """Retourne les nouvelles brutes de cette source."""
        ...

    def __repr__(self) -> str:
        return f"<Agent:{self.name}>"

    # ------------------------------------------------------------------
    # Helpers partagés — filtrage, déduplication, sélection LLM
    # ------------------------------------------------------------------

    def _filter_by_freshness(
        self, items: list[RawNewsItem], max_hours: int
    ) -> list[RawNewsItem]:
        """Garde uniquement les articles dans la fenêtre de fraîcheur."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_hours)
        return [i for i in items if i.published_at >= cutoff]

    def _load_submitted_urls(self) -> set[str]:
        """Retourne toutes les URLs déjà en DB — évite de re-soumettre un article connu."""
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from core.models import NewsItem

            db_url = self.config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
            engine = create_engine(db_url)
            session = sessionmaker(bind=engine)()
            urls = {url for url, in session.query(NewsItem.source_url).all()}
            session.close()
            return urls
        except Exception:
            return set()

    def _load_recent_history(self, category: str, days: int = 30) -> list[dict]:
        """Retourne les titres des articles récents de cette catégorie.

        Utilisé par _llm_select pour la veille de continuité (étape 2 du prompt journaliste).
        """
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from core.models import NewsItem

            db_url = self.config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
            engine = create_engine(db_url)
            session = sessionmaker(bind=engine)()
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            rows = (
                session.query(NewsItem.title, NewsItem.source_url)
                .filter(NewsItem.category == category)
                .filter(NewsItem.created_at >= cutoff)
                .order_by(NewsItem.created_at.desc())
                .limit(50)
                .all()
            )
            session.close()
            return [{"titre": r.title, "url": r.source_url} for r in rows]
        except Exception:
            return []

    def _llm_select(
        self,
        candidates: list[RawNewsItem],
        system_prompt: str,
        category: str,
        max_items: int = 5,
    ) -> list[RawNewsItem]:
        """Sélectionne les meilleurs articles via Claude (prompt journaliste).

        Args:
            candidates: Articles candidats pré-filtrés (fraîcheur + dédup URL).
            system_prompt: Prompt système du journaliste depuis son fichier .md.
            category: Catégorie DB pour charger l'historique de continuité.
            max_items: Quota quotidien (défaut 5).

        Returns:
            Liste d'articles sélectionnés dans l'ordre de priorité décroissante.
            En cas d'échec Claude : les premiers max_items candidats (fallback).
        """
        if not candidates:
            return []

        if not system_prompt:
            return candidates[:max_items]

        history = self._load_recent_history(category)

        articles_payload = [
            {
                "idx": i,
                "titre": c.title,
                "description": (c.description or "")[:300],
                "source": c.source_name,
                "publie_le": c.published_at.isoformat(),
            }
            for i, c in enumerate(candidates)
        ]

        history_section = ""
        if history:
            history_section = (
                "\n\nSujets déjà couverts dans les 30 derniers jours "
                "(veille de continuité — priorité absolue si suite) :\n"
                + "\n".join(f"- {h['titre']}" for h in history[:20])
            )

        user_prompt = (
            f"Voici les {len(candidates)} articles disponibles aujourd'hui :"
            f"{history_section}\n\n"
            f"{json.dumps(articles_payload, ensure_ascii=False, indent=2)}\n\n"
            f'Retourne un objet JSON : {{"selectionnes": [0, 3, 2, ...]}} — '
            f"au maximum {max_items} indices dans l'ordre de priorité décroissante. "
            f"Réponds UNIQUEMENT avec le JSON."
        )

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            model = self.config.get("claude", {}).get("model", "claude-sonnet-4-6")
            response = client.messages.create(
                model=model,
                max_tokens=200,
                temperature=0.1,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw_text = response.content[0].text.strip()
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("Aucun JSON dans la réponse")
            data = json.loads(raw_text[start:end])
            indices: list[int] = data.get("selectionnes", [])
            selected = [
                candidates[i]
                for i in indices
                if isinstance(i, int) and 0 <= i < len(candidates)
            ]
            return selected[:max_items]

        except Exception as exc:
            if hasattr(self, "_log"):
                self._log.warning(
                    "LLM select échoué — fallback ordre brut",
                    extra={"agent": self.name, "error": str(exc)},
                )
            return candidates[:max_items]
