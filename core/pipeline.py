"""Pipeline séquentiel : RawNewsItem → gate → résumé → DB → sélection éditoriale → audio → ready."""

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
from processors.article_fetcher import ArticleFetcher
from processors.content_gate import ContentGate
from processors.image_extractor import ImageExtractor
from processors.summarizer import Summarizer
from processors.tts_generator import TTSGenerator


class Pipeline:
    """Enchaîne les processeurs et persiste les résultats en DB.

    Ordre d'exécution :
    1. ArticleFetcher    — enrichit raw_content avec le texte complet de l'article
    2. ContentGate       — rejette les articles techniquement inutilisables
    3. Summarizer        — génère summary_fr pour tous les candidats restants
    ✦  SAVE proposed     — tous les candidats résumés → news_items (pipeline_status="proposed")
    4. ChefDeNouvelles   — sélection éditoriale + ordonnancement (≤ max_feed_items)
    ✦  UPDATE statuses   — selected → "published", rejected → "rejected_chef" + editorial_note
    ✦  CREATE DailyFeed  — status="generating", item_ids dans l'ordre éditorial
    5. ImageExtractor    — uniquement pour les articles sélectionnés
    6. TTSGenerator      — article par article, commit immédiat après chaque audio
    ✦  UPDATE DailyFeed  — status="ready"
    """

    def __init__(self, config: dict) -> None:
        self._config = config
        self._log = get_logger("core.pipeline", config.get("logging"))
        self._article_fetcher = ArticleFetcher(config)
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

        # 1. Fetch contenu complet
        items = self._article_fetcher.process(raw_items)

        # 2. Gate technique
        items = self._content_gate.process(items)
        self._log.info("Gate technique terminée", extra={"restants": len(items)})

        if not items:
            self._log.error("Gate technique a tout filtré — pipeline abandonné")
            return []

        # 3. Summarisation — tous les candidats
        items = self._summarizer.process(items)
        self._log.info("Résumés générés", extra={"items": len(items)})

        # --- Ouverture de la session DB — reste ouverte jusqu'à la fin ---
        session = get_session(self._session_factory)
        try:
            # ✦ SAVE — tous les candidats résumés (pipeline_status="proposed")
            db_map = self._save_proposed(items, session)
            session.commit()
            self._log.info("Candidats sauvegardés en DB", extra={"items": len(db_map)})

            # 4. Chef de nouvelles
            selected_raw, rejected_notes = self._chef.select(items)
            self._log.info(
                "Chef de nouvelles terminé",
                extra={"sélectionnés": len(selected_raw), "rejetés": len(rejected_notes)},
            )

            if not selected_raw:
                self._log.error("Chef de nouvelles n'a sélectionné aucun article")
                return []

            # ✦ UPDATE statuses + CREATE DailyFeed (status="generating")
            published_db = self._apply_chef_decisions(selected_raw, rejected_notes, db_map, session)
            session.commit()

            # 5. Image extraction — sur les sélectionnés uniquement
            selected_raw = self._image_extractor.process(selected_raw)
            for raw in selected_raw:
                db_item = db_map.get(raw.source_url)
                if db_item and raw.image_path:
                    db_item.image_path = raw.image_path
                    db_item.updated_at = datetime.now(timezone.utc)
            session.commit()
            self._log.info("Images extraites", extra={"items": len(selected_raw)})

            # 6. TTS — article par article, commit immédiat après chaque audio
            for raw in selected_raw:
                self._tts.process_one(raw)
                db_item = db_map.get(raw.source_url)
                if db_item and raw.audio_path:
                    db_item.audio_path = raw.audio_path
                    db_item.updated_at = datetime.now(timezone.utc)
                    session.commit()

            self._log.info("Audio généré", extra={"items": len(selected_raw)})

            # ✦ DailyFeed → ready
            today = date.today().isoformat()
            feed = session.query(DailyFeed).filter_by(date=today).first()
            if feed:
                feed.status = "ready"
                feed.updated_at = datetime.now(timezone.utc)
                session.commit()

            session.expunge_all()
            self._log.info("Pipeline terminé", extra={"publiés": len(published_db)})
            return published_db

        except Exception as exc:
            session.rollback()
            self._log.error("Erreur pipeline DB", extra={"error": str(exc)})
            raise
        finally:
            session.close()

    def _save_proposed(
        self, items: list[RawNewsItem], session
    ) -> dict[str, NewsItem]:
        """Insère ou met à jour tous les candidats résumés. Retourne {source_url: NewsItem}."""
        db_map: dict[str, NewsItem] = {}

        for raw in items:
            existing = session.query(NewsItem).filter_by(source_url=raw.source_url).first()
            if existing:
                if raw.summary_fr:
                    existing.summary_fr = raw.summary_fr
                if raw.raw_content:
                    existing.raw_content = raw.raw_content
                existing.pipeline_status = "proposed"
                existing.updated_at = datetime.now(timezone.utc)
                db_map[raw.source_url] = existing
            else:
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
                    final_score=raw.final_score,
                    pipeline_status="proposed",
                )
                session.add(item)
                session.flush()
                db_map[raw.source_url] = item

        return db_map

    def _apply_chef_decisions(
        self,
        selected_raw: list[RawNewsItem],
        rejected_notes: dict[str, str],
        db_map: dict[str, NewsItem],
        session,
    ) -> list[NewsItem]:
        """Met à jour les statuts post-Chef et crée le DailyFeed (status='generating')."""
        selected_urls = {raw.source_url for raw in selected_raw}
        now = datetime.now(timezone.utc)

        # Marquer les sélectionnés
        published: list[NewsItem] = []
        for raw in selected_raw:
            db_item = db_map.get(raw.source_url)
            if db_item:
                db_item.pipeline_status = "published"
                db_item.updated_at = now
                published.append(db_item)

        # Marquer les rejetés
        for url, db_item in db_map.items():
            if url not in selected_urls:
                db_item.pipeline_status = "rejected_chef"
                note = rejected_notes.get(url)
                if note:
                    db_item.editorial_note = note
                db_item.updated_at = now

        # Créer ou mettre à jour le DailyFeed
        today = date.today().isoformat()
        item_ids = [item.id for item in published if item.id]
        feed = session.query(DailyFeed).filter_by(date=today).first()
        if feed:
            feed.item_count = len(item_ids)
            feed.item_ids = json.dumps(item_ids)
            feed.status = "generating"
            feed.updated_at = now
        else:
            session.add(DailyFeed(
                date=today,
                status="generating",
                item_count=len(item_ids),
                item_ids=json.dumps(item_ids),
            ))

        return published
