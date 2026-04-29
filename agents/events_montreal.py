"""Agent événements Montréal — RSS Radio-Canada Montréal + arts & culture."""

from __future__ import annotations

from agents.rss_generic import RSSAgent

_MONTREAL_FEEDS = [
    {"url": "https://ici.radio-canada.ca/rss/4169", "name": "RC Montréal"},
    {"url": "https://ici.radio-canada.ca/rss/4175", "name": "RC Arts & culture"},
    {"url": "https://ici.radio-canada.ca/rss/4503", "name": "RC Grand Montréal"},
]


class EventsMontrealAgent(RSSAgent):
    """Collecte les nouvelles et événements de la région montréalaise."""

    def __init__(self, config: dict) -> None:
        super().__init__("evenements_mtl", _MONTREAL_FEEDS, config)
        self.name = "events_montreal"
