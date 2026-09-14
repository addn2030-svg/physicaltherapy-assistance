@echo off
REM Rehab RCH Agent — double-click to update + restart the bot (Windows).
REM Does: git pull, stop any running bot, start a fresh one in a new window.
cd /d "%~dp0"

echo ============================================================
echo  Rehab RCH Bot - update and restart
echo ============================================================
echo.
echo [1/3] Pulling latest code...
git pull
echo.
echo [2/3] Stopping old bot (if any)...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*bot.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('  Stopped PID ' + $_.ProcessId) }"
timeout /t 2 /nobreak >nul
echo.
echo [3/3] Starting bot in a new window...
if not exist "venv\Scripts\python.exe" (
  echo  ERROR: venv not found. Run setup first (python -m venv venv).
  echo.
  pause
  exit /b 1
)
start "Rehab RCH Bot" "%~dp0venv\Scripts\python.exe" bot.py
echo.
echo Done! A new window called "Rehab RCH Bot" is starting.
echo Keep THAT window open while you use Telegram.
echo You can close THIS window now.
echo.
pause
