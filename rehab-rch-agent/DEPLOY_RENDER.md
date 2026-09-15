# Deploy to Render.com (Free Tier)

⚠️ **Important Limitation:** Render's free tier **spins down after 15 minutes of inactivity**. This means:
- Your bot will stop responding when inactive
- First message after sleep takes 30-60 seconds to wake up
- Not ideal for production use, but good for testing

**Better for production:** Oracle Cloud (truly free, always-on) - see [`DEPLOY_ORACLE.md`](DEPLOY_ORACLE.md)

---

## Prerequisites

1. GitHub account
2. Your bot code pushed to a GitHub repository
3. Telegram bot token (from @BotFather)
4. Gemini API key (from https://aistudio.google.com/app/apikey)
5. Your Telegram user ID (from @userinfobot)

---

## Step 1: Prepare Your Repository

Your project already has a [`Dockerfile`](Dockerfile), which Render will use automatically.

Make sure your repository is pushed to GitHub:

```bash
cd C:\Users\RCH-Rehab\physicaltherapy-assistance\rehab-rch-agent

# If not already a git repo:
git init
git add .
git commit -m "Initial commit - Rehab RCH Agent"

# Create a new private repository on GitHub, then:
git remote add origin https://github.com/YOUR-USERNAME/rehab-rch-agent.git
git branch -M main
git push -u origin main
```

⚠️ **Security:** Make sure `.env` and `credentials.json` are in `.gitignore` (they already are)

---

## Step 2: Create Render Account

1. Go to https://render.com
2. Sign up with your GitHub account (easiest option)
3. Authorize Render to access your repositories

---

## Step 3: Create a Background Worker

1. Click **"New +"** → **"Background Worker"**
2. Connect your GitHub repository
3. Configure the service:

### Basic Settings:
- **Name:** `rehab-rch-agent`
- **Region:** Choose closest to Iraq (e.g., Frankfurt or Singapore)
- **Branch:** `main`
- **Runtime:** `Docker`

### Docker Settings:
Render will automatically detect your [`Dockerfile`](Dockerfile) - no changes needed!

### Instance Type:
- Select **"Free"** ($0/month)
- ⚠️ Remember: Free tier sleeps after 15 min inactivity

---

## Step 4: Add Environment Variables

In the Render dashboard, scroll to **"Environment Variables"** and add:

| Key | Value | Notes |
|-----|-------|-------|
| `TELEGRAM_BOT_TOKEN` | `123456:AAH...` | From @BotFather |
| `GEMINI_API_KEY` | `AIza...` | From Google AI Studio |
| `ALLOWED_TELEGRAM_IDS` | `123456789` | Your Telegram ID (comma-separated for multiple users) |

**Optional variables** (if using Google Sheets/Drive):
| Key | Value |
|-----|-------|
| `STAFF_SHEET_ID` | Your Google Sheet ID |
| `GOOGLE_DRIVE_FOLDER_ID` | Your Drive folder ID |

⚠️ **Note:** For Google credentials, you'll need to add them differently (see Step 5)

---

## Step 5: Handle Google Credentials (Optional)

If your bot uses Google Sheets/Drive, you need to add `credentials.json`:

### Option A: Use Environment Variable (Recommended)
1. Convert your `credentials.json` to a single-line string:
```bash
# On Windows PowerShell:
$json = Get-Content credentials.json -Raw
$json -replace "`r`n", "" -replace "`n", ""
```

2. Add as environment variable:
   - Key: `GOOGLE_CREDENTIALS_JSON`
   - Value: (paste the single-line JSON)

3. Update [`config.py`](config.py) to read from environment variable (see code below)

### Option B: Use Render Disk (Persistent Storage)
Render Free tier doesn't include persistent disks, so Option A is better.

---

## Step 6: Deploy

1. Click **"Create Background Worker"**
2. Render will:
   - Clone your repository
   - Build the Docker image
   - Start your bot
3. Watch the logs in real-time

---

## Step 7: Test Your Bot

1. Open Telegram
2. Find your bot (@Rehab_RCSH_bot or whatever you named it)
3. Send `/start`
4. You should get a welcome message

⚠️ **Remember:** After 15 minutes of no activity, the bot will sleep. The next message will take 30-60 seconds to wake it up.

---

## Monitoring & Logs

### View Logs:
- Go to your service in Render dashboard
- Click **"Logs"** tab
- See real-time output

### Check Status:
- **"Live"** = Bot is running
- **"Sleeping"** = Inactive for 15+ minutes (free tier)

---

## Keeping It Awake (Workaround)

To prevent sleeping, you can use a free uptime monitor:

### Option 1: UptimeRobot (Recommended)
1. Sign up at https://uptimerobot.com (free)
2. Create a monitor that pings your bot every 5 minutes
3. ⚠️ Problem: Render background workers don't have HTTP endpoints

### Option 2: Self-Ping
Add this to your [`bot.py`](bot.py):
```python
import asyncio
from datetime import datetime

async def keep_alive():
    """Prevent Render free tier from sleeping"""
    while True:
        print(f"[{datetime.now()}] Keepalive ping")
        await asyncio.sleep(600)  # Every 10 minutes

# In your main() function:
asyncio.create_task(keep_alive())
```

⚠️ **Note:** This still won't prevent sleep on Render's free tier for background workers.

---

## Limitations of Render Free Tier

| Feature | Free Tier | Paid Tier |
|---------|-----------|-----------|
| Always On | ❌ Sleeps after 15 min | ✅ Yes |
| RAM | 512 MB | Up to 16 GB |
| CPU | Shared | Dedicated |
| Build Time | 15 min limit | Unlimited |
| Cost | $0/month | $7+/month |

---

## Upgrading to Paid Tier

If you need 24/7 uptime on Render:

1. Go to your service settings
2. Change instance type to **"Starter"** ($7/month)
3. Bot will stay awake 24/7

**Alternative:** Use Oracle Cloud (free forever, always-on) - see [`DEPLOY_ORACLE.md`](DEPLOY_ORACLE.md)

---

## Troubleshooting

### Bot Not Responding
1. Check logs in Render dashboard
2. Verify environment variables are set correctly
3. Make sure bot token is valid (test with @BotFather)

### "Service Unavailable" After Sleep
- Normal behavior on free tier
- Wait 30-60 seconds for bot to wake up
- Consider upgrading or switching to Oracle Cloud

### Build Failed
1. Check Dockerfile syntax
2. Verify requirements.txt has all dependencies
3. Check build logs for specific errors

### Google Credentials Not Working
1. Verify `GOOGLE_CREDENTIALS_JSON` is set correctly
2. Make sure it's valid JSON (no line breaks)
3. Check that service account has proper permissions

---

## Updating Your Bot

When you push changes to GitHub:

1. Render automatically detects the push
2. Rebuilds the Docker image
3. Redeploys with zero downtime (on paid tier)

Or manually redeploy:
1. Go to Render dashboard
2. Click **"Manual Deploy"** → **"Deploy latest commit"**

---

## Cost Comparison

| Platform | Cost | Always On | Setup Time |
|----------|------|-----------|------------|
| **Render Free** | $0 | ❌ Sleeps | 10 min |
| **Render Paid** | $7/mo | ✅ Yes | 10 min |
| **Oracle Cloud** | $0 | ✅ Yes | 20 min |

**Recommendation:** Start with Render free for testing, then move to Oracle Cloud for production (free + always-on).

---

## Next Steps

1. ✅ Deploy to Render (you are here)
2. Test with `/start` command
3. Add more staff to `ALLOWED_TELEGRAM_IDS`
4. Set up Google Sheets integration (optional)
5. Consider migrating to Oracle Cloud for 24/7 uptime

---

## Support

- **Render Docs:** https://render.com/docs
- **Render Community:** https://community.render.com
- **Your Bot Docs:** [`README.md`](README.md)
- **Oracle Alternative:** [`DEPLOY_ORACLE.md`](DEPLOY_ORACLE.md)
