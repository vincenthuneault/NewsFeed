"""Routes /api/dev/* — interface de développement (lecture DB)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import func

from backend.auth import require_auth
from core.models import (
    AgentRun,
    BugReport,
    DailyFeed,
    Feedback,
    NewsComment,
    NewsItem,
    get_session,
    init_db,
)

dev_bp = Blueprint("dev", __name__)


def _get_session():
    config = current_app.config["PROJECT_CONFIG"]
    db_url = config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
    return get_session(init_db(db_url))


@dev_bp.route("/dev/stats")
@require_auth
def dev_stats():
    """Vue d'ensemble : compteurs globaux et activité récente."""
    session = _get_session()
    try:
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)

        total_news = session.query(NewsItem).count()
        total_comments = session.query(NewsComment).count()
        total_bugs = session.query(BugReport).count()

        comments_week = session.query(NewsComment).filter(
            NewsComment.created_at >= week_ago
        ).count()
        bugs_week = session.query(BugReport).filter(
            BugReport.created_at >= week_ago
        ).count()

        fb_rows = session.query(Feedback.action, func.count()).group_by(Feedback.action).all()
        fb_counts = {action: count for action, count in fb_rows}

        total_runs = session.query(AgentRun).count()
        success_runs = session.query(AgentRun).filter_by(status="success").count()
        last_run = session.query(AgentRun).order_by(AgentRun.created_at.desc()).first()

        return jsonify({
            "news_items": {"total": total_news},
            "comments": {"total": total_comments, "this_week": comments_week},
            "bugs": {"total": total_bugs, "this_week": bugs_week},
            "feedbacks": {
                "total": sum(fb_counts.values()),
                "likes": fb_counts.get("like", 0),
                "dislikes": fb_counts.get("dislike", 0),
                "skips": fb_counts.get("skip", 0),
            },
            "agent_runs": {
                "total": total_runs,
                "success_rate": round(success_runs / total_runs, 3) if total_runs else 0,
                "last_run": last_run.created_at.isoformat() if last_run else None,
            },
        })
    finally:
        session.close()


@dev_bp.route("/dev/comments")
@require_auth
def dev_comments():
    """Liste tous les commentaires avec l'article associé.

    Query params : page (int), per_page (int), q (str — filtre texte)
    """
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))
    q = request.args.get("q", "").strip()

    session = _get_session()
    try:
        query = session.query(NewsComment).join(
            NewsItem, NewsComment.news_item_id == NewsItem.id
        )
        if q:
            query = query.filter(NewsComment.body.ilike(f"%{q}%"))

        total = query.count()
        items = (
            query.order_by(NewsComment.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return jsonify({
            "total": total,
            "page": page,
            "per_page": per_page,
            "items": [
                {
                    "id": c.id,
                    "body": c.body,
                    "created_at": c.created_at.isoformat(),
                    "news_item": {
                        "id": c.news_item.id,
                        "title": c.news_item.title,
                        "source_name": c.news_item.source_name,
                        "category": c.news_item.category,
                        "published_at": c.news_item.published_at.isoformat(),
                    },
                }
                for c in items
            ],
        })
    finally:
        session.close()


@dev_bp.route("/dev/bugs")
@require_auth
def dev_bugs():
    """Liste tous les rapports de bug avec contexte JSON parsé.

    Query params : page (int), per_page (int)
    """
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))

    session = _get_session()
    try:
        total = session.query(BugReport).count()
        items = (
            session.query(BugReport)
            .order_by(BugReport.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return jsonify({
            "total": total,
            "page": page,
            "per_page": per_page,
            "items": [
                {
                    "id": b.id,
                    "description": b.description,
                    "context": json.loads(b.context) if b.context else None,
                    "created_at": b.created_at.isoformat(),
                }
                for b in items
            ],
        })
    finally:
        session.close()


@dev_bp.route("/dev/agent-runs")
@require_auth
def dev_agent_runs():
    """Historique des exécutions d'agents.

    Query params : page (int), per_page (int), agent (str — nom exact)
    """
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 50, type=int)))
    agent = request.args.get("agent", "").strip()

    session = _get_session()
    try:
        query = session.query(AgentRun)
        if agent:
            query = query.filter_by(agent_name=agent)

        total = query.count()
        items = (
            query.order_by(AgentRun.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        # Liste des agents distincts pour le filtre
        agent_names = [
            row[0] for row in session.query(AgentRun.agent_name).distinct().order_by(AgentRun.agent_name).all()
        ]

        return jsonify({
            "total": total,
            "page": page,
            "per_page": per_page,
            "agent_names": agent_names,
            "items": [
                {
                    "id": r.id,
                    "agent_name": r.agent_name,
                    "status": r.status,
                    "items_collected": r.items_collected,
                    "duration_seconds": round(r.duration_seconds, 1),
                    "error_message": r.error_message,
                    "created_at": r.created_at.isoformat(),
                }
                for r in items
            ],
        })
    finally:
        session.close()


@dev_bp.route("/dev/news")
@require_auth
def dev_news():
    """Parcourir les articles avec filtres.

    Query params : page (int), per_page (int), q (str — titre), category (str)
    """
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))
    category = request.args.get("category", "").strip()
    q = request.args.get("q", "").strip()

    session = _get_session()
    try:
        query = session.query(NewsItem)
        if category:
            query = query.filter_by(category=category)
        if q:
            query = query.filter(NewsItem.title.ilike(f"%{q}%"))

        total = query.count()
        items = (
            query.order_by(NewsItem.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return jsonify({
            "total": total,
            "page": page,
            "per_page": per_page,
            "items": [
                {
                    "id": i.id,
                    "title": i.title,
                    "source_name": i.source_name,
                    "source_url": i.source_url,
                    "category": i.category,
                    "published_at": i.published_at.isoformat(),
                    "final_score": round(i.final_score, 3),
                    "popularity_score": round(i.popularity_score, 3),
                    "has_summary": bool(i.summary_fr),
                    "has_audio": bool(i.audio_path),
                    "has_image": bool(i.image_path),
                    "comments_count": len(i.comments),
                    "feedbacks_count": len(i.feedbacks),
                    "created_at": i.created_at.isoformat(),
                }
                for i in items
            ],
        })
    finally:
        session.close()
