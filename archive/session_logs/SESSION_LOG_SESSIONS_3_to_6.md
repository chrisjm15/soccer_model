# Session 6 — 2026-05-03

## Status at session end
Live prediction pipeline updated to EPL AH at 7% threshold and working. First real predictions run. Two bets flagged this week. Several output improvements made. Three CLI tasks queued for next session (Wednesday).

## What was done this session
- CLI ran `prompts/CLI_PROMPT_UPDATE_PREDICT.md` — `run.py predict` now outputs EPL AH predictions at 7% threshold. AH odds confirmed available on free tier.
- Verified fixture data is correct (Liverpool vs Chelsea is a real May 9 fixture; Man Utd vs Liverpool today is correctly at 14:30 UTC = 15:30 BST)
- Fixed `date.today()` in run.py to use `datetime.now(timezone.utc)` — now always GMT regardless of system timezone
- Fixed truncated `model/markets.py` in sandbox (file was cut off at line 303 on Linux mount; repaired via bash append)
- Added match date column to output table; sort changed to date-first then edge-descending
- Added H%/D%/A% columns (model's raw 1X2 win probabilities) to the full table
- Added "No Bet" / "*** BET" signal column
- Rewrote flagged bets section to show: exact bet, plain-English outcome, API odds, min odds for AU bookmakers, model probability
- Identified European Handicap vs Asian Handicap distinction — Ladbrokes "Match Handicap" is a 3-way European Handicap, NOT Asian Handicap. Model is calibrated for AH only. Bet365 AU is the cleanest AH source in Australia.

## This week's flagged bets (paper trading)
| Date | Match | Bet | AH Line | Min Odds | API Odds | Edge |
|---|---|---|---|---|---|---|
| 2026-05-04 | Everton vs Man City | Everton Home | +1.00 | 2.07 | 2.14 | +9.2% |
| 2026-05-09 | Liverpool vs Chelsea | Chelsea Away | +0.50 | 1.96 | 1.80 | +9.0% |

Outcome: Everton win, draw, or lose by 1 (push if lose by exactly 1). Chelsea win or draw.

## All EPL matches this week
| Date | Home | Away | H% | D% | A% | AH | Signal |
|---|---|---|---|---|---|---|---|
| 2026-05-03 | Bournemouth | Crystal Palace | 48% | 24% | 28% | -1.00 Away | No Bet (+0.2%) |
| 2026-05-03 | Man Utd | Liverpool | 43% | 23% | 34% | -0.25 Home | No Bet (-3.9%) |
| 2026-05-03 | Aston Villa | Tottenham | 46% | 25% | 29% | -0.25 Home | No Bet (-5.2%) |
| 2026-05-04 | Everton | Man City | 31% | 24% | 45% | +1.00 Home | *** BET (+9.2%) |
| 2026-05-04 | Chelsea | Nott'm Forest | 52% | 22% | 26% | -0.75 Away | No Bet (-0.4%) |
| 2026-05-09 | Liverpool | Chelsea | 42% | 23% | 35% | -0.50 Away | *** BET (+9.0%) |

## Issues identified
- **Bookmaker restriction risk**: Bet365 AU restricts/bans consistent AH winners. Need to spread action across multiple bookmakers.
- **AU odds**: Currently pulling UK bookmaker odds. Min odds calculation is approximate. Should switch to AU region.
- **European vs Asian Handicap**: Ladbrokes AU "Match Handicap" is 3-way European Handicap — incompatible with model. Must use Asian Handicap markets only. Bet365 AU is most reliable for AH in Australia.

## Queued CLI tasks (run Wednesday when tokens reset)

### Task 1 — Switch odds to Australian bookmakers
Change `fetch_epl_ah_odds()` in `scrapers/odds_api.py` to use `regions='au'` instead of `regions='uk'`. Print which AU bookmakers are returned so we can see what's available. Update min-odds note in output to say "AU bookmakers".

### Task 2 — Add `run.py results` command
New command that:
1. Reads `output/paper_trading/log_ah.csv` for rows with empty `actual_ah_result`
2. Looks up actual score from `data/processed/all_merged.csv` (updated by `run.py update`)
3. Calculates AH result (win/loss/push/half-win/half-loss) using same logic as `backtest/multi_market_engine.py`
4. Calculates profit/loss assuming flat $10 paper stake
5. Writes back to log — no manual entry needed
6. Prints a summary: bets settled, running P&L, ROI so far

### Task 3 — Write weekly schedule doc
Create `docs/WEEKLY_SCHEDULE.md` with the exact weekly workflow:
- **Monday AEST**: `python run.py update` then `python run.py results`
- **Thursday AEST**: `python run.py predict` (weekend fixtures)
- **Monday evening AEST (if midweek EPL)**: `python run.py predict` again
- Include AEST times for EPL kickoffs (most are Saturday night / Sunday morning AEST)
- Include reminder to check Bet365 AU for AH market availability

## Next session checklist
- [ ] Run CLI Task 1 (AU region switch)
- [ ] Run CLI Task 2 (results command)
- [ ] Run CLI Task 3 (weekly schedule doc)
- [ ] After Everton vs Man City (May 4): manually note result to verify results command works
- [ ] After Liverpool vs Chelsea (May 9): same

---

# Session 5 — 2026-05-03

## Status at session end
Multi-market analysis complete. EPL Asian Handicap at 7% threshold confirmed as the target market. Live prediction pipeline needs updating to EPL AH. Next CLI task written and ready.

## What was done this session
- Strategic pivot: ran multi-market backtest (1X2, O/U 2.5, AH) against real historical odds with no-vig correction
- Dropped 1X2 (-21% ROI, unviable)
- Identified EPL AH as the only credible signal
- Threshold sweep confirmed 7% as optimal
- Season-on-season trend confirmed signal is real and growing

## Key findings — multi-market backtest (2023-24 to 2025-26, 5051 matches)
| Market | ROI | Bets | Verdict |
|---|---|---|---|
| 1X2 | -21.1% | 3883 | Drop — unviable |
| O/U 2.5 | -4.3% | 2496 | Drop — too thin |
| AH all leagues | -2.8% | 1926 | Drop — EPL signal diluted |
| **EPL AH only** | **+7.1%** | **498** | **Target market** |

## Threshold sweep — EPL AH
| Threshold | Bets | ROI |
|---|---|---|
| 5% | 498 | +7.1% |
| 7% | 419 | +11.3% ← optimal |
| 8% | 368 | +9.8% |
| 10% | 247 | +8.1% |

## Season-by-season EPL AH at 7% threshold
| Season | Bets | ROI |
|---|---|---|
| 2023-24 | ~140 | +2.8% |
| 2024-25 | ~140 | +13.2% |
| 2025-26 | ~139 | +16.2% |

Improving trend — model signal is real and growing.

## Strategic decisions locked
- **Target market: EPL Asian Handicap only**
- **Edge threshold: 7%**
- **Staking: flat stake for paper trading phase**
- **Other leagues: dropped until model is validated on EPL**
- **O/U 2.5 and 1X2: dropped**

## Next action — CLI
Update `run.py predict` to output EPL AH predictions at 7% threshold instead of current O/U 2.5 output. Prompt is at `prompts/CLI_PROMPT_UPDATE_PREDICT.md`.

## Files created this session
- `model/markets.py` (new — 1X2, O/U, AH output layers with no-vig edge calculation)
- `backtest/multi_market_engine.py` (new — multi-market backtest)
- `scripts/threshold_sweep.py` (new — threshold optimisation sweep)
- `prompts/MARKETS_PROMPT_QWEN3.md`
- `prompts/MULTI_MARKET_BACKTEST_GEMMA.md`
- `prompts/THRESHOLD_SWEEP_QWEN3.md`

---

# Session 4 — 2026-05-03

## Status at session end
Fixture bug fixed and pushed. Live prediction pipeline now producing correct fixtures. First valid paper trading predictions logged for week of May 3–9.

## What was done this session
- Wrote `prompts/CLI_PROMPT_FIXTURE_BUG.md` (Cowork)
- CLI ran the prompt and fixed the bug

## Fixture bug — resolved
**Root cause:** Hypothesis B — multi-round stacking. The Odds API returns ~15 fixtures per league across two rounds (~7 days + ~8 days ahead). `fetch_league_odds` had no date filter, so both rounds were passed to the model and fixtures appeared mixed.

**Fix:** 7-day cutoff filter added to `scrapers/odds_api.py`. Any match with `commence_time > now + 7 days` is skipped. One-line change, no interface changes.

**Note on Real Oviedo:** Legitimately in La Liga 2025-26 (promoted from Segunda). Not a bug.

## First valid predictions — week of May 3–9
45 total matches processed. All fixtures verified correct.

| Match | League | P(Ov2.5) | Best Odds | Edge |
|---|---|---|---|---|
| St. Pauli vs Mainz 05 | Bundesliga | 61.0% | 2.08 | +12.9% |
| Real Betis vs Real Oviedo | La Liga | 60.7% | 1.98 | +10.2% |
| Elche vs Alaves | La Liga | 63.5% | 1.82 | +8.6% |
| Freiburg vs Wolfsburg | Bundesliga | 67.0% | 1.70 | +8.2% |

Unmapped teams: None — all 45 teams resolved.

**Caveat:** O/U 2.5 backtest not yet done. Edge figures are model output — not yet validated against historical O/U 2.5 performance with real odds.

## Priority order for next phase

| Priority | Task | Type |
|---|---|---|
| 1 | Backtest O/U 2.5 with real odds | CLI session |
| 2 | Investigate SportsGameOdds free tier | Research (Cowork) |
| 3 | Team news layer — Gemini API design | Design (Cowork) |
| 4 | Nordic leagues investigation | Research (Cowork) |

## Weekly workflow (now working)
```
python run.py update    # Sunday/Monday — ~5 mins
python run.py predict   # Outputs flagged bets — ~30 secs
```
After each gameweek: fill `actual_over25` (TRUE/FALSE) and `profit_loss` in `output/paper_trading/log.csv`

---

# Session 3 — 2026-05-03

## Status at session end
Phase 3 complete and pushed. Live prediction pipeline running but has a **critical fixture data bug** — must be fixed before paper trading results can be trusted. Strategic direction for next phase locked.

## What was built this session (by CLI — not Cowork)
Phase 3 live prediction pipeline, committed and pushed to GitHub:
- `model/live_ratings.py` — latest team ratings lookup from ratings.csv
- `scrapers/team_name_mapper.py` — maps Odds API team names to canonical names
- `run.py predict` — fetches live odds, runs Poisson model, outputs flagged bets ≥8% edge
- `run.py update` — weekly data refresh (understat → footballdata → merge → ratings)
- `output/paper_trading/log.csv` — paper trading tracker initialised

## First live prediction run — 8 matches flagged
| Match | League | P(Ov2.5) | Best Odds | Edge |
|---|---|---|---|---|
| Real Oviedo vs Getafe | La Liga | 53.0% | 2.75 | +16.6% |
| St. Pauli vs Mainz 05 | Bundesliga | 61.0% | 2.18 | +15.1% |
| Crystal Palace vs Everton | EPL | 61.3% | 2.06 | +12.8% |
| Cremonese vs Pisa | Serie A | 56.4% | 2.20 | +11.0% |
| Paris FC vs Brest | Ligue 1 | 61.6% | 1.93 | +9.8% |
| Real Betis vs Real Oviedo | La Liga | 60.7% | 1.92 | +8.6% |
| Elche vs Alaves | La Liga | 63.5% | 1.82 | +8.6% |
| Freiburg vs Wolfsburg | Bundesliga | 67.0% | 1.70 | +8.2% |

**These fixtures are wrong.** Crystal Palace play Bournemouth (not Everton). Real Oviedo is a Segunda División club and should not appear under La Liga. Almost all fixtures appear incorrect.

## Critical bug — fixture data
The Odds API sport key `soccer_spain_la_liga` may be pulling from multiple competitions (Copa del Rey, Segunda, playoffs) or returning matches from multiple upcoming rounds simultaneously. Team name mapper then pairs them incorrectly.

**First thing next CLI session:** Print raw API response before any team mapping. Verify actual match dates and competitions returned. Fix from there.

## The Odds API free tier limitation confirmed
Free tier does NOT include BTTS odds. Includes:
- 1X2 (home/draw/away)
- Spreads (Asian handicap)
- Totals (over/under goals, including O/U 2.5)

Live predictions currently use **Over/Under 2.5** as proxy market. Backtest was calibrated on BTTS so edge figures not directly comparable. Model already outputs P(over 2.5) natively — needs a proper O/U 2.5 backtest with real odds.

BTTS requires paid tier ($79/month). Not worth paying until paper trading shows positive ROI.

## Strategic decisions this session

### Market priority order
1. **Over/Under 2.5** — currently active market, needs proper backtest with real odds
2. **BTTS** — best backtest result (+15.1% ROI) but needs paid API access. Return to after paper trading validates.
3. **1X2** — most liquid, hardest to beat. Lower priority.
4. **O/U 1.5 / O/U 3.5** — less efficient lines, check if available on free tier.

### Data sources to investigate
- **SportsGameOdds** — may have free tier with Pinnacle odds and BTTS. Check before next billing cycle.
- **Pinnacle API** — closed to public July 2025. Email sent to api@pinnacle.com requesting academic/research access. Use as reference price / line movement signal if granted.
- **Google Gemini API (free)** — identified for team news parsing pipeline (high upside edge source).

### Team news layer (future)
Scrape club social media / BBC Sport injury tracker → feed to Gemini API → extract injury/suspension data → apply as match-level adjustment on top of Poisson model. Bookmaker odds lag real team news by 15-30 mins — genuine information edge.

### Leagues
Stick with Big 5 through paper trading phase. Nordic leagues (Swedish Allsvenskan, Norwegian Eliteserien) identified as potentially less efficient for Australian bookmakers — worth investigating after Big 5 validated. Blocked on finding xG data source for Nordic leagues.

## Priority order for next phase

| Priority | Task | Type |
|---|---|---|
| 1 | Fix fixture data bug | CLI session — blocker |
| 2 | Backtest O/U 2.5 with real odds | CLI session |
| 3 | Investigate SportsGameOdds free tier | Research (Cowork) |
| 4 | Team news layer — Gemini API design | Design (Cowork) |
| 5 | Nordic leagues investigation | Research (Cowork) |

## Weekly workflow (once bug is fixed)
```
python run.py update    # Sunday/Monday — ~5 mins
python run.py predict   # Outputs flagged bets — ~30 secs
```
After each gameweek: fill `actual_over25` (TRUE/FALSE) and `profit_loss` in `output/paper_trading/log.csv`

## Files created/modified this session (by CLI)
**GitHub repo (committed and pushed):**
- `model/live_ratings.py` (new)
- `scrapers/team_name_mapper.py` (new)
- `run.py` (updated — predict and update commands added)
- `output/paper_trading/log.csv` (new)

**Local project folder:**
- `SESSION_LOG_COWORK.md` (this file — replaces session 2 log)
- `docs/INDEX.md` (updated)
