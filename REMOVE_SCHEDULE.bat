@echo off
REM Removes the 3 tasks created by SETUP_SCHEDULE.bat (not the 12:00 settle/predict task).
schtasks /delete /f /tn "Soccer Model - AU prices"
schtasks /delete /f /tn "Soccer Model - Status"
schtasks /delete /f /tn "Soccer Model - Push"
pause
