"""Modèle de données central — RawNewsItem + modèles SQLAlchemy."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker


# ============================================================
# Dataclass interne (Agent → Pipeline)
# ============================================================


@dataclass
class RawNewsItem:
    """Contrat de données entre les agents et le pipeline.

    Champs obligatoires : remplis par l'agent.
    Champs optionnels : remplis par l'agent si disponible.
    Champs pipeline : JAMAIS remplis par l'agent (réservés au pipeline).
    """

    # --- Obligatoires (agent) ---
    title: str
    source_url: str
    source_name: str
    category: str
    published_at: datetime

    # --- Optionnels (agent) ---
    description: str | None = None
    image_url: str | None = None
    video_url: str | None = None
    video_type: str | None = None  # "short" (< 60s) ou "long"
    raw_content: str | None = None
    popularity_score: float = 0.0
    metadata: dict | None = None

    # --- Générés par le pipeline (jamais par l'agent) ---
    summary_fr: str | None = field(default=None, repr=False)
    image_path: str | None = field(default=None, repr=False)
    audio_path: str | None = field(default=None, repr=False)
    final_score: float = field(default=0.0, repr=False)


# ============================================================
# Catégories normalisées
# ============================================================

CATEGORIES = {
    "youtube_subs": "Mes abonnements YouTube",
    "youtube_trending": "Tendances YouTube",
    "viral": "Contenu viral",
    "tech_ai": "Tech & IA",
    "politique_intl": "Politique internationale",
    "politique_ca": "Politique canadienne",
    "politique_qc": "Politique québécoise",
    "evenements_mtl": "Événements Montréal",
    "musique_electro": "Musique électronique",
    "humour": "Humour",
    "local_contrecoeur": "Contrecoeur & Sorel",
    "local_alerte": "Alertes locales",
    "vehicules_ev": "Véhicules électriques & autonomes",
    "spatial": "Espace & exploration",
}


# ============================================================
# SQLAlchemy — Base et modèles
# ============================================================


class Base(DeclarativeBase):
    """Base déclarative pour tous les modèles SQLAlchemy."""
    pass


class NewsItem(Base):
    """Nouvelle traitée et stockée en base."""

    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    source_url = Column(String(2000), nullable=False, unique=True)
    source_name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    published_at = Column(DateTime, nullable=False, index=True)

    description = Column(Text, nullable=True)
    image_url = Column(String(2000), nullable=True)
    video_url = Column(String(2000), nullable=True)
    video_type = Column(String(10), nullable=True)
    raw_content = Column(Text, nullable=True)
    popularity_score = Column(Float, default=0.0)

    # Champs pipeline
    summary_fr = Column(Text, nullable=True)
    image_path = Column(String(500), nullable=True)
    audio_path = Column(String(500), nullable=True)
    final_score = Column(Float, default=0.0, index=True)

    # Timestamps
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(DateTime, nullable=True, onupdate=lambda: datetime.now(timezone.utc))

    # Relations
    feedbacks = relationship("Feedback", back_populates="news_item", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<NewsItem(id={self.id}, title='{self.title[:40]}...')>"


class DailyFeed(Base):
    """Fil quotidien assemblé."""

    __tablename__ = "daily_feeds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), nullable=False, unique=True, index=True)  # YYYY-MM-DD
    status = Column(String(20), nullable=False, default="pending")  # pending|ready|partial|failed
    item_count = Column(Integer, default=0)
    item_ids = Column(Text, nullable=True)  # JSON array d'IDs ordonnés

    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(DateTime, nullable=True, onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<DailyFeed(date='{self.date}', status='{self.status}')>"


class Feedback(Base):
    """Feedback utilisateur sur une nouvelle."""

    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    news_item_id = Column(Integer, ForeignKey("news_items.id"), nullable=False, index=True)
    action = Column(String(20), nullable=False)  # like|dislike|skip
    comment = Column(Text, nullable=True)

    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relations
    news_item = relationship("NewsItem", back_populates="feedbacks")

    def __repr__(self) -> str:
        return f"<Feedback(news_item_id={self.news_item_id}, action='{self.action}')>"


class AgentRun(Base):
    """Log d'exécution d'un agent."""

    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False)  # success|partial|failed
    items_collected = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)

    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<AgentRun(agent='{self.agent_name}', status='{self.status}')>"


# ============================================================
# Utilitaires DB
# ============================================================


def init_db(database_url: str, echo: bool = False) -> sessionmaker:
    """Crée les tables et retourne une factory de sessions.

    Args:
        database_url: URL SQLAlchemy (ex: "sqlite:///data/newsfeed.db").
        echo: Afficher les requêtes SQL.

    Returns:
        sessionmaker configuré.
    """
    engine = create_engine(database_url, echo=echo)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def get_session(session_factory: sessionmaker) -> Session:
    """Crée une nouvelle session DB.

    Args:
        session_factory: Factory retournée par init_db().

    Returns:
        Session SQLAlchemy.
    """
    return session_factory()
