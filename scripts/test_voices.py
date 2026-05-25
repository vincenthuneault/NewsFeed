#!/usr/bin/env python3
"""Test des voix Gemini 2.5 Pro TTS — génère un MP3 de test par voix.

Usage :
    python scripts/test_voices.py                  # toutes les voix candidates
    python scripts/test_voices.py --voice Charon   # une seule voix
    python scripts/test_voices.py --list           # lister les candidats sans générer

Les MP3 sont sauvegardés dans static/audio/voice_tests/.
Écoute-les pour choisir les voix à assigner aux journalistes.
"""

from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Auto-détection du venv si les dépendances ne sont pas dans le Python système
_venv_site = PROJECT_ROOT / "venv" / "lib"
for _p in _venv_site.glob("python*/site-packages"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
    break

import google.auth.transport.requests
import google.oauth2.service_account
import yaml

_TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
_OUTPUT_DIR = PROJECT_ROOT / "static" / "audio" / "voice_tests"

# Phrase de test — représentative du style journaliste
_TEST_TEXT = (
    "Nouveau sommet entre les États-Unis et le Canada. "
    "Les deux gouvernements ont annoncé aujourd'hui la signature d'un accord commercial "
    "portant sur les exportations technologiques, estimé à douze milliards de dollars. "
    "La mesure entrera en vigueur dès le premier janvier prochain."
)

# Voix candidates — actives (à tester) + backup
CANDIDATES: dict[str, str] = {
    # Voix actives assignées aux journalistes
    "Achernar": "politique_ca — Politique canadienne",
    "Charon":   "politique_qc — Politique québécoise  [À TESTER]",
    "Erinome":  "evenements_mtl — Événements Montréal",
    "Fenrir":   "youtube_trending — Tendances YouTube  [À TESTER]",
    "Garux":    "politique_intl — Politique internationale",
    "Kore":     "youtube_subs — Abonnements YouTube  [À TESTER]",
    "Leda":     "local_contrecoeur — Local Contrecoeur",
    "Puck":     "viral — Contenu viral  [À TESTER]",
    # Backup
    "Zephyr":     "backup",
    "Orbit":      "backup",
    "Sulafat":    "backup",
    "Ganymede":   "backup",
    "Despina":    "backup",
    "Callirrhoe": "backup",
    "Aoede":      "backup",
}


def _load_session() -> google.auth.transport.requests.AuthorizedSession:
    config_path = PROJECT_ROOT / "config" / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    creds_path = config.get("tts", {}).get(
        "credentials_path",
        str(PROJECT_ROOT / "secrets" / "google_tts_credentials.json"),
    )
    credentials = google.oauth2.service_account.Credentials.from_service_account_file(
        creds_path, scopes=_SCOPES
    )
    return google.auth.transport.requests.AuthorizedSession(credentials)


def test_voice(session, voice_name: str) -> tuple[bool, str]:
    """Génère un MP3 de test pour une voix. Retourne (succès, message)."""
    dest = _OUTPUT_DIR / f"test_{voice_name.lower()}.mp3"
    if dest.exists():
        return True, f"[déjà existant] {dest.name}"

    payload = {
        "audioConfig": {"audioEncoding": "MP3"},
        "input": {
            "text": _TEST_TEXT,
            "prompt": "Présentateur de nouvelles professionnel à la radio québécoise. Voix claire et posée.",
        },
        "voice": {
            "languageCode": "fr-CA",
            "modelName": "gemini-2.5-pro-tts",
            "name": voice_name,
        },
    }

    try:
        response = session.post(_TTS_URL, json=payload)
        response.raise_for_status()
        audio_bytes = base64.b64decode(response.json()["audioContent"])
        dest.write_bytes(audio_bytes)
        return True, f"✅ {dest.name} ({len(audio_bytes) // 1024} KB)"
    except Exception as exc:
        return False, f"❌ {voice_name} — {exc}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--voice", help="Tester une seule voix par nom")
    parser.add_argument("--list", action="store_true", help="Lister les candidats sans générer")
    parser.add_argument("--backup-only", action="store_true", help="Tester seulement les voix backup")
    args = parser.parse_args()

    if args.list:
        print("\nVoix candidates :")
        for name, desc in CANDIDATES.items():
            print(f"  {name:<14} — {desc}")
        return

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.voice:
        voices_to_test = {args.voice: CANDIDATES.get(args.voice, "inconnu")}
    elif args.backup_only:
        voices_to_test = {k: v for k, v in CANDIDATES.items() if v == "backup"}
    else:
        voices_to_test = CANDIDATES

    print(f"\nChargement des credentials Google...")
    try:
        session = _load_session()
    except Exception as exc:
        print(f"Erreur credentials : {exc}")
        sys.exit(1)

    print(f"Génération de {len(voices_to_test)} MP3 dans {_OUTPUT_DIR}/\n")
    results = {"ok": [], "fail": []}

    for voice_name, description in voices_to_test.items():
        success, message = test_voice(session, voice_name)
        print(f"  {message}  ({description})")
        (results["ok"] if success else results["fail"]).append(voice_name)

    print(f"\n{'─'*50}")
    print(f"Résultat : {len(results['ok'])} voix OK, {len(results['fail'])} échouées")
    if results["fail"]:
        print(f"Échouées : {', '.join(results['fail'])}")
    print(f"\nFichiers dans : {_OUTPUT_DIR}/")
    print("Pour écouter : ouvre les MP3 dans un lecteur audio ou via l'interface web.")


if __name__ == "__main__":
    main()
