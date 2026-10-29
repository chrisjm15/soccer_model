@echo off
REM Cowork session 18: lineup research (backlog item 4). Research only - the live model is not touched.
REM Makes ~2,300 requests to Understat (1 every 1.5 s), the same site the Friday 12:00 update uses. Takes about 1 hour.
REM Do not run it Friday 09:00-13:00. Step 5 checks that the Friday update can still reach Understat. Resumable.
set "PY=C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=python"
set PYTHONIOENCODING=utf-8
cd /d "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
echo === 1. Parser test ===
"%PY%" scripts\test_understat_lineups.py || goto :fail
echo === 2. Probe: first match of each season ===
"%PY%" scrapers\understat_lineups.py probe || goto :fail
echo === 3. Fetch EPL lineups 2020-21 to 2025-26 (about 1 hour) ===
"%PY%" scrapers\understat_lineups.py fetch --seasons 2020-21,2021-22,2022-23,2023-24,2024-25,2025-26 || goto :fail
echo === 4. Research report ===
"%PY%" scripts\lineup_research.py > output\lineup_latest.txt 2>&1
type output\lineup_latest.txt
echo.
echo === 5. Check: can the Friday 12:00 update still reach Understat? ===
"%PY%" -c "import requests; r=requests.get('https://understat.com/getLeagueData/EPL/2026', headers={'User-Agent':'Mozilla/5.0','X-Requested-With':'XMLHttpRequest'}, timeout=30); n=len(r.json().get('dates', [])) if r.ok else 0; print('UNDERSTAT OK - Friday update will work' if n else 'UNDERSTAT NOT OK (status %%s) - tell Claude' %% r.status_code)"
echo.
echo Done. Tell Claude: "lineups fetched".
pause
exit /b 0
:fail
echo.
echo STOPPED at the step above. Tell Claude what it printed.
pause
exit /b 1
