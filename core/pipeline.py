"""Pipeline séquentiel : RawNewsItem → gate → résumé → DB → sélection éditoriale → audio → ready."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

from core.logger import get_logger
from core.models import (
    DailyFeed,
    NewsItem,
    PipelineCheckpoint,
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

    Ordre d'exécution et checkpoints :
    1. ArticleFetcher    — enrichit raw_content avec le texte complet de l'article
    2. ContentGate       — rejette les articles techniquement inutilisables
    3. Summarizer        — génère summary_fr pour tous les candidats restants
    ✦  _save_proposed    — tous les candidats résumés → news_items (pipeline_status="proposed")
    ✦  checkpoint("journalists")
    4. ChefDeNouvelles   — lit TOUS les "proposed" du jour depuis DB, sélection éditoriale
    ✦  _apply_chef_decisions — "published" / "rejected_chef" + DailyFeed "generating"
    ✦  checkpoint("chef")
    5. ImageExtractor    — uniquement pour les articles sélectionnés
    6. TTSGenerator      — article par article, commit immédiat après chaque audio
    ✦  DailyFeed "ready" + checkpoint("tts")
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

    # ------------------------------------------------------------------ #
    # Point d'entrée principal                                            #
    # ------------------------------------------------------------------ #

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

        session = get_session(self._session_factory)
        try:
            # Sauvegarder tous les candidats résumés en DB
            self._save_proposed(items, session)
            session.commit()
            self._checkpoint("journalists", session, {"articles": len(items)})

            # Chef lit TOUS les proposés du jour — couvre les relances partielles
            all_proposed = self._load_proposed_today(session)

            return self._run_from_chef(all_proposed, session)

        except Exception as exc:
            session.rollback()
            self._log.error("Erreur pipeline", extra={"error": str(exc)})
            raise
        finally:
            session.close()

    # ------------------------------------------------------------------ #
    # Points de reprise (appelés par run_recovery.py)                     #
    # ------------------------------------------------------------------ #

    def resume_from_chef(self, today: str) -> list[NewsItem]:
        """Reprend depuis le Chef de nouvelles — charge les proposés depuis la DB."""
        self._log.info("Pipeline — reprise depuis Chef", extra={"date": today})
        session = get_session(self._session_factory)
        try:
            all_proposed = self._load_proposed_today(session, today)
            if not all_proposed:
                self._log.error("Resume Chef — aucun article proposé en DB pour aujourd'hui")
                return []
            self._log.info("Articles proposés chargés", extra={"count": len(all_proposed)})
            return self._run_from_chef(all_proposed, session, today)
        except Exception as exc:
            session.rollback()
            self._log.error("Erreur resume_from_chef", extra={"error": str(exc)})
            raise
        finally:
            session.close()

    def resume_from_tts(self, today: str) -> list[NewsItem]:
        """Reprend depuis le TTS — charge les publiés depuis le DailyFeed."""
        self._log.info("Pipeline — reprise depuis TTS", extra={"date": today})
        session = get_session(self._session_factory)
        try:
            feed = session.query(DailyFeed).filter_by(date=today).first()
            if not feed or not feed.item_ids:
                self._log.error("Resume TTS — DailyFeed introuvable pour aujourd'hui")
                return []
            item_ids = json.loads(feed.item_ids)
            published = session.query(NewsItem).filter(NewsItem.id.in_(item_ids)).all()
            self._log.info("Articles publiés chargés", extra={"count": len(published)})
            return self._run_tts_phase(published, feed, session, today)
        except Exception as exc:
            session.rollback()
            self._log.error("Erreur resume_from_tts", extra={"error": str(exc)})
            raise
        finally:
            session.close()

    # ------------------------------------------------------------------ #
    # Phases internes partagées                                           #
    # ------------------------------------------------------------------ #

    def _run_from_chef(
        self,
        all_proposed: list[NewsItem],
        session,
        today: str | None = None,
    ) -> list[NewsItem]:
        """Chef → Images → TTS. Travaille sur des NewsItem depuis la DB."""
        today = today or date.today().isoformat()

        selected, rejected_notes = self._chef.select(all_proposed)
        self._log.info(
            "Chef de nouvelles terminé",
            extra={"sélectionnés": len(selected), "rejetés": len(rejected_notes)},
        )

        if not selected:
            self._log.error("Chef de nouvelles n'a sélectionné aucun article")
            return []

        published = self._apply_chef_decisions(selected, rejected_notes, all_proposed, session, today)
        session.commit()
        self._checkpoint("chef", session, {"sélectionnés": len(published)})

        feed = session.query(DailyFeed).filter_by(date=today).first()
        return self._run_tts_phase(published, feed, session, today)

    def _run_tts_phase(
        self,
        published: list[NewsItem],
        feed: DailyFeed | None,
        session,
        today: str,
    ) -> list[NewsItem]:
        """Images → TTS article par article → DailyFeed ready."""

        # Images sur les articles qui n'en ont pas encore
        for item in published:
            if not item.image_path:
                self._image_extractor.process([item])
                if item.image_path:
                    item.updated_at = datetime.now(timezone.utc)
        session.commit()
        self._log.info("Images extraites", extra={"items": len(published)})

        # TTS — commit immédiat après chaque article
        for item in published:
            if not item.audio_path:
                self._tts.process_one(item)
                if item.audio_path:
                    item.updated_at = datetime.now(timezone.utc)
                    session.commit()
        self._log.info("Audio généré", extra={"items": len(published)})

        # DailyFeed → ready
        if feed:
            feed.status = "ready"
            feed.updated_at = datetime.now(timezone.utc)
            session.commit()

        audio_count = sum(1 for i in published if i.audio_path)
        self._checkpoint("tts", session, {"audio": audio_count, "total": len(published)})
        self._log.info("Pipeline terminé", extra={"publiés": len(published), "audio": audio_count})

        session.expunge_all()
        return published

    # ------------------------------------------------------------------ #
    # Helpers DB                                                          #
    # ------------------------------------------------------------------ #

    def _save_proposed(self, items: list[RawNewsItem], session) -> None:
        """Insère ou met à jour tous les candidats résumés (pipeline_status='proposed')."""
        for raw in items:
            existing = session.query(NewsItem).filter_by(source_url=raw.source_url).first()
            if existing:
                if raw.summary_fr:
                    existing.summary_fr = raw.summary_fr
                if raw.raw_content:
                    existing.raw_content = raw.raw_content
                existing.pipeline_status = "proposed"
                existing.updated_at = datetime.now(timezone.utc)
            else:
                session.add(NewsItem(
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
                ))
        session.flush()

    def _load_proposed_today(self, session, today: str | None = None) -> list[NewsItem]:
        """Charge tous les news_items proposés pour aujourd'hui depuis la DB.

        Utilise une plage datetime UTC couvrant toute la journée locale (America/Montreal)
        pour éviter les décalages UTC/EDT qui cassent func.date() après 20h EDT.
        """
        from datetime import timedelta
        from zoneinfo import ZoneInfo

        today_str = today or date.today().isoformat()
        today_date = date.fromisoformat(today_str)
        tz = ZoneInfo("America/Montreal")
        start_local = datetime(today_date.year, today_date.month, today_date.day, tzinfo=tz)
        start_utc = start_local.astimezone(timezone.utc)
        end_utc = start_utc + timedelta(days=1)

        return (
            session.query(NewsItem)
            .filter(
                NewsItem.pipeline_status == "proposed",
                NewsItem.created_at >= start_utc,
                NewsItem.created_at < end_utc,
            )
            .all()
        )

    def _apply_chef_decisions(
        self,
        selected: list,
        rejected_notes: dict[str, str],
        all_proposed: list[NewsItem],
        session,
        today: str,
    ) -> list[NewsItem]:
        """Met à jour les statuts post-Chef et crée le DailyFeed (status='generating')."""
        selected_urls = {item.source_url for item in selected}
        now = datetime.now(timezone.utc)

        published: list[NewsItem] = []
        for item in all_proposed:
            if item.source_url in selected_urls:
                item.pipeline_status = "published"
                item.updated_at = now
                published.append(item)
            else:
                item.pipeline_status = "rejected_chef"
                note = rejected_notes.get(item.source_url)
                if note:
                    item.editorial_note = note
                item.updated_at = now

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

    def _checkpoint(self, step: str, session, details: dict | None = None) -> None:
        """Enregistre la complétion d'une étape dans pipeline_checkpoints."""
        from zoneinfo import ZoneInfo
        run_date = datetime.now(ZoneInfo("America/Montreal")).date().isoformat()
        session.add(PipelineCheckpoint(
            run_date=run_date,
            step=step,
            checked_in_at=datetime.now(timezone.utc),
            details=json.dumps(details, ensure_ascii=False) if details else None,
        ))
        session.commit()
        self._log.info("Checkpoint enregistré", extra={"step": step, **(details or {})})
