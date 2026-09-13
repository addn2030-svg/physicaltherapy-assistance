# 24/7 Hosting — Oracle Cloud Free Tier

Best free option: Oracle Cloud **Always Free** VM (Ampere A1 or E2 Micro),
Ubuntu 22.04/24.04. Estimated cost: **$0/month** for department usage.

## 1. Create the VM
1. Sign up at https://cloud.oracle.com (Always Free account).
2. Compute → Create Instance:
   - Image: **Ubuntu 22.04** (or 24.04)
   - Shape: **Ampere A1** (free: up to 4 OCPU / 24 GB) or E2 Micro
   - Add your SSH public key.
3. Note the public IP.

## 2. First login
```bash
ssh ubuntu@<VM-PUBLIC-IP>
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv git -y
```

## 3. Clone + install
```bash
git clone https://github.com/<yourname>/rehab-rch-agent.git
cd rehab-rch-agent
bash scripts/setup_oracle.sh
```

Or manually:
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
nano .env   # TELEGRAM_BOT_TOKEN, GEMINI_API_KEY, STAFF_SHEET_ID...
```

Copy credentials:
```bash
# from your laptop:
scp credentials.json ubuntu@<VM-IP>:~/rehab-rch-agent/
scp staff_allowlist.json ubuntu@<VM-IP>:~/rehab-rch-agent/   # if not using Sheets
```

Copy knowledge files:
```bash
scp SOP.pdf "Department Guideline.docx" ubuntu@<VM-IP>:~/rehab-rch-agent/knowledge/
```

## 4. Test run
```bash
.venv/bin/python bot.py
# In Telegram: /start → welcome. Ctrl+C to stop.
```

## 5. Run 24/7 with systemd (auto-restart on reboot/crash)
```bash
sudo cp systemd/rehab-agent.service /etc/systemd/system/rehab-agent.service
sudo systemctl daemon-reload
sudo systemctl enable rehab-agent
sudo systemctl start rehab-agent
sudo systemctl status rehab-agent
sudo journalctl -u rehab-agent -f   # live logs
```

The bot automatically restarts after power outages, reboots, or updates.

## 6. Updates
```bash
cd ~/rehab-rch-agent
git pull
.venv/bin/pip install -r requirements.txt
sudo systemctl restart rehab-agent
```

## Security checklist
- [ ] `.env`, `credentials.json` present on VM, never committed to GitHub
- [ ] VM firewall: outbound HTTPS only needed (Telegram/Google); no inbound ports required for polling
- [ ] `sudo apt upgrade` monthly; `systemctl status rehab-agent` after reboot
- [ ] Staff offboarding: remove row from the access Sheet (takes effect on next `/start` after `/kb reload` or restart)
