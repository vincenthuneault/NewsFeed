"""Chargement et validation de la configuration YAML + .env."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


# Racine du projet (un niveau au-dessus de core/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Chemins par défaut
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"
DEFAULT_ENV_PATH = PROJECT_ROOT / "secrets" / ".env"


def load_config(
    config_path: Path | str | None = None,
    env_path: Path | str | None = None,
) -> dict[str, Any]:
    """Charge la config YAML et les variables d'environnement.

    Args:
        config_path: Chemin vers config.yaml. Si None, utilise le défaut.
        env_path: Chemin vers .env. Si None, utilise le défaut.

    Returns:
        Dictionnaire de configuration complet.

    Raises:
        FileNotFoundError: Si le fichier config.yaml n'existe pas.
        yaml.YAMLError: Si le YAML est invalide.
    """
    config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    env_path = Path(env_path) if env_path else DEFAULT_ENV_PATH

    # Charger .env si présent (ne crash pas si absent)
    if env_path.exists():
        load_dotenv(env_path)

    # Charger config.yaml
    if not config_path.exists():
        raise FileNotFoundError(f"Config introuvable : {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise ValueError("Le fichier config.yaml doit contenir un dictionnaire YAML.")

    # Injecter les secrets depuis l'environnement
    config = _inject_secrets(config)

    # Valider les sections obligatoires
    _validate(config)

    return config


def _inject_secrets(config: dict[str, Any]) -> dict[str, Any]:
    """Injecte les clés API depuis les variables d'environnement."""
    # Anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        config.setdefault("claude", {})["api_key"] = api_key

    # YouTube
    yt_key = os.getenv("YOUTUBE_API_KEY")
    if yt_key:
        config.setdefault("youtube", {})["api_key"] = yt_key

    # Google TTS — credentials path
    tts_creds = os.getenv("GOOGLE_TTS_CREDENTIALS")
    if tts_creds:
        config.setdefault("tts", {})["credentials_path"] = tts_creds

    return config


REQUIRED_SECTIONS = ["app", "database", "logging"]


def _validate(config: dict[str, Any]) -> None:
    """Valide que les sections obligatoires existent.

    Raises:
        KeyError: Si une section obligatoire est manquante.
    """
    for section in REQUIRED_SECTIONS:
        if section not in config:
            raise KeyError(f"Section obligatoire manquante dans config.yaml : '{section}'")


def get_nested(config: dict[str, Any], dotted_key: str, default: Any = None) -> Any:
    """Accède à une valeur imbriquée avec notation pointée.

    Args:
        config: Dictionnaire de configuration.
        dotted_key: Clé en notation pointée, ex: "claude.model"
        default: Valeur par défaut si la clé n'existe pas.

    Returns:
        La valeur trouvée ou le défaut.

    Example:
        >>> get_nested(config, "claude.model")
        "claude-sonnet-4-20250514"
    """
    keys = dotted_key.split(".")
    current = config
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current
