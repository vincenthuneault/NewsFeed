"""Agent Ticketmaster — événements à venir à Montréal.

Interroge l'API Ticketmaster Discovery v2 avec 3 requêtes :
  1. Tous les événements Montréal (marketId=522)
  2. Musique / concerts
  3. Arts & Théâtre / humour

Déduplique par event ID Ticketmaster, construit raw_content à partir des données
structurées de l'API, puis sélectionne via LLM (journaliste Montréal événements).

Les URLs ticketmaster.com sont dans _SKIP_DOMAINS de l'ArticleFetcher :
raw_content passé ici est conservé intact dans le pipeline.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import requests

from agents.base_agent import BaseAgent
from core.logger import get_logger
from core.models import RawNewsItem

_API_BASE = "https://app.ticketmaster.com/discovery/v2/events.json"
_MARKET_ID = "522"  # Marché Montréal

_QUERIES = [
    {"label": "général",      "extra": {}},
    {"label": "musique",      "extra": {"classificationName": "music"}},
    {"label": "arts-théâtre", "extra": {"classificationName": "Arts & Theatre"}},
]

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NewsFeed/1.0; Montreal)"}

_SYSTEM_PROMPT = """Tu es un journaliste spécialisé dans les événements et la vie culturelle à Montréal.
Tu sélectionnes les événements à venir les plus intéressants pour un couple québécois adulte (30-40 ans).

## Périmètre accepté
- Concerts majeurs (artistes connus, venues importantes : Bell Centre, MTelus, Place des Arts…)
- Spectacles d'humour, théâtre, arts de la scène avec artistes reconnus
- Festivals et grands événements culturels montréalais (Osheaga, FIJM, Juste pour Rire…)
- Événements sportifs professionnels (Canadiens, CF Montréal, Alouettes)
- Premières, tournées d'adieu, événements rares ou uniques

## Refusé
- Artistes totalement inconnus du grand public
- Événements génériques récurrents sans intérêt particulier
- Événements hors de la région montréalaise

## Priorisation
1. Artiste ou production de renommée nationale ou internationale
2. Événement rare, unique, ou à venir dans moins de 3 semaines
3. Festival ou événement de grande envergure
4. Match sportif professionnel à domicile

Quota : maximum 5 événements.
"""


class TicketmasterAgent(BaseAgent):
    """Collecte les événements à venir à Montréal via l'API Ticketmaster Discovery v2."""

    def __init__(self, config: dict) -> None:
        super().__init__("ticketmaster", config)
        self._log = get_logger("agents.ticketmaster", config.get("logging"))
        tm = config.get("ticketmaster", {})
        self._max_items: int = tm.get("max_items", 5)

    def collect(self) -> list[RawNewsItem]:
        api_key = os.getenv("TICKETMASTER_API_KEY", "")
        if not api_key:
            self._log.warning("TICKETMASTER_API_KEY manquante — agent ignoré")
            return []

        submitted = self._load_submitted_urls()
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z")

        base_params = {
            "apikey": api_key,
            "marketId": _MARKET_ID,
            "countryCode": "CA",
            "preferredCountry": "ca",
            "locale": "*",
            "startDateTime": today_str,
            "size": "200",
            "sort": "date,asc",
        }

        seen_ids: set[str] = set()
        candidates: list[RawNewsItem] = []

        for query in _QUERIES:
            params = {**base_params, **query["extra"]}
            try:
                resp = requests.get(_API_BASE, params=params, headers=_HEADERS, timeout=15)
                resp.raise_for_status()
                events = resp.json().get("_embedded", {}).get("events", [])

                for event in events:
                    eid = event.get("id", "")
                    if not eid or eid in seen_ids:
                        continue
                    seen_ids.add(eid)

                    item = self._build_item(event)
                    if item and item.source_url not in submitted:
                        candidates.append(item)

            except Exception as exc:
                self._log.error(
                    f"Requête Ticketmaster '{query['label']}' échouée",
                    extra={"error": str(exc)},
                )

        self._log.info(
            "Ticketmaster — candidats collectés",
            extra={"total": len(candidates), "ids_vus": len(seen_ids)},
        )

        if not candidates:
            return []

        return self._llm_select(candidates, _SYSTEM_PROMPT, "evenements_mtl", self._max_items)

    def _build_item(self, event: dict) -> RawNewsItem | None:
        try:
            name = event.get("name", "").strip()
            url = event.get("url", "")
            if not name or not url:
                return None

            # Date de l'événement
            start = event.get("dates", {}).get("start", {})
            event_date = start.get("localDate", "")
            event_time = start.get("localTime", "")
            if event_date and event_time:
                date_str = f"{event_date} à {event_time[:5]}"
            elif event_date:
                date_str = event_date
            else:
                date_str = "Date à confirmer"

            # Lieu
            venues = event.get("_embedded", {}).get("venues", [])
            if venues:
                venue_name = venues[0].get("name", "")
                venue_city = venues[0].get("city", {}).get("name", "Montréal")
                lieu = f"{venue_name}, {venue_city}" if venue_name else venue_city
            else:
                lieu = "Montréal"

            # Artistes / attractions
            attractions = event.get("_embedded", {}).get("attractions", [])
            artistes = ", ".join(a["name"] for a in attractions[:4]) if attractions else name

            # Genre
            classifications = event.get("classifications", [])
            genre = ""
            if classifications:
                segment = classifications[0].get("segment", {}).get("name", "")
                genre_name = classifications[0].get("genre", {}).get("name", "")
                if genre_name and genre_name not in ("Undefined", "Other"):
                    genre = f"{segment} — {genre_name}"
                elif segment:
                    genre = segment

            # Prix
            price_ranges = event.get("priceRanges", [])
            prix = ""
            if price_ranges:
                pr = price_ranges[0]
                min_p = pr.get("min")
                max_p = pr.get("max")
                currency = pr.get("currency", "CAD")
                if min_p and max_p and min_p != max_p:
                    prix = f"{min_p:.0f}$ – {max_p:.0f}$ {currency}"
                elif min_p:
                    prix = f"À partir de {min_p:.0f}$ {currency}"

            lines = [
                f"Événement : {name}",
                f"Artiste(s) : {artistes}" if artistes != name else "",
                f"Date : {date_str}",
                f"Lieu : {lieu}",
                f"Catégorie : {genre}" if genre else "",
                f"Prix : {prix}" if prix else "",
                f"Billet : {url}",
            ]
            raw_content = "\n".join(line for line in lines if line)

            description = f"{artistes} — {lieu} — {date_str}"

            return RawNewsItem(
                title=name,
                source_url=url,
                source_name="Ticketmaster",
                category="evenements_mtl",
                published_at=datetime.now(timezone.utc),
                description=description,
                raw_content=raw_content,
            )

        except Exception as exc:
            self._log.debug("Événement ignoré", extra={"error": str(exc)})
            return None
