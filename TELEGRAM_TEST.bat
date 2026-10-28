@echo off
REM ============================================================
REM  Telegram check: sends ONE test message to the channel, then
REM  shows (does not send) what Friday's 5pm post would look like.
REM ============================================================
set "PY=C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=python"
set PYTHONIOENCODING=utf-8
cd /d "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
"%PY%" scripts\telegram_post.py test
echo.
echo  ---- Preview of the Friday post (NOT sent) ----
"%PY%" scripts\telegram_post.py preview
echo.
echo  Check the channel for "Test from the other sports model." and tell Claude.
pause
