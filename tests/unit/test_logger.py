"""Tests unitaires — Logger structuré."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.logger import StructuredLogger, get_logger


@pytest.fixture(autouse=True)
def reset_loggers():
    """Reset les loggers avant et après chaque test."""
    StructuredLogger.reset()
    yield
    StructuredLogger.reset()


class TestStructuredLogger:
    """Tests pour le logger JSON structuré."""

    def test_creation_logger(self, tmp_path: Path) -> None:
        """Le logger se crée sans erreur."""
        log_file = tmp_path / "test.log"
        logger = get_logger("test_creation", {
            "level": "DEBUG",
            "file": str(log_file),
        })
        assert logger is not None
        assert logger.name == "test_creation"

    def test_singleton(self, tmp_path: Path) -> None:
        """Même nom → même instance."""
        log_file = tmp_path / "test.log"
        config = {"level": "DEBUG", "file": str(log_file)}
        logger1 = get_logger("test_singleton", config)
        logger2 = get_logger("test_singleton", config)
        assert logger1 is logger2

    def test_format_json(self, tmp_path: Path) -> None:
        """Les logs sont écrits en JSON valide."""
        log_file = tmp_path / "test.log"
        logger = get_logger("test_json", {
            "level": "DEBUG",
            "file": str(log_file),
            "format": "json",
        })

        logger.info("Message test", extra={"agent": "youtube", "count": 5})

        content = log_file.read_text(encoding="utf-8").strip()
        lines = content.split("\n")
        assert len(lines) >= 1

        # La dernière ligne doit être du JSON valide
        entry = json.loads(lines[-1])
        assert "message" in entry
        assert entry["message"] == "Message test"
        assert entry["agent"] == "youtube"
        assert entry["count"] == 5

    def test_champs_standard(self, tmp_path: Path) -> None:
        """Le JSON contient timestamp, level, name."""
        log_file = tmp_path / "test.log"
        logger = get_logger("test_champs", {
            "level": "INFO",
            "file": str(log_file),
            "format": "json",
        })

        logger.warning("Attention test")

        content = log_file.read_text(encoding="utf-8").strip()
        entry = json.loads(content.split("\n")[-1])

        assert "timestamp" in entry
        assert entry["level"] == "WARNING"
        assert "test_champs" in entry.get("name", "")

    def test_niveaux_filtrage(self, tmp_path: Path) -> None:
        """Les messages sous le niveau configuré sont ignorés."""
        log_file = tmp_path / "test.log"
        logger = get_logger("test_level", {
            "level": "WARNING",
            "file": str(log_file),
            "format": "json",
        })

        logger.debug("Debug ignoré")
        logger.info("Info ignorée")
        logger.warning("Warning visible")

        content = log_file.read_text(encoding="utf-8").strip()
        lines = [l for l in content.split("\n") if l.strip()]
        assert len(lines) == 1
        assert "Warning visible" in lines[0]

    def test_format_text(self, tmp_path: Path) -> None:
        """Le mode texte produit un format lisible (pas JSON)."""
        log_file = tmp_path / "test.log"
        logger = get_logger("test_text", {
            "level": "DEBUG",
            "file": str(log_file),
            "format": "text",
        })

        logger.info("Message texte")

        content = log_file.read_text(encoding="utf-8").strip()
        lines = content.split("\n")
        last = lines[-1]

        # Ne devrait PAS être du JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(last)

        assert "Message texte" in last

    def test_reset(self, tmp_path: Path) -> None:
        """Reset supprime tous les loggers."""
        log_file = tmp_path / "test.log"
        get_logger("test_reset", {"level": "DEBUG", "file": str(log_file)})
        assert "test_reset" in StructuredLogger._instances

        StructuredLogger.reset()
        assert len(StructuredLogger._instances) == 0

    def test_creation_dossier_log(self, tmp_path: Path) -> None:
        """Le dossier de logs est créé automatiquement."""
        log_file = tmp_path / "sous_dossier" / "deep" / "test.log"
        logger = get_logger("test_mkdir", {
            "level": "DEBUG",
            "file": str(log_file),
        })

        logger.info("Test dossier créé")
        assert log_file.exists()
