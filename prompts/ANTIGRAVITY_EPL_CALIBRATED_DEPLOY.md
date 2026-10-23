# Antigravity Task: Deploy the calibrated EPL Asian Handicap model (2026-27)

Workspace: `C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer`
Risk tier: **MONEY-CRITICAL.** This code decides which bets get placed. A subtly wrong edge
will look normal, so correctness is checked by fixed tests you must not edit.

## Context (read these files first, in this order)
1. `CLAUDE.md`: project rules
2. `COWORK_HANDOFF_PROMPT.md`: the 2026-07-12 strategy verdict
3. `output/backtest_results/recalibration_report.txt`: the M3 market-blend model being deployed
4. `scripts/recalibration_test.py`, `scripts/calibration_backtest.py`: how training data was defined
5. `run.py` (`cmd_predict`), `model/markets.py`, `scrapers/odds_api.py`, `model/ratings.py`, `model/live_ratings.py`

Summary: raw model probabilities are badly overconfident. For the EPL only, a fractional-logit
blend `calib = sigmoid(b0 + b1*logit(market_novig) + b2*logit(model_prob))` (M3) carried a weak
signal out-of-sample. This season is the live test: paper-trade it at a **1% calibrated-edge
threshold**. `run.py predict` still uses the retired raw-edge 7% rule, and the data pipeline
stopped at 2025-26. Both must be fixed.

## Hard rules
- Do NOT edit `scripts/test_calibration.py`. Its expected values are hand-verified. Implement
  code until it passes. If you believe an assertion is wrong, stop and say why; do not change it.
- Do NOT touch settlement / P&L / CLV logic in `run.py results`, or anything in `backtest/`.
- Do NOT regenerate `output/backtest_results/calibration_matches.csv`.
- The refit must use seasons 2020-21 to 2025-26 ONLY. 2026-27 is the season that judges the
  model; any 2026-27 row in the fit is leakage.
- Do not commit `.env`. Coefficients and thresholds live in config, not hard-coded.

## Task 1: Pipeline is stuck on 2025-26 (fix first)
`scrapers/understat.py` has `SEASONS = list(range(2020, 2026))`, and `scrapers/footballdata.py`'s
`SEASONS` dict ends at `"2025-26"`. The weekly `run.py update` has been "succeeding" while ratings
stayed frozen at 2026-05-24.
- Add 2026-27 to both (Understat `2026`; football-data code `"2627"`).
- Run `python run.py update`. Report: EPL 2026-27 rows in `data/processed/all_merged.csv`, latest
  date in `ratings.csv`, and any merge/alias failures (new team names → `data/aliases/team_aliases.json`).
- Ratings are a sequential EMA, so adding 2026-27 must not change any pre-2026-27 row of
  `ratings.csv`. Verify this (diff the pre-2026-27 rows before and after). If they differ, stop.

## Task 2: Refit EPL calibration on all six training seasons
New script `scripts/fit_epl_calibration.py`, reusing the exact method in `recalibration_test.py`
(statsmodels GLM Binomial on `actual_score`, HC1 SEs, probabilities clipped to [0.01, 0.99]).
- Input: `calibration_matches.csv`, EPL rows, seasons 2020-21 to 2025-26 (assert no 2026-27).
- Fit M3 (`logit_market + logit_model`) and M1 (`logit_market` only, diagnostic).
- Write `config/calibration.yaml`:
  ```yaml
  epl_ah:
    fit_date: <today>
    seasons: [2020-21, ..., 2025-26]
    n: <int>
    edge_threshold: 0.01
    m3: {intercept: , b_market: , b_model: , p_model: }
    m1: {intercept: , b_market: }
    market_prob_range: [<1st pct>, <99th pct>]   # of EPL market_prob_novig in the fit data
    promoted_min_matches: 10
  ```
- **Stop condition:** if `b_model <= 0`, write nothing to config and report. The deployment
  premise is gone.
- Print the coefficients next to the 2026-07-12 train-only values (intercept -0.1416,
  b_market 0.2850, b_model 0.2858) so the shift is visible.

## Task 3: Pure calibration module (`model/calibration.py`)
Three pure functions. No I/O, no pandas.
- `consensus_novig(book_prices: list[tuple[float, float]]) -> float`: mean across bookmakers of
  each book's no-vig HOME probability `(1/h)/(1/h + 1/a)`. Raise `ValueError` on an empty list or
  any price <= 1.0.
- `calibrate_prob(market_prob, model_prob, coefs) -> float`: clip both to [0.01, 0.99], return
  `sigmoid(intercept + b_market*logit(m) + b_model*logit(x))`.
- `calibrated_ah_decision(p_home, p_push, p_away, novig_home, coefs, threshold) -> dict` with
  keys `bet_side, model_prob, market_prob, calib_prob, calib_edge, should_bet`. This must
  reproduce the training definition exactly:
  - `novig_away = 1 - novig_home`
  - side = the larger RAW edge (`p_home - novig_home` vs `p_away - novig_away`), ties → home
  - `model_prob = p_side + 0.5 * p_push`; `market_prob = novig_side`
  - `calib_edge = calib_prob - market_prob`; `should_bet = round(calib_edge, 6) >= threshold`

Then run `python scripts/test_calibration.py`. It must print `ALL CALIBRATION GOLD TESTS PASSED`.

## Task 4: Odds fetch returns the per-book prices
In `fetch_epl_ah_odds`, keep the modal-line logic and the `*_best` prices. Also return
`book_prices` (a list of (home, away) tuples at the modal line) and `bookmakers` (the keys).
Print once whether `bet365` appears in the response. Training market probabilities came from
Bet365's single-book AH prices (`B365AHH/B365AHA`), so we need to know.

**Why the consensus matters:** a no-vig computed from best-home and best-away prices taken from
different books has an artificially low overround. That biases the market probability. Use the
consensus for the market probability and the best price for the bet price. Never mix them.

## Task 5: Rewire `run.py predict`
- Remove every 7% reference (`EDGE_THRESHOLD = 0.07`, the `- 0.07` min-odds formulas, header text).
  Load coefs, threshold and guards from `config/calibration.yaml`.
- Per match: `compute_match_probs` → `compute_ah_probs(goal_grid, ah_line)` →
  `novig_home = consensus_novig(book_prices)` → `calibrated_ah_decision(...)`.
- Bet price = best price for the chosen side. Approximate break-even odds = `1 / calib_prob`.
- **Extrapolation guard:** if `market_prob` is outside `market_prob_range`, force
  `bet_flag=False` and set notes `out_of_range`.
- **Promoted-team guard:** a promoted team is one with EPL rows in 2026-27 but none in 2025-26
  (derive it from `all_merged.csv`; don't hard-code names). If either team is promoted AND has
  fewer than `promoted_min_matches` EPL matches this season, force `bet_flag=False` and set notes
  `promoted_veto`. Background: `model/ratings.py` seeds never-seen teams with `DEFAULT_PRIORS`
  (roughly average-team strength, which overrates promoted sides). Teams returning after an absence
  carry their old rating regressed 30% to the mean. Report which case each promoted team falls in.
- Log columns to append to `output/paper_trading/log_ah.csv` (keep all existing columns and rows;
  old rows get blanks): `market_prob_consensus, calib_prob, calib_edge, calib_prob_m1_only,
  n_books, coef_fit_date`. `calib_prob_m1_only` = M1 applied to the market prob alone. At
  Christmas it separates real model signal from a market-shape effect. Keep `odds_ah_home_at_bet` /
  `odds_ah_away_at_bet` as the best prices (the CLV code already uses them).
- Keep the existing logging rule: every match is logged, flagged or not. Vetoes go in `notes` only.
- Update the console output: threshold 1% calibrated, and per flagged bet: calib prob, market prob,
  calibrated edge, best price, break-even odds.

## Task 6: Verify (show me the full output of each)
1. `python scripts/test_calibration.py` passes.
2. `python scripts/fit_epl_calibration.py`: coefficients plus the side-by-side with the train fit.
3. `python run.py predict`: one live call (this spends Odds API credits; run it once). Report the
   number of matches, flagged bets, any vetoes, the range of live market probs vs
   `market_prob_range`, and whether bet365 was present.
4. Hand-check ONE logged row: recompute `calib_prob` from its `market_prob_consensus`, its model
   prob and the config coefs, and show the arithmetic.
5. `python run.py results`: no regression (existing settled P&L unchanged).

## Task 7: Docs and commit
- Update `docs/INDEX.md` (new script, module, config, test file).
- Commit 1: the uncommitted Session 14 docs and prompt moves (see "Commit block" in
  `COWORK_HANDOFF_PROMPT.md`).
- Commit 2: `Deploy calibrated EPL AH model: 2026-27 data, M3 refit, 1% calibrated threshold`.
- Push.

## Report back in plain English
1. Did 2026-27 data load, and is the latest ratings date current?
2. What are the refit coefficients, and did `b_model` stay positive?
3. Did all gold tests pass on the first run? If not, what was wrong?
4. This week: how many EPL matches, how many flagged, how many vetoed and why?
5. Was bet365 in the odds feed?
