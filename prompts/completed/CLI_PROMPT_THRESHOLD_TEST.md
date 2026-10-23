# CLI Prompt — Edge Threshold Sensitivity Test

## Instructions for Chris

### Step 1:
```
cd "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
claude --model claude-sonnet-4-6
```

### Step 2:
```
/effort max
```

### Step 3: Paste everything between the --- lines

---

## PROMPT START

Read `CLAUDE.md` first. This is a short session — one task only.

The backtest in `backtest/engine.py` and `run.py` currently uses a default `edge_threshold` of 0.05 (5%). We want to test higher thresholds to see how selectivity affects results.

**TASK: Run the backtest at three edge thresholds and print a comparison.**

Do this by calling `run_backtest()` and `compute_metrics()` directly from a script — do not modify the default values in `engine.py` or `run.py`. Write a temporary script `scripts/threshold_test.py` that:

1. Imports `run_backtest` from `backtest.engine` and `compute_metrics`, `print_metrics_report` from `backtest.metrics`
2. Runs the backtest at three thresholds: 0.05, 0.08, 0.10
3. For each threshold, prints a compact summary showing:
   - Edge threshold used
   - Total bets flagged (and % of matches)
   - Hit rate
   - ROI %
   - Brier score (flagged bets only)
4. After the three summaries, also prints the full calibration bins from the 0.08 run — we want to see predicted probability vs actual BTTS rate across the probability range

Note: `run_backtest()` already saves predictions to `output/backtest_results/predictions.csv`. To avoid re-running the full prediction loop three times (slow), load the saved predictions CSV once and just re-filter by edge threshold for each test. The predictions CSV has an `edge` column — filter rows where `edge >= threshold` to simulate each threshold.

The actual `should_bet` column in the CSV was generated at threshold=0.05, so ignore it. Recompute on the fly from the `edge` column.

Run `scripts/threshold_test.py` and show Chris the output. No git commit needed — this is exploratory only.

## PROMPT END

---

## What to expect
Fast session — under 5 minutes. It's just loading a CSV and refiltering it three ways.
