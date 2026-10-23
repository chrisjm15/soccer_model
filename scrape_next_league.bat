@echo off
REM ============================================================
REM  Sofascore scraper - one league per click, remembers progress
REM  Safe to copy to Desktop (all paths are absolute).
REM  Progress file: experiment\sofascore_done.txt
REM ============================================================

set "PROJECT=C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
set "STATE=%PROJECT%\experiment\sofascore_done.txt"
set "QUEUE=N1 B1 P1 SC0 T1 SWE NOR DNK FIN"

if not exist "%STATE%" type nul > "%STATE%"

echo.
echo  Completed so far:
type "%STATE%"
echo.

REM ---- find first league in queue not yet marked done ----
set "NEXT="
for %%L in (%QUEUE%) do (
    if not defined NEXT (
        findstr /x /c:"%%L" "%STATE%" >nul || set "NEXT=%%L"
    )
)

if not defined NEXT (
    echo  ALL LEAGUES COMPLETE. Nothing left to scrape.
    echo  Next step: Module 4 merge - mention it to Claude.
    pause
    exit /b 0
)

echo  ------------------------------------------------------------
echo  Next league: %NEXT%  (6 seasons back, roughly 60-110 minutes)
echo  Keep the computer awake - plugged in, lid open, no sleep.
echo  You can close this window to stop; progress is only saved
echo  when a league finishes completely.
echo  ------------------------------------------------------------
echo.

python "%PROJECT%\experiment\load_sofascore.py" --all-seasons --seasons-back 6 --leagues %NEXT%

if %errorlevel% equ 0 (
    echo %NEXT%>>"%STATE%"
    echo.
    echo  SUCCESS - %NEXT% marked complete.
    echo  Click the bat file again any time for the next league.
) else (
    echo.
    echo  FAILED - %NEXT% NOT marked complete, it will retry next click.
    echo  If this was a 403 error, Sofascore has blocked the session.
    echo  Wait until tomorrow and click again.
)
echo.
pause
