#!/bin/bash
# ============================================================
# Lecteur de nouvelle — Setup initial
# ============================================================

set -e

echo "=== Lecteur de nouvelle — Setup ==="
echo ""

# Vérifier Python 3.11+
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 11 ]); then
    echo "✗ Python 3.11+ requis (trouvé: $PYTHON_VERSION)"
    exit 1
fi
echo "✓ Python $PYTHON_VERSION"

# Créer le venv
if [ ! -d "venv" ]; then
    echo "  Création du venv..."
    python3 -m venv venv
    echo "✓ venv créé"
else
    echo "✓ venv existant"
fi

# Activer le venv
source venv/bin/activate
echo "✓ venv activé"

# Installer les dépendances
echo "  Installation des dépendances..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✓ Dépendances installées"

# Créer les dossiers nécessaires
mkdir -p data logs secrets static/images/defaults static/audio
echo "✓ Dossiers créés"

# Créer le .env template si absent
if [ ! -f "secrets/.env" ]; then
    cat > secrets/.env << 'EOF'
# === Clés API — Lecteur de nouvelle ===

# Anthropic (Claude)
# ANTHROPIC_API_KEY=sk-ant-...

# YouTube Data API
# YOUTUBE_API_KEY=AIza...

# Google TTS — chemin vers le fichier JSON de credentials
# GOOGLE_TTS_CREDENTIALS=/chemin/vers/google_tts_credentials.json
# ou bien :
# GOOGLE_APPLICATION_CREDENTIALS=/chemin/vers/google_tts_credentials.json
EOF
    echo "✓ secrets/.env créé (à remplir)"
else
    echo "✓ secrets/.env existant"
fi

echo ""
echo "=== Setup terminé ==="
echo ""
echo "Prochaines étapes :"
echo "  1. Remplir secrets/.env avec tes clés API"
echo "  2. Activer le venv : source venv/bin/activate"
echo "  3. Lancer le POC : python scripts/poc_m0_apis.py"
