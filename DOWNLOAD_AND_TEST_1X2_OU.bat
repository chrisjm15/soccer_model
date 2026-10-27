@echo off
REM ============================================================
REM  Research test: does the model beat the close in 1X2 / O/U 2.5?
REM  1. Downloads full football-data CSVs (Big 5, 2020-26, ~30 files, ~1 min).
REM  2. Runs the line-movement / CLV test. Read-only for the live model.
REM  Report: output\backtest_results\ou_1x2_clv_report.txt
REM ============================================================
set "PROJECT=C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
set "PY=C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=python"
set PYTHONIOENCODING=utf-8
cd /d "%PROJECT%"

"%PY%" scripts\download_full_footballdata.py
if errorlevel 1 (
    echo.
    echo  Some downloads failed. Click again later - finished files are kept.
    pause
    exit /b 1
)
echo.
echo  Running the test (about 1 minute)...
"%PY%" scripts\ou_1x2_clv_check.py
echo.
echo  Done. Tell Claude: "1X2/OU test ran".
pause
