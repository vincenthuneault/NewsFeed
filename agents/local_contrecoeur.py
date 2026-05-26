"""Agent local Contrecoeur & Sorel-Tracy — scraping municipal + presse régionale + alertes.

Journaliste-Contrecoeur : sélectionne via LLM l'actualité locale pertinente.
Fraîcheur : 72h (local = moins fréquent, fenêtre plus large que les autres agents).
Référence : Lecteur de nouvelle/Agents/Journaliste-Contrecoeur.md

Sources :
  Presse régionale     — RSS : Le Soir, Les 2 Rives, Le Contrecourant
  Actualités ville     — Scraping : ville.contrecoeur.qc.ca/actualites
  Avis publics ville   — Scraping : ville.contrecoeur.qc.ca/ville/administration/avis-publics
  Alertes EC           — Scraping : meteo.gc.ca (alertes Montérégie)
  Pannes HQ            — API GeoJSON (Phase 1 — stub si inaccessible)
  Eau potable Québec   — Scraping : quebec.ca (filtre région Contrecœur)
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

from agents.base_agent import BaseAgent
from agents.rss_generic import RSSAgent
from core.logger import get_logger
from core.models import RawNewsItem

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NewsFeed/1.0; Contrecoeur)"}
_TIMEOUT = 15

_BASE_VILLE = "https://www.ville.contrecoeur.qc.ca"

_SYSTEM_PROMPT = """\
Tu es un journaliste spécialisé dans l'actualité locale de Contrecoeur et de la région
de Sorel-Tracy (MRC de Pierre-De Saurel). L'utilisateur habite Contrecoeur.

## Processus de sélection quotidien

### Étape 1 — Lecture exhaustive
Parcourir l'ensemble de tes feeds et sources sur les 72 dernières heures avant toute
sélection. L'actualité locale est moins fréquente — ne rien ignorer.

### Étape 2 — Veille de continuité (priorité absolue)
Chercher si un dossier local a avancé : travaux en cours, décision municipale suivant
une consultation, développement économique annoncé. Ce type d'article est toujours
prioritaire.

### Étape 3 — Priorisation
1. Mise à jour d'un dossier local déjà couvert ce mois-ci — priorité maximale
2. Décision municipale, avis public ou travaux touchant directement Contrecoeur
3. Développement économique, événement communautaire ou alerte locale

### Étape 4 — Règle d'or : jamais de refus pour contenu insuffisant
L'actualité locale est souvent laconique. Toujours contextualiser :
- Quel secteur ou rue est touché
- Quelle décision ou organisme est impliqué
Tu ne dis jamais "l'information est insuffisante".

## Critères de sélection
- Concerne directement Contrecoeur, Sorel-Tracy ou la MRC de Pierre-De Saurel
- Décision municipale, travaux, avis public, événement communautaire ou développement

## Rejeter si
- Actualité générale du Québec sans lien spécifique avec la région
- Événement dans une ville sans lien local (Longueuil, Québec City, etc.)
- Communiqué vague sans contenu réel ni action concrète

Quota : maximum 5 articles par jour. Moins est normal — les actualités locales sont rares.\
"""

# Mots-clés pour alertes météo (Environnement Canada)
_EC_ALERT_KEYWORDS = [
    "avertissement", "veille", "bulletin spécial", "alerte", "avis spécial",
    "verglas", "orage", "pluie abondante", "vent fort", "chaleur accablante",
    "froid extrême", "blizzard", "tempête", "grêle",
]

# Filtres région pour Québec.ca eau potable
_EAU_POTABLE_FILTER = [
    "contrecoeur", "contrecœur",
    "marguerite-d'youville", "marguerite d'youville",
    "montérégie", "pierre-de saurel", "sorel",
]

# Boîte géo Contrecœur pour pannes HQ (lat/lon ±~15 km)
_HQ_LAT_MIN, _HQ_LAT_MAX = 45.70, 45.95
_HQ_LON_MIN, _HQ_LON_MAX = -73.45, -73.10
_HQ_SEUIL_CLIENTS_CRITIQUE = 500


class LocalContrecoeurAgent(BaseAgent):
    """Collecte les nouvelles locales de Contrecoeur et Sorel-Tracy.

    Catégories produites :
      local_contrecoeur — nouvelles municipales et presse régionale (sélection LLM)
      local_alerte      — alertes critiques EC / HQ / eau potable (toujours incluses)
    """

    def __init__(self, config: dict) -> None:
        super().__init__("local_contrecoeur", config)
        self._log = get_logger("agents.local_contrecoeur", config.get("logging"))

        local_cfg = config.get("local_contrecoeur", {})
        self._max_age_hours: int = local_cfg.get("max_age_hours", 72)
        self._max_items: int = config.get("app", {}).get("max_articles_per_agent", 5)

        rss_feeds = local_cfg.get("rss_feeds") or [
            {"url": "https://www.journallesoir.ca/feed/", "name": "Journal Le Soir"},
            {"url": "https://www.les2rives.com/feed/", "name": "Les 2 Rives"},
            {"url": "https://lecontrecourant.ca/feed/", "name": "Le Contrecourant"},
        ]
        self._rss_agent = RSSAgent("local_contrecoeur", rss_feeds, config)

        self._scrape_sources = local_cfg.get("scrape_sources") or [
            {
                "url": f"{_BASE_VILLE}/actualites",
                "name": "Ville de Contrecoeur",
                "base_url": _BASE_VILLE,
            },
            {
                "url": "https://ville.sorel-tracy.qc.ca/actualites",
                "name": "Ville de Sorel-Tracy",
                "base_url": "https://ville.sorel-tracy.qc.ca",
            },
        ]

    # ------------------------------------------------------------------ #
    # Point d'entrée principal                                            #
    # ------------------------------------------------------------------ #

    def collect(self) -> list[RawNewsItem]:
        submitted = self._load_submitted_urls()

        # --- 1. Sources nouvelles municipales (sélection LLM) ---
        municipal: list[RawNewsItem] = []

        try:
            municipal.extend(self._rss_agent.collect())
        except Exception as exc:
            self._log.warning("RSS local échoué", extra={"error": str(exc)})

        for source in self._scrape_sources:
            try:
                scraped = self._scrape_actualites(source)
                municipal.extend(scraped)
            except Exception as exc:
                self._log.warning(
                    "Scraping actualités échoué",
                    extra={"source": source["name"], "error": str(exc)},
                )

        try:
            municipal.extend(self._scrape_avis_publics())
        except Exception as exc:
            self._log.warning("Scraping avis publics échoué", extra={"error": str(exc)})

        # Déduplication + fraîcheur pour les nouvelles municipales
        municipal = [i for i in municipal if i.source_url not in submitted]
        municipal = self._filter_by_freshness(municipal, self._max_age_hours)

        selected = self._llm_select(municipal, _SYSTEM_PROMPT, "local_contrecoeur", self._max_items)
        self._log.info(
            "Nouvelles municipales",
            extra={"candidats": len(municipal), "sélectionnés": len(selected)},
        )

        # --- 2. Alertes critiques (toujours incluses, pas de LLM) ---
        alerts: list[RawNewsItem] = []

        for collector, label in [
            (self._collect_environnement_canada, "Environnement Canada"),
            (self._collect_hydro_quebec, "Hydro-Québec"),
            (self._collect_quebec_eau_potable, "Québec.ca eau potable"),
        ]:
            try:
                found = collector()
                new = [a for a in found if a.source_url not in submitted]
                alerts.extend(new)
                self._log.info(label, extra={"alertes": len(new)})
            except Exception as exc:
                self._log.warning(f"Collecte {label} échouée", extra={"error": str(exc)})

        return selected + alerts

    # ------------------------------------------------------------------ #
    # Scraping actualités ville                                           #
    # ------------------------------------------------------------------ #

    def _scrape_actualites(self, source: dict) -> list[RawNewsItem]:
        resp = requests.get(source["url"], headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        items: list[RawNewsItem] = []
        seen_urls: set[str] = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Liens vers des articles d'actualités (format /actualites/<catégorie>/<slug>)
            if "/actualites/" not in href or href.rstrip("/") == "/actualites":
                continue

            full_url = href if href.startswith("http") else source["base_url"] + href
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            raw_text = a.get_text(separator=" ", strip=True)
            if not raw_text or len(raw_text) < 5:
                continue

            # Nettoyer la date collée au titre (ex: "Titre25 mai 2026Catégorie")
            title = re.sub(r"\s*\d{1,2}\s+\w+\s+\d{4}.*$", "", raw_text).strip()
            if not title or len(title) < 5:
                title = raw_text[:120]

            items.append(RawNewsItem(
                title=title,
                source_url=full_url,
                source_name=source["name"],
                category="local_contrecoeur",
                published_at=datetime.now(timezone.utc),
                description=raw_text[:300],
            ))

            if len(items) >= 20:
                break

        return items

    # ------------------------------------------------------------------ #
    # Scraping avis publics ville                                         #
    # ------------------------------------------------------------------ #

    def _scrape_avis_publics(self) -> list[RawNewsItem]:
        url = f"{_BASE_VILLE}/ville/administration/avis-publics"
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        items: list[RawNewsItem] = []
        seen_urls: set[str] = set()
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        for a in soup.find_all("a", href=True):
            href = a["href"]
            is_pdf = ".pdf" in href.lower()
            is_avis = "/actualites/avis-publics" in href

            if not (is_pdf or is_avis):
                continue

            full_url = href if href.startswith("http") else _BASE_VILLE + href
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            raw_text = a.get_text(separator=" ", strip=True)
            if not raw_text or len(raw_text) < 5:
                continue

            # Extraire et valider la date (filtrer les vieux avis)
            date_match = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", raw_text)
            pub_date = datetime.now(timezone.utc)
            if date_match:
                parsed = _parse_french_date(date_match.group(0))
                if parsed:
                    pub_date = parsed
                    if pub_date < cutoff:
                        continue  # Avis trop ancien

            title = re.sub(r"^\d{1,2}\s+\w+\s+\d{4}\s*", "", raw_text).strip()
            if not title or len(title) < 5:
                title = raw_text[:120]

            items.append(RawNewsItem(
                title=title,
                source_url=full_url,
                source_name="Ville de Contrecoeur — Avis publics",
                category="local_contrecoeur",
                published_at=pub_date,
                description=f"Avis public{'  (PDF)' if is_pdf else ''}. {title}",
            ))

        return items

    # ------------------------------------------------------------------ #
    # Alertes Environnement Canada — Montérégie                          #
    # ------------------------------------------------------------------ #

    def _collect_environnement_canada(self) -> list[RawNewsItem]:
        url = "https://meteo.gc.ca/warnings/report_f.html?qc12="
        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        items: list[RawNewsItem] = []
        now = datetime.now(timezone.utc)

        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            cell_text = " ".join(c.get_text(strip=True) for c in cells).lower()
            if not any(kw in cell_text for kw in _EC_ALERT_KEYWORDS):
                continue

            link = row.find("a", href=True)
            alert_url = url
            if link:
                href = link["href"]
                alert_url = href if href.startswith("http") else "https://meteo.gc.ca" + href

            title_text = cells[0].get_text(strip=True)
            detail_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            title = title_text or detail_text[:80] or "Alerte météo — Montérégie"

            items.append(RawNewsItem(
                title=f"⚠️ {title}",
                source_url=alert_url,
                source_name="Environnement Canada — Montérégie",
                category="local_alerte",
                published_at=now,
                description=detail_text[:400] if detail_text else None,
            ))

        return items

    # ------------------------------------------------------------------ #
    # Pannes Hydro-Québec — Zone Contrecœur (Phase 1)                    #
    # ------------------------------------------------------------------ #

    def _collect_hydro_quebec(self) -> list[RawNewsItem]:
        _API_URLS = [
            "https://pannes.hydroquebec.com/pannes/donnees/geojson",
        ]
        web_url = "https://pannes.hydroquebec.com/pannes/en-cours"
        now = datetime.now(timezone.utc)

        for api_url in _API_URLS:
            try:
                resp = requests.get(api_url, headers=_HEADERS, timeout=12)
                if resp.status_code == 200 and resp.content:
                    return self._parse_hq_geojson(resp.json(), web_url, now)
            except Exception:
                continue

        self._log.debug(
            "Hydro-Québec — API GeoJSON inaccessible (site JS-only). "
            "Phase 2 : scraping headless requis."
        )
        return []

    def _parse_hq_geojson(self, data: dict | list, web_url: str, now: datetime) -> list[RawNewsItem]:
        features = data.get("features", []) if isinstance(data, dict) else data
        items: list[RawNewsItem] = []

        for feature in features:
            if not isinstance(feature, dict):
                continue
            props = feature.get("properties", {})
            coords = (feature.get("geometry") or {}).get("coordinates", [])

            if len(coords) >= 2:
                lon, lat = coords[0], coords[1]
                if not (_HQ_LAT_MIN <= lat <= _HQ_LAT_MAX and _HQ_LON_MIN <= lon <= _HQ_LON_MAX):
                    continue

            nb_clients = int(props.get("nb_clients_touches", props.get("affectedCustomers", 0)) or 0)
            if not nb_clients:
                continue

            municipalite = props.get("municipalite", props.get("municipality", "Contrecœur"))
            statut = props.get("statut", props.get("status", ""))
            cause = props.get("cause", "")
            title = f"⚡ Panne Hydro-Québec — {municipalite} ({nb_clients} clients)"
            description = " ".join(filter(None, [
                f"Statut : {statut}" if statut else "",
                f"Cause : {cause}" if cause else "",
            ])) or None

            # Clé stable par municipalité pour la déduplication
            panne_url = f"{web_url}#{municipalite.lower().replace(' ', '-')}"

            items.append(RawNewsItem(
                title=title,
                source_url=panne_url,
                source_name="Hydro-Québec — Pannes",
                category="local_alerte",
                published_at=now,
                description=description,
            ))

        return items

    # ------------------------------------------------------------------ #
    # Avis eau potable Québec.ca — filtre région Contrecœur              #
    # ------------------------------------------------------------------ #

    def _collect_quebec_eau_potable(self) -> list[RawNewsItem]:
        url = (
            "https://www.quebec.ca/agriculture-environnement-et-ressources-naturelles"
            "/eau-potable/qualite-eau-potable/avis-ebullition-avis-non-consommation"
        )
        resp = requests.get(url, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        items: list[RawNewsItem] = []
        seen_urls: set[str] = set()
        now = datetime.now(timezone.utc)

        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                texts = [c.get_text(strip=True) for c in cells]
                row_text = " ".join(texts).lower()

                if not any(t in row_text for t in _EAU_POTABLE_FILTER):
                    continue

                municipalite = texts[0] if texts else "Contrecœur"
                avis_type = texts[1] if len(texts) > 1 else "Avis"
                pub_date_str = texts[2] if len(texts) > 2 else None

                title = f"🚰 {avis_type} — {municipalite}"
                link = row.find("a", href=True)
                avis_url = url
                if link:
                    href = link["href"]
                    avis_url = href if href.startswith("http") else "https://www.quebec.ca" + href

                if avis_url in seen_urls:
                    continue
                seen_urls.add(avis_url)

                items.append(RawNewsItem(
                    title=title,
                    source_url=avis_url,
                    source_name="Québec.ca — Avis eau potable",
                    category="local_alerte",
                    published_at=now,
                    description=f"{avis_type} en vigueur pour {municipalite}."
                                + (f" Date : {pub_date_str}." if pub_date_str else ""),
                ))

        return items


# ------------------------------------------------------------------ #
# Utilitaire — parsing date française                                #
# ------------------------------------------------------------------ #

_MOIS = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
}


def _parse_french_date(text: str) -> datetime | None:
    m = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", text.lower())
    if not m:
        return None
    day, month_str, year = int(m.group(1)), m.group(2), int(m.group(3))
    month = _MOIS.get(month_str)
    if not month:
        return None
    try:
        return datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError:
        return None
