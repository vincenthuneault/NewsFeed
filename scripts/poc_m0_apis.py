#!/usr/bin/env python3
"""POC M0 — Validation de toutes les briques de base.

Lance ce script pour vérifier que l'environnement est prêt :
    python scripts/poc_m0_apis.py

Résultat attendu : X/7 checks passed
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Ajouter la racine du projet au path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _header(name: str) -> None:
    print(f"\n{'='*50}")
    print(f"  CHECK: {name}")
    print(f"{'='*50}")


def check_config() -> bool:
    """1. Config — Chargement depuis YAML."""
    _header("Config (YAML + .env)")
    try:
        from core.config import load_config, get_nested

        config = load_config()
        app_name = get_nested(config, "app.name")
        db_url = get_nested(config, "database.url")
        print(f"  ✓ Config chargée")
        print(f"  ✓ app.name = {app_name}")
        print(f"  ✓ database.url = {db_url}")
        return True
    except Exception as e:
        print(f"  ✗ Erreur : {e}")
        return False


def check_logger() -> bool:
    """2. Logger — Entrée JSON structurée."""
    _header("Logger (JSON structuré)")
    try:
        from core.logger import get_logger, StructuredLogger

        # Utiliser un fichier temporaire pour le test
        logger = get_logger("poc_m0", {"level": "DEBUG", "file": "logs/poc_test.log"})
        logger.info("POC M0 test", extra={"check": "logger", "status": "ok"})
        print(f"  ✓ Logger créé")
        print(f"  ✓ Message JSON écrit dans logs/poc_test.log")

        # Vérifier le fichier
        log_path = PROJECT_ROOT / "logs" / "poc_test.log"
        if log_path.exists():
            last_line = log_path.read_text(encoding="utf-8").strip().split("\n")[-1]
            parsed = json.loads(last_line)
            print(f"  ✓ Format JSON valide : {list(parsed.keys())}")

        StructuredLogger.reset()
        return True
    except Exception as e:
        print(f"  ✗ Erreur : {e}")
        return False


def check_database() -> bool:
    """3. SQLite DB — Tables créées, CRUD OK."""
    _header("SQLite DB (SQLAlchemy)")
    try:
        from core.models import (
            init_db, get_session,
            NewsItem, DailyFeed, Feedback, AgentRun,
        )

        # DB en mémoire pour le test
        SessionFactory = init_db("sqlite:///:memory:", echo=False)
        session = get_session(SessionFactory)

        # CREATE
        item = NewsItem(
            title="Test nouvelle POC",
            source_url="https://example.com/test",
            source_name="POC Test",
            category="tech_ai",
            published_at=datetime.now(timezone.utc),
            summary_fr="Ceci est un résumé test.",
        )
        session.add(item)
        session.commit()
        print(f"  ✓ INSERT NewsItem (id={item.id})")

        # READ
        found = session.query(NewsItem).filter_by(id=item.id).first()
        assert found is not None
        assert found.title == "Test nouvelle POC"
        print(f"  ✓ SELECT NewsItem OK")

        # UPDATE
        found.final_score = 0.85
        session.commit()
        print(f"  ✓ UPDATE NewsItem (score={found.final_score})")

        # DELETE
        session.delete(found)
        session.commit()
        assert session.query(NewsItem).count() == 0
        print(f"  ✓ DELETE NewsItem OK")

        # Vérifier les autres tables
        feed = DailyFeed(date="2026-04-18", status="ready", item_count=0)
        session.add(feed)

        run = AgentRun(agent_name="poc_test", status="success", items_collected=1)
        session.add(run)

        session.commit()
        print(f"  ✓ DailyFeed + AgentRun créés")

        session.close()
        return True
    except Exception as e:
        print(f"  ✗ Erreur : {e}")
        return False


def check_youtube_api() -> bool:
    """4. YouTube Data API — Liste des abonnements."""
    _header("YouTube Data API")
    try:
        from core.config import load_config, get_nested

        config = load_config()
        api_key = get_nested(config, "youtube.api_key")

        if not api_key:
            print("  ⚠ YOUTUBE_API_KEY non configurée (skip)")
            print("  → Ajouter YOUTUBE_API_KEY dans secrets/.env")
            return False

        from googleapiclient.discovery import build

        youtube = build("youtube", "v3", developerKey=api_key)
        request = youtube.videos().list(part="snippet", chart="mostPopular", maxResults=5, regionCode="CA")
        response = request.execute()
        count = len(response.get("items", []))
        print(f"  ✓ YouTube API accessible ({count} vidéos tendances CA)")
        return True
    except Exception as e:
        print(f"  ✗ Erreur : {e}")
        return False


def check_claude_api() -> bool:
    """5. Claude API — Résumé test."""
    _header("Claude API (Anthropic)")
    try:
        from core.config import load_config, get_nested

        config = load_config()
        api_key = get_nested(config, "claude.api_key")

        if not api_key:
            print("  ⚠ ANTHROPIC_API_KEY non configurée (skip)")
            print("  → Ajouter ANTHROPIC_API_KEY dans secrets/.env")
            return False

        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        model = get_nested(config, "claude.model", "claude-sonnet-4-6")

        message = client.messages.create(
            model=model,
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": "Résume en une phrase : Le Canadien de Montréal a gagné 4-2 contre les Leafs.",
            }],
        )
        text = message.content[0].text
        print(f"  ✓ Claude API OK")
        print(f"  ✓ Résumé : {text[:80]}...")
        return True
    except Exception as e:
        print(f"  ✗ Erreur : {e}")
        return False


def check_google_tts() -> bool:
    """6. Google Cloud TTS — Fichier audio test."""
    _header("Google Cloud TTS")
    try:
        from core.config import load_config, get_nested

        config = load_config()
        creds_path = get_nested(config, "tts.credentials_path")

        # Vérifier si les credentials sont configurées
        if not creds_path and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            print("  ⚠ Google TTS credentials non configurées (skip)")
            print("  → Configurer GOOGLE_TTS_CREDENTIALS dans secrets/.env")
            print("    ou GOOGLE_APPLICATION_CREDENTIALS dans l'environnement")
            return False

        from google.cloud import texttospeech

        client = texttospeech.TextToSpeechClient()

        voice_name = get_nested(config, "tts.voice_name", "fr-CA-Wavenet-A")
        language_code = get_nested(config, "tts.language_code", "fr-CA")

        synthesis_input = texttospeech.SynthesisInput(
            text="Ceci est un test du lecteur de nouvelles."
        )
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # Sauvegarder dans un fichier temp
        audio_dir = PROJECT_ROOT / "static" / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        test_path = audio_dir / "poc_test.mp3"

        with open(test_path, "wb") as f:
            f.write(response.audio_content)

        size = test_path.stat().st_size
        print(f"  ✓ Google TTS OK")
        print(f"  ✓ Audio : {test_path} ({size} bytes)")
        return True
    except Exception as e:
        print(f"  ✗ Erreur : {e}")
        return False


def check_sqlite_file() -> bool:
    """7. SQLite fichier — DB persistante sur disque."""
    _header("SQLite fichier (persistant)")
    try:
        from core.config import load_config, get_nested
        from core.models import init_db, get_session, NewsItem

        config = load_config()
        db_url = get_nested(config, "database.url", "sqlite:///data/newsfeed.db")

        # S'assurer que le dossier data/ existe
        data_dir = PROJECT_ROOT / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        SessionFactory = init_db(db_url, echo=False)
        session = get_session(SessionFactory)

        # Test simple
        count = session.query(NewsItem).count()
        print(f"  ✓ DB fichier créée/accessible")
        print(f"  ✓ {count} items existants en base")

        session.close()
        return True
    except Exception as e:
        print(f"  ✗ Erreur : {e}")
        return False


def main() -> None:
    """Exécute tous les checks M0."""
    print("\n" + "=" * 50)
    print("  LECTEUR DE NOUVELLE — POC M0")
    print("  Validation de l'environnement")
    print("=" * 50)

    checks = [
        ("Config (YAML)", check_config),
        ("Logger (JSON)", check_logger),
        ("SQLite (mémoire)", check_database),
        ("YouTube Data API", check_youtube_api),
        ("Claude API", check_claude_api),
        ("Google Cloud TTS", check_google_tts),
        ("SQLite (fichier)", check_sqlite_file),
    ]

    results = []
    for name, fn in checks:
        try:
            ok = fn()
        except Exception as e:
            print(f"  ✗ Exception inattendue : {e}")
            ok = False
        results.append((name, ok))

    # Résumé
    passed = sum(1 for _, ok in results if ok)
    total = len(results)

    print(f"\n{'='*50}")
    print(f"  RÉSULTAT : {passed}/{total} checks passed")
    print(f"{'='*50}")

    for name, ok in results:
        status = "✓" if ok else "✗"
        print(f"  {status} {name}")

    print()

    if passed < total:
        skipped = [name for name, ok in results if not ok]
        print("  Pour compléter les checks manquants :")
        print("  1. Créer secrets/.env avec les clés API")
        print("  2. Configurer Google Cloud credentials")
        print("  3. Relancer : python scripts/poc_m0_apis.py")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
