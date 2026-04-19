"""Tests unitaires — Module de configuration."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import yaml

# Ajouter la racine du projet au path
import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import load_config, get_nested, REQUIRED_SECTIONS


@pytest.fixture
def minimal_config(tmp_path: Path) -> Path:
    """Crée un fichier config.yaml minimal valide."""
    config = {
        "app": {"name": "Test App", "env": "test"},
        "database": {"url": "sqlite:///:memory:", "echo": False},
        "logging": {"level": "DEBUG", "file": "logs/test.log"},
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(config), encoding="utf-8")
    return config_path


@pytest.fixture
def full_config(tmp_path: Path) -> Path:
    """Crée un fichier config.yaml complet."""
    config = {
        "app": {
            "name": "Lecteur de nouvelle",
            "env": "test",
            "timezone": "America/Montreal",
            "daily_run_hour": 6,
            "max_feed_items": 30,
        },
        "database": {"url": "sqlite:///:memory:", "echo": False},
        "claude": {
            "model": "claude-sonnet-4-20250514",
            "max_input_tokens": 2000,
            "temperature": 0.3,
        },
        "tts": {
            "provider": "google",
            "language_code": "fr-CA",
            "voice_name": "fr-CA-Wavenet-A",
        },
        "logging": {"level": "INFO", "file": "logs/test.log"},
        "scoring": {"weights": {"freshness": 0.3, "reliability": 0.25}},
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(config), encoding="utf-8")
    return config_path


class TestLoadConfig:
    """Tests pour load_config()."""

    def test_charge_config_minimale(self, minimal_config: Path) -> None:
        """Config minimale se charge sans erreur."""
        config = load_config(config_path=minimal_config)
        assert config["app"]["name"] == "Test App"

    def test_charge_config_complete(self, full_config: Path) -> None:
        """Config complète se charge correctement."""
        config = load_config(config_path=full_config)
        assert config["app"]["name"] == "Lecteur de nouvelle"
        assert config["claude"]["model"] == "claude-sonnet-4-20250514"

    def test_erreur_fichier_manquant(self, tmp_path: Path) -> None:
        """FileNotFoundError si le fichier n'existe pas."""
        with pytest.raises(FileNotFoundError):
            load_config(config_path=tmp_path / "inexistant.yaml")

    def test_erreur_section_manquante(self, tmp_path: Path) -> None:
        """KeyError si une section obligatoire manque."""
        bad_config = {"app": {"name": "Test"}}  # manque database et logging
        config_path = tmp_path / "bad.yaml"
        config_path.write_text(yaml.dump(bad_config), encoding="utf-8")
        with pytest.raises(KeyError, match="database"):
            load_config(config_path=config_path)

    def test_erreur_yaml_invalide(self, tmp_path: Path) -> None:
        """ValueError si le YAML ne contient pas un dict."""
        config_path = tmp_path / "list.yaml"
        config_path.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="dictionnaire"):
            load_config(config_path=config_path)

    def test_injection_secrets_env(self, minimal_config: Path) -> None:
        """Les variables d'environnement sont injectées."""
        os.environ["ANTHROPIC_API_KEY"] = "test-key-123"
        try:
            config = load_config(config_path=minimal_config)
            assert config["claude"]["api_key"] == "test-key-123"
        finally:
            del os.environ["ANTHROPIC_API_KEY"]

    def test_dotenv_charge(self, minimal_config: Path, tmp_path: Path) -> None:
        """Le fichier .env est chargé si présent."""
        env_path = tmp_path / ".env"
        env_path.write_text("ANTHROPIC_API_KEY=from-dotenv\n", encoding="utf-8")
        config = load_config(config_path=minimal_config, env_path=env_path)
        assert config["claude"]["api_key"] == "from-dotenv"
        # Nettoyer
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]


class TestGetNested:
    """Tests pour get_nested()."""

    def test_acces_simple(self) -> None:
        config = {"app": {"name": "Test"}}
        assert get_nested(config, "app.name") == "Test"

    def test_acces_profond(self) -> None:
        config = {"scoring": {"weights": {"freshness": 0.3}}}
        assert get_nested(config, "scoring.weights.freshness") == 0.3

    def test_cle_manquante_retourne_default(self) -> None:
        config = {"app": {"name": "Test"}}
        assert get_nested(config, "app.missing") is None
        assert get_nested(config, "app.missing", "fallback") == "fallback"

    def test_section_manquante_retourne_default(self) -> None:
        config = {"app": {"name": "Test"}}
        assert get_nested(config, "inexistant.key", "default") == "default"

    def test_cle_premier_niveau(self) -> None:
        config = {"app": {"name": "Test"}}
        assert get_nested(config, "app") == {"name": "Test"}


class TestRequiredSections:
    """Vérifie que les sections obligatoires sont bien définies."""

    def test_sections_attendues(self) -> None:
        assert "app" in REQUIRED_SECTIONS
        assert "database" in REQUIRED_SECTIONS
        assert "logging" in REQUIRED_SECTIONS
