"""Route GET /api/health — rapport de santé complet."""

from __future__ import annotations

import os
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

from flask import Blueprint, current_app, jsonify

from core.models import AgentRun, DailyFeed, Feedback, NewsItem, get_session, init_db

health_bp = Blueprint("health", __name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Coûts Claude Sonnet ($/MTok — approximatif)
_COST_INPUT_PER_MTOK = 3.0
_COST_OUTPUT_PER_MTOK = 15.0
_AVG_INPUT_TOKENS = 600
_AVG_OUTPUT_TOKENS = 120


def _get_session():
    config = current_app.config["PROJECT_CONFIG"]
    db_url = config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
    return get_session(init_db(db_url))


def _dir_size_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return round(total / 1_048_576, 2)


def _file_size_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    return round(path.stat().st_size / 1_048_576, 2)


@health_bp.route("/health")
def health():
    """Rapport de santé : statut global, feed, agents, stockage, coûts."""
    session = _get_session()
    issues: list[str] = []

    try:
        # ── Feed du jour ──────────────────────────────────────────
        today = date.today().isoformat()
        feed = session.query(DailyFeed).filter_by(date=today).first()

        feed_info = {
            "date": today,
            "status": feed.status if feed else "missing",
            "item_count": feed.item_count if feed else 0,
        }
        if not feed or feed.status != "ready":
            issues.append(f"Fil du {today} absent ou incomplet")

        # ── Derniers runs agents ──────────────────────────────────
        from sqlalchemy import func
        subq = (
            session.query(AgentRun.agent_name, func.max(AgentRun.created_at).label("last_run"))
            .group_by(AgentRun.agent_name)
            .subquery()
        )
        last_runs = (
            session.query(AgentRun)
            .join(subq, (AgentRun.agent_name == subq.c.agent_name) &
                        (AgentRun.created_at == subq.c.last_run))
            .all()
        )

        agents_info = []
        for run in last_runs:
            agents_info.append({
                "agent": run.agent_name,
                "status": run.status,
                "items": run.items_collected,
                "duration_s": round(run.duration_seconds, 1),
                "last_run": run.created_at.isoformat() if run.created_at else None,
            })
            if run.status == "failed":
                issues.append(f"Agent {run.agent_name} en échec")

        # ── DB stats ──────────────────────────────────────────────
        total_items = session.query(NewsItem).count()
        total_feedback = session.query(Feedback).count()
        total_feeds = session.query(DailyFeed).filter_by(status="ready").count()

        db_path = PROJECT_ROOT / "data" / "newsfeed.db"
        db_size_mb = _file_size_mb(db_path)

        # ── Stockage ──────────────────────────────────────────────
        images_mb = _dir_size_mb(PROJECT_ROOT / "static" / "images")
        audio_mb = _dir_size_mb(PROJECT_ROOT / "static" / "audio")
        logs_mb = _dir_size_mb(PROJECT_ROOT / "logs")

        disk = shutil.disk_usage(PROJECT_ROOT)
        disk_free_gb = round(disk.free / 1_073_741_824, 2)

        if disk_free_gb < 1.0:
            issues.append(f"Espace disque faible : {disk_free_gb} GB restants")

        # ── Coûts estimés ─────────────────────────────────────────
        items_today = feed.item_count if feed else 0
        items_month = session.query(NewsItem).filter(
            NewsItem.created_at >= datetime(datetime.now().year, datetime.now().month, 1, tzinfo=timezone.utc)
        ).count()

        cost_today = _estimate_cost(items_today)
        cost_month = _estimate_cost(items_month)

        if cost_month > 10.0:
            issues.append(f"Coût mensuel estimé élevé : ${cost_month:.2f}")

        # ── Statut global ─────────────────────────────────────────
        if not issues:
            status = "healthy"
        elif any("absent" in i or "échec" in i for i in issues):
            status = "unhealthy"
        else:
            status = "degraded"

    finally:
        session.close()

    return jsonify({
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "issues": issues,
        "feed": feed_info,
        "agents": agents_info,
        "database": {
            "total_items": total_items,
            "total_feeds": total_feeds,
            "total_feedback": total_feedback,
            "size_mb": db_size_mb,
        },
        "storage": {
            "images_mb": images_mb,
            "audio_mb": audio_mb,
            "logs_mb": logs_mb,
            "disk_free_gb": disk_free_gb,
        },
        "costs_estimated": {
            "today_usd": cost_today,
            "month_usd": cost_month,
            "note": "Estimation basée sur ~600 tokens input + ~120 output par item (Claude Sonnet)",
        },
    })


def _estimate_cost(items: int) -> float:
    input_cost = items * _AVG_INPUT_TOKENS * _COST_INPUT_PER_MTOK / 1_000_000
    output_cost = items * _AVG_OUTPUT_TOKENS * _COST_OUTPUT_PER_MTOK / 1_000_000
    return round(input_cost + output_cost, 4)
