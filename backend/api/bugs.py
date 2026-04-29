"""Route POST /api/bugs — rapport de bug depuis l'interface."""

from __future__ import annotations

import json

from flask import Blueprint, current_app, jsonify, request

from core.models import BugReport, get_session, init_db

bugs_bp = Blueprint("bugs", __name__)

_MAX_DESC = 5000


def _get_session():
    config = current_app.config["PROJECT_CONFIG"]
    db_url = config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
    return get_session(init_db(db_url))


@bugs_bp.route("/bugs", methods=["POST"])
def post_bug():
    """Soumet un rapport de bug.

    Body JSON : {"description": "...", "context": {...}}
    """
    data = request.get_json(silent=True) or {}
    description = (data.get("description") or "").strip()

    if not description:
        return jsonify({"error": True, "message": "description requise", "code": "BAD_REQUEST"}), 400
    if len(description) > _MAX_DESC:
        return jsonify({"error": True, "message": f"description trop longue (max {_MAX_DESC})", "code": "BAD_REQUEST"}), 400

    context_raw = data.get("context")
    context_str = json.dumps(context_raw) if context_raw else None

    session = _get_session()
    try:
        report = BugReport(description=description, context=context_str)
        session.add(report)
        session.commit()

        return jsonify({"success": True, "bug_id": report.id}), 201
    except Exception as exc:
        session.rollback()
        return jsonify({"error": True, "message": str(exc), "code": "SERVER_ERROR"}), 500
    finally:
        session.close()
