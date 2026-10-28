@echo off
REM Scheduled Fri 17:00: post this round's EPL bets to the Telegram channel (no pause). Output: output\telegram_latest.txt
set "PY=C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=python"
set PYTHONIOENCODING=utf-8
cd /d "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
"%PY%" scripts\telegram_post.py send > output\telegram_latest.txt 2>&1
