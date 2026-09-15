# Free 24/7 Hosting Options for Rehab RCH Agent

Your bot is already Docker-ready and has deployment scripts. Here are the best **free** platforms to keep it running 24/7:

## 🏆 Best Option: Oracle Cloud (Recommended)

**Cost:** $0/month forever  
**Setup Time:** 20 minutes  
**Reliability:** Excellent (true VM, no sleep)

### Why Oracle Cloud?
- **Always Free tier** with real VMs (not containers)
- No credit card required after trial
- 4 OCPU / 24GB RAM Ampere A1 (ARM) or 1 OCPU / 1GB E2 Micro (x86)
- Never sleeps, true 24/7 uptime
- Your bot already has deployment guide: [`DEPLOY_ORACLE.md`](DEPLOY_ORACLE.md)

### Quick Start:
1. Sign up: https://cloud.oracle.com (Always Free account)
2. Create Ubuntu 22.04 VM (Ampere A1 or E2 Micro)
3. SSH into VM and run:
```bash
git clone https://github.com/YOUR-REPO/physicaltherapy-assistance.git
cd physicaltherapy-assistance/rehab-rch-agent
bash scripts/setup_oracle.sh
nano .env  # Add your tokens
sudo systemctl start rehab-agent
```

**Full guide:** See [`DEPLOY_ORACLE.md`](DEPLOY_ORACLE.md) in this folder

---

## Alternative Free Options

### 2. Render.com
**Cost:** Free tier available  
**Setup Time:** 10 minutes  
**Limitation:** Spins down after 15 min inactivity (not ideal for Telegram bots)

- Connect GitHub repo
- Deploy as "Background Worker"
- Add environment variables
- ⚠️ Free tier sleeps when inactive

### 3. Railway.app
**Cost:** $5 free credit/month (≈500 hours)  
**Setup Time:** 5 minutes  
**Limitation:** Credits run out mid-month

- Connect GitHub repo
- Deploy from Dockerfile
- Add environment variables
- ⚠️ Not truly "always free"

### 4. Fly.io
**Cost:** Free tier (3 shared-cpu VMs)  
**Setup Time:** 15 minutes  
**Limitation:** Requires credit card

```bash
fly launch
fly secrets set TELEGRAM_BOT_TOKEN=xxx GEMINI_API_KEY=xxx
fly deploy
```

### 5. Google Cloud Run
**Cost:** 2M requests/month free  
**Setup Time:** 15 minutes  
**Limitation:** Cold starts, not ideal for polling bots

### 6. Heroku
**Cost:** No longer has free tier  
**Status:** ❌ Discontinued free tier in 2022

---

## 📊 Comparison Table

| Platform | Cost | Always On? | Setup | Best For |
|----------|------|------------|-------|----------|
| **Oracle Cloud** | $0 | ✅ Yes | 20 min | **Production bots** |
| Render | $0 | ❌ Sleeps | 10 min | Testing only |
| Railway | $5/mo credit | ⚠️ Limited | 5 min | Short-term |
| Fly.io | $0 (CC req) | ✅ Yes | 15 min | Alternative to Oracle |
| Google Cloud Run | $0 | ⚠️ Cold start | 15 min | HTTP bots only |

---

## 🎯 Recommendation

**Use Oracle Cloud** - it's the only truly free, always-on option that works perfectly for Telegram bots. Your project already includes:
- ✅ [`Dockerfile`](Dockerfile)
- ✅ [`docker-compose.yml`](docker-compose.yml)
- ✅ [`DEPLOY_ORACLE.md`](DEPLOY_ORACLE.md) - Complete deployment guide
- ✅ `systemd/rehab-agent.service` - Auto-restart service
- ✅ `scripts/setup_oracle.sh` - Automated setup script

---

## Need Help?

1. **Read the deployment guide:** [`DEPLOY_ORACLE.md`](DEPLOY_ORACLE.md)
2. **Check restart instructions:** [`HOW_TO_RESTART.md`](HOW_TO_RESTART.md)
3. **Arabic instructions:** [`RESTART_INSTRUCTIONS_AR.md`](RESTART_INSTRUCTIONS_AR.md)

The entire setup takes ~20 minutes and your bot will run 24/7 with automatic restarts after crashes or reboots.
