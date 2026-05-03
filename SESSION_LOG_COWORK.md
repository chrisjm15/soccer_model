# Session 4 — 2026-05-03

## Status at session end
Fixture bug prompt written. CLI session not yet run — hit session limit. Ready to go next session.

## What was done this session (Cowork only)
- Read session log and confirmed fixture bug is the blocker
- Wrote `prompts/CLI_PROMPT_FIXTURE_BUG.md` — targeted diagnostic + fix prompt for the CLI

## Next action (first thing next session)
Paste into CLI:
```
Read `CLAUDE.md` and `SESSION_LOG_COWORK.md`, then follow all steps in `prompts/CLI_PROMPT_FIXTURE_BUG.md` exactly.
```

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
