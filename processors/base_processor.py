"""Classe abstraite pour les processeurs du pipeline."""

from abc import ABC, abstractmethod


class BaseProcessor(ABC):
    """Chaque étape du pipeline hérite de BaseProcessor."""

    def __init__(self, name: str, config: dict) -> None:
        self.name = name
        self.config = config

    @abstractmethod
    def process(self, items: list) -> list:
        """Transforme une liste d'items et retourne la liste modifiée."""
        ...

    def __repr__(self) -> str:
        return f"<Processor:{self.name}>"
