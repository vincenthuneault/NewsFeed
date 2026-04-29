"""Processeur d'images — télécharge, redimensionne, sauvegarde en JPEG."""

from __future__ import annotations

import hashlib
from pathlib import Path

import requests
from PIL import Image

from core.logger import get_logger
from core.models import RawNewsItem
from processors.base_processor import BaseProcessor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = PROJECT_ROOT / "static" / "images"
DEFAULTS_DIR = IMAGES_DIR / "defaults"
DEFAULT_CATEGORY = "default"

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NewsFeed/1.0)"}
_TIMEOUT = 10


class ImageExtractor(BaseProcessor):
    """Télécharge et normalise les images des nouvelles."""

    def __init__(self, config: dict) -> None:
        super().__init__("image_extractor", config)
        self._log = get_logger("processors.image_extractor", config.get("logging"))
        img = config.get("images", {})
        self._max_width: int = img.get("max_width", 720)
        self._quality: int = img.get("quality", 85)
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    def process(self, items: list) -> list:
        for item in items:
            try:
                item.image_path = self._extract(item)
            except Exception as exc:
                self._log.warning(
                    "Image échouée, fallback",
                    extra={"processor": self.name, "error": str(exc), "url": item.image_url},
                )
                item.image_path = self._default_path(item.category)
        return items

    def _extract(self, item: RawNewsItem) -> str:
        if item.image_url:
            path = self._download_and_resize(item.image_url)
            if path:
                return path

        # Fallback : og:image scraping pour les sources non-YouTube
        if item.source_url and "youtube.com" not in item.source_url:
            og_url = self._scrape_og_image(item.source_url)
            if og_url:
                path = self._download_and_resize(og_url)
                if path:
                    return path

        return self._default_path(item.category)

    def _download_and_resize(self, url: str) -> str | None:
        url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
        dest = IMAGES_DIR / f"{url_hash}.jpg"

        if dest.exists():
            return str(dest.relative_to(PROJECT_ROOT))

        resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT, stream=True)
        resp.raise_for_status()

        img = Image.open(resp.raw)
        img = img.convert("RGB")

        if img.width > self._max_width:
            ratio = self._max_width / img.width
            new_size = (self._max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        img.save(dest, "JPEG", quality=self._quality, optimize=True)
        self._log.info(
            "Image sauvegardée",
            extra={"processor": self.name, "path": str(dest), "size": f"{img.width}x{img.height}"},
        )
        return str(dest.relative_to(PROJECT_ROOT))

    def _scrape_og_image(self, url: str) -> str | None:
        try:
            from bs4 import BeautifulSoup

            resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
            soup = BeautifulSoup(resp.text, "lxml")
            tag = soup.find("meta", property="og:image")
            if tag and tag.get("content"):
                return tag["content"]
        except Exception:
            pass
        return None

    def _default_path(self, category: str) -> str:
        candidate = DEFAULTS_DIR / f"{category}.jpg"
        if candidate.exists():
            return str(candidate.relative_to(PROJECT_ROOT))
        fallback = DEFAULTS_DIR / f"{DEFAULT_CATEGORY}.jpg"
        if fallback.exists():
            return str(fallback.relative_to(PROJECT_ROOT))
        return ""
