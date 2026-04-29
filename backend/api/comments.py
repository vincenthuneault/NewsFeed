"""Routes /api/news/<id>/comments — notes personnelles sur une nouvelle."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from core.models import NewsComment, NewsItem, get_session, init_db

comments_bp = Blueprint("comments", __name__)

_MAX_BODY = 2000


def _get_session():
    config = current_app.config["PROJECT_CONFIG"]
    db_url = config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
    return get_session(init_db(db_url))


@comments_bp.route("/news/<int:news_id>/comments", methods=["POST"])
def post_comment(news_id: int):
    """Crée un commentaire sur une nouvelle.

    Body JSON : {"body": "mon commentaire"}
    """
    data = request.get_json(silent=True) or {}
    body = (data.get("body") or "").strip()

    if not body:
        return jsonify({"error": True, "message": "body requis", "code": "BAD_REQUEST"}), 400
    if len(body) > _MAX_BODY:
        return jsonify({"error": True, "message": f"body trop long (max {_MAX_BODY})", "code": "BAD_REQUEST"}), 400

    session = _get_session()
    try:
        item = session.query(NewsItem).get(news_id)
        if not item:
            return jsonify({"error": True, "message": "Nouvelle introuvable", "code": "NOT_FOUND"}), 404

        comment = NewsComment(news_item_id=news_id, body=body)
        session.add(comment)
        session.commit()

        return jsonify({"success": True, "comment_id": comment.id}), 201
    except Exception as exc:
        session.rollback()
        return jsonify({"error": True, "message": str(exc), "code": "SERVER_ERROR"}), 500
    finally:
        session.close()


@comments_bp.route("/news/<int:news_id>/comments", methods=["GET"])
def get_comments(news_id: int):
    """Retourne les commentaires d'une nouvelle, ordre chronologique."""
    session = _get_session()
    try:
        comments = (
            session.query(NewsComment)
            .filter_by(news_item_id=news_id)
            .order_by(NewsComment.created_at.asc())
            .all()
        )
        return jsonify({
            "news_id": news_id,
            "comments": [
                {"id": c.id, "body": c.body, "created_at": c.created_at.isoformat()}
                for c in comments
            ],
        })
    finally:
        session.close()
