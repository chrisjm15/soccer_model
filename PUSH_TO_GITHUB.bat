@echo off
REM ============================================================
REM  Push the local commits (made by Claude) to GitHub.
REM ============================================================
cd /d "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
echo  Before push:
git status -sb
echo.
git push
echo.
echo  After push (should NOT say "ahead"):
git status -sb
echo.
pause
