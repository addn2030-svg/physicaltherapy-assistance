# How to Restart the Bot

## Method 1: Using Keyboard (Recommended)

1. Click on the terminal window where the bot is running
2. Press `Ctrl + C` on your keyboard
3. Wait for the bot to stop (you'll see "Application stopped" or similar message)
4. Run this command to restart:
   ```
   cd C:\Users\RCH-Rehab\physicaltherapy-assistance\rehab-rch-agent
   .\venv\Scripts\python.exe bot.py
   ```

## Method 2: Close Terminal and Open New One

1. Close the terminal window (X button)
2. Open a new terminal in VS Code (Terminal > New Terminal)
3. Run:
   ```
   cd C:\Users\RCH-Rehab\physicaltherapy-assistance\rehab-rch-agent
   .\venv\Scripts\python.exe bot.py
   ```

## What to Look For After Restart:

You should see:
```
INFO | rehab-rch-agent | Staff source=env count=1 active=1
```

Or:
```
INFO | rehab-rch-agent | Staff source=json count=1 active=1
```

This means your Telegram ID (7398495644) is now authorized!

## Then Test on Telegram:

Send `/start` to @Rehab_RCSH_bot and you should get a welcome message instead of "Access denied"
