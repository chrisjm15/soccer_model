"""Refit EPL Asian Handicap calibration model on all six training seasons (2020-21 to 2025-26).

Uses statsmodels GLM Binomial on actual_score with HC1 robust standard errors.
Outputs config/calibration.yaml if b_model > 0.
"""
import os
import sys
import datetime
import numpy as np
import pandas as pd
import yaml

import statsmodels.api as sm
from statsmodels.genmod.families import Binomial

CSV_PATH = 'output/backtest_results/calibration_matches.csv'
CONFIG_PATH = 'config/calibration.yaml'

CLIP_LO, CLIP_HI = 0.01, 0.99
TRAIN_SEASONS = ['2020-21', '2021-22', '2022-23', '2023-24', '2024-25', '2025-26']

# 2026-07-12 Train-only values (for comparison display)
TRAIN_ONLY_COEFS = {
    'intercept': -0.1416,
    'b_market': 0.2850,
    'b_model': 0.2858,
}


def fit_model(y, X):
    """Fractional logit via GLM Binomial, robust HC1 standard errors."""
    glm = sm.GLM(y.values, X.values, family=Binomial())
    try:
        result = glm.fit(cov_type='HC1')
    except TypeError:
        result = glm.fit()
        result = result.get_robustcov_results(cov_type='HC1')
    result._xnames = list(X.columns)
    return result


def main():
    print("=" * 70)
    print("REFIT EPL CALIBRATION MODEL (2020-21 to 2025-26)")
    print("=" * 70)

    df = pd.read_csv(CSV_PATH)

    # Filter to EPL
    df_epl = df[df['league'] == 'EPL'].copy()
    assert '2026-27' not in df_epl['season'].values, "Leakage assertion failed: 2026-27 rows found in fit data!"

    df_epl = df_epl[df_epl['season'].isin(TRAIN_SEASONS)].copy()
    df_epl = df_epl.dropna(subset=['model_prob', 'market_prob_novig', 'actual_score'])
    df_epl = df_epl.reset_index(drop=True)

    n_fit = len(df_epl)
    print(f"Fit sample size: n = {n_fit} matches across seasons {sorted(df_epl['season'].unique())}")

    # Clip probabilities
    df_epl['model_prob_c'] = df_epl['model_prob'].clip(CLIP_LO, CLIP_HI)
    df_epl['market_prob_c'] = df_epl['market_prob_novig'].clip(CLIP_LO, CLIP_HI)

    # Logits
    df_epl['logit_model'] = np.log(df_epl['model_prob_c'] / (1.0 - df_epl['model_prob_c']))
    df_epl['logit_market'] = np.log(df_epl['market_prob_c'] / (1.0 - df_epl['market_prob_c']))

    y = df_epl['actual_score']

    # 1. Fit M1 (market only, diagnostic)
    X_m1 = pd.DataFrame({
        'const': 1.0,
        'logit_market': df_epl['logit_market'],
    })
    res_m1 = fit_model(y, X_m1)

    # 2. Fit M3 (market + model)
    X_m3 = pd.DataFrame({
        'const': 1.0,
        'logit_market': df_epl['logit_market'],
        'logit_model': df_epl['logit_model'],
    })
    res_m3 = fit_model(y, X_m3)

    # Extract coefficients
    m1_intercept = float(res_m1.params[0])
    m1_b_market = float(res_m1.params[1])

    m3_intercept = float(res_m3.params[0])
    m3_b_market = float(res_m3.params[1])
    m3_b_model = float(res_m3.params[2])
    m3_p_model = float(res_m3.pvalues[2])

    # Market prob range (1st and 99th percentiles of raw market_prob_novig in fit data)
    pct_1 = float(np.percentile(df_epl['market_prob_novig'], 1))
    pct_99 = float(np.percentile(df_epl['market_prob_novig'], 99))

    # Print comparison table
    print("\n" + "=" * 70)
    print("COEFFICIENT COMPARISON: 2026-07-12 Train-only vs 2020-2026 Full Refit")
    print("=" * 70)
    print(f"{'Parameter':<15} {'Train (4 seasons)':>18} {'Refit (6 seasons)':>18} {'Shift':>12}")
    print("-" * 70)
    print(f"{'intercept':<15} {TRAIN_ONLY_COEFS['intercept']:>18.4f} {m3_intercept:>18.4f} {m3_intercept - TRAIN_ONLY_COEFS['intercept']:>+12.4f}")
    print(f"{'b_market':<15} {TRAIN_ONLY_COEFS['b_market']:>18.4f} {m3_b_market:>18.4f} {m3_b_market - TRAIN_ONLY_COEFS['b_market']:>+12.4f}")
    print(f"{'b_model':<15} {TRAIN_ONLY_COEFS['b_model']:>18.4f} {m3_b_model:>18.4f} {m3_b_model - TRAIN_ONLY_COEFS['b_model']:>+12.4f}")
    print(f"{'p_model':<15} {'0.0196':>18} {m3_p_model:>18.4f} {'-':>12}")
    print(f"{'n':<15} {'1520':>18} {n_fit:>18} {n_fit - 1520:>+12}")
    print("-" * 70)
    print(f"M1 diagnostic: intercept={m1_intercept:.4f}, b_market={m1_b_market:.4f}")
    print(f"Market prob 1st-99th pct range: [{pct_1:.4f}, {pct_99:.4f}]")

    # Stop condition check
    if m3_b_model <= 0:
        print("\n" + "!" * 70)
        print(f"STOP CONDITION TRIGGERED: b_model = {m3_b_model:.4f} <= 0.")
        print("Model carries no positive predictive signal. Config NOT updated.")
        print("!" * 70)
        sys.exit(1)

    print(f"\nCondition passed: b_model = {m3_b_model:.4f} > 0. Writing config...")

    today_str = datetime.date.today().strftime('%Y-%m-%d')
    calibration_cfg = {
        'epl_ah': {
            'fit_date': today_str,
            'seasons': TRAIN_SEASONS,
            'n': int(n_fit),
            'edge_threshold': 0.01,
            'm3': {
                'intercept': round(m3_intercept, 6),
                'b_market': round(m3_b_market, 6),
                'b_model': round(m3_b_model, 6),
                'p_model': round(m3_p_model, 6),
            },
            'm1': {
                'intercept': round(m1_intercept, 6),
                'b_market': round(m1_b_market, 6),
            },
            'market_prob_range': [round(pct_1, 4), round(pct_99, 4)],
            'promoted_min_matches': 10,
        }
    }

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        yaml.dump(calibration_cfg, f, default_flow_style=False, sort_keys=False)

    print(f"Config successfully written to {CONFIG_PATH}:")
    with open(CONFIG_PATH, 'r') as f:
        print(f.read())


if __name__ == '__main__':
    main()
