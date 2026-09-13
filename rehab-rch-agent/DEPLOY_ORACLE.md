# Go Live — Oracle Cloud Free Tier (24/7, $0/month)

Best free option: Oracle Cloud **Always Free** VM (Ampere A1 or E2 Micro),
Ubuntu 22.04/24.04. Estimated cost: **$0/month** for department usage.

> Why Oracle and not "one click" here? The bot needs outbound access to
> `api.telegram.org` and Google APIs. Any normal server or laptop works;
> Oracle's free tier is simply the best always-on free home for it.

## 0. Collect 3 secrets (5 min, on your phone/laptop)

1. **Telegram token** — message [@BotFather](https://t.me/BotFather) → `/newbot` →
   name it `Rehab RCH Agent` → copy the `123456:AAH...` token.
2. **Gemini key** — https://aistudio.google.com/app/apikey → Create API key → copy.
3. **Your Telegram ID** — message [@userinfobot](https://t.me/userinfobot) → copy the number.

⛔ Paste secrets **only** into `.env` on your server. Never into chat, email, or GitHub.

## 1. Create the VM (10 min)

1. Sign up at https://cloud.oracle.com (Always Free account).
2. Compute → Create Instance:
   - Image: **Ubuntu 22.04** (or 24.04)
   - Shape: **Ampere A1** (free: up to 4 OCPU / 24 GB) or E2 Micro
   - Add your SSH public key (or choose "paste public key" and generate one).
3. Note the public IP.

## 2. Go live (10 min — copy/paste runbook)

```bash
# --- on the VM ---
ssh ubuntu@<VM-PUBLIC-IP>

git clone https://github.com/addn2030-svg/physicaltherapy-assistance.git
cd physicaltherapy-assistance/rehab-rch-agent
git checkout arena/01a09ac7-physicaltherapy-assistance   # until merged to main
bash scripts/setup_oracle.sh
```

The script installs everything, runs the 26-test self-check, and registers
the auto-restart service. Then:

```bash
nano .env
# Set exactly these 3 lines (no spaces around =):
#   TELEGRAM_BOT_TOKEN=123456:AAH...
#   GEMINI_API_KEY=AIza...
#   ALLOWED_TELEGRAM_IDS=123456789     (your Telegram ID; comma-separated for more staff)

.venv/bin/python bot.py
# Now send /start to your bot in Telegram. Welcome message = LIVE. Ctrl+C to stop the test.

sudo systemctl start rehab-agent          # 24/7 mode
sudo journalctl -u rehab-agent -f         # watch live logs
```

The bot now runs 24/7 and **automatically restarts** after reboots, crashes,
or power outages. Add more staff anytime: append their Telegram IDs to
`ALLOWED_TELEGRAM_IDS` and `sudo systemctl restart rehab-agent`.

## 3. Later upgrades (optional, no code changes)

- **Google Drive auto-save + Sheets auth:** follow [docs/GOOGLE_SETUP.md](docs/GOOGLE_SETUP.md),
  copy `credentials.json` to the folder (`scp credentials.json ubuntu@<VM-IP>:~/physicaltherapy-assistance/rehab-rch-agent/`),
  set `STAFF_SHEET_ID` in `.env`, restart the service.
- **Approved SOPs:** copy files into `knowledge/` (or Drive Knowledge Base folder), then `/kb reload` in Telegram.
- **Pre-launch gate:** work through [docs/PRELAUNCH_CHECKLIST.md](docs/PRELAUNCH_CHECKLIST.md)
  (adversarial PHI tests, approvals, pilot testers).

## 4. Operate

```bash
sudo systemctl status rehab-agent     # health
sudo journalctl -u rehab-agent -n 100 # recent logs
cd ~/physicaltherapy-assistance/rehab-rch-agent && git pull && .venv/bin/pip install -r requirements.txt && sudo systemctl restart rehab-agent  # update
```

## Security checklist

- [ ] `.env`, `credentials.json` on the VM only, never committed to GitHub
- [ ] GitHub repository set to **private**
- [ ] VM firewall: outbound HTTPS only needed (Telegram/Google polling — no inbound ports required)
- [ ] `sudo apt upgrade` monthly; verify `systemctl status rehab-agent` after reboot
- [ ] Staff offboarding: remove their ID from `.env` (or set `Status=Suspended` in the Sheet) + restart
