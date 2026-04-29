"""Route POST /api/news/<id>/feedback."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from core.models import Feedback, NewsItem, get_session, init_db

feedback_bp = Blueprint("feedback", __name__)

_VALID_ACTIONS = {"like", "dislike", "skip"}


def _get_session():
    config = current_app.config["PROJECT_CONFIG"]
    db_url = config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
    return get_session(init_db(db_url))


@feedback_bp.route("/news/<int:news_id>/feedback", methods=["POST"])
def post_feedback(news_id: int):
    """Enregistre un feedback sur une nouvelle.

    Body JSON : {"action": "like"|"dislike"|"skip", "comment": "..."}
    """
    data = request.get_json(silent=True) or {}
    action = data.get("action", "").lower()

    if action not in _VALID_ACTIONS:
        return jsonify({
            "error": True,
            "message": f"action invalide : '{action}'. Valeurs : {sorted(_VALID_ACTIONS)}",
            "code": "BAD_REQUEST",
        }), 400

    session = _get_session()
    try:
        item = session.query(NewsItem).get(news_id)
        if not item:
            return jsonify({"error": True, "message": "Nouvelle introuvable", "code": "NOT_FOUND"}), 404

        fb = Feedback(
            news_item_id=news_id,
            action=action,
            comment=data.get("comment"),
        )
        session.add(fb)
        session.commit()

        return jsonify({"success": True, "feedback_id": fb.id, "action": action}), 201
    except Exception as exc:
        session.rollback()
        return jsonify({"error": True, "message": str(exc), "code": "SERVER_ERROR"}), 500
    finally:
        session.close()


@feedback_bp.route("/news/<int:news_id>/feedback", methods=["GET"])
def get_feedback(news_id: int):
    """Retourne les feedbacks d'une nouvelle."""
    session = _get_session()
    try:
        feedbacks = (
            session.query(Feedback)
            .filter_by(news_item_id=news_id)
            .order_by(Feedback.created_at.desc())
            .all()
        )
        return jsonify({
            "news_id": news_id,
            "feedbacks": [
                {
                    "id": f.id,
                    "action": f.action,
                    "comment": f.comment,
                    "created_at": f.created_at.isoformat(),
                }
                for f in feedbacks
            ],
        })
    finally:
        session.close()
