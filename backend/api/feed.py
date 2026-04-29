"""Routes /api/feed/* et /api/news/<id>."""

from __future__ import annotations

import json
from datetime import date, datetime

from flask import Blueprint, current_app, jsonify

from core.models import DailyFeed, NewsItem, get_session, init_db

feed_bp = Blueprint("feed", __name__)


def _get_session():
    config = current_app.config["PROJECT_CONFIG"]
    db_url = config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
    factory = init_db(db_url)
    return get_session(factory)


def _item_to_dict(item: NewsItem) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "source_url": item.source_url,
        "source_name": item.source_name,
        "category": item.category,
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "description": item.description,
        "image_url": item.image_url,
        "image_path": f"/{item.image_path}" if item.image_path else None,
        "video_url": item.video_url,
        "video_type": item.video_type,
        "summary_fr": item.summary_fr,
        "audio_path": f"/{item.audio_path}" if item.audio_path else None,
        "final_score": item.final_score,
    }


@feed_bp.route("/feed/today")
def feed_today():
    """Retourne le fil du jour."""
    session = _get_session()
    try:
        today = date.today().isoformat()
        feed = session.query(DailyFeed).filter_by(date=today).first()

        if not feed:
            return jsonify({"error": True, "message": "Aucun fil pour aujourd'hui", "code": "NOT_FOUND"}), 404

        item_ids = json.loads(feed.item_ids) if feed.item_ids else []
        if not item_ids:
            return jsonify({"date": today, "status": feed.status, "items": []})

        items = (
            session.query(NewsItem)
            .filter(NewsItem.id.in_(item_ids))
            .all()
        )
        # Respecter l'ordre du fil
        id_to_item = {item.id: item for item in items}
        ordered = [id_to_item[i] for i in item_ids if i in id_to_item]

        return jsonify({
            "date": today,
            "status": feed.status,
            "count": len(ordered),
            "items": [_item_to_dict(i) for i in ordered],
        })
    finally:
        session.close()


@feed_bp.route("/feed/dates")
def feed_dates():
    """Retourne la liste des dates disponibles."""
    session = _get_session()
    try:
        feeds = (
            session.query(DailyFeed)
            .filter_by(status="ready")
            .order_by(DailyFeed.date.desc())
            .all()
        )
        return jsonify({
            "dates": [
                {"date": f.date, "count": f.item_count}
                for f in feeds
            ]
        })
    finally:
        session.close()


@feed_bp.route("/feed/<string:feed_date>")
def feed_by_date(feed_date: str):
    """Retourne le fil d'une date passée (format YYYY-MM-DD)."""
    session = _get_session()
    try:
        feed = session.query(DailyFeed).filter_by(date=feed_date).first()
        if not feed:
            return jsonify({"error": True, "message": f"Aucun fil pour {feed_date}", "code": "NOT_FOUND"}), 404

        item_ids = json.loads(feed.item_ids) if feed.item_ids else []
        items = session.query(NewsItem).filter(NewsItem.id.in_(item_ids)).all()
        id_to_item = {item.id: item for item in items}
        ordered = [id_to_item[i] for i in item_ids if i in id_to_item]

        return jsonify({
            "date": feed_date,
            "status": feed.status,
            "count": len(ordered),
            "items": [_item_to_dict(i) for i in ordered],
        })
    finally:
        session.close()


@feed_bp.route("/news/<int:news_id>")
def get_news(news_id: int):
    """Retourne le détail d'une nouvelle."""
    session = _get_session()
    try:
        item = session.query(NewsItem).get(news_id)
        if not item:
            return jsonify({"error": True, "message": "Nouvelle introuvable", "code": "NOT_FOUND"}), 404
        return jsonify(_item_to_dict(item))
    finally:
        session.close()
