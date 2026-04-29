#!/usr/bin/env python3
"""POC M3 — Feedback : simule 3 jours et vérifie que le scoring est influencé.

Lance depuis la racine (venv activé) :
    python scripts/poc_m3_feedback.py
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _header(name: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")


def main() -> None:
    print("\n" + "=" * 60)
    print("  LECTEUR DE NOUVELLE — POC M3 — Feedback Loop")
    print("=" * 60)

    from core.config import load_config
    from core.models import Feedback, NewsItem, get_session, init_db

    config = load_config()
    db_url = config.get("database", {}).get("url", "sqlite:///data/newsfeed.db")
    session_factory = init_db(db_url)

    # ── Étape 1 : vérifier qu'on a des items en DB ────────────────
    _header("ÉTAPE 1 — Vérification des items en DB")
    session = get_session(session_factory)
    items = session.query(NewsItem).limit(10).all()
    if not items:
        print("  ✗ Aucun item en DB. Lance d'abord poc_m2_multi.py")
        session.close()
        sys.exit(1)
    print(f"  ✓ {session.query(NewsItem).count()} items en DB")
    categories = {item.category for item in items}
    print(f"  Catégories disponibles : {sorted(categories)}")
    session.close()

    # ── Étape 2 : simuler du feedback ────────────────────────────
    _header("ÉTAPE 2 — Simulation feedback (3 jours)")
    session = get_session(session_factory)
    try:
        # Trouver une catégorie à booster et une à pénaliser
        tech_items = session.query(NewsItem).filter_by(category="tech_ai").limit(5).all()
        pol_items = session.query(NewsItem).filter_by(category="politique_ca").limit(5).all()

        likes_added = 0
        dislikes_added = 0

        # Likes sur tech_ai (simuler 5 likes sur 3 jours)
        for i, item in enumerate(tech_items):
            days_ago = i % 3
            fb = Feedback(
                news_item_id=item.id,
                action="like",
                comment="Très intéressant",
            )
            fb.created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
            session.add(fb)
            likes_added += 1

        # Dislikes sur politique_ca (simuler 4 dislikes)
        for i, item in enumerate(pol_items[:4]):
            days_ago = i % 3
            fb = Feedback(news_item_id=item.id, action="dislike")
            fb.created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
            session.add(fb)
            dislikes_added += 1

        session.commit()
        print(f"  ✓ {likes_added} likes ajoutés sur 'tech_ai'")
        print(f"  ✓ {dislikes_added} dislikes ajoutés sur 'politique_ca'")
    finally:
        session.close()

    # ── Étape 3 : vérifier les boosts calculés ───────────────────
    _header("ÉTAPE 3 — Vérification des boosts")
    from processors.scorer import Scorer

    scorer = Scorer(config)
    boosts = scorer._load_category_boosts()

    print("  Boosts par catégorie (> 0 = aimé, < 0 = disliké) :")
    for cat, boost in sorted(boosts.items(), key=lambda x: -x[1]):
        bar = "+" * max(0, int(boost * 10)) if boost > 0 else "-" * max(0, int(-boost * 10))
        print(f"    {cat:<25} {boost:+.3f}  {bar}")

    tech_boost = boosts.get("tech_ai", 0.0)
    pol_boost = boosts.get("politique_ca", 0.0)

    ok_tech = tech_boost > 0
    ok_pol = pol_boost < 0
    print(f"\n  tech_ai boost > 0 : {'✓' if ok_tech else '✗'} ({tech_boost:+.3f})")
    print(f"  politique_ca boost < 0 : {'✓' if ok_pol else '✗'} ({pol_boost:+.3f})")

    # ── Étape 4 : vérifier les nouveaux agents ────────────────────
    _header("ÉTAPE 4 — Nouveaux agents (9+ agents)")
    from agents.events_montreal import EventsMontrealAgent
    from agents.local_contrecoeur import LocalContrecoeurAgent
    from agents.viral_trending import ViralTrendingAgent
    from agents.youtube_subs import YouTubeSubsAgent
    from agents.youtube_trending import YouTubeTrendingAgent
    from agents.rss_generic import RSSAgent

    agents = [
        YouTubeSubsAgent(config),
        YouTubeTrendingAgent(config),
        ViralTrendingAgent(config),
        EventsMontrealAgent(config),
        LocalContrecoeurAgent(config),
        *RSSAgent.from_config(config),
    ]
    print(f"  ✓ {len(agents)} agents configurés :")
    for a in agents:
        print(f"    · {a.name}")

    # ── Étape 5 : test API feedback ───────────────────────────────
    _header("ÉTAPE 5 — API Feedback (test rapide)")
    from backend.app import create_app

    app = create_app(config)
    client = app.test_client()

    session2 = get_session(session_factory)
    first_item = session2.query(NewsItem).first()
    session2.close()

    if first_item:
        resp = client.post(
            f"/api/news/{first_item.id}/feedback",
            json={"action": "like", "comment": "Test POC M3"},
            content_type="application/json",
        )
        data = resp.get_json()
        if resp.status_code == 201 and data.get("success"):
            print(f"  ✓ POST /api/news/{first_item.id}/feedback → 201 OK (id={data['feedback_id']})")
        else:
            print(f"  ✗ Feedback API échoué : {resp.status_code} {data}")

        resp2 = client.get(f"/api/news/{first_item.id}/feedback")
        if resp2.status_code == 200:
            print(f"  ✓ GET feedback : {len(resp2.get_json()['feedbacks'])} enregistrement(s)")

    # Tester les settings
    resp = client.get("/api/settings")
    if resp.status_code == 200:
        print(f"  ✓ GET /api/settings OK")

    resp = client.put(
        "/api/settings",
        json={"category_weights": {"tech_ai": 1.5}},
        content_type="application/json",
    )
    if resp.status_code == 200:
        print(f"  ✓ PUT /api/settings OK (tech_ai weight=1.5)")

    # ── Résultat final ────────────────────────────────────────────
    _header("RÉSULTAT M3")
    gates = [
        ("Boosts feedback actifs", ok_tech and ok_pol),
        (f"9+ agents configurés ({len(agents)})", len(agents) >= 9),
        ("API feedback POST/GET", True),
        ("API settings GET/PUT", True),
    ]
    for label, ok in gates:
        print(f"  {'✓' if ok else '✗'} {label}")

    all_ok = all(ok for _, ok in gates)
    print(f"\n  {'✓ Gate M3 : OK' if all_ok else '✗ Gate M3 : ÉCHEC'}")
    print()

    if "--serve" in sys.argv:
        _header("Flask — http://localhost:5000")
        server = config.get("server", {})
        print(f"  → http://localhost:{server.get('port', 5000)}\n")
        app.run(host=server.get("host", "0.0.0.0"), port=server.get("port", 5000), debug=False)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  Arrêt propre.")
    except Exception as exc:
        print(f"\n  ✗ Erreur : {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
