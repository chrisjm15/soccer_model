"""
Recalibration market-blend test.

Tests whether the xG model adds predictive information beyond what the betting
market already prices in, using fractional logit regression on calibration_matches.csv.

Train: 2020-21 through 2023-24 (temporal, no leakage)
Test:  2024-25, 2025-26 (out-of-sample only)

Output:
  output/backtest_results/recalibration_report.txt
  output/backtest_results/recalibrated_test_matches.csv
"""
import os
import sys
import warnings
from datetime import datetime

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

try:
    import statsmodels.api as sm
    from statsmodels.genmod.families import Binomial
except ImportError:
    print("Installing statsmodels...")
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'statsmodels', '--break-system-packages'])
    import statsmodels.api as sm
    from statsmodels.genmod.families import Binomial

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
CSV_PATH = 'output/backtest_results/calibration_matches.csv'
REPORT_PATH = 'output/backtest_results/recalibration_report.txt'
MATCHES_PATH = 'output/backtest_results/recalibrated_test_matches.csv'

TRAIN_SEASONS = {'2020-21', '2021-22', '2022-23', '2023-24'}
TEST_SEASONS  = {'2024-25', '2025-26'}
CLIP_LO, CLIP_HI = 0.01, 0.99
THRESHOLDS = [0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05]
N_BOOT = 1000
SEED = 42

# ──────────────────────────────────────────────────────────────────────────────
# Load and prepare data
# ──────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("RECALIBRATION MARKET-BLEND TEST")
print("=" * 70)

print("\nLoading data...")
df = pd.read_csv(CSV_PATH)
n_raw = len(df)
print(f"  Raw rows: {n_raw}")

df = df.dropna(subset=['model_prob', 'market_prob_novig', 'actual_score'])
n_dropped = n_raw - len(df)
print(f"  Dropped (missing values): {n_dropped} | Remaining: {len(df)}")

# Clip
n_clip_model = int(((df['model_prob'] < CLIP_LO) | (df['model_prob'] > CLIP_HI)).sum())
n_clip_market = int(((df['market_prob_novig'] < CLIP_LO) | (df['market_prob_novig'] > CLIP_HI)).sum())
df['model_prob_c']  = df['model_prob'].clip(CLIP_LO, CLIP_HI)
df['market_prob_c'] = df['market_prob_novig'].clip(CLIP_LO, CLIP_HI)
print(f"  Rows clipped (model_prob): {n_clip_model}  (market_prob_novig): {n_clip_market}")

# Logits
df['logit_model']  = np.log(df['model_prob_c'] / (1 - df['model_prob_c']))
df['logit_market'] = np.log(df['market_prob_c'] / (1 - df['market_prob_c']))

# Sanity: no NaN/inf
for col in ['logit_model', 'logit_market']:
    assert not df[col].isnull().any(), f"NaN in {col}"
    assert not np.isinf(df[col]).any(), f"Inf in {col}"
print("  Logit features clean (no NaN/inf)")

# Big line dummy
df['big_line'] = (df['ah_line'].abs() >= 1.5).astype(float)
df['logit_model_x_big'] = df['logit_model'] * df['big_line']

# Train / test split (temporal, by season string)
df['in_train'] = df['season'].isin(TRAIN_SEASONS)
df['in_test']  = df['season'].isin(TEST_SEASONS)

train_all = df[df['in_train']].copy().reset_index(drop=True)
test_all  = df[df['in_test']].copy().reset_index(drop=True)
train_epl = df[df['in_train'] & (df['league'] == 'EPL')].copy().reset_index(drop=True)
test_epl  = df[df['in_test']  & (df['league'] == 'EPL')].copy().reset_index(drop=True)

print(f"\nTrain (all leagues): n={len(train_all)}  |  Test (all leagues): n={len(test_all)}")
print(f"Train (EPL only):    n={len(train_epl)}  |  Test (EPL only):    n={len(test_epl)}")

# ──────────────────────────────────────────────────────────────────────────────
# Regression helpers
# ──────────────────────────────────────────────────────────────────────────────
def fit_model(y, X):
    """Fractional logit via GLM Binomial, robust HC1 standard errors."""
    glm = sm.GLM(y.values, X.values, family=Binomial())
    try:
        result = glm.fit(cov_type='HC1')
    except TypeError:
        result = glm.fit()
        result = result.get_robustcov_results(cov_type='HC1')
    # Attach column names so we can look up by name
    result._xnames = list(X.columns)
    return result


def reg_table(result, label):
    names = result._xnames
    params = result.params
    bse    = result.bse
    pvals  = result.pvalues
    lines = [f"\n  {label}",
             f"  {'Variable':<30} {'Coef':>10} {'SE (HC1)':>10} {'p-value':>10} {'':>4}",
             f"  {'-'*66}"]
    for i, name in enumerate(names):
        sig = ('***' if pvals[i] < 0.001 else
               '**'  if pvals[i] < 0.01  else
               '*'   if pvals[i] < 0.05  else '')
        lines.append(f"  {name:<30} {params[i]:>10.4f} {bse[i]:>10.4f} {pvals[i]:>10.4f} {sig:>4}")
    lines.append(f"  n = {int(result.nobs)}")
    return '\n'.join(lines)


def predict(result, X_pred):
    return result.predict(X_pred.values)


# ──────────────────────────────────────────────────────────────────────────────
# Fit M1-M4 on TRAIN (all leagues)
# ──────────────────────────────────────────────────────────────────────────────
print("\nFitting M1-M4 on train seasons (all leagues)...")

y_tr = train_all['actual_score']

X_m1 = pd.DataFrame({'const': 1.0, 'logit_market': train_all['logit_market']})
X_m2 = pd.DataFrame({'const': 1.0, 'logit_model':  train_all['logit_model']})
X_m3 = pd.DataFrame({'const': 1.0, 'logit_market': train_all['logit_market'],
                      'logit_model': train_all['logit_model']})
X_m4 = pd.DataFrame({'const': 1.0, 'logit_market': train_all['logit_market'],
                      'logit_model': train_all['logit_model'],
                      'big_line': train_all['big_line'],
                      'logit_model_x_big': train_all['logit_model_x_big']})

m1 = fit_model(y_tr, X_m1)
m2 = fit_model(y_tr, X_m2)
m3 = fit_model(y_tr, X_m3)
m4 = fit_model(y_tr, X_m4)

print("  Done.")

# ──────────────────────────────────────────────────────────────────────────────
# Fit M1-M4 on TRAIN (EPL only)
# ──────────────────────────────────────────────────────────────────────────────
print("Fitting M1-M4 on train seasons (EPL only)...")

y_tr_epl = train_epl['actual_score']

X_m1_epl = pd.DataFrame({'const': 1.0, 'logit_market': train_epl['logit_market']})
X_m2_epl = pd.DataFrame({'const': 1.0, 'logit_model':  train_epl['logit_model']})
X_m3_epl = pd.DataFrame({'const': 1.0, 'logit_market': train_epl['logit_market'],
                          'logit_model': train_epl['logit_model']})
X_m4_epl = pd.DataFrame({'const': 1.0, 'logit_market': train_epl['logit_market'],
                          'logit_model': train_epl['logit_model'],
                          'big_line': train_epl['big_line'],
                          'logit_model_x_big': train_epl['logit_model_x_big']})

m1_epl = fit_model(y_tr_epl, X_m1_epl)
m2_epl = fit_model(y_tr_epl, X_m2_epl)
m3_epl = fit_model(y_tr_epl, X_m3_epl)
m4_epl = fit_model(y_tr_epl, X_m4_epl)

print("  Done.")

# ──────────────────────────────────────────────────────────────────────────────
# Sanity checks
# ──────────────────────────────────────────────────────────────────────────────
print("\n=== SANITY CHECKS ===")

m1_intercept   = m1.params[0]
m1_market_coef = m1.params[1]
print(f"  M1 intercept    = {m1_intercept:.4f}   (expected ~0)")
print(f"  M1 logit_market = {m1_market_coef:.4f}   (expected ~1.0)")

if abs(m1_intercept) > 0.25:
    print(f"\n  FATAL: M1 intercept ({m1_intercept:.4f}) is far from 0.")
    print("  This suggests a problem with the no-vig market probability computation. Stopping.")
    sys.exit(1)

if abs(m1_market_coef - 1.0) > 0.25:
    print(f"\n  FATAL: M1 logit_market coef ({m1_market_coef:.4f}) is far from 1.0.")
    print("  The market is not tracking actual outcomes as expected. Stopping.")
    sys.exit(1)

print(f"  Train n (all)   = {len(train_all)}   (expected ~7,200)")
print(f"  Test  n (all)   = {len(test_all)}   (expected ~3,500)")
print("  SANITY CHECKS PASSED")

# ──────────────────────────────────────────────────────────────────────────────
# OOS predictions (test seasons)
# ──────────────────────────────────────────────────────────────────────────────
print("\nGenerating out-of-sample predictions (test seasons)...")

# All-leagues M3 and M4 predictions
X_test_m3 = pd.DataFrame({'const': 1.0, 'logit_market': test_all['logit_market'],
                           'logit_model': test_all['logit_model']})
X_test_m4 = pd.DataFrame({'const': 1.0, 'logit_market': test_all['logit_market'],
                           'logit_model': test_all['logit_model'],
                           'big_line': test_all['big_line'],
                           'logit_model_x_big': test_all['logit_model_x_big']})

test_all['calib_prob_m3'] = np.clip(predict(m3, X_test_m3), 1e-7, 1 - 1e-7)
test_all['calib_prob_m4'] = np.clip(predict(m4, X_test_m4), 1e-7, 1 - 1e-7)

# EPL M3 predictions on EPL test set
X_tepl_m3 = pd.DataFrame({'const': 1.0, 'logit_market': test_epl['logit_market'],
                           'logit_model': test_epl['logit_model']})
test_epl['calib_prob_m3_epl'] = np.clip(predict(m3_epl, X_tepl_m3), 1e-7, 1 - 1e-7)

# Sanity: all predictions in (0,1)
for col in ['calib_prob_m3', 'calib_prob_m4']:
    assert (test_all[col] > 0).all() and (test_all[col] < 1).all(), f"{col} out of (0,1)"
assert (test_epl['calib_prob_m3_epl'] > 0).all() and (test_epl['calib_prob_m3_epl'] < 1).all()
print("  All predicted probabilities in (0,1). OK.")

# ──────────────────────────────────────────────────────────────────────────────
# OOS metrics
# ──────────────────────────────────────────────────────────────────────────────
def log_loss_frac(y, p):
    """Log-loss with fractional y in [0,1]."""
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def brier(y, p):
    return float(np.mean((y - p) ** 2))


y_te = test_all['actual_score']

ll_market    = log_loss_frac(y_te, test_all['market_prob_c'])
ll_model_raw = log_loss_frac(y_te, test_all['model_prob_c'])
ll_m3        = log_loss_frac(y_te, test_all['calib_prob_m3'])
ll_m4        = log_loss_frac(y_te, test_all['calib_prob_m4'])

bs_market    = brier(y_te, test_all['market_prob_c'])
bs_model_raw = brier(y_te, test_all['model_prob_c'])
bs_m3        = brier(y_te, test_all['calib_prob_m3'])
bs_m4        = brier(y_te, test_all['calib_prob_m4'])

m3_beats_m1_ll = ll_m3 < ll_market
m3_beats_m1_bs = bs_m3 < bs_market

# ──────────────────────────────────────────────────────────────────────────────
# Calibrated edges
# ──────────────────────────────────────────────────────────────────────────────
test_all['calibrated_edge']     = test_all['calib_prob_m3']  - test_all['market_prob_c']
test_epl['calibrated_edge_epl'] = test_epl['calib_prob_m3_epl'] - test_epl['market_prob_c']

# ──────────────────────────────────────────────────────────────────────────────
# Bootstrap ROI CI
# ──────────────────────────────────────────────────────────────────────────────
def bootstrap_roi_ci(pnl_arr, n_boot=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    n = len(pnl_arr)
    if n == 0:
        return np.nan, np.nan
    boot = [rng.choice(pnl_arr, size=n, replace=True).sum() / (n * 10.0) * 100
            for _ in range(n_boot)]
    return float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


# ──────────────────────────────────────────────────────────────────────────────
# Threshold sweep
# ──────────────────────────────────────────────────────────────────────────────
def run_sweep(df_test, edge_col):
    n_seasons = df_test['season'].nunique()
    rows = []
    for thr in THRESHOLDS:
        bets = df_test[df_test[edge_col] >= thr]
        n = len(bets)
        if n == 0:
            rows.append({'thr': thr, 'n': 0, 'bps': 0.0,
                         'me': np.nan, 'act': np.nan,
                         'roi': np.nan, 'lo': np.nan, 'hi': np.nan})
            continue
        roi = bets['pnl_flat10'].sum() / (n * 10.0) * 100
        lo, hi = bootstrap_roi_ci(bets['pnl_flat10'].values)
        rows.append({
            'thr': thr,
            'n': n,
            'bps': n / n_seasons,
            'me': bets[edge_col].mean() * 100,
            'act': bets['actual_score'].mean(),
            'roi': roi,
            'lo': lo,
            'hi': hi,
        })
    return rows


sweep_all = run_sweep(test_all, 'calibrated_edge')
sweep_epl = run_sweep(test_epl, 'calibrated_edge_epl')

# 2% breakdown
thr2_bets = test_all[test_all['calibrated_edge'] >= 0.02].copy()

if len(thr2_bets) > 0:
    thr2_by_league = thr2_bets.groupby('league').apply(
        lambda g: pd.Series({
            'n': len(g),
            'actual': g['actual_score'].mean(),
            'roi': g['pnl_flat10'].sum() / (len(g) * 10.0) * 100,
        })
    ).reset_index()

    bins   = [-0.001, 0.5, 1.25, 2.0, 99.0]
    labels = ['<=0.5', '0.75-1.25', '1.5-2.0', '>=2.25']
    thr2_bets['line_bkt'] = pd.cut(thr2_bets['ah_line'].abs(), bins=bins, labels=labels)
    thr2_by_line = thr2_bets.groupby('line_bkt', observed=True).apply(
        lambda g: pd.Series({
            'n': len(g),
            'actual': g['actual_score'].mean(),
            'roi': g['pnl_flat10'].sum() / (len(g) * 10.0) * 100,
        })
    ).reset_index()
else:
    thr2_by_league = pd.DataFrame()
    thr2_by_line   = pd.DataFrame()

# ──────────────────────────────────────────────────────────────────────────────
# Save test-season CSV
# ──────────────────────────────────────────────────────────────────────────────
out_cols = [
    'date', 'league', 'season', 'home_team', 'away_team',
    'ah_line', 'bet_side', 'model_prob', 'market_prob_novig',
    'calib_prob_m3', 'calib_prob_m4', 'calibrated_edge',
    'actual_score', 'pnl_flat10',
]
out_df = test_all[[c for c in out_cols if c in test_all.columns]].copy()
os.makedirs('output/backtest_results', exist_ok=True)
out_df.to_csv(MATCHES_PATH, index=False)
print(f"\nSaved: {MATCHES_PATH}  ({len(out_df)} rows)")

# ──────────────────────────────────────────────────────────────────────────────
# Build report
# ──────────────────────────────────────────────────────────────────────────────
lines = []
W = 90

def L(s=''):    lines.append(s)
def DIV():      lines.append('=' * W)
def div():      lines.append('-' * W)
def H(title):   DIV(); L(f'  {title}'); DIV()


H(f"RECALIBRATION MARKET-BLEND TEST  —  {datetime.now().strftime('%Y-%m-%d')}")
L(f"  Train seasons: 2020-21 to 2023-24  |  Test seasons: 2024-25, 2025-26")
L(f"  Train n (all leagues): {len(train_all)}  |  Test n (all leagues): {len(test_all)}")
L(f"  Train n (EPL only):    {len(train_epl)}  |  Test n (EPL only):    {len(test_epl)}")
L(f"  Rows dropped (missing): {n_dropped}")
L(f"  Rows clipped — model_prob: {n_clip_model}  |  market_prob_novig: {n_clip_market}")
L()

# ── Section 1: Regressions ────────────────────────────────────────────────────
H("SECTION 1 — REGRESSION TABLES  (train seasons only, robust HC1 SEs)")
L()
L("  Specifications:")
L("    M1 : actual_score ~ logit_market")
L("    M2 : actual_score ~ logit_model")
L("    M3 : actual_score ~ logit_market + logit_model   ← HEADLINE")
L("    M4 : M3 + big_line + logit_model × big_line      (large-line interaction)")
L()
L("  Response: actual_score ∈ {0, 0.25, 0.5, 0.75, 1.0}  (AH bet perspective)")
L("  Estimator: fractional logit  (GLM with Binomial family, logit link)")
L()
div()
L("  ALL LEAGUES")
div()
L(reg_table(m1, "M1 — logit_market only"))
L(reg_table(m2, "M2 — logit_model only"))
L(reg_table(m3, "M3 — logit_market + logit_model"))
L()
m3_coef_all = m3.params[m3._xnames.index('logit_model')]
m3_pval_all = m3.pvalues[m3._xnames.index('logit_model')]
L(f"  >>> HEADLINE (all leagues): logit_model coef in M3 = {m3_coef_all:.4f}  p = {m3_pval_all:.4f}")
L()
L(reg_table(m4, "M4 — M3 + big_line interaction"))
L()
div()
L("  EPL ONLY")
div()
L(reg_table(m1_epl, "M1 — logit_market only  (EPL)"))
L(reg_table(m2_epl, "M2 — logit_model only   (EPL)"))
L(reg_table(m3_epl, "M3 — logit_market + logit_model  (EPL)"))
L()
m3_coef_epl = m3_epl.params[m3_epl._xnames.index('logit_model')]
m3_pval_epl = m3_epl.pvalues[m3_epl._xnames.index('logit_model')]
L(f"  >>> HEADLINE (EPL only): logit_model coef in M3 = {m3_coef_epl:.4f}  p = {m3_pval_epl:.4f}")
L()
L(reg_table(m4_epl, "M4 — M3 + big_line interaction  (EPL)"))
L()

# ── Section 2: OOS metrics ────────────────────────────────────────────────────
H("SECTION 2 — OUT-OF-SAMPLE METRICS  (test seasons: 2024-25, 2025-26)")
L()
L(f"  {'Model':<35} {'Log-Loss':>10} {'Δ vs Mkt':>10} {'Brier':>10} {'Δ vs Mkt':>10}")
L(f"  {'-'*77}")

def _oos_row(label, ll, bs):
    return (f"  {label:<35} {ll:>10.6f} {ll - ll_market:>+10.6f} "
            f"{bs:>10.6f} {bs - bs_market:>+10.6f}")

L(_oos_row("Market (M1, no-vig probs)",   ll_market,    bs_market))
L(_oos_row("Raw model (uncalibrated)",     ll_model_raw, bs_model_raw))
L(_oos_row("M3 calibrated (all-lg fit)",  ll_m3,        bs_m3))
L(_oos_row("M4 calibrated (all-lg fit)",  ll_m4,        bs_m4))
L()
L(f"  Model earns its place if M3 log-loss < market log-loss:")
L(f"    Log-loss: M3 {'<' if m3_beats_m1_ll else '>='} Market => {'YES  ***' if m3_beats_m1_ll else 'NO'}")
L(f"    Brier:    M3 {'<' if m3_beats_m1_bs else '>='} Market => {'YES  ***' if m3_beats_m1_bs else 'NO'}")
L(f"  M3 − Market log-loss delta: {ll_m3 - ll_market:+.6f}")
L()

# ── Section 3: Threshold sweep ────────────────────────────────────────────────
H("SECTION 3 — POST-CALIBRATION THRESHOLD SWEEP  (test seasons only)")
L()
L("  calibrated_edge = calib_prob (M3) − market_prob_novig")
L("  ROI = sum(pnl_flat10) / (n_bets × 10) × 100.  Flat $10 stake.")
L("  Bootstrap 95% CI: 1,000 resamples of the qualifying bet set.")
L()

def _sweep_hdr():
    return (f"  {'Threshold':>10} {'N':>6} {'Bets/Ssn':>9} {'MeanEdge':>9} "
            f"{'ActScore':>9} {'ROI':>8}   {'95% CI':>18}")

def _sweep_row(r):
    if r['n'] == 0:
        return f"  {r['thr']*100:>9.1f}% {0:>6} {0.0:>9.0f} {'—':>9} {'—':>9} {'—':>8}   {'—':>18}"
    lo_s = f"{r['lo']:+.1f}%" if not np.isnan(r['lo']) else '—'
    hi_s = f"{r['hi']:+.1f}%" if not np.isnan(r['hi']) else '—'
    return (f"  {r['thr']*100:>9.1f}% {r['n']:>6} {r['bps']:>9.0f} "
            f"{r['me']:>8.1f}% {r['act']:>9.3f} {r['roi']:>+7.1f}%   [{lo_s:>7}, {hi_s:>7}]")

L("  ALL LEAGUES — M3 (all-leagues fit):")
L(_sweep_hdr())
L(f"  {'-'*70}")
for r in sweep_all:
    L(_sweep_row(r))

L()
L("  EPL ONLY — M3 (EPL-only fit):")
L(_sweep_hdr())
L(f"  {'-'*70}")
for r in sweep_epl:
    L(_sweep_row(r))

if len(thr2_bets) > 0:
    L()
    L("  BREAKDOWN AT 2% THRESHOLD  (all leagues, M3 all-fit) — by league:")
    L(f"  {'League':<14} {'N':>6} {'Actual':>8} {'ROI':>8}")
    L(f"  {'-'*40}")
    for _, r in thr2_by_league.iterrows():
        L(f"  {r['league']:<14} {int(r['n']):>6} {r['actual']:>8.3f} {r['roi']:>+7.1f}%")

    L()
    L("  BREAKDOWN AT 2% THRESHOLD  (all leagues, M3 all-fit) — by |line| bucket:")
    L(f"  {'Bucket':<14} {'N':>6} {'Actual':>8} {'ROI':>8}")
    L(f"  {'-'*40}")
    for _, r in thr2_by_line.iterrows():
        L(f"  {str(r['line_bkt']):<14} {int(r['n']):>6} {r['actual']:>8.3f} {r['roi']:>+7.1f}%")
else:
    L()
    L("  No bets qualified at 2% threshold.")

L()

# ── Section 4: Sanity log ────────────────────────────────────────────────────
H("SECTION 4 — SANITY CHECK LOG")
L(f"  M1 intercept      = {m1.params[0]:.4f}  (expected ≈ 0)")
L(f"  M1 logit_market   = {m1.params[1]:.4f}  (expected ≈ 1.0)")
L(f"  Train n (all)     = {len(train_all)}  (expected ≈ 7,200)")
L(f"  Test  n (all)     = {len(test_all)}  (expected ≈ 3,500)")
L(f"  M3 pred range (test): [{test_all['calib_prob_m3'].min():.4f}, {test_all['calib_prob_m3'].max():.4f}]")
L(f"  No NaN/inf in logit features: CONFIRMED")
L()
DIV()
L("  END OF REPORT")
DIV()

report_text = '\n'.join(lines)
with open(REPORT_PATH, 'w', encoding='utf-8') as f:
    f.write(report_text)

print(f"\nReport saved: {REPORT_PATH}")

# Print to console — strip any chars the terminal can't handle
safe_report = report_text.encode('ascii', errors='replace').decode('ascii')
print()
print(safe_report)
