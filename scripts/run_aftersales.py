#!/usr/bin/env python3
"""Pipeline Aftersales — lancé par systemd à 22h00 ou manuellement.

Analyse les commentaires, feedbacks et rapports de bugs reçus depuis le
dernier cycle. Produit des ECR, MCA ou journalisations selon la conclusion.

Usage :
    python scripts/run_aftersales.py          # run complet
    python scripts/run_aftersales.py --dry    # affiche les signaux sans les traiter
    python scripts/run_aftersales.py --since "2026-05-01"  # depuis une date précise
"""

from __future__ import annotations

import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main(dry_run: bool = False, since: str | None = None) -> int:
    from core.config import load_config
    from core.logger import get_logger

    config = load_config()
    log = get_logger("cron.aftersales", config.get("logging"))

    log.info("Aftersales démarré", extra={"date": date.today().isoformat(), "dry_run": dry_run})

    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from core.models import Base, NewsComment, Feedback, BugReport, Investigation

        db_url = config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
        engine = create_engine(db_url)
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()

        # Déterminer le timestamp de départ
        if since:
            try:
                since_dt = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
            except ValueError:
                print(f"[ERREUR] Format de date invalide : {since} (attendu : YYYY-MM-DD)")
                return 1
        else:
            # Dernier cycle connu
            last = (
                session.query(Investigation.completed_at)
                .filter(Investigation.completed_at.isnot(None))
                .order_by(Investigation.completed_at.desc())
                .first()
            )
            from datetime import timedelta
            since_dt = last[0] if (last and last[0]) else datetime.now(timezone.utc) - timedelta(days=7)

        # Compter les signaux disponibles
        n_comments = session.query(NewsComment).filter(NewsComment.created_at > since_dt).count()
        n_feedbacks = (
            session.query(Feedback)
            .filter(Feedback.created_at > since_dt)
            .filter(Feedback.comment.isnot(None))
            .filter(Feedback.comment != "")
            .count()
        )
        n_bugs = session.query(BugReport).filter(BugReport.created_at > since_dt).count()

        print(f"[Aftersales] Signaux depuis {since_dt.strftime('%Y-%m-%d %H:%M')} :")
        print(f"  {n_comments} commentaires · {n_feedbacks} feedbacks texte · {n_bugs} bug reports")

        if dry_run:
            print("[dry-run] Aucun traitement effectué.")
            session.close()
            return 0

        if n_comments + n_feedbacks + n_bugs == 0:
            print("[OK] Aucun nouveau signal — rien à traiter.")
            session.close()
            return 0

        # Lancer l'agent
        t0 = time.time()
        from agents.aftersales_agent import AftersalesAgent
        summary = AftersalesAgent(config).run(session, since=since_dt)
        session.close()

        elapsed = time.time() - t0
        log.info("Aftersales terminé", extra={**summary, "duration_s": round(elapsed, 1)})

        print(
            f"[OK] Aftersales — {summary['investigations']} investigations · "
            f"{summary['ecrs']} ECR · {summary['mcas']} MCA "
            f"({elapsed:.0f}s)"
        )
        return 0

    except Exception as exc:
        log.error("Aftersales ÉCHOUÉ", extra={"error": str(exc)})
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    dry = "--dry" in sys.argv
    since_arg = None
    if "--since" in sys.argv:
        idx = sys.argv.index("--since")
        if idx + 1 < len(sys.argv):
            since_arg = sys.argv[idx + 1]
    sys.exit(main(dry_run=dry, since=since_arg))
