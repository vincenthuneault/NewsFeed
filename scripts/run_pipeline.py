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
        # 1. Agents
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
        log.info("Orchestrateur terminé", extra={"agents_ok": agents_ok, "total": len(reports), "items": len(raw_items)})

        if not raw_items:
            log.error("Aucun item collecté — pipeline abandonné")
            return 1

        # 3. Déduplication
        from core.deduplicator import Deduplicator
        deduped = Deduplicator(config).deduplicate(raw_items)

        # 4. Scoring
        from processors.scorer import Scorer
        scored = Scorer(config).process(deduped)

        # 5. Pipeline
        from core.pipeline import Pipeline
        news_items = Pipeline(config).run(scored)

        elapsed = time.time() - t_total
        log.info(
            "Pipeline quotidien terminé",
            extra={
                "date": date.today().isoformat(),
                "items_saved": len(news_items),
                "duration_s": round(elapsed, 1),
                "agents_ok": f"{agents_ok}/{len(reports)}",
            },
        )

        print(f"[OK] {date.today()} — {len(news_items)} items en {elapsed:.0f}s ({agents_ok}/{len(reports)} agents)")
        return 0

    except Exception as exc:
        log.error("Pipeline quotidien ÉCHOUÉ", extra={"error": str(exc)})
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    dry = "--dry" in sys.argv
    sys.exit(main(dry_run=dry))
