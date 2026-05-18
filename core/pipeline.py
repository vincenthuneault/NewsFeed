"""Pipeline séquentiel : RawNewsItem → gate → résumé → sélection éditoriale → image → audio → DB."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

from core.logger import get_logger
from core.models import (
    DailyFeed,
    NewsItem,
    RawNewsItem,
    get_session,
    init_db,
)
from processors.content_gate import ContentGate
from processors.image_extractor import ImageExtractor
from processors.summarizer import Summarizer
from processors.tts_generator import TTSGenerator


class Pipeline:
    """Enchaîne les processeurs et persiste les résultats en DB.

    Ordre d'exécution :
    1. ContentGate  — rejette les articles techniquement inutilisables
    2. Summarizer   — génère summary_fr pour tous les candidats restants
    3. ChefDeNouvelles — sélection éditoriale + ordonnancement (≤ max_feed_items)
    4. ImageExtractor  — uniquement pour les articles sélectionnés
    5. TTSGenerator    — uniquement pour les articles sélectionnés
    6. _save_to_db     — persiste tout en DB, crée DailyFeed avec l'ordre éditorial
    """

    def __init__(self, config: dict) -> None:
        self._config = config
        self._log = get_logger("core.pipeline", config.get("logging"))
        self._content_gate = ContentGate(config)
        self._summarizer = Summarizer(config)
        self._image_extractor = ImageExtractor(config)
        self._tts = TTSGenerator(config)

        from agents.chef_de_nouvelles import ChefDeNouvelles
        self._chef = ChefDeNouvelles(config)

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from core.models import Base

        db_url = config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)
        self._session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def run(self, raw_items: list[RawNewsItem]) -> list[NewsItem]:
        """Traite une liste de RawNewsItem et retourne les NewsItem publiés dans le fil."""
        if not raw_items:
            self._log.warning("Pipeline lancé avec liste vide")
            return []

        self._log.info("Pipeline démarré", extra={"candidats": len(raw_items)})

        # 1. Gate technique — exclure articles inutilisables
        items = self._content_gate.process(raw_items)
        self._log.info("Gate technique terminée", extra={"restants": len(items)})

        if not items:
            self._log.error("Gate technique a tout filtré — pipeline abandonné")
            return []

        # 2. Summarisation — tous les candidats
        items = self._summarizer.process(items)
        self._log.info("Résumés générés", extra={"items": len(items)})

        # 3. Chef de nouvelles — sélection éditoriale + ordonnancement
        selected, rejected_notes = self._chef.select(items)
        self._log.info(
            "Chef de nouvelles terminé",
            extra={"sélectionnés": len(selected), "rejetés": len(rejected_notes)},
        )

        if not selected:
            self._log.error("Chef de nouvelles n'a sélectionné aucun article")
            return []

        # 4. Image — uniquement sur les sélectionnés
        selected = self._image_extractor.process(selected)
        self._log.info("Images extraites", extra={"items": len(selected)})

        # 5. TTS — uniquement sur les sélectionnés
        selected = self._tts.process(selected)
        self._log.info("Audio généré", extra={"items": len(selected)})

        # 6. Sauvegarde DB
        news_items = self._save_to_db(selected, rejected_notes, items)
        self._log.info("Pipeline terminé", extra={"publiés": len(news_items)})
        return news_items

    def _save_to_db(
        self,
        selected: list[RawNewsItem],
        rejected_notes: dict[str, str],
        all_candidates: list[RawNewsItem],
    ) -> list[NewsItem]:
        """Persiste tous les articles en DB et crée le DailyFeed.

        - selected : articles retenus par le Chef, avec image/audio, dans l'ordre éditorial
        - rejected_notes : {source_url → editorial_note} pour les articles rejetés
        - all_candidates : tous les candidats post-summarisation (pour sauvegarder les rejetés)
        """
        session = get_session(self._session_factory)
        published: list[NewsItem] = []

        try:
            # Sauvegarder les articles sélectionnés (avec image + audio)
            selected_urls = {item.source_url for item in selected}
            for raw in selected:
                news_item = self._upsert_item(session, raw, editorial_note=None)
                if news_item:
                    published.append(news_item)

            # Sauvegarder les articles rejetés (sans image/audio, avec editorial_note)
            for raw in all_candidates:
                if raw.source_url in selected_urls:
                    continue  # Déjà sauvegardé ci-dessus
                note = rejected_notes.get(raw.source_url)
                if note:
                    self._upsert_item(session, raw, editorial_note=note)

            session.commit()

            # Créer le DailyFeed dans l'ordre éditorial du Chef de nouvelles
            self._create_daily_feed(session, published)
            session.commit()
            session.expunge_all()

        except Exception as exc:
            session.rollback()
            self._log.error("Erreur sauvegarde DB", extra={"error": str(exc)})
            raise
        finally:
            session.close()

        return published

    def _upsert_item(
        self, session, raw: RawNewsItem, editorial_note: str | None
    ) -> NewsItem | None:
        """Insère ou met à jour un NewsItem. Retourne l'instance si elle doit figurer dans le DailyFeed."""
        existing = (
            session.query(NewsItem).filter_by(source_url=raw.source_url).first()
        )
        if existing:
            # Mettre à jour les champs pipeline si l'item existait déjà
            if raw.summary_fr:
                existing.summary_fr = raw.summary_fr
            if raw.image_path:
                existing.image_path = raw.image_path
            if raw.audio_path:
                existing.audio_path = raw.audio_path
            if raw.final_score:
                existing.final_score = raw.final_score
            if editorial_note is not None:
                existing.editorial_note = editorial_note
            existing.updated_at = datetime.now(timezone.utc)
            # Inclure dans le DailyFeed uniquement si l'article a été créé aujourd'hui
            # Évite de recycler un article de la veille dans le fil d'aujourd'hui
            return existing if existing.created_at.date() == date.today() else None

        item = NewsItem(
            title=raw.title,
            source_url=raw.source_url,
            source_name=raw.source_name,
            category=raw.category,
            published_at=raw.published_at,
            description=raw.description,
            image_url=raw.image_url,
            video_url=raw.video_url,
            video_type=raw.video_type,
            raw_content=raw.raw_content,
            popularity_score=raw.popularity_score,
            summary_fr=raw.summary_fr,
            image_path=raw.image_path,
            audio_path=raw.audio_path,
            final_score=raw.final_score,
            editorial_note=editorial_note,
        )
        session.add(item)
        session.flush()  # Obtenir l'ID immédiatement
        return item

    def _create_daily_feed(self, session, items: list[NewsItem]) -> None:
        """Crée ou met à jour le DailyFeed avec les IDs dans l'ordre éditorial."""
        today = date.today().isoformat()
        feed = session.query(DailyFeed).filter_by(date=today).first()
        item_ids = [item.id for item in items if item.id]

        if feed:
            feed.item_count = len(item_ids)
            feed.item_ids = json.dumps(item_ids)
            feed.status = "ready"
            feed.updated_at = datetime.now(timezone.utc)
        else:
            session.add(
                DailyFeed(
                    date=today,
                    status="ready",
                    item_count=len(item_ids),
                    item_ids=json.dumps(item_ids),
                )
            )
