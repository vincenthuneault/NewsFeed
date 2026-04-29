#!/usr/bin/env python3
"""Monitoring quotidien — vérifie l'état du système et alerte si nécessaire.

Usage :
    python scripts/daily_monitor.py          # rapport complet
    python scripts/daily_monitor.py --quiet  # silencieux sauf si erreur
    python scripts/daily_monitor.py --json   # sortie JSON brute
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

QUIET = "--quiet" in sys.argv
JSON_OUT = "--json" in sys.argv


def _p(msg: str) -> None:
    if not QUIET and not JSON_OUT:
        print(msg)


def _check_api(port: int = 5000) -> dict:
    import urllib.request
    try:
        t0 = time.time()
        with urllib.request.urlopen(f"http://localhost:{port}/api/health", timeout=10) as resp:
            data = json.loads(resp.read())
            data["_latency_ms"] = round((time.time() - t0) * 1000)
            return data
    except Exception as exc:
        return {"status": "unreachable", "error": str(exc)}


def main() -> int:
    from core.config import load_config
    from core.models import AgentRun, DailyFeed, NewsItem, get_session, init_db

    config = load_config()
    db_url = config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
    session = get_session(init_db(db_url))

    today = date.today().isoformat()
    now = datetime.now(timezone.utc)
    issues: list[str] = []
    warnings: list[str] = []

    _p(f"\n{'='*55}")
    _p(f"  MONITORING — {today}")
    _p(f"{'='*55}")

    # ── 1. Feed du jour ───────────────────────────────────────────
    _p("\n  Feed du jour")
    feed = session.query(DailyFeed).filter_by(date=today).first()
    if not feed:
        issues.append(f"❌ Aucun fil généré pour {today}")
        _p(f"    ✗ Aucun fil pour {today}")
    elif feed.status != "ready":
        issues.append(f"⚠ Fil {today} en statut '{feed.status}'")
        _p(f"    ⚠ Statut : {feed.status}")
    else:
        _p(f"    ✓ {feed.item_count} items — statut : {feed.status}")

    # ── 2. Agents (dernier run) ───────────────────────────────────
    _p("\n  Derniers runs agents")
    from sqlalchemy import func
    subq = (
        session.query(AgentRun.agent_name, func.max(AgentRun.created_at).label("last"))
        .group_by(AgentRun.agent_name)
        .subquery()
    )
    runs = (
        session.query(AgentRun)
        .join(subq, (AgentRun.agent_name == subq.c.agent_name) &
                    (AgentRun.created_at == subq.c.last))
        .all()
    )
    for run in sorted(runs, key=lambda r: r.agent_name):
        icon = "✓" if run.status == "success" else "✗"
        _p(f"    {icon} {run.agent_name:<28} {run.items_collected:>3} items  {run.duration_seconds:.1f}s")
        if run.status != "success":
            issues.append(f"❌ Agent {run.agent_name} en échec")

    # ── 3. Stockage ───────────────────────────────────────────────
    _p("\n  Stockage")
    import shutil

    db_path = PROJECT_ROOT / "data" / "newsfeed.db"
    db_mb = db_path.stat().st_size / 1_048_576 if db_path.exists() else 0
    images_mb = sum(f.stat().st_size for f in (PROJECT_ROOT / "static" / "images").rglob("*") if f.is_file()) / 1_048_576
    audio_mb = sum(f.stat().st_size for f in (PROJECT_ROOT / "static" / "audio").rglob("*") if f.is_file()) / 1_048_576
    disk = shutil.disk_usage(PROJECT_ROOT)
    disk_free_gb = disk.free / 1_073_741_824

    _p(f"    DB      : {db_mb:.1f} MB")
    _p(f"    Images  : {images_mb:.1f} MB")
    _p(f"    Audio   : {audio_mb:.1f} MB")
    _p(f"    Disque  : {disk_free_gb:.1f} GB libres")

    if disk_free_gb < 1.0:
        issues.append(f"❌ Espace disque critique : {disk_free_gb:.2f} GB")
    elif disk_free_gb < 2.0:
        warnings.append(f"⚠ Espace disque faible : {disk_free_gb:.2f} GB")

    # ── 4. Coûts estimés ─────────────────────────────────────────
    _p("\n  Coûts estimés (Claude Sonnet)")
    total_items = session.query(NewsItem).count()
    month_start = datetime(now.year, now.month, 1)
    items_this_month = session.query(NewsItem).filter(
        NewsItem.created_at >= month_start
    ).count()
    cost_month = items_this_month * (600 * 3.0 + 120 * 15.0) / 1_000_000
    _p(f"    Items ce mois  : {items_this_month}")
    _p(f"    Coût estimé    : ${cost_month:.3f} / 10.00 max")
    if cost_month > 10.0:
        warnings.append(f"⚠ Coût mensuel estimé : ${cost_month:.2f}")

    # ── 5. API health ─────────────────────────────────────────────
    _p("\n  API Flask")
    health = _check_api()
    if health.get("status") == "unreachable":
        issues.append(f"❌ API inaccessible : {health.get('error')}")
        _p(f"    ✗ Inaccessible : {health.get('error')}")
    else:
        _p(f"    ✓ {health['status']} — {health.get('_latency_ms', '?')}ms")

    session.close()

    # ── Résumé ────────────────────────────────────────────────────
    _p(f"\n{'='*55}")
    overall = "OK" if not issues else "ALERTE"
    _p(f"  STATUT : {overall}")
    if issues:
        for i in issues:
            _p(f"  {i}")
    if warnings:
        for w in warnings:
            _p(f"  {w}")
    _p(f"{'='*55}\n")

    if JSON_OUT:
        print(json.dumps({
            "date": today,
            "status": overall,
            "issues": issues,
            "warnings": warnings,
            "feed": {"date": today, "status": feed.status if feed else "missing", "items": feed.item_count if feed else 0},
            "storage": {"db_mb": round(db_mb, 1), "images_mb": round(images_mb, 1), "audio_mb": round(audio_mb, 1), "disk_free_gb": round(disk_free_gb, 1)},
            "cost_month_usd": round(cost_month, 3),
        }, indent=2))

    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
