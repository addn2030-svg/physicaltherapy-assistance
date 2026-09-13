#!/usr/bin/env bash
# Rehab RCH Agent — one-command update + restart for the live server.
# Usage (on Oracle VM, first install via scripts/setup_oracle.sh):
#   bash scripts/go_live.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Pulling latest..."
git pull

echo "==> Installing deps..."
.venv/bin/pip install -r requirements.txt

echo "==> Self-test (must be green)..."
.venv/bin/python -m pytest tests/ -q

echo "==> Restarting 24/7 service..."
sudo systemctl restart rehab-agent
sleep 4
sudo systemctl status rehab-agent --no-pager | head -12
echo "--- recent logs ---"
sudo journalctl -u rehab-agent -n 15 --no-pager
echo ""
echo "LIVE ✅  Verify: send /briefing and /schedule to the bot in Telegram."
