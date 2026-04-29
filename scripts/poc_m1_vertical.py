#!/usr/bin/env python3
"""POC M1 — Vertical slice complet : YouTube → pipeline → API → frontend.

Lance ce script depuis la racine du projet (venv activé) :
    python scripts/poc_m1_vertical.py

Le script :
1. Collecte 3 vidéos YouTube (tendances CA)
2. Génère les résumés, images et audio via le pipeline
3. Démarre Flask sur http://localhost:5000
4. Affiche les métriques de chaque étape
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _header(name: str) -> None:
    print(f"\n{'='*55}")
    print(f"  {name}")
    print(f"{'='*55}")


def step_agent(config: dict) -> list:
    _header("ÉTAPE 1 — Agent YouTube (tendances CA)")
    from agents.youtube_subs import YouTubeSubsAgent

    agent = YouTubeSubsAgent(config)
    t0 = time.time()
    items = agent.collect()
    elapsed = time.time() - t0

    # Limiter à 3 pour le POC
    items = items[:3]
    print(f"  ✓ {len(items)} vidéos collectées en {elapsed:.1f}s")
    for item in items:
        print(f"    · {item.title[:70]}")
    return items


def step_pipeline(config: dict, items: list) -> list:
    _header("ÉTAPE 2 — Pipeline (résumé → image → audio)")
    from core.pipeline import Pipeline

    pipeline = Pipeline(config)
    t0 = time.time()
    news_items = pipeline.run(items)
    elapsed = time.time() - t0

    print(f"  ✓ Pipeline terminé en {elapsed:.1f}s ({len(news_items)} items)")
    for item in news_items:
        summary_ok = "✓" if item.summary_fr else "✗"
        image_ok = "✓" if item.image_path else "✗"
        audio_ok = "✓" if item.audio_path else "✗"
        print(f"    [{summary_ok} résumé] [{image_ok} image] [{audio_ok} audio] {item.title[:50]}")
    return news_items


def step_flask(config: dict) -> None:
    _header("ÉTAPE 3 — API Flask + Frontend")
    from backend.app import create_app

    app = create_app(config)
    server_config = config.get("server", {})
    host = server_config.get("host", "0.0.0.0")
    port = server_config.get("port", 5000)

    print(f"  ✓ Serveur démarré sur http://{host}:{port}")
    print(f"  → Ouvre http://localhost:{port} dans ton navigateur")
    print(f"  → API : http://localhost:{port}/api/feed/today")
    print(f"\n  Ctrl+C pour arrêter\n")

    app.run(host=host, port=port, debug=False)


def main() -> None:
    print("\n" + "=" * 55)
    print("  LECTEUR DE NOUVELLE — POC M1 — Vertical Slice")
    print("=" * 55)

    from core.config import load_config
    config = load_config()

    t_total = time.time()

    try:
        raw_items = step_agent(config)
        if not raw_items:
            print("\n  ✗ Aucun item collecté, arrêt.")
            sys.exit(1)

        news_items = step_pipeline(config, raw_items)
        if not news_items:
            print("\n  ✗ Pipeline n'a produit aucun item, arrêt.")
            sys.exit(1)

        elapsed_total = time.time() - t_total
        _header(f"RÉSULTAT — {len(news_items)}/3 items — {elapsed_total:.1f}s total")
        for item in news_items:
            print(f"  ✓ [{item.id}] {item.title[:60]}")

        print()
        step_flask(config)

    except KeyboardInterrupt:
        print("\n  Arrêt propre.")
    except Exception as exc:
        print(f"\n  ✗ Erreur : {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
