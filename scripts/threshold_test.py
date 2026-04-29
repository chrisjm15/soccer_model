"""
Threshold sensitivity test.
Loads the saved predictions CSV once and re-evaluates at three edge thresholds
without re-running the full prediction loop.
"""
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backtest.metrics import compute_metrics

PREDICTIONS_PATH = 'output/backtest_results/predictions.csv'
THRESHOLDS = [0.05, 0.08, 0.10]

df = pd.read_csv(PREDICTIONS_PATH)
df = df.dropna(subset=['actual_btts', 'prob_btts_yes', 'edge'])
n_total = len(df)

print("=" * 60)
print("  EDGE THRESHOLD SENSITIVITY TEST")
print(f"  Total test matches: {n_total}")
print("=" * 60)

metrics_08 = None

for threshold in THRESHOLDS:
    working = df.copy()
    working['should_bet'] = working['edge'] >= threshold

    m = compute_metrics(working)

    n_bets = m['n_bets']
    bet_pct = (n_bets / n_total * 100.0) if n_total > 0 else 0.0
    hit_pct = m['hit_rate'] * 100.0 if m['hit_rate'] is not None else 0.0
    roi = m['roi_pct'] if m['roi_pct'] is not None else 0.0
    brier_f = m['brier_flagged'] if m['brier_flagged'] is not None else float('nan')

    print(f"\nEdge threshold: {threshold:.0%}")
    print(f"  Bets flagged : {n_bets:>5}  ({bet_pct:.1f}% of matches)")
    print(f"  Hit rate     : {hit_pct:.1f}%  (break-even: 52.6%)")
    print(f"  ROI          : {roi:+.1f}%")
    print(f"  Brier (bets) : {brier_f:.4f}")

    if threshold == 0.08:
        metrics_08 = m

print()
print("=" * 60)
print("  CALIBRATION AT THRESHOLD 0.08 (all 3,497 matches)")
print("  Shows how well model probabilities match reality")
print("=" * 60)
for b in metrics_08['calibration']:
    if b['n'] == 0:
        continue
    lo_pct = b['bin_low'] * 100
    hi_pct = b['bin_high'] * 100
    pred_pct = b['mean_pred'] * 100
    act_pct = b['actual_rate'] * 100
    bar_len = int(round(act_pct / 2))
    bar = '#' * bar_len
    print(f"  {lo_pct:3.0f}-{hi_pct:3.0f}%  pred={pred_pct:4.1f}%  actual={act_pct:4.1f}%  {bar}  n={b['n']}")
print()
