# Handoff

CLAUDE.md is already loaded. Read `SESSION_LOG_COWORK.md` only. Use `docs/INDEX.md` to locate files if needed — do not read files preemptively.

## Current state
- Live EPL AH prediction pipeline fully operational (`run.py predict`, `run.py update`, `run.py results`)
- Odds source: Matchbook + playup via `regions='uk,au'` — ceiling for The Odds API free tier on AH. Bet365/Ladbrokes not available.
- Target market: EPL AH only, 7% edge threshold
- Paper trading active — first results in: 3W 2L, +$13.00, ROI +26% (5 bets, $50 staked)
- 4 bets pending settlement from May 9-10 weekend

## Next actions
1. **Monday AEST:** `python run.py update` then `python run.py results` — settle the 4 May 9-10 flagged bets
2. Review results, note any pattern on the two large-edge bets (Brentford +1.50 at 19.2%, Wolves +1.75 at 17.6%)
3. **Thursday AEST:** `python run.py predict` for GW38 (final EPL round)

## Pending flagged bets (May 9-10)
| Match | Bet | Edge |
|---|---|---|
| Liverpool vs Chelsea | Chelsea +0.50 Away | +9.0% |
| Man City vs Brentford | Brentford +1.50 Away | +19.2% |
| Brighton vs Wolves | Wolves +1.75 Away | +17.6% |
| Sunderland vs Man United | Sunderland +0.50 Home | +9.8% |

## CLI launch
```
cd "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
claude --model claude-sonnet-4-6
/effort max
```
