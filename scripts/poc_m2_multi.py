#!/usr/bin/env python3
"""POC M2 — Multi-agents : orchestrateur + dédup + scoring + pipeline.

Lance depuis la racine (venv activé) :
    python scripts/poc_m2_multi.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _header(name: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")


def main() -> None:
    print("\n" + "=" * 60)
    print("  LECTEUR DE NOUVELLE — POC M2 — Multi-agents")
    print("=" * 60)

    from core.config import load_config
    config = load_config()

    t_total = time.time()

    # ── Étape 1 : construire les agents ───────────────────────────
    _header("ÉTAPE 1 — Agents")
    from agents.youtube_subs import YouTubeSubsAgent
    from agents.youtube_trending import YouTubeTrendingAgent
    from agents.rss_generic import RSSAgent

    agents = [
        YouTubeSubsAgent(config),
        YouTubeTrendingAgent(config),
        *RSSAgent.from_config(config),
    ]
    print(f"  {len(agents)} agents configurés :")
    for a in agents:
        print(f"    · {a.name}")

    # ── Étape 2 : orchestrateur ───────────────────────────────────
    _header("ÉTAPE 2 — Orchestrateur (parallèle)")
    from core.orchestrator import Orchestrator

    orchestrator = Orchestrator(agents, config)
    t0 = time.time()
    raw_items, reports = orchestrator.run()
    elapsed_orch = time.time() - t0

    print(f"\n  Résultats par agent ({elapsed_orch:.1f}s total) :")
    for r in sorted(reports, key=lambda x: x.agent_name):
        icon = "✓" if r.status == "success" else "✗"
        print(f"    {icon} {r.agent_name:<30} {r.items_collected:>3} items  {r.duration_seconds:.1f}s")
        if r.error_message:
            print(f"      → {r.error_message}")

    print(f"\n  Total brut : {len(raw_items)} items")

    # ── Étape 3 : déduplication ───────────────────────────────────
    _header("ÉTAPE 3 — Déduplication")
    from core.deduplicator import Deduplicator

    deduplicator = Deduplicator(config)
    t0 = time.time()
    deduped = deduplicator.deduplicate(raw_items)
    print(f"  {len(raw_items)} → {len(deduped)} items après dédup ({time.time()-t0:.1f}s)")

    # ── Étape 4 : scoring ─────────────────────────────────────────
    _header("ÉTAPE 4 — Scoring + sélection top 30")
    from processors.scorer import Scorer

    scorer = Scorer(config)
    t0 = time.time()
    scored = scorer.process(deduped)
    print(f"  {len(deduped)} → {len(scored)} items sélectionnés ({time.time()-t0:.1f}s)")
    print("\n  Distribution des catégories :")
    dist: dict[str, int] = {}
    for item in scored:
        dist[item.category] = dist.get(item.category, 0) + 1
    for cat, count in sorted(dist.items(), key=lambda x: -x[1]):
        bar = "█" * count
        pct = count / len(scored) * 100
        print(f"    {cat:<25} {count:>2}  {bar}  {pct:.0f}%")

    # ── Étape 5 : pipeline ────────────────────────────────────────
    _header("ÉTAPE 5 — Pipeline (résumé → image → audio → DB)")
    from core.pipeline import Pipeline

    pipeline = Pipeline(config)
    t0 = time.time()
    news_items = pipeline.run(scored)
    elapsed_pipeline = time.time() - t0
    print(f"  {len(news_items)} items traités en {elapsed_pipeline:.1f}s")

    ok = sum(1 for i in news_items if i.summary_fr and i.image_path and i.audio_path)
    print(f"  Complets (résumé + image + audio) : {ok}/{len(news_items)}")

    # ── Résultat final ────────────────────────────────────────────
    elapsed_total = time.time() - t_total
    _header(f"RÉSULTAT — {len(news_items)} items — {elapsed_total:.0f}s total")

    agents_ok = sum(1 for r in reports if r.status == "success")
    print(f"  Agents réussis    : {agents_ok}/{len(reports)}")
    print(f"  Items bruts       : {len(raw_items)}")
    print(f"  Après dédup       : {len(deduped)}")
    print(f"  Sélectionnés      : {len(scored)}")
    print(f"  Sauvegardés en DB : {len(news_items)}")
    print(f"  Complets          : {ok}/{len(news_items)}")
    print(f"  Durée totale      : {elapsed_total:.0f}s")

    if elapsed_total < 600:
        print("  ✓ Pipeline < 10 min")
    else:
        print("  ✗ Pipeline > 10 min — optimisation nécessaire")

    print()

    # Démarrer Flask
    _header("API Flask — http://localhost:5000")
    from backend.app import create_app
    app = create_app(config)
    server = config.get("server", {})
    print(f"  → http://localhost:{server.get('port', 5000)}/api/feed/today")
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
