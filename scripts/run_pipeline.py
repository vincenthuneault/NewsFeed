#!/usr/bin/env python3
"""Pipeline quotidien — lancé par systemd à 6h00.

Usage :
    python scripts/run_pipeline.py          # run complet
    python scripts/run_pipeline.py --dry    # vérifie la config seulement
"""

from __future__ import annotations

import sys
import time
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main(dry_run: bool = False) -> int:
    from core.config import load_config
    from core.logger import get_logger

    config = load_config()
    log = get_logger("cron.pipeline", config.get("logging"))

    log.info("Pipeline quotidien démarré", extra={"date": date.today().isoformat(), "dry_run": dry_run})

    if dry_run:
        log.info("Dry run — arrêt avant collecte")
        return 0

    t_total = time.time()

    try:
        # 1. Agents — collecte parallèle
        from agents.youtube_subs import YouTubeSubsAgent
        from agents.youtube_trending import YouTubeTrendingAgent
        from agents.viral_trending import ViralTrendingAgent
        from agents.events_montreal import EventsMontrealAgent
        from agents.local_contrecoeur import LocalContrecoeurAgent
        from agents.rss_generic import RSSAgent

        agents = [
            YouTubeSubsAgent(config),
            YouTubeTrendingAgent(config),
            ViralTrendingAgent(config),
            EventsMontrealAgent(config),
            LocalContrecoeurAgent(config),
            *RSSAgent.from_config(config),
        ]

        # 2. Orchestrateur
        from core.orchestrator import Orchestrator
        orchestrator = Orchestrator(agents, config)
        raw_items, reports = orchestrator.run()

        agents_ok = sum(1 for r in reports if r.status == "success")
        log.info("Orchestrateur terminé", extra={
            "agents_ok": agents_ok,
            "total": len(reports),
            "items": len(raw_items),
        })

        if not raw_items:
            log.error("Aucun item collecté — pipeline abandonné")
            return 1

        # 3. Agrégation — la déduplication est distribuée aux agents (chaque journaliste
        #    vérifie son historique DB et applique son filtre de fraîcheur)
        deduped = raw_items
        log.info("Agrégation agents terminée", extra={"items": len(deduped)})

        # 4. Pipeline : gate → résumés → Chef de nouvelles → image → TTS → DB
        from core.pipeline import Pipeline
        news_items = Pipeline(config).run(deduped)

        elapsed = time.time() - t_total
        log.info(
            "Pipeline quotidien terminé",
            extra={
                "date": date.today().isoformat(),
                "items_publiés": len(news_items),
                "duration_s": round(elapsed, 1),
                "agents_ok": f"{agents_ok}/{len(reports)}",
            },
        )

        print(f"[OK] {date.today()} — {len(news_items)} items en {elapsed:.0f}s ({agents_ok}/{len(reports)} agents)")

        # 5. Agent Aftersales — analyse des signaux utilisateur post-publication
        try:
            from agents.aftersales_agent import AftersalesAgent
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from core.models import Base

            db_url = config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
            engine = create_engine(db_url)
            Base.metadata.create_all(engine)
            af_session = sessionmaker(bind=engine)()
            AftersalesAgent(config).run(af_session)
            af_session.close()
        except Exception as exc:
            # L'Aftersales est non-bloquant — le pipeline est déjà terminé
            log.warning("Agent Aftersales échoué (non bloquant)", extra={"error": str(exc)})

        return 0

    except Exception as exc:
        log.error("Pipeline quotidien ÉCHOUÉ", extra={"error": str(exc)})
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    dry = "--dry" in sys.argv
    sys.exit(main(dry_run=dry))
