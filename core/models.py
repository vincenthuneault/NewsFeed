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
    editorial_note = Column(Text, nullable=True)  # Rempli par Chef de nouvelles pour les articles rejetés

    # Timestamps
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(DateTime, nullable=True, onupdate=lambda: datetime.now(timezone.utc))

    # Relations
    feedbacks = relationship("Feedback", back_populates="news_item", cascade="all, delete-orphan")
    comments  = relationship("NewsComment", back_populates="news_item", cascade="all, delete-orphan")

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


class NewsComment(Base):
    """Note personnelle de l'utilisateur sur une nouvelle."""

    __tablename__ = "news_comments"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    news_item_id = Column(Integer, ForeignKey("news_items.id"), nullable=False, index=True)
    body         = Column(Text, nullable=False)

    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    news_item = relationship("NewsItem", back_populates="comments")

    def __repr__(self) -> str:
        return f"<NewsComment(news_item_id={self.news_item_id})>"


class BugReport(Base):
    """Rapport de bug soumis depuis l'interface."""

    __tablename__ = "bug_reports"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(Text, nullable=False)
    context     = Column(Text, nullable=True)  # JSON : article actif, user_agent, timestamp

    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<BugReport(id={self.id})>"


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
# Aftersales — Suivi ECR / MCA / Investigations
# ============================================================


class ECR(Base):
    """Engineering Change Record — modification de code requise."""

    __tablename__ = "ecr"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    ecr_number   = Column(String(20), nullable=False, unique=True, index=True)
    title        = Column(String(500), nullable=False)
    status       = Column(String(30), nullable=False, default="a_transmettre", index=True)
    # a_transmettre | en_cours | corrige | annule
    priority     = Column(String(10), nullable=False, default="normale")
    # haute | normale | basse
    severity     = Column(String(10), nullable=False, default="normale")
    # critique | haute | normale | basse
    symptom      = Column(Text, nullable=True)
    root_cause   = Column(Text, nullable=True)
    proposed_fix = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=True, onupdate=lambda: datetime.now(timezone.utc))
    closed_at  = Column(DateTime, nullable=True)

    status_history = relationship("ECRStatusHistory", back_populates="ecr", cascade="all, delete-orphan")
    investigations = relationship("Investigation", back_populates="ecr", foreign_keys="Investigation.ecr_id")

    def __repr__(self) -> str:
        return f"<ECR({self.ecr_number}, status='{self.status}')>"


class MCA(Base):
    """Mise à jour Contexte Agent — changement de configuration sans code."""

    __tablename__ = "mca"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    mca_number      = Column(String(20), nullable=False, unique=True, index=True)
    title           = Column(String(500), nullable=False)
    status          = Column(String(20), nullable=False, default="a_appliquer", index=True)
    # a_appliquer | applique | en_attente
    target_agent    = Column(String(200), nullable=True)
    description     = Column(Text, nullable=True)
    justification   = Column(Text, nullable=True)
    blocking_ecr_id = Column(Integer, ForeignKey("ecr.id"), nullable=True)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=True, onupdate=lambda: datetime.now(timezone.utc))
    applied_at = Column(DateTime, nullable=True)

    status_history = relationship("MCAStatusHistory", back_populates="mca", cascade="all, delete-orphan")
    investigations = relationship("Investigation", back_populates="mca", foreign_keys="Investigation.mca_id")

    def __repr__(self) -> str:
        return f"<MCA({self.mca_number}, status='{self.status}')>"


class Investigation(Base):
    """Log d'investigation Aftersales — une entrée par cycle."""

    __tablename__ = "investigations"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    trigger_type   = Column(String(30), nullable=False)
    # comment | bug_report | feedback | manual
    trigger_id     = Column(Integer, nullable=True)
    hypothesis     = Column(Text, nullable=True)
    data_plan      = Column(Text, nullable=True)
    data_collected = Column(Text, nullable=True)
    conclusion     = Column(Text, nullable=True)
    decision       = Column(String(20), nullable=True)
    # journalisation | mca | ecr | business
    ecr_id         = Column(Integer, ForeignKey("ecr.id"), nullable=True)
    mca_id         = Column(Integer, ForeignKey("mca.id"), nullable=True)

    created_at   = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    ecr = relationship("ECR", back_populates="investigations", foreign_keys=[ecr_id])
    mca = relationship("MCA", back_populates="investigations", foreign_keys=[mca_id])

    def __repr__(self) -> str:
        return f"<Investigation(id={self.id}, decision='{self.decision}')>"


class ECRStatusHistory(Base):
    """Audit trail des changements de statut ECR."""

    __tablename__ = "ecr_status_history"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    ecr_id     = Column(Integer, ForeignKey("ecr.id"), nullable=False, index=True)
    old_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=False)
    note       = Column(Text, nullable=True)
    changed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    ecr = relationship("ECR", back_populates="status_history")


class MCAStatusHistory(Base):
    """Audit trail des changements de statut MCA."""

    __tablename__ = "mca_status_history"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    mca_id     = Column(Integer, ForeignKey("mca.id"), nullable=False, index=True)
    old_status = Column(String(20), nullable=True)
    new_status = Column(String(20), nullable=False)
    note       = Column(Text, nullable=True)
    changed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    mca = relationship("MCA", back_populates="status_history")


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


def seed_aftersales_data(session) -> dict:
    """Initialise les ECR et MCA depuis l'analyse Aftersales Mai 2026.

    Idempotent — ne crée rien si les enregistrements existent déjà.
    Retourne un dict {"ecr": [...], "mca": [...]} des IDs créés.
    """
    created: dict = {"ecr": [], "mca": []}

    ecrs = [
        {
            "ecr_number": "ECR-003",
            "title": "Redéfinition architecturale — Agent Journaliste et Chef de nouvelles",
            "priority": "haute",
            "severity": "haute",
            "symptom": "11% du contenu présenté est du déjà-vu (44 slots sur 390). Articles hors profil utilisateur, sélection algorithmique sans compréhension éditoriale du contexte.",
            "root_cause": "Le Scorer algorithmique (processors/scorer.py) sélectionne le top 30 par score multi-facteur sans vision éditoriale. Il n'a pas accès au profil utilisateur, ne peut pas évaluer la suffisance informationnelle, et ne garantit pas que seuls les articles du jour sont présentés.",
            "proposed_fix": "Remplacement du Scorer comme sélecteur final par un agent IA Chef de nouvelles (agents/chef_de_nouvelles.py). Le Chef reçoit tous les articles summarisés du jour, évalue leur qualité informationnelle, sélectionne et ordonne ≤30 articles selon le profil utilisateur. Les doublons cross-journées deviennent architecturalement impossibles — le Chef ne voit que les articles créés aujourd'hui. Décision architecturale prise le 2026-05-14.",
        },
        {
            "ecr_number": "ECR-004",
            "title": "Gate qualité contenu + blacklist The Verge + filtre live streams",
            "priority": "haute",
            "severity": "haute",
            "symptom": "Articles derrière paywall (The Verge) et live streams YouTube passent le filtre avec un contenu inutilisable.",
            "root_cause": "Absence de seuil minimum sur raw_content avant génération du résumé. Aucun filtre sur patterns live dans les titres YouTube.",
            "proposed_fix": "1) Gate longueur min raw_content (300 chars). 2) Blacklist domaines dans config.yaml (theverge.com). 3) Filtre titre YouTube : 🔴LIVE, #LIVE, LIVE |.",
        },
        {
            "ecr_number": "ECR-005",
            "title": "Resserrer catégories vehicules_ev et evenements_mtl",
            "priority": "normale",
            "severity": "normale",
            "symptom": "Articles de vélos électriques et d'infrastructure routière mal catégorisés dans vehicules_ev et evenements_mtl.",
            "root_cause": "Définitions de catégories trop larges dans les prompts de classification.",
            "proposed_fix": "vehicules_ev → voitures/camions EV uniquement (exclure vélos, solaire). evenements_mtl → spectacles/sorties culturelles uniquement (exclure infrastructure, politique).",
        },
        {
            "ecr_number": "ECR-006",
            "title": "Bug stabilité lecteur audio",
            "priority": "normale",
            "severity": "normale",
            "symptom": "Sur certains articles, le lecteur audio nécessite plusieurs tentatives avant de lire l'article en entier.",
            "root_cause": "Inconnue — investigation requise. Hypothèses : timeout chargement fichier long, audio_path invalide, race condition pipeline/affichage.",
            "proposed_fix": "1) Ajouter onerror handler sur <audio> côté frontend pour capturer les échecs. 2) Corriger selon analyse des logs.",
        },
        {
            "ecr_number": "ECR-007",
            "title": "Afficher 'Pourquoi ce contenu' dans l'interface",
            "priority": "basse",
            "severity": "basse",
            "symptom": "L'utilisateur ne comprend pas pourquoi certains articles lui sont présentés.",
            "root_cause": "Aucun champ presentation_reason dans news_items, aucun affichage frontend.",
            "proposed_fix": "Ajouter champ presentation_reason (JSON) dans news_items. Afficher catégorie + source + score dans l'interface (tooltip ou menu ⋮).",
        },
    ]

    mcas = [
        {
            "mca_number": "MCA-001",
            "title": "Géographie locale resserrée",
            "target_agent": "Agent Scraping (local_contrecoeur, evenements_mtl)",
            "description": "Zone acceptée : Contrecoeur, Sorel-Tracy, Grand Montréal (île + rive sud). Exclure : Rimouski, Québec, Ottawa, Toronto, autres provinces.",
            "justification": "6 articles hors zone : Rimouski, Nouveau-Brunswick, Ottawa, Québec (ville), Toronto.",
        },
        {
            "mca_number": "MCA-002",
            "title": "Exclusions catégorie vehicules_ev",
            "target_agent": "Chef de nouvelle / Scorer",
            "description": "Exclure ou pénaliser dans vehicules_ev : vélos électriques, trottinettes, panneaux solaires, éoliennes.",
            "justification": "Articles #40 (vélos) et #35 (ferme solaire) mal catégorisés dans vehicules_ev.",
        },
        {
            "mca_number": "MCA-003",
            "title": "Exclusions catégorie musique_electro",
            "target_agent": "Agent RSS (musique), Scorer",
            "description": "Genres acceptés : électro, EDM, techno, house, trance. Exclure : rap, hip-hop, R&B, reggaeton, Bollywood.",
            "justification": "Article #12 (Fetty Wap — rap) présenté dans catégorie électro. Profil : électro/EDM/techno.",
        },
        {
            "mca_number": "MCA-004",
            "title": "Filtre géographique viral_trending",
            "target_agent": "Agent YouTube / Agent Scraping (viral_trending)",
            "description": "Restreindre au contenu viral nord-américain. Profil : homme 35 ans Québec. Exclure Bollywood, K-pop, tendances hors NA.",
            "justification": "Article #9 (Drishyam 3 — Bollywood) présenté dans trending.",
        },
        {
            "mca_number": "MCA-005",
            "title": "Scorer à 0 : sport, jeux vidéo, contenu jeunesse",
            "target_agent": "Chef de nouvelle / Scorer (tous agents)",
            "description": "Exclure : sport, jeux vidéo, esports, contenu jeunesse/éducation, articles sans substance.",
            "justification": "5 articles indésirables : hockey (#13), gaming (#11, #4), jeunesse (#14), article vide (#25).",
        },
    ]

    for ecr_data in ecrs:
        if not session.query(ECR).filter_by(ecr_number=ecr_data["ecr_number"]).first():
            session.add(ECR(**ecr_data))
            created["ecr"].append(ecr_data["ecr_number"])

    for mca_data in mcas:
        if not session.query(MCA).filter_by(mca_number=mca_data["mca_number"]).first():
            session.add(MCA(**mca_data))
            created["mca"].append(mca_data["mca_number"])

    session.commit()
    return created


def get_session(session_factory: sessionmaker) -> Session:
    """Crée une nouvelle session DB.

    Args:
        session_factory: Factory retournée par init_db().

    Returns:
        Session SQLAlchemy.
    """
    return session_factory()
