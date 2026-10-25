# Handoff

CLAUDE.md is already loaded. Read `SESSION_LOG_COWORK.md` only. Use `docs/INDEX.md` to locate files — do not read files preemptively.
*Last updated: 2026-10-25 (session 15).*

## Strategy verdict (2026-07-12, unchanged — constrains everything below)
- **Big 5 ex-EPL: retired.** Model adds no information beyond the market. No bets there.
- **EPL: live hypothesis, being tested now (2026-27).** Refit M3 b_model +0.245 (p=0.022). OOS expectation at
  1% threshold: ~92 bets/season, +8.9% ROI, CI straddles zero.
- Raw model probabilities and the 7% threshold are retired. Edge = calibrated prob (M3) − consensus no-vig.
- 10-factor large-line layer: superseded, do not build.

## Current state
- Live and automated. Tuesday 12:00 task = update + results. Friday 12:00 task = update + predict.
  Both run `scripts/run_update.ps1`. Check `output/scheduler_log.txt` and `output/predict_latest.txt`.
- Paper log: `output/paper_trading/log_ah.csv`. 2026-27 rows start 2026-10-24 (GW9). First 2 flagged bets:
  Aston Villa +1.00 v Man City (1.83, betonlineag), Sunderland 0.00 v Leeds (2.15, onexbet).
- Season started ~GW1 without the model → ~20 bets of sample lost.

## Priorities (in order)

### 1. Commit (first thing next session — Antigravity or by hand)
```
git add -A prompts/ scripts/run_update.ps1 SESSION_LOG_COWORK.md COWORK_HANDOFF_PROMPT.md CLAUDE.md docs/WEEKLY_SCHEDULE.md docs/INDEX.md archive/session_logs/SESSION_LOG_SESSION_14.md data/aliases/team_aliases.json output/scheduler_log.txt
git commit -m "Session 15: weekly automation (settle/predict modes), handoff + docs"
git push
```
Also delete `scripts/run_update.ps1.bak`. Decide whether `output/predictions/` should be committed (small text files; suggest yes).

### 2. Verify the first automated settle (Tue 2026-10-27)
- Villa and Sunderland bets settled correctly; P&L sensible.
- **CLV line-match rate:** football-data closing AH line vs our logged main line. Old ±1.5 bets matched
  5/11. Main-line bets should match far more often. If the match rate stays low, CLV — the season's verdict
  metric — is unusable and needs fixing before more bets accrue.
- Calibration columns still present after the scheduled results run.

### 3. Re-plan the checkpoint — the Christmas target is unreachable
~2.4 flagged bets/round from GW9 → ~20 by Christmas, ~40 by mid-Feb, ~70 by season end. Two options to
decide next session:
- Move the decision checkpoint to ~40 flagged bets (≈ Feb 2027), and/or
- Measure CLV on **all** logged matches (both sides are logged every week, 9–10/round), regressing CLV on
  calib_edge. That's ~4× the sample and answers "does a higher calibrated edge predict line movement?"
  sooner. Needs a short analysis script — Antigravity, standard tier.

### 4. Soft-league expansion (where the remaining upside is)
P1 verified (306 rows × 5 seasons). FIN parked; SC0 parked (one xG season). Next: write the **Module 4
merge** Antigravity brief (Sofascore xG + football-data results/odds) for B1, N1, DNK, T1, E1, SWE, NOR,
P1. Check whether the Scandinavian football-data files carry AH odds or only 1X2 → decides the test
market. Then replicate calibration_backtest + recalibration_test per league. See
`prompts/rescrape_plan_2026-07-18.md` (Step 3 table) and `docs/FUTURE_DEVELOPMENT.md` item 7.

### 5. Known issues / tech debt (not urgent)
- **No AU execution path:** only PlayUp (±1.5) appears for EPL spreads in the API. Before any real stakes,
  manually check Bet365 AU / Sportsbet / TAB / Betfair AU for main Asian lines.
- Matchbook (exchange) prices exclude commission → its "best price" is slightly overstated.
- `scrapers/merge.py` reorders rows by reading `ratings.csv` / `ratings_backup.csv` (Antigravity hack to
  keep historical ratings bit-identical). Fragile; a stale backup file will dictate row order. Replace with
  a deterministic sort key when convenient.
- Display text bug: 0.00 line prints "lose by up to 0.00".
- Odds API key was echoed in a Cowork tool error on 2026-10-24 → rotate at some point.
- 1% rule ignores margin (some flagged bets ≈ 0 EV at best price). Deliberately unchanged for the season.

### 6. Edge research backlog — `docs/FUTURE_DEVELOPMENT.md` (unchanged; read before any edge work)

## How work gets executed
Cowork scopes and QCs; Antigravity codes, using the `antigravity-handoff` skill. Briefs go in `prompts/`;
Chris pastes one line: `Read prompts/<FILE>.md and carry out every task in it, in order.` Money-critical
code gets Cowork-written gold test files that Antigravity may not edit. **Always QC Antigravity's report
against the repo** — this session it claimed a check that hadn't happened.
