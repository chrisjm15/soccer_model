@echo off
REM Scheduled (no pause): push Cowork's local commits; result appended to output\push_log.txt
cd /d "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
echo [%date% %time%] >> output\push_log.txt
git push >> output\push_log.txt 2>&1
git status -sb >> output\push_log.txt 2>&1
