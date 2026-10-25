# Antigravity brief — Soft-league calibration test: does the xG model add information beyond the market?

Written by Cowork 2026-10-25 (session 16). Carry out every part in order; report after each part.
Repo root: `C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer`
Tier: standard (analysis, no live betting code) — but its result decides where the project goes next, so
every number must be reproducible and the stop conditions below are hard stops. Cowork interprets the results.

## Background (read, don't re-derive)
The EPL verdict (July + 2026-10-25) came from two tests, both of which you will replicate per soft league:
1. **Market-blend regression (M1/M3)** — `scripts/recalibration_test.py`: fractional logit
   `actual_score ~ logit(market) + logit(model)`, HC1 SEs. `b_model > 0` ⇒ model adds information.
2. **Line-movement test** — `scripts/clv_edge_analysis.py`: does the pre-closing → closing move go toward
   the model? Regress move on signal, and on `logit(model) + logit(pre price)` as an artefact control.

Data: `data/processed/soft_merged.csv` (built by `experiment/merge_data.py`; 7,841 matched xG rows).
Leagues: **B1, N1, P1, T1, E1** (Asian Handicap odds, pre-closing) and **DNK, SWE, NOR** (1X2 only, odds
are closing prices). xG exists from proxy 2023-24, DNK 2022, SWE/NOR 2023.

## Read first
`model/ratings.py` (`build_ratings`), `model/poisson.py` (`compute_match_probs`), `model/markets.py`
(`compute_ah_probs`), `backtest/multi_market_engine.py` (`compute_actual_ah_result`),
`scripts/calibration_backtest.py` (AH scoring convention — docstring), `scripts/recalibration_test.py`
(regression + threshold sweep + bootstrap), `scripts/clv_edge_analysis.py`, `model/clv.py`,
`experiment/load_footballdata.py`, `experiment/merge_data.py`.

## Hard rules
- Do **not** modify `model/`, `backtest/`, `scripts/calibration_backtest.py`, `scripts/recalibration_test.py`,
  `scripts/clv_edge_analysis.py`, `run.py`, `scrapers/`, or any gold test file.
- `data/processed/ratings.csv` (live EPL ratings) must be **bit-identical** before and after. Record its
  SHA-256 at the start and the end.
- xG only. Never fall back to goals for ratings. Rows without xG are never fed into ratings.
- Reuse existing functions for probabilities and settlement; do not re-implement Poisson or AH settlement.

---

## Part A — Carry closing odds for the proxy leagues (needed for the movement test)
1. `experiment/load_footballdata.py`: for **proxy leagues only**, append these output columns when present
   in the source file (do not change any existing column or its fallback logic):
   `close_ah_line` ← `AHCh`; `close_avg_ah_home/away` ← `AvgCAHH/AvgCAHA`;
   `avg_ah_home/away` ← `AvgAHH/AvgAHA` (market-average **pre-closing**, like-for-like baseline);
   `close_avg_home/draw/away` ← `AvgCH/AvgCD/AvgCA`; `avg_home/draw/away` ← `AvgH/AvgD/AvgA`.
2. Re-download proxy leagues 2023-24..2025-26 only:
   `python experiment/load_footballdata.py --proxy-only --seasons 2023-24 2024-25 2025-26`
3. `experiment/merge_data.py`: pass the new columns through to `soft_merged.csv` (blank for Scandinavian).
   Run it.
4. Verify and report: every pre-existing column in the re-downloaded proxy files and in `soft_merged.csv`
   is value-identical to before (compare against copies you take first); per league-season non-null counts
   of the new columns. If `AHCh` / `AvgCAHH` are missing for a league-season, report it and carry on — Part E
   just skips that league-season.

## Part B — Ratings for the soft leagues
1. Build `data/processed/soft_ratings_input.csv` from `soft_merged.csv`: rows with `matched == True` and both
   xG values present; columns as `build_ratings` expects; sort by `date, league, home_team` (stable).
   Assert no team name appears in more than one league (report any that do and stop).
2. Call `model.ratings.build_ratings(data_path='data/processed/soft_ratings_input.csv',
   output_path='data/processed/soft_ratings.csv')` — import and call it; do not copy or edit it.
3. Pre-match only: ratings rows are pre-match by construction in `build_ratings`. Confirm by checking one
   team's first three rows (first row = DEFAULT_PRIORS).

## Part C — Per-match dataset `scripts/soft_league_calibration.py`
One script, read-only on inputs, writes `output/backtest_results/soft_calibration_matches.csv` (one row per
match per market, all inputs + derived values) and `output/backtest_results/soft_calibration_report.txt`.

**Sample filters, in this order — report the row count after each, per league-season:**
1. Rated rows (inner join soft_merged ⇄ soft_ratings on date, league, season, home, away).
2. **Warm-up excluded:** drop each league's first xG season (proxy 2023-24; DNK 2022; SWE/NOR 2023).
   Evaluation seasons: proxy 2024-25, 2025-26; DNK 2023, 2024, 2025; SWE/NOR 2024, 2025, 2026 (partial).
3. **Experience guard:** drop a match if either team has fewer than 10 earlier rows in `soft_ratings.csv`
   (same idea as the live promoted-team guard).
4. Market data present (AH: `ah_line, odds_ah_home, odds_ah_away`; 1X2: `odds_home, odds_draw, odds_away`).

**Model probabilities:** `compute_match_probs(home_attack, home_defence, away_attack, away_defence,
home_advantage=0.0)` using the pre-match ratings (venue-split ratings already carry home advantage — same as
EPL config).

**AH market (proxy leagues only)** — identical conventions to `scripts/calibration_backtest.py`:
bet side = larger raw edge (`p_side − novig_side`, ties → home); `model_prob = p_side + 0.5·p_push`;
`market_prob_novig` from `odds_ah_home/away`; `actual_score` ∈ {0, .25, .5, .75, 1} via
`compute_actual_ah_result`; `pnl_flat10` at the logged odds of the side.

**1X2 market (all 8 leagues):** `market_i = (1/o_i) / Σ_j (1/o_j)` for i ∈ {H, D, A};
model_i = `prob_home_win / prob_draw / prob_away_win`. Chosen outcome = largest `model_i − market_i`
(ties → H, then D). `actual = 1` if that outcome happened else 0. `pnl_flat10 = 10·(o−1)` if won else −10.
Label `odds_timing` (`pre_closing` proxy, `closing` Scandinavian).

## Part D — Tests (one report section each)
Use `fit_model` exactly as in `recalibration_test.py` (GLM Binomial fractional logit, HC1). Clip probs to
the same bounds it uses.

**D1 Sanity.** Per league-season: mean λ_home, λ_away vs mean actual goals and mean xG; 1X2 Brier score of
model vs market (market should win — report both).

**D2 AH, M1 and M3 (proxy leagues).** Fit on all evaluation seasons. Per league and pooled
(pooled adds league dummy intercepts): n, b_market, b_model (coef, SE, p), log-loss of M1 vs M3. Also M3
per evaluation season.

**D3 1X2, M1 and M3 (all 8 leagues).** Same as D2 on the chosen-outcome rows. Pooled groups: proxy-5 and
Scandinavian-3 (league dummies). Robustness: stacked version — all three outcomes per match as rows
(`actual ∈ {0,1}`), cluster-robust SEs by match — report b_model, SE, p per group.

**D4 Out-of-sample threshold sweep** (per pooled group × market: proxy-AH, proxy-1X2, Scand-1X2).
Train M3 on the earliest evaluation season, test on the later ones. Calibrated edge = calib_prob −
market_prob. Thresholds `[0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05]`: n bets, ROI, bootstrap 95% CI
(1,000 resamples, seed as in `recalibration_test.py`). Label Scandinavian ROI "at closing prices".

**D5 Line-movement test (proxy leagues, AH; needs Part A).** Per league and pooled, with
`model.clv` (mu=2.8), home perspective, exactly as H1 in `clv_edge_analysis.py`:
`move_avg` = market-average closing no-vig (converted onto the pre line) − market-average pre-closing
no-vig; `signal` = logit(model_home) − logit(pre_home_avg). Report (a) `move_avg ~ signal` and
(b) `move_avg ~ logit(model_home) + logit(pre_home_avg)`: n, coefficient on the model term, HC1 SE, t, p.
Include **EPL 2024-25 + 2025-26** from `output/backtest_results/clv_edge_matches.csv` as a benchmark row
computed the same way.

## Stop conditions (report and stop instead of continuing)
- `ratings.csv` SHA-256 changes.
- Any evaluation league-season loses more than 25% of rows at filter 3 (experience guard) — likely a team-name
  or season-transition problem.
- D1: any league-season where mean predicted total goals differs from actual mean goals by more than 0.5.

## Verify (paste actual output)
1. Full report text.
2. Hand-check 2 rows from the matches CSV — one AH (show novig, model_prob, actual_score, pnl) and one 1X2
   (show the three no-vig probs, model probs, chosen outcome, pnl).
3. SHA-256 of `data/processed/ratings.csv` start and end.
4. `git status` — only the files listed below changed.

## Commit
```
git add experiment/load_footballdata.py experiment/merge_data.py data/proxy/ scripts/soft_league_calibration.py output/backtest_results/soft_calibration_matches.csv output/backtest_results/soft_calibration_report.txt prompts/
git commit -m "Soft-league calibration test: ratings, AH/1X2 M1-M3, OOS sweep, line-movement test"
git push
```
`data/processed/` is gitignored — do not force-add it.
