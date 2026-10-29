@echo off
REM One-off (Cowork session 18): commit the session 18 files, then push. Safe to run once; delete afterwards.
cd /d "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
git add .gitignore CLAUDE.md COWORK_HANDOFF_PROMPT.md SESSION_LOG_COWORK.md docs/INDEX.md docs/RESEARCH_SESSION_17.md docs/FUTURE_DEVELOPMENT.md archive/session_logs/SESSION_LOG_SESSION_17.md FIX_SCHEDULE.bat LINEUPS_FETCH_AND_TEST.bat SCANDI_UPDATE.bat COMMIT_SESSION_18.bat scripts/fix_schedule.ps1 scripts/live_status.py experiment/load_sofascore.py scripts/live_rule_oos_check.py scripts/advanced_research.py scripts/advanced_research2.py output/backtest_results/live_rule_oos_report.txt output/backtest_results/advanced_A.txt output/backtest_results/advanced_J.txt README.md requirements.txt docs/WEEKLY_SCHEDULE.md scripts/luck_paper_big5.py scripts/stop_date_analysis.py scripts/lineup_research.py scripts/test_understat_lineups.py scripts/fixtures/understat_match_28778_rosters.html scrapers/understat_lineups.py experiment/offseason_2027 output/backtest_results/stop_date_report.txt output/backtest_results/lineup_report.txt
git commit -m "Session 18: Friday pre-flight, schedule catch-up fix, stop-date analysis + price-error fix, off-season ratings fix (not wired in), lineup research tooling"
git push
git status -sb
pause
