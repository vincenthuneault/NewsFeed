"""Logger structuré JSON pour le projet Lecteur de nouvelle."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from pythonjsonlogger import jsonlogger


# Racine du projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class StructuredLogger:
    """Logger JSON structuré avec sortie fichier + stdout.

    Usage:
        from core.logger import get_logger
        logger = get_logger("mon_module")
        logger.info("Message", extra={"agent": "youtube_subs", "items": 42})
    """

    _instances: dict[str, logging.Logger] = {}

    @classmethod
    def get_logger(
        cls,
        name: str,
        config: dict[str, Any] | None = None,
    ) -> logging.Logger:
        """Retourne un logger configuré (singleton par nom).

        Args:
            name: Nom du logger (ex: "core.config", "agents.youtube").
            config: Section 'logging' de config.yaml. Si None, utilise les défauts.

        Returns:
            Logger Python configuré.
        """
        if name in cls._instances:
            return cls._instances[name]

        config = config or {}
        level = config.get("level", "INFO").upper()
        log_file = config.get("file", "logs/newsfeed.log")
        max_bytes = config.get("max_bytes", 10_485_760)  # 10MB
        backup_count = config.get("backup_count", 7)
        use_json = config.get("format", "json") == "json"

        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level, logging.INFO))
        logger.propagate = False

        # Formatter
        if use_json:
            formatter = jsonlogger.JsonFormatter(
                fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
                rename_fields={"asctime": "timestamp", "levelname": "level"},
            )
        else:
            formatter = logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        # Handler fichier (avec rotation)
        log_path = PROJECT_ROOT / log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Handler stdout
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        logger.addHandler(stdout_handler)

        cls._instances[name] = logger
        return logger

    @classmethod
    def reset(cls) -> None:
        """Réinitialise tous les loggers (utile pour les tests)."""
        for name, logger in cls._instances.items():
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
        cls._instances.clear()


def get_logger(name: str, config: dict[str, Any] | None = None) -> logging.Logger:
    """Raccourci pour StructuredLogger.get_logger().

    Args:
        name: Nom du logger.
        config: Section 'logging' de config.yaml.

    Returns:
        Logger configuré.
    """
    return StructuredLogger.get_logger(name, config)
