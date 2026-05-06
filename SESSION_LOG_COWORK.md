# Session 8 — 2026-05-06

## Status at session end
All three queued CLI tasks completed. First paper trading results in. 4 bets flagged for May 9-10 weekend. Model and pipeline fully operational.

## What was done this session

### Paper trading result confirmed
- **Everton vs Man City (May 4):** Ended 3-3. Bet was Everton +1.00 Home. Result: **WIN** (+$11.40).

### Task 1 — AU region switch (COMPLETED via Sonnet CLI)
**Finding:** AU-only region returned just `playup`. Bet365, Tab, Sportsbet absent — they don't share AH data with The Odds API at any tier.
**Decision:** Use `regions='uk,au'` combined. Returns Matchbook (UK exchange) + playup (AU).
**Impact:** One match improved 1.82 → 1.91 (Matchbook better price). All others identical.
**Live config:** `regions='uk,au'` committed and pushed.
**Note:** Bet365/Ladbrokes AH data not available via this API regardless of tier. Matchbook + playup is the ceiling for the free plan.

### Task 2 — `run.py results` command (COMPLETED via Sonnet CLI)
Command working. Reads `log_ah.csv`, looks up scores from `all_merged.csv`, calculates AH results including quarter-ball lines, writes P&L at $10 flat stake, prints summary.

### Task 3 — `docs/WEEKLY_SCHEDULE.md` (COMPLETED — written directly in Cowork)
Monday/Thursday workflow, AEST kickoff times, bookmaker notes. Bet365 section updated to reflect Matchbook + playup as actual sources.

### CLAUDE.md updated
Added escalation rule: "needs testing" is not a reason to use Sonnet CLI — Colab QC handles that. Added Colab to Tool Allocation table.

### First paper trading results
5 of 13 bets settled (8 pending May 9-10):

| Date  | Match                         | Score | AH    | Side | Result | P&L     |
|-------|-------------------------------|-------|-------|------|--------|---------|
| May 4 | Everton vs Man City           | 3-3   | +1.00 | Home | Win    | +$11.40 |
| May 3 | Bournemouth vs Crystal Palace | 3-0   | -1.00 | Away | Loss   | -$10.00 |
| May 4 | Chelsea vs Nottm Forest       | 1-3   | -0.75 | Away | Win    | +$10.60 |
| May 3 | Man United vs Liverpool       | 3-2   | -0.25 | Home | Win    | +$11.00 |
| May 3 | Aston Villa vs Tottenham      | 1-2   | -0.25 | Home | Loss   | -$10.00 |

**Running totals: +$13.00 | ROI +26.0% | 3W 2L | $50 staked** (sample too small to read into)

### 4 flagged bets pending — May 9-10

| Match | Bet | Edge | Odds |
|---|---|---|---|
| Liverpool vs Chelsea (May 9) | Chelsea +0.50 Away | +9.0% | 1.80 |
| Man City vs Brentford (May 9) | Brentford +1.50 Away | +19.2% | 1.78 |
| Brighton vs Wolves (May 9) | Wolves +1.75 Away | +17.6% | 1.86 |
| Sunderland vs Man United (May 9) | Sunderland +0.50 Home | +9.8% | 1.97 |

**Watch points:**
- Brentford +1.50 and Wolves +1.75 edges (19.2%, 17.6%) are unusually large — either genuine or model calibration issue. Monitor closely.
- Sunderland are newly promoted — model ratings may be thin. Less reliable prediction.

## Next session checklist
- [ ] Monday AEST: `python run.py update` then `python run.py results` — settle May 9-10 bets
- [ ] Review all 4 flagged bet results and note any pattern (especially the large-edge ones)
- [ ] Thursday AEST: `python run.py predict` for GW38 fixtures (final round of season)
- [ ] Ongoing: watch whether large edges (>15%) are genuine or model overconfidence
