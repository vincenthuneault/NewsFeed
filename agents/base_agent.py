"""Classe abstraite pour tous les agents de collecte."""

from abc import ABC, abstractmethod

from core.models import RawNewsItem


class BaseAgent(ABC):
    """Chaque agent hérite de BaseAgent et implémente collect().

    Un agent ne remplit JAMAIS les champs du pipeline
    (summary_fr, image_path, audio_path, final_score).
    """

    def __init__(self, name: str, config: dict) -> None:
        self.name = name
        self.config = config

    @abstractmethod
    def collect(self) -> list[RawNewsItem]:
        """Retourne les nouvelles brutes de cette source."""
        ...

    def __repr__(self) -> str:
        return f"<Agent:{self.name}>"
