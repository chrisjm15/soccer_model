# Handoff

CLAUDE.md is already loaded. Read `SESSION_LOG_COWORK.md` only. Use `docs/INDEX.md` to locate files if needed — do not read files preemptively.

## Current state
- Live EPL AH pipeline fully operational
- Flagging bug fixed — min odds post-filter now live in `run.py`
- Tottenham alias added — all EPL teams now mapping correctly
- Paper trading: 3W 2L, +$9.10, **ROI +18.2%** (5 settled, bet_flag=True only)
- Calibration: 55-65% zone reliable, 65%+ zone 0W 2L — overconfidence confirmed
- 5 bets logged for final 2 rounds (May 13-18) — settle after season ends
- GW38: 0 bets logged (relegated teams + suspicious lines)
- EPL season ends May 18-19

## Next actions
1. **After May 18-19:** `python run.py update` then `python run.py results` — settle final bets
2. **Pre-season priority:** Large line calibration backtest — see `docs/LARGE_LINE_CALIBRATION.md`

## Priority after results — Large line calibration backtest
See `docs/LARGE_LINE_CALIBRATION.md` for full research notes.
We have 10,617 historical matches with AH lines/odds + 9,867 with Pinnacle odds.
Can measure model calibration error now — no need to wait for paper trading volume.
Sonnet CLI session to build backtest script, then analysis in Cowork.

## Scandinavian Expansion — BACK BURNER
Module 2 (Sofascore) script complete but paused — 403 rate limit block.

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
