#!/usr/bin/env bash
# Rehab RCH Agent v2 — Oracle Cloud Free Tier setup (Ubuntu 22.04/24.04)
# Usage (on the VM):
#   git clone https://github.com/<yourname>/rehab-rch-agent.git
#   cd rehab-rch-agent
#   bash scripts/setup_oracle.sh
set -euo pipefail

echo "==> Updating system..."
sudo apt update && sudo apt upgrade -y

echo "==> Installing Python, pip, git..."
sudo apt install -y python3 python3-pip python3-venv git

echo "==> Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> Created .env from template — EDIT IT NOW (nano .env):"
  echo "    TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, STAFF_SHEET_ID..."
fi

if [ ! -f credentials.json ]; then
  echo "==> NOTE: copy your Google service-account credentials.json here:"
  echo "    scp credentials.json ubuntu@<VM-IP>:~/rehab-rch-agent/"
fi

echo "==> Installing systemd service (auto-restart on reboot)..."
sudo cp systemd/rehab-agent.service /etc/systemd/system/rehab-agent.service
sudo systemctl daemon-reload
sudo systemctl enable rehab-agent

echo ""
echo "Setup complete. Next steps:"
echo "  1) nano .env            # fill in tokens/keys"
echo "  2) test:  .venv/bin/python bot.py   (Ctrl+C to stop)"
echo "  3) start: sudo systemctl start rehab-agent"
echo "  4) logs:  sudo journalctl -u rehab-agent -f"
