@echo off
REM Cowork session 18: lets the Status / Push / Telegram tasks catch up if the PC was asleep, and wake the PC.
REM Safe to run again. Result saved to output\schedule_check.txt
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer\scripts\fix_schedule.ps1"
echo.
echo  Every line under AFTER should say catch-up=True wake=True
pause
