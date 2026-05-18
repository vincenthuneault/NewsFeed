"""Agent événements Montréal — RSS Radio-Canada Montréal + Voir.ca + MTL Blog.

Journaliste-Montreal : sélectionne via LLM les événements culturels montréalais.
Sources définies dans config.yaml section rss.feeds.evenements_mtl.
Référence : Lecteur de nouvelle/Agents/Journaliste-Montreal.md
"""

from __future__ import annotations

from agents.rss_generic import RSSAgent, _PROMPTS_BY_CATEGORY


class EventsMontrealAgent(RSSAgent):
    """Collecte les nouvelles et événements de la région montréalaise."""

    def __init__(self, config: dict) -> None:
        feeds = config.get("rss", {}).get("feeds", {}).get("evenements_mtl", [
            # Fallback si config absente
            {"url": "https://ici.radio-canada.ca/rss/4169", "name": "RC Montréal"},
            {"url": "https://ici.radio-canada.ca/rss/4175", "name": "RC Arts & culture"},
            {"url": "https://ici.radio-canada.ca/rss/4503", "name": "RC Grand Montréal"},
            {"url": "https://voir.ca/feed/", "name": "Voir.ca"},
            {"url": "https://www.mtlblog.com/feeds/news.rss", "name": "MTL Blog"},
        ])
        prompt = _PROMPTS_BY_CATEGORY.get("evenements_mtl", "")
        super().__init__("evenements_mtl", feeds, config, system_prompt=prompt)
        self.name = "events_montreal"
