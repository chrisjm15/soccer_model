@echo off
REM ============================================================
REM  One-off check of the Big-5 luck paper log BEFORE Friday.
REM  Fetches this week's La Liga / Bundesliga / Serie A / Ligue 1
REM  AH odds (~8 Odds API credits), maps team names, prints the
REM  bets it WOULD log. Writes nothing (dry run).
REM ============================================================
set "PROJECT=C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
set "PY=C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=python"
set PYTHONIOENCODING=utf-8
cd /d "%PROJECT%"
"%PY%" scripts\test_luck_paper.py
"%PY%" scripts\luck_paper_big5.py log --dry-run
echo.
echo  If you see "UNMAPPED team names", paste this window to Claude.
pause
