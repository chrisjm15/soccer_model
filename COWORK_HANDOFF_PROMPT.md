# Handoff

CLAUDE.md is already loaded. Read `SESSION_LOG_COWORK.md` only. Use `docs/INDEX.md` to locate files if needed — do not read files preemptively.

## Current state
- Live EPL AH pipeline fully operational (`run.py predict`, `run.py update`, `run.py results`)
- Odds source: Matchbook + playup via `regions='uk,au'`
- Target market: EPL AH only, 7% edge threshold
- Paper trading: 3W 2L, +$13.00, ROI +26% (5 settled bets). 4 pending from May 9-10.
- AH backtest bug fixed — EPL AH ROI validated at +6.5% (not an artefact)
- **Key calibration finding:** model reliable at 55–65% confidence, overconfident above 65%

## Calibration summary
| Confidence | Win rate | Verdict |
|---|---|---|
| 55–60% | 57% | Reliable ✓ |
| 60–65% | 63% | Reliable ✓ |
| 65%+ | 50% | Overconfident ⚠️ |

## Pending flagged bets (May 9-10)
| Match | Bet | Edge | Zone |
|---|---|---|---|
| Liverpool vs Chelsea | Chelsea +0.50 Away | +9.0% | Reliable ✓ |
| Sunderland vs Man United | Sunderland +0.50 Home | +9.8% | Reliable ✓ |
| Brighton vs Wolves | Wolves +1.75 Away | +17.6% | Overconfident ⚠️ |
| Man City vs Brentford | Brentford +1.50 Away | +19.2% | Overconfident ⚠️ |

## Next actions
1. **Monday AEST:** `python run.py update` then `python run.py results`
2. Note whether the two overconfident-zone bets (Brentford, Wolves) win or lose
3. **Thursday AEST:** `python run.py predict` for GW38 (final EPL round)
4. Future: confidence cap on live model for bets >65% confidence

## CLI launch
```
cd "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
claude --model claude-sonnet-4-6
/effort max
```
