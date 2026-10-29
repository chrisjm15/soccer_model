@echo off
REM Cowork session 18: bring Sweden, Norway, Denmark up to date (current season only). Research data only -
REM the live EPL model is not touched. A Chrome window opens for Sofascore: leave it open. About 30-60 minutes.
REM Do not run it Friday 09:00-13:00. Safe to run again (it rewrites the current-season files).
set "PY=C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=python"
set PYTHONIOENCODING=utf-8
cd /d "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
echo === 1. Sofascore xG, current season: SWE NOR DNK ===
"%PY%" experiment\load_sofascore.py --current-only --leagues SWE NOR DNK || goto :fail
echo === 2. football-data odds: Scandinavian files ===
"%PY%" experiment\load_footballdata.py --scandinavian-only || goto :fail
echo === 3. Rebuild the soft-league merge ===
"%PY%" experiment\merge_data.py > output\scandi_update_latest.txt 2>&1 || goto :fail
type output\scandi_update_latest.txt
echo.
echo Done. Tell Claude: "scandi updated".
pause
exit /b 0
:fail
echo.
echo STOPPED at the step above. If it says 403, Sofascore blocked the session - try again tomorrow.
echo Tell Claude what it printed.
pause
exit /b 1
