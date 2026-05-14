# Handoff

CLAUDE.md is already loaded. Read `SESSION_LOG_COWORK.md` only. Use `docs/INDEX.md` to locate files if needed — do not read files preemptively.

## Priority for this session
Large line calibration backtest — see `docs/LARGE_LINE_CALIBRATION.md`.

Results already settled (done 2026-05-12). 5 new bets logged for May 13-18 — settle those
at end of week once all matches played.

## Current state
- Live EPL AH pipeline fully operational
- Paper trading: 3W 2L, +$9.10, **ROI +18.2%** (5 settled, bet_flag=True only)
- Calibration: 55-65% zone reliable, 65%+ zone 0W 2L — overconfidence confirmed
- 5 bets logged for final 2 rounds — see session log for details
- EPL season ends ~May 18. Pre-season work starts after.

## Known bugs to fix (next coding session)
1. **Flagging logic inconsistency** — 3 of 5 this week's bets have API odds below their
   own min odds but were still flagged. Edge check and min odds display are inconsistent.
   Single-file fix in `run.py` predict/flagging logic.

## Priority after results — Large line calibration backtest
See `docs/LARGE_LINE_CALIBRATION.md` for full research notes.
We have 10,617 historical matches with AH lines/odds + 9,867 with Pinnacle odds.
Can measure model calibration error now — no need to wait for paper trading volume.
Sonnet CLI session to build backtest script, then analysis in Cowork.

## Scandinavian Expansion — BACK BURNER
Module 2 (Sofascore) script is complete and working but paused due to 403 rate limit block.

### When resuming (separate session):
- Block should have cleared overnight
- E1 already done (5 seasons, 2760 rows saved to `data/proxy/`)
- Run remaining 9 leagues one at a time — N1 first:
  ```
  python "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer\experiment\load_sofascore.py" --all-seasons --seasons-back 5 --leagues N1
  ```
- Then B1, P1, SC0, T1, SWE, NOR, DNK, FIN
- DELAY is now 1.0s — do not reduce

### ⚠️ CRITICAL — HOW TO RUN PYTHON SCRIPTS
Always use plain Windows Terminal. Never paste python commands into Claude Code CLI.

Win key → "Terminal" → Enter → paste command.

## CLI launch (for multi-file / git work only)
```
cd "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
claude --model claude-sonnet-4-6
/effort max
```
