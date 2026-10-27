@echo off
REM ============================================================
REM  AU price sheet - use AFTER the Friday 12:00 predict run.
REM  1. Adds this week's flagged bets to the sheet (keeps old rows).
REM  2. Opens the sheet in Excel for you to type AU prices.
REM ============================================================
set "PROJECT=C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
set "PY=C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=python"
set PYTHONIOENCODING=utf-8
cd /d "%PROJECT%"

"%PY%" scripts\au_prices.py prepare
if errorlevel 1 (
    echo.
    pause
    exit /b 1
)

echo.
echo  ------------------------------------------------------------
echo  HOW TO FILL IN THE SHEET
echo  - One row per flagged bet. Column "au_market" says which
echo    market to look for at each AU book.
echo  - Type the decimal price in bet365_price, sportsbet_price,
echo    ladbrokes_price, tab_price, betfair_back_price (the blue
echo    BACK price, before commission) or other_price + other_book.
echo  - Leave a cell empty if the book does not offer that market.
echo  - Do not change the first 10 columns.
echo  - Save (if Excel asks, choose "Keep Current Format"), close
echo    Excel, then double-click STATUS.bat to see the comparison.
echo  ------------------------------------------------------------
start "" "%PROJECT%\output\paper_trading\au_prices.csv"
echo.
pause
