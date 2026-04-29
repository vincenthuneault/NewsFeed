"""Processeur d'assemblage — crée ou met à jour le DailyFeed en DB."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

from core.logger import get_logger
from core.models import DailyFeed, NewsItem, get_session, init_db
from processors.base_processor import BaseProcessor


class FeedAssembler(BaseProcessor):
    """Crée l'entrée DailyFeed pour aujourd'hui à partir de NewsItems sauvegardés."""

    def __init__(self, config: dict) -> None:
        super().__init__("feed_assembler", config)
        self._log = get_logger("processors.feed_assembler", config.get("logging"))
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import create_engine
        from core.models import Base

        db_url = config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)
        self._session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def process(self, items: list) -> list:
        """Prend une liste de NewsItem et crée/met à jour le DailyFeed du jour."""
        if not items:
            return items

        today = date.today().isoformat()
        item_ids = [item.id for item in items if hasattr(item, "id") and item.id]

        session = get_session(self._session_factory)
        try:
            feed = session.query(DailyFeed).filter_by(date=today).first()
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
            session.commit()
            self._log.info(
                "DailyFeed assemblé",
                extra={"date": today, "items": len(item_ids)},
            )
        except Exception as exc:
            session.rollback()
            self._log.error("Erreur assemblage", extra={"error": str(exc)})
        finally:
            session.close()

        return items
