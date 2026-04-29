#!/bin/bash
# ============================================================
# Lecteur de nouvelle — Installation production
# ============================================================
# Usage : bash deploy/install.sh
# ============================================================

set -e

PROJECT=/home/vhds/NewsFeed
USER=vhds

echo ""
echo "=== Installation Lecteur de nouvelle ==="
echo ""

# 1. Nginx
echo "→ Configuration Nginx..."
if command -v nginx &> /dev/null; then
    sudo cp "$PROJECT/deploy/nginx.conf" /etc/nginx/sites-available/newsfeed
    sudo ln -sf /etc/nginx/sites-available/newsfeed /etc/nginx/sites-enabled/newsfeed
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t && sudo systemctl reload nginx
    echo "  ✓ Nginx configuré"
else
    echo "  ⚠ Nginx non installé : sudo apt install nginx"
fi

# 2. Systemd — Flask
echo "→ Service Flask (Gunicorn)..."
sudo cp "$PROJECT/deploy/newsfeed.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable newsfeed.service
sudo systemctl restart newsfeed.service
echo "  ✓ newsfeed.service actif"

# 3. Systemd — Cron
echo "→ Timer cron 6h00..."
sudo cp "$PROJECT/deploy/newsfeed-cron.service" /etc/systemd/system/
sudo cp "$PROJECT/deploy/newsfeed-cron.timer"   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable newsfeed-cron.timer
sudo systemctl start  newsfeed-cron.timer
echo "  ✓ newsfeed-cron.timer actif"
systemctl list-timers newsfeed-cron.timer --no-pager 2>/dev/null || true

# 4. Logrotate
echo "→ Logrotate..."
sudo cp "$PROJECT/deploy/logrotate.conf" /etc/logrotate.d/newsfeed
sudo logrotate --debug /etc/logrotate.d/newsfeed &>/dev/null && echo "  ✓ Logrotate configuré" || echo "  ⚠ Logrotate debug a des warnings (normal)"

# 5. Vérification
echo ""
echo "=== Vérification ==="
echo ""
sleep 2
if curl -sf http://localhost:5000/api/health > /dev/null 2>&1; then
    echo "  ✓ API accessible sur http://localhost:5000"
else
    echo "  ⚠ API non accessible encore (Gunicorn démarre...)"
    echo "    → journalctl -u newsfeed -n 20"
fi

echo ""
echo "=== Commandes utiles ==="
echo "  journalctl -u newsfeed -f              # logs Flask"
echo "  journalctl -u newsfeed-cron -f         # logs pipeline"
echo "  systemctl list-timers                   # prochain lancement"
echo "  python scripts/daily_monitor.py        # monitoring manuel"
echo "  python scripts/run_pipeline.py --dry   # test config pipeline"
echo ""
