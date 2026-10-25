# Antigravity brief — Does our edge predict closing-line movement? (analysis script)

Written by Cowork 2026-10-25 (session 16). **Run only after `prompts/ANTIGRAVITY_CLOSING_LINE_CLV.md`
is complete and committed** (this uses its closing columns and `model/clv.py`).
Repo root: `C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer`
Tier: standard. Cowork will interpret the results — your job is correct numbers, clearly reported.

## Why
At ~2.4 flagged bets/round the live season gives ~40 bets by February: far too few to judge ROI.
Closing-line movement is a much faster test: if the model knows something the market doesn't,
the market should move toward the model between our bet and kick-off. We can test that on
**six seasons of history right now** (football-data has pre-closing and closing prices for every
EPL match), and keep testing it live on every logged match, not just the flagged ones.

## Read first
`model/clv.py`, `scripts/test_clv.py` (definitions), `scripts/recalibration_test.py` (how the July
OOS test was built, its regression style and HC1 SEs), `output/backtest_results/calibration_matches.csv`,
`output/backtest_results/recalibrated_test_matches.csv`, `data/processed/all_merged.csv`,
`output/paper_trading/log_ah.csv`.

## Build `scripts/clv_edge_analysis.py`
Read-only on all inputs. Writes `output/backtest_results/clv_edge_report.txt` and
`output/backtest_results/clv_edge_matches.csv` (one row per match used, all inputs and derived values).
Use `model.clv` for every no-vig and line-conversion calculation (mu=2.8). statsmodels OLS with HC1 SEs.

### Joining
Join `calibration_matches.csv` / `recalibrated_test_matches.csv` to `all_merged.csv` on league,
home, away, date (±1 day). Report the join rate per league-season. **Stop and report if any
EPL season joins below 95%.**

### Definitions (home perspective unless stated)
- Pre-closing line = the row's `ah_line` (football-data AHh). Closing line = `close_ah_line`.
- `pre_home` = no-vig home prob of B365 pre-closing (`odds_ah_home/away`) on the pre line.
- `pre_home_pin` = same from Pinnacle pre-closing (`pin_ah_home/away`), where present.
- `close_home` = Pinnacle closing no-vig (fallback market-average closing), **converted onto the
  pre-closing line** with `convert_q_home`. Record which source.
- `move` = close_home − pre_home. `move_pin` = close_home − pre_home_pin (like-for-like book).
- Model home prob: if `bet_side == 'home'` then `model_prob`, else `1 − model_prob`
  (valid because model_prob = p_side + 0.5·p_push, so home and away sum to 1).
  Market home prob at bet time = `pre_home`.
- `signal` = logit(model_home) − logit(pre_home), both clipped to [0.01, 0.99].

### Analyses — one section each in the report
**H1 — EPL 2020-21 … 2025-26, all matches.** OLS `move ~ signal`. Report n, intercept, slope,
HC1 SE, t, p, R², SD of move, SD of signal. Repeat with `move_pin` (rows where Pinnacle
pre-closing exists). Repeat per season (n, slope, SE).

**H2 — EPL out-of-sample calibrated edge (recalibrated_test_matches, 2024-25 and 2025-26).**
Bet-side perspective here: `move_side` = closing no-vig of the bet side (converted onto the pre
line) − `market_prob_novig`. OLS `move_side ~ calibrated_edge`. Then, for flagged rows
(`calibrated_edge ≥ 0.01`): n, mean `move_side` (SE), mean price CLV = `market_odds × closing
prob of bet side − 1` (SE), share with positive price CLV.

**H3 — Big 5 ex-EPL, 2020-21 … 2025-26** (control). Same as H1, per league and pooled.

**H4 — Live 2026-27 log.** Rows with `clv_move` present: OLS `clv_move ~ calib_edge`
(n, slope, SE). Flagged rows: n, mean `clv_price`, mean `clv_move`. Print "insufficient data" if
n < 20 — that is expected for now.

**Sanity block.** For EPL: share of matches where the closing line ≠ pre line; mean and SD of
`move`; mean `close_home − pre_home` when lines were equal vs converted (they should be similar
in mean; a large gap means the conversion is biased — flag it).

## Verify and report
1. Run the script; paste the full report text.
2. Hand-check two rows from `clv_edge_matches.csv` (one with a converted line): show the
   no-vig arithmetic, the conversion output, `move`, and `signal`.
3. Confirm no input file was modified (`git status`).

## Commit
```
git add scripts/clv_edge_analysis.py output/backtest_results/clv_edge_report.txt output/backtest_results/clv_edge_matches.csv prompts/
git commit -m "CLV-vs-edge analysis: historical EPL/Big5 line movement vs model signal, live log"
git push
```
