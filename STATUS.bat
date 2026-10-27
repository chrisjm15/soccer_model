@echo off
REM ============================================================
REM  Soccer model - live status report. READ-ONLY, safe any time.
REM  Shows: scheduled runs, flagged bets, CLV checkpoint, AU prices.
REM  A copy is saved to output\status_latest.txt
REM ============================================================
set "PROJECT=C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
set "PY=C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=python"
set PYTHONIOENCODING=utf-8
cd /d "%PROJECT%"

"%PY%" scripts\test_au_prices.py >nul 2>&1
if errorlevel 1 (
    echo  WARNING: AU price self-test FAILED. Numbers below may be wrong. Tell Claude.
    echo.
)

"%PY%" scripts\live_status.py > output\status_latest.txt 2>&1
type output\status_latest.txt
echo.
pause
