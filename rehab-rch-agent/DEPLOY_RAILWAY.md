# Deploy Rehab RCH Agent to Railway

**Complete step-by-step guide to deploy your bot to Railway for 24/7 operation**

---

## Prerequisites

- ✅ GitHub account with your code pushed
- ✅ Railway account (free tier available)
- ✅ Your `.env` file with all credentials
- ✅ `credentials.json` file from Google Cloud

---

## Method 1: Deploy via Railway Dashboard (Recommended - No CLI needed)

### Step 1: Create Railway Account

1. Go to: https://railway.app/
2. Click **"Login"** or **"Start a New Project"**
3. Sign in with your **GitHub account** (addn2030-svg)
4. Authorize Railway to access your repositories

### Step 2: Create New Project

1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Choose repository: **`addn2030-svg/physicaltherapy-assistance`**
4. Select branch: **`arena/01a09ac7-physicaltherapy-assistance`**
5. Click **"Deploy Now"**

### Step 3: Configure Root Directory

Railway will try to deploy the entire repository. We need to specify the bot directory:

1. Go to your project **Settings**
2. Find **"Root Directory"** setting
3. Set to: **`rehab-rch-agent`**
4. Click **"Save"**

### Step 4: Add Environment Variables

Click on **"Variables"** tab and add these from your `.env` file:

#### Required Variables

```bash
TELEGRAM_BOT_TOKEN=8707934456:AAHz7LRS9UimT4Fq466YGjwh1aShKOQFaa8
GEMINI_API_KEY=AIzaSyAb8RN6JucHuu7LZFwRLDQ1w2Ijr-QrRx1HLkftdKT97D4Jo0BQ
OPS_SHEET_ID=1dQD79RYWzenLkVqtK2p1GkcfNSzXzXh_owhs9krxQtw
TELEGRAM_ADMIN_IDS=7398495644
ALLOWED_TELEGRAM_IDS=7398495644
GOOGLE_CREDENTIALS_FILE=credentials.json
```

#### Optional Variables (copy from your .env)

```bash
TELEGRAM_BOT_NAME=@Rehab_RCSH_bot
TELEGRAM_CHAT_ID=7398495644
ENROLL_CODE=RCH-2026-STAFF
GOOGLE_SHEETS_ID=1dQD79RYWzenLkVqtK2p1GkcfNSzXzXh_owhs9krxQtw
GOOGLE_PROJECT_ID=named-messenger-508516-k3
SERVICE_ACCOUNT_CLIENT_EMAIL=rehab-bot@named-messenger-508516-k3.iam.gserviceaccount.com
SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
GOOGLE_CALENDAR_ID=
NOTES_VAULT_PATH=
DEMO_MODE=false
LOG_LEVEL=INFO
STAFF_SHEET_ID=
```

**How to add variables:**
1. Click **"+ New Variable"**
2. Enter **Variable Name** (e.g., `TELEGRAM_BOT_TOKEN`)
3. Enter **Value** (paste from your `.env`)
4. Click **"Add"**
5. Repeat for all variables

### Step 5: Add credentials.json File

Railway needs your Google service account credentials:

#### Option A: As Environment Variable (Recommended)

1. Open your `credentials.json` file
2. Copy the entire JSON content
3. In Railway Variables, add:
   - **Name:** `GOOGLE_CREDENTIALS_JSON`
   - **Value:** Paste the entire JSON content
4. The bot will create the file from this variable

#### Option B: As File (Alternative)

1. In Railway, go to **"Settings"**
2. Scroll to **"Volumes"**
3. Click **"Add Volume"**
4. Mount path: `/app/credentials.json`
5. Upload your `credentials.json` file

### Step 6: Configure Build Settings

1. Go to **"Settings"** tab
2. Under **"Build"** section:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
3. Click **"Save Changes"**

### Step 7: Deploy

1. Go to **"Deployments"** tab
2. Click **"Deploy"** or **"Redeploy"**
3. Watch the build logs
4. Wait for deployment to complete (2-5 minutes)

### Step 8: Verify Deployment

Check the logs for:
```
Starting Rehab RCH Agent v2 | dept=Rehabilitation Department — RCH
Staff source=ops-telegram-users count=1 active=1
Bot started successfully
```

Test in Telegram:
1. Open @Rehab_RCSH_bot
2. Send `/start`
3. Should receive welcome message

---

## Method 2: Deploy via Railway CLI

### Step 1: Install Railway CLI

**Windows (PowerShell):**
```powershell
iwr https://railway.app/install.ps1 | iex
```

**Or using npm:**
```bash
npm install -g @railway/cli
```

### Step 2: Login to Railway

```bash
railway login
```

This will open a browser window to authenticate.

### Step 3: Initialize Project

```bash
cd C:\Users\RCH-Rehab\physicaltherapy-assistance\rehab-rch-agent
railway init
```

Select:
- **Create a new project**
- **Name:** `rehab-rch-agent`

### Step 4: Link to GitHub

```bash
railway link
```

Select your GitHub repository.

### Step 5: Add Environment Variables

```bash
# Add all variables from your .env file
railway variables set TELEGRAM_BOT_TOKEN="8707934456:AAHz7LRS9UimT4Fq466YGjwh1aShKOQFaa8"
railway variables set GEMINI_API_KEY="AIzaSyAb8RN6JucHuu7LZFwRLDQ1w2Ijr-QrRx1HLkftdKT97D4Jo0BQ"
railway variables set OPS_SHEET_ID="1dQD79RYWzenLkVqtK2p1GkcfNSzXzXh_owhs9krxQtw"
railway variables set TELEGRAM_ADMIN_IDS="7398495644"
railway variables set ALLOWED_TELEGRAM_IDS="7398495644"
railway variables set GOOGLE_CREDENTIALS_FILE="credentials.json"

# Add all other variables from your .env
```

### Step 6: Add credentials.json

```bash
# Convert credentials.json to base64 and set as variable
railway variables set GOOGLE_CREDENTIALS_JSON="$(cat credentials.json)"
```

### Step 7: Deploy

```bash
railway up
```

This will:
1. Upload your code
2. Install dependencies
3. Start the bot
4. Show deployment logs

### Step 8: Monitor Logs

```bash
railway logs
```

---

## Configuration Files Included

Your repository now includes:

### 1. `railway.json`
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -r requirements.txt"
  },
  "deploy": {
    "startCommand": "python bot.py",
    "healthcheckPath": "/",
    "healthcheckTimeout": 300,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### 2. `nixpacks.toml`
```toml
[phases.setup]
nixPkgs = ["python311", "pip"]

[phases.install]
cmds = ["pip install -r requirements.txt"]

[start]
cmd = "python bot.py"
```

### 3. `Procfile`
```
worker: python bot.py
```

---

## Troubleshooting

### Issue: Build Fails

**Error:** `ModuleNotFoundError: No module named 'X'`

**Solution:**
1. Check `requirements.txt` includes all dependencies
2. Redeploy: `railway up` or click "Redeploy" in dashboard

### Issue: Bot Doesn't Start

**Error:** `TELEGRAM_BOT_TOKEN is not set`

**Solution:**
1. Verify all environment variables are set
2. Check variable names match exactly (case-sensitive)
3. Restart deployment

### Issue: Google Credentials Not Found

**Error:** `credentials.json not found`

**Solution:**
1. Ensure `GOOGLE_CREDENTIALS_JSON` variable is set
2. Or upload `credentials.json` as a file
3. Check file path in `GOOGLE_CREDENTIALS_FILE` variable

### Issue: Bot Crashes Repeatedly

**Check logs:**
```bash
railway logs
```

**Common causes:**
- Invalid Telegram token
- Invalid Gemini API key
- Google Sheets access denied
- Network connectivity issues

**Solution:**
1. Verify all credentials are correct
2. Check Google service account has access to sheets
3. Ensure Gemini API key is valid

### Issue: Can't Access Google Sheets

**Error:** `Permission denied` or `Spreadsheet not found`

**Solution:**
1. Share the Google Sheet with service account email:
   `rehab-bot@named-messenger-508516-k3.iam.gserviceaccount.com`
2. Give "Editor" permissions
3. Redeploy bot

---

## Monitoring Your Bot

### Railway Dashboard

1. Go to: https://railway.app/dashboard
2. Select your project: `rehab-rch-agent`
3. View:
   - **Deployments:** Build history and status
   - **Logs:** Real-time bot logs
   - **Metrics:** CPU, Memory, Network usage
   - **Variables:** Environment configuration

### View Logs

**Via Dashboard:**
- Click on your service
- Go to "Logs" tab
- See real-time output

**Via CLI:**
```bash
railway logs
railway logs --follow  # Follow logs in real-time
```

### Check Status

```bash
railway status
```

### Restart Bot

**Via Dashboard:**
- Click "Restart" button

**Via CLI:**
```bash
railway restart
```

---

## Automatic Deployments

Railway automatically deploys when you push to GitHub:

1. Make changes to your code locally
2. Commit and push:
   ```bash
   git add .
   git commit -m "Update bot features"
   git push origin arena/01a09ac7-physicaltherapy-assistance
   ```
3. Railway automatically detects the push
4. Builds and deploys the new version
5. Zero-downtime deployment

---

## Cost & Limits

### Railway Free Tier

- **$5 credit per month** (enough for your bot)
- **500 hours of execution** (more than enough for 24/7)
- **100 GB bandwidth**
- **1 GB memory**
- **1 vCPU**

### Estimated Usage

Your bot typically uses:
- **Memory:** ~150 MB
- **CPU:** < 5%
- **Bandwidth:** < 1 GB/month
- **Cost:** ~$2-3/month (well within free tier)

### If You Exceed Free Tier

Railway will notify you. You can:
1. Add a payment method (pay only for what you use)
2. Optimize bot to use less resources
3. Switch to another free hosting option

---

## Security Best Practices

### 1. Never Commit Secrets

Ensure `.gitignore` includes:
```
.env
credentials.json
staff_allowlist.json
```

### 2. Rotate Credentials Regularly

- Telegram bot token: Every 6 months
- Gemini API key: Every 6 months
- Google service account: Annually

### 3. Monitor Access Logs

Check Railway logs regularly for:
- Unauthorized access attempts
- PHI blocking events
- Unusual activity patterns

### 4. Enable 2FA

Enable two-factor authentication on:
- GitHub account
- Railway account
- Google Cloud Console

---

## Updating Your Bot

### Method 1: Push to GitHub (Automatic)

```bash
cd C:\Users\RCH-Rehab\physicaltherapy-assistance\rehab-rch-agent
# Make your changes
git add .
git commit -m "Your update message"
git push origin arena/01a09ac7-physicaltherapy-assistance
# Railway automatically deploys
```

### Method 2: Manual Redeploy

**Via Dashboard:**
1. Go to Railway dashboard
2. Click "Redeploy"

**Via CLI:**
```bash
railway up
```

---

## Backup & Recovery

### Backup Strategy

1. **Code:** Backed up on GitHub ✅
2. **Configuration:** Environment variables in Railway ✅
3. **Data:** Google Sheets (auto-saved) ✅
4. **Audit Logs:** Stored in Google Sheets ✅

### Recovery Procedure

If bot fails:

1. **Check logs:**
   ```bash
   railway logs
   ```

2. **Restart bot:**
   ```bash
   railway restart
   ```

3. **Redeploy from last known good version:**
   - Go to "Deployments" tab
   - Find last successful deployment
   - Click "Redeploy"

4. **Rollback code:**
   ```bash
   git log --oneline -10  # Find good commit
   git checkout <commit-hash>
   git push origin arena/01a09ac7-physicaltherapy-assistance --force
   ```

---

## Support & Resources

### Railway Documentation
- Main docs: https://docs.railway.app/
- Deployment guide: https://docs.railway.app/deploy/deployments
- Environment variables: https://docs.railway.app/develop/variables

### Railway Community
- Discord: https://discord.gg/railway
- Forum: https://help.railway.app/

### Your Bot Documentation
- Main README: `README.md`
- Architecture: `docs/ARCHITECTURE.md`
- Security: `docs/SECURITY.md`
- Troubleshooting: `NETWORK_TROUBLESHOOTING.md`

---

## Quick Reference Commands

```bash
# Login to Railway
railway login

# Initialize project
railway init

# Add environment variable
railway variables set KEY="value"

# Deploy
railway up

# View logs
railway logs
railway logs --follow

# Check status
railway status

# Restart bot
railway restart

# Open dashboard
railway open

# Link to GitHub repo
railway link
```

---

## Success Checklist

Before going live, verify:

- [ ] Code pushed to GitHub
- [ ] Railway project created
- [ ] All environment variables set
- [ ] credentials.json uploaded
- [ ] Bot deployed successfully
- [ ] Logs show "Bot started successfully"
- [ ] Test `/start` command in Telegram
- [ ] Test `/help` command
- [ ] Test PHI blocking
- [ ] Test report generation
- [ ] Verify Google Sheets access
- [ ] Verify Google Drive uploads
- [ ] Set up monitoring alerts
- [ ] Document Railway project URL
- [ ] Share access with team (if needed)

---

## Next Steps After Deployment

1. **Monitor for 24 hours** - Watch logs for any issues
2. **Test all features** - Verify everything works in production
3. **Set up alerts** - Configure Railway to notify you of issues
4. **Document** - Update team on new deployment
5. **Train staff** - Ensure everyone knows bot is now 24/7
6. **Backup** - Export current configuration
7. **Plan updates** - Schedule regular maintenance windows

---

**Deployment Guide Version:** 1.0  
**Last Updated:** September 16, 2026  
**Bot Version:** Rehab RCH Agent v2.0.0
