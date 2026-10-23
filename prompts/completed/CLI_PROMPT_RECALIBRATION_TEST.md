# Sonnet CLI Prompt — Recalibration / Market-Blend Test

Copy everything below the line into the Sonnet CLI session (after `/effort max`).

---

## Context

The calibration backtest (`output/backtest_results/calibration_report.txt`, per-match data in `output/backtest_results/calibration_matches.csv`, 10,702 rows) showed the model is overconfident at every probability zone and that, across all leagues, actual outcomes track the MARKET's no-vig probability, not the model's. EPL shows a weak but possibly real signal (>10% disagreement bucket: actual 53.7% vs market 50.0%, n=1,071).

This session answers the decisive question: **does the model contain any information beyond what the market already prices in?** We test it with a market-blend logistic regression, trained on early seasons, evaluated strictly out-of-sample on recent seasons. Whatever the answer, it settles the Big-5 strategy.

**Hard rules:**
- Everything runs off `calibration_matches.csv` — do NOT regenerate predictions or modify anything in `model/` or `backtest/`.
- Train/test split is BY SEASON, temporal only. Train: 2020-21 through 2023-24. Test: 2024-25 and 2025-26. No shuffling, no leakage of test seasons into any fitting step.
- This is decision-critical analysis. Boring explicit code. If a result looks too good, assume a bug first.

## Task 1 — `scripts/recalibration_test.py`

### Data prep
- Load `calibration_matches.csv`. Drop rows missing `model_prob`, `market_prob_novig`, or `actual_score`.
- Clip both probabilities to [0.01, 0.99], then compute `logit_model = ln(p/(1-p))` and `logit_market` likewise. Report how many rows were clipped.
- Response variable: `actual_score` (values 0, 0.25, 0.5, 0.75, 1.0). Use a fractional logit: `statsmodels` GLM with `family=Binomial()` accepts fractional outcomes directly. `pip install statsmodels --break-system-packages` if missing. Use robust (HC1) standard errors.

### Regressions (fit on TRAIN seasons only)
Fit each specification twice: all leagues, and EPL-only.

- **M1 (baseline):** `actual_score ~ logit_market`
- **M2:** `actual_score ~ logit_model`
- **M3 (the test):** `actual_score ~ logit_market + logit_model`
- **M4 (secondary):** M3 plus `big_line` dummy (|ah_line| >= 1.5) and `logit_model × big_line` interaction — tests whether the model's information is concentrated in large lines.

Report for every model: coefficients, robust SEs, p-values, n.

**The headline number is the `logit_model` coefficient in M3.** If it is positive and significant, the model adds information the market lacks. If ~zero, it doesn't.

### Out-of-sample evaluation (TEST seasons only, using train-fitted models)
- Log-loss and Brier score for: raw market prob (M1 predictions), raw model prob (uncalibrated, straight from the CSV), M3 predictions, M4 predictions.
- The model earns its place only if M3 beats M1 out-of-sample. Report the differences explicitly.

### Sanity checks (print, fail loudly)
- M1 on train should show `logit_market` coefficient ≈ 1.0 and intercept ≈ 0 (the market is well calibrated — if this fails, something is wrong with the no-vig computation, stop and investigate).
- Train n ≈ 7,200, test n ≈ 3,500 (report exact).
- No NaN/inf in features; all predicted probabilities in (0,1).

### Post-calibration threshold sweep (TEST seasons only)
Using M3's calibrated probability (all-leagues fit and EPL-only fit separately):
- `calibrated_edge = calib_prob − market_prob_novig`
- Sweep thresholds 1%, 1.5%, 2%, 2.5%, 3%, 4%, 5%: report n bets, bets per season, mean calibrated edge, actual_score, flat-stake ROI, and a bootstrap 95% CI on ROI (1,000 resamples of the bet set).
- Break down the surviving bets by league and by |line| bucket at the 2% threshold.

This table is what a live 2024-26 strategy would have looked like with honest probabilities. Expect edges of 1-4pp and small bet counts — that is the realistic shape. If the sweep shows 15%+ ROI on hundreds of bets, suspect leakage and stop.

### Outputs
- `output/backtest_results/recalibration_report.txt` — all regression tables, OOS metrics, sweep tables.
- `output/backtest_results/recalibrated_test_matches.csv` — test-season rows with raw model prob, market prob, M3 and M4 calibrated probs, calibrated edge, actual_score, pnl.

## Task 2 — Log both AH sides at predict time (small `run.py` change)

The CLV computation is currently biased because `log_ah.csv` stores only the bet side's odds (gross implied vs no-vig closing is apples-to-oranges). Fix for next season:
- In the `predict` logging path, add columns `odds_ah_home_at_bet` and `odds_ah_away_at_bet` (both sides from the Odds API response, same snapshot as the logged bet).
- Preserve all existing rows/columns; old rows get blanks.
- Update the CLV calculation in `results` to use no-vig at bet time (from the two new columns) vs no-vig at close, only when lines match — leave the existing fallback behaviour for old rows.
- Do not touch settlement or P&L logic. Run `python run.py results` after the change to confirm no regression (0 unsettled, P&L unchanged).

## Task 3 — Verify, document, commit

1. Run the script end to end. Show me the full report.
2. Update `docs/INDEX.md` with the new script and outputs.
3. Commit: `Recalibration market-blend test + both-sides odds logging`. Push.

## Plain-English summary required at the end

Answer these directly:
1. Is the `logit_model` coefficient in M3 positive and significant (train), and does M3 beat market-only out-of-sample? All-leagues and EPL answers separately.
2. Does M4 say the model's information lives mainly in large lines?
3. From the sweep: at the best-looking sensible threshold, how many bets per season survive, at what ROI, with what confidence interval?
4. Bottom line: does the Big-5 model have a real, exploitable edge after honest calibration — yes, no, or too close to call?
