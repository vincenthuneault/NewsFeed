#!/usr/bin/env python3
"""Recovery à 6h30 — reprend le pipeline depuis la dernière étape complétée.

Logique de décision (du plus avancé au moins avancé) :
  tts complété       → log "déjà complet", rien à faire
  chef complété      → reprendre depuis TTS
  journalists complété → reprendre depuis Chef de nouvelles
  aucune étape       → relance complète du pipeline

Usage :
    python scripts/run_recovery.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

LOCK_FILE = Path("/tmp/newsfeed_pipeline.lock")


def main() -> int:
    from core.config import load_config
    from core.logger import get_logger

    config = load_config()
    log = get_logger("cron.recovery", config.get("logging"))
    today = date.today().isoformat()

    log.info("Recovery démarré", extra={"date": today})

    # 1. Vérifier si le pipeline tourne encore (lock file + PID vivant)
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            os.kill(pid, 0)  # Lève OSError si le processus n'existe plus
            log.info(
                "Pipeline encore en cours d'exécution — recovery annulé",
                extra={"pid": pid},
            )
            return 0
        except (OSError, ValueError):
            log.warning("Lock file obsolète (processus mort) — nettoyage et recovery")
            LOCK_FILE.unlink(missing_ok=True)

    # 2. Lire les checkpoints du jour
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from core.models import PipelineCheckpoint

    db_url = config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        rows = session.query(PipelineCheckpoint).filter_by(run_date=today).all()
        done = {row.step for row in rows}
    finally:
        session.close()

    log.info("Checkpoints du jour", extra={"étapes_complétées": sorted(done)})

    # 3. Décision de reprise
    if "tts" in done:
        log.info("Pipeline déjà complet à la première passe — rien à faire")
        return 0

    from core.pipeline import Pipeline
    pipeline = Pipeline(config)

    if "chef" in done:
        log.info("Reprise depuis TTS")
        pipeline.resume_from_tts(today)
        return 0

    if "journalists" in done:
        log.info("Reprise depuis Chef de nouvelles")
        pipeline.resume_from_chef(today)
        return 0

    # Aucune étape complétée → relance complète
    log.info("Aucune étape complétée — relance complète du pipeline")
    result = subprocess.run(
        [
            str(PROJECT_ROOT / "venv" / "bin" / "python"),
            str(PROJECT_ROOT / "scripts" / "run_pipeline.py"),
        ],
        cwd=str(PROJECT_ROOT),
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
