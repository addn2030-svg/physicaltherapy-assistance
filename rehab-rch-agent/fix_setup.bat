@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==================================================================
echo  Rehab RCH Agent - config fix
echo ==================================================================
echo.

if not exist ".env" (
  echo [FAIL] .env not found in this folder.
  echo        Expected: %CD%\.env
  goto :done
)

rem ---- backup ------------------------------------------------------
copy /y ".env" ".env.backup" >nul
echo [ OK ] Backed up .env  ->  .env.backup
echo.

set "CHANGED=0"

rem ---- OPS_SHEET_ID -------------------------------------------------
findstr /B /C:"OPS_SHEET_ID=" ".env" >nul 2>&1
if errorlevel 1 (
  >>".env" echo.
  >>".env" echo # Operations workbook - the code reads OPS_SHEET_ID, not GOOGLE_SHEETS_ID
  >>".env" echo OPS_SHEET_ID=1dQD79RYWzenLkVqtK2p1GkcfNSzXzXh_owhs9krxQtw
  echo [ADD ] OPS_SHEET_ID
  set "CHANGED=1"
) else (
  echo [SKIP] OPS_SHEET_ID already present
)

rem ---- STAFF_SHEET_ID (intentionally empty) --------------------------
findstr /B /C:"STAFF_SHEET_ID=" ".env" >nul 2>&1
if errorlevel 1 (
  >>".env" echo # Empty on purpose: the allowlist lives in the Telegram_Users tab
  >>".env" echo STAFF_SHEET_ID=
  echo [ADD ] STAFF_SHEET_ID ^(empty^)
  set "CHANGED=1"
) else (
  echo [SKIP] STAFF_SHEET_ID already present
)

rem ---- TELEGRAM_ADMIN_IDS -------------------------------------------
findstr /B /C:"TELEGRAM_ADMIN_IDS=" ".env" >nul 2>&1
if errorlevel 1 (
  >>".env" echo # Required for admin-only commands
  >>".env" echo TELEGRAM_ADMIN_IDS=7398495644
  echo [ADD ] TELEGRAM_ADMIN_IDS
  set "CHANGED=1"
) else (
  echo [SKIP] TELEGRAM_ADMIN_IDS already present
)

echo.
if "%CHANGED%"=="1" (
  echo [ OK ] .env updated.
) else (
  echo [ OK ] .env already had all three keys - nothing changed.
)

echo.
echo ==================================================================
echo  Running setup doctor
echo ==================================================================
echo.

if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" doctor.py > doctor_report.txt 2>&1
) else (
  echo [WARN] venv not found, trying system python...
  python doctor.py > doctor_report.txt 2>&1
)

type doctor_report.txt

echo.
echo ==================================================================
echo  Report saved to: %CD%\doctor_report.txt
echo  Tell Claude "done" and it will read this file for you.
echo ==================================================================

:done
echo.
pause
