#!/usr/bin/env bash
# Rehab RCH Agent v2 — Oracle Cloud Free Tier setup (Ubuntu 22.04/24.04)
# Run ONCE on the VM, from inside the rehab-rch-agent folder:
#   git clone https://github.com/addn2030-svg/physicaltherapy-assistance.git
#   cd physicaltherapy-assistance/rehab-rch-agent
#   git checkout arena/01a09ac7-physicaltherapy-assistance  # until merged to main
#   bash scripts/setup_oracle.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Updating system..."
sudo apt update && sudo apt upgrade -y

echo "==> Installing Python, pip, git..."
sudo apt install -y python3 python3-pip python3-venv git

echo "==> Creating virtual environment..."
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "==> Self-test..."
.venv/bin/python -m pytest tests/ -q

if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> Created .env from template."
fi

if [ ! -f credentials.json ]; then
  echo "==> NOTE (optional for now): Google Drive/Sheets stay in demo mode"
  echo "    until you copy credentials.json here + set STAFF_SHEET_ID in .env."
  echo "    Auth works immediately via ALLOWED_TELEGRAM_IDS in .env."
fi

echo "==> Installing systemd service (auto-restart on reboot)..."
APP_DIR="$PWD"
APP_USER="$(whoami)"
sed -e "s|^User=.*|User=${APP_USER}|" \
    -e "s|/home/ubuntu/physicaltherapy-assistance/rehab-rch-agent|${APP_DIR}|g" \
    systemd/rehab-agent.service | sudo tee /etc/systemd/system/rehab-agent.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable rehab-agent

echo ""
echo "Setup complete. To go LIVE:"
echo "  1) nano .env   # set TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, ALLOWED_TELEGRAM_IDS"
echo "  2) test:  .venv/bin/python bot.py   (send /start in Telegram, then Ctrl+C)"
echo "  3) live:  sudo systemctl start rehab-agent"
echo "  4) logs:  sudo journalctl -u rehab-agent -f"
