@echo off
REM ============================================================
REM  Creates 3 Windows scheduled tasks for the soccer model.
REM  Safe to run again (it replaces them). Remove with REMOVE_SCHEDULE.bat
REM   (Fri 12:30 AU prices task removed 28 Oct - Chris uses automatic prices only)
REM   - Tue + Fri 13:00   STATUS.bat opens (report)
REM   - Tue + Fri 13:15   git push runs in the background
REM   - Fri 17:00         this round's EPL bets are posted to Telegram
REM  The 12:00 settle/predict task you already have is unchanged.
REM ============================================================
set "P=C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"

schtasks /delete /f /tn "Soccer Model - AU prices" >nul 2>&1
schtasks /create /f /tn "Soccer Model - Status" /sc weekly /d TUE,FRI /st 13:00 /tr "\"%P%\STATUS.bat\""
schtasks /create /f /tn "Soccer Model - Telegram" /sc weekly /d FRI /st 17:00 /tr "\"%P%\scripts\telegram_send.bat\""
schtasks /create /f /tn "Soccer Model - Push" /sc weekly /d TUE,FRI /st 13:15 /tr "\"%P%\scripts\push_quiet.bat\""

echo.
echo  Check: the three tasks should be listed below with a Next Run Time.
schtasks /query /tn "Soccer Model - Status"
schtasks /query /tn "Soccer Model - Push"
schtasks /query /tn "Soccer Model - Telegram"
echo.
pause
