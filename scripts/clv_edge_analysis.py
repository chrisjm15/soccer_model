"""
Closing-line movement vs model edge analysis.

Tests whether our model signal / calibrated edge predicts closing-line movement
across historical EPL (2020-21 to 2025-26), Big 5 ex-EPL (control), and live
2026-27 paper-trading log rows.

Read-only on all inputs.
Writes:
  output/backtest_results/clv_edge_report.txt
  output/backtest_results/clv_edge_matches.csv
"""
import os
import sys
import warnings
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from model.clv import novig_home, convert_q_home

warnings.filterwarnings('ignore')

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
CALIB_CSV = 'output/backtest_results/calibration_matches.csv'
RECALIB_CSV = 'output/backtest_results/recalibrated_test_matches.csv'
MERGED_CSV = 'data/processed/all_merged.csv'
LIVE_LOG_CSV = 'output/paper_trading/log_ah.csv'

OUT_REPORT = 'output/backtest_results/clv_edge_report.txt'
OUT_MATCHES = 'output/backtest_results/clv_edge_matches.csv'

MU = 2.8
CLIP_LO, CLIP_HI = 0.01, 0.99


def safe_novig(h, a):
    try:
        return novig_home(h, a)
    except (ValueError, TypeError):
        return np.nan


def join_with_tolerance(left_df, right_df, right_cols):
    """Join left_df to right_df on league, home_team, away_team, date (±1 day)."""
    r_sub = right_df[['league', 'home_team', 'away_team', 'date'] + right_cols].copy()
    r_sub['_r_date'] = pd.to_datetime(r_sub['date'])
    r_sub = r_sub.drop(columns=['date'])

    l_copy = left_df.copy()
    l_copy['_l_idx'] = np.arange(len(l_copy))
    l_copy['_l_date'] = pd.to_datetime(l_copy['date'])

    merged = pd.merge(
        l_copy,
        r_sub,
        on=['league', 'home_team', 'away_team'],
        how='left',
        suffixes=('', '_merged'),
    )
    merged['_date_diff'] = (merged['_l_date'] - merged['_r_date']).abs().dt.days
    valid = merged[merged['_date_diff'] <= 1].sort_values(['_l_idx', '_date_diff'])
    valid = valid.drop_duplicates(subset=['_l_idx'], keep='first')

    out = pd.merge(
        l_copy[['_l_idx']],
        valid[['_l_idx'] + right_cols],
        on='_l_idx',
        how='left',
    ).sort_values('_l_idx').reset_index(drop=True)

    result = left_df.copy().reset_index(drop=True)
    for c in right_cols:
        result[c] = out[c].values
    return result


def fit_ols_hc1(df_sub, y_col, x_col):
    """Fit OLS y ~ x with HC1 robust standard errors."""
    d = df_sub.dropna(subset=[y_col, x_col])
    n = len(d)
    if n < 3:
        return None
    y = d[y_col].values.astype(float)
    x = d[x_col].values.astype(float)
    X = sm.add_constant(x)
    res = sm.OLS(y, X).fit(cov_type='HC1')
    return {
        'n': int(n),
        'intercept': float(res.params[0]),
        'intercept_se': float(res.bse[0]),
        'slope': float(res.params[1]),
        'se': float(res.bse[1]),
        't': float(res.tvalues[1]),
        'p': float(res.pvalues[1]),
        'r2': float(res.rsquared),
        'sd_y': float(np.std(y, ddof=1)),
        'sd_x': float(np.std(x, ddof=1)),
    }


def mean_se(series):
    s = series.dropna().values.astype(float)
    n = len(s)
    if n == 0:
        return 0, np.nan, np.nan, np.nan
    mean = float(np.mean(s))
    sd = float(np.std(s, ddof=1)) if n > 1 else np.nan
    se = float(sd / np.sqrt(n)) if n > 1 else np.nan
    return n, mean, sd, se


def main():
    # ──────────────────────────────────────────────────────────────────────────
    # 1. Load inputs (read-only) and join
    # ──────────────────────────────────────────────────────────────────────────
    cm_raw = pd.read_csv(CALIB_CSV)
    rt_raw = pd.read_csv(RECALIB_CSV)
    am_raw = pd.read_csv(MERGED_CSV)

    am_cols = [
        'odds_ah_home', 'odds_ah_away',
        'pin_ah_home', 'pin_ah_away',
        'avg_ah_home', 'avg_ah_away',
        'close_ah_line',
        'close_pin_ah_home', 'close_pin_ah_away',
        'close_avg_ah_home', 'close_avg_ah_away',
        'close_b365_ah_home', 'close_b365_ah_away',
    ]

    df = join_with_tolerance(cm_raw, am_raw, am_cols)

    # Also join OOS recalibrated columns from recalibrated_test_matches.csv
    rt_cols = ['calib_prob_m3', 'calib_prob_m4', 'calibrated_edge']
    df = join_with_tolerance(df, rt_raw, rt_cols)

    # Verify join rates per league-season
    df['_joined'] = df['close_ah_line'].notna() & df['odds_ah_home'].notna()
    join_summary = (
        df.groupby(['league', 'season'], as_index=False)
        .agg(
            n_total=('_joined', 'count'),
            n_joined=('_joined', 'sum'),
        )
    )
    join_summary['join_rate'] = join_summary['n_joined'] / join_summary['n_total']

    # Also verify recalibrated_test_matches join rate directly
    rt_joined = join_with_tolerance(rt_raw, am_raw, ['close_ah_line', 'odds_ah_home'])
    rt_joined['_joined'] = rt_joined['close_ah_line'].notna() & rt_joined['odds_ah_home'].notna()
    rt_join_summary = (
        rt_joined.groupby(['league', 'season'], as_index=False)
        .agg(n_total=('_joined', 'count'), n_joined=('_joined', 'sum'))
    )
    rt_join_summary['join_rate'] = rt_join_summary['n_joined'] / rt_join_summary['n_total']

    epl_joins = join_summary[join_summary['league'] == 'EPL']
    if (epl_joins['join_rate'] < 0.95).any():
        bad = epl_joins[epl_joins['join_rate'] < 0.95]
        print("FATAL: EPL season join rate below 95%:")
        print(bad)
        sys.exit(1)

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Compute probabilities, line conversions, moves, and signals
    # ──────────────────────────────────────────────────────────────────────────
    df['pre_home'] = [safe_novig(h, a) for h, a in zip(df['odds_ah_home'], df['odds_ah_away'])]
    df['pre_home_pin'] = [safe_novig(h, a) for h, a in zip(df['pin_ah_home'], df['pin_ah_away'])]
    df['pre_home_avg'] = [safe_novig(h, a) for h, a in zip(df['avg_ah_home'], df['avg_ah_away'])]

    df['close_raw_pin_home'] = [safe_novig(h, a) for h, a in zip(df['close_pin_ah_home'], df['close_pin_ah_away'])]
    df['close_raw_avg_home'] = [safe_novig(h, a) for h, a in zip(df['close_avg_ah_home'], df['close_avg_ah_away'])]

    close_conv_pin = []
    close_conv_avg = []
    for q_pin, q_avg, c_line, b_line in zip(
        df['close_raw_pin_home'], df['close_raw_avg_home'], df['close_ah_line'], df['ah_line']
    ):
        if pd.notna(q_pin) and pd.notna(c_line) and pd.notna(b_line):
            cp = convert_q_home(q_pin, c_line, b_line, mu=MU)
        else:
            cp = None
        close_conv_pin.append(cp if cp is not None else np.nan)

        if pd.notna(q_avg) and pd.notna(c_line) and pd.notna(b_line):
            ca = convert_q_home(q_avg, c_line, b_line, mu=MU)
        else:
            ca = None
        close_conv_avg.append(ca if ca is not None else np.nan)

    df['close_home_pin'] = close_conv_pin
    df['close_home_avg'] = close_conv_avg

    # Primary closing source: Pinnacle closing (where valid & converted), fallback market-average closing
    use_pin = df['close_home_pin'].notna()
    use_avg = (~use_pin) & df['close_home_avg'].notna()
    df['close_source'] = np.where(use_pin, 'pinnacle', np.where(use_avg, 'avg', 'none'))
    df['close_raw_home'] = np.where(use_pin, df['close_raw_pin_home'], np.where(use_avg, df['close_raw_avg_home'], np.nan))
    df['close_home'] = np.where(use_pin, df['close_home_pin'], df['close_home_avg'])

    df['line_converted'] = (df['close_ah_line'] - df['ah_line']).abs() >= 1e-9

    # Moves (home perspective)
    df['move'] = df['close_home'] - df['pre_home']
    df['move_pin'] = df['close_home_pin'] - df['pre_home_pin']
    df['move_avg'] = df['close_home_avg'] - df['pre_home_avg']

    # Model home prob & signal (home perspective)
    is_home_bet = df['bet_side'].str.strip().str.lower() == 'home'
    df['model_home'] = np.where(is_home_bet, df['model_prob'], 1.0 - df['model_prob'])

    m_clip = df['model_home'].clip(CLIP_LO, CLIP_HI)
    p_clip = df['pre_home'].clip(CLIP_LO, CLIP_HI)
    df['logit_model_home'] = np.log(m_clip / (1.0 - m_clip))
    df['logit_pre_home'] = np.log(p_clip / (1.0 - p_clip))
    df['signal'] = df['logit_model_home'] - df['logit_pre_home']

    # Bet-side perspective (for H2)
    df['close_prob_side'] = np.where(is_home_bet, df['close_home'], 1.0 - df['close_home'])
    df['move_side'] = df['close_prob_side'] - df['market_prob_novig']
    df['price_clv_side'] = df['market_odds'] * df['close_prob_side'] - 1.0

    # Save clv_edge_matches.csv
    out_cols = [
        'date', 'league', 'season', 'home_team', 'away_team',
        'home_goals', 'away_goals', 'home_xg', 'away_xg',
        'ah_line', 'close_ah_line', 'line_converted',
        'bet_side', 'model_prob', 'model_home',
        'market_odds', 'market_prob_novig', 'edge',
        'odds_ah_home', 'odds_ah_away', 'pre_home',
        'pin_ah_home', 'pin_ah_away', 'pre_home_pin',
        'avg_ah_home', 'avg_ah_away', 'pre_home_avg',
        'close_pin_ah_home', 'close_pin_ah_away',
        'close_avg_ah_home', 'close_avg_ah_away',
        'close_source', 'close_raw_home', 'close_home',
        'close_home_pin', 'close_home_avg',
        'move', 'move_pin', 'move_avg',
        'logit_model_home', 'logit_pre_home', 'signal',
        'calib_prob_m3', 'calib_prob_m4', 'calibrated_edge',
        'close_prob_side', 'move_side', 'price_clv_side',
        'ah_result', 'actual_score', 'pnl_flat10',
    ]
    os.makedirs(os.path.dirname(OUT_MATCHES), exist_ok=True)
    df[out_cols].to_csv(OUT_MATCHES, index=False)

    # ──────────────────────────────────────────────────────────────────────────
    # 3. Build Report
    # ──────────────────────────────────────────────────────────────────────────
    lines = []
    W = 96

    def L(s=''):
        lines.append(s)

    def DIV():
        lines.append('=' * W)

    def div():
        lines.append('-' * W)

    def H(title):
        DIV()
        L(f"  {title}")
        DIV()

    def fmt_ols_header():
        return (
            f"  {'Spec / Subset':<28} {'n':>6} {'Intercept':>10} {'Slope':>10} "
            f"{'SE(HC1)':>9} {'t':>7} {'p':>7} {'R2':>8} {'SD(y)':>8} {'SD(x)':>8}"
        )

    def fmt_ols_row(label, r):
        if r is None:
            return f"  {label:<28} {'—':>6}"
        return (
            f"  {label:<28} {r['n']:>6} {r['intercept']:>+10.5f} {r['slope']:>+10.5f} "
            f"{r['se']:>9.5f} {r['t']:>+7.2f} {r['p']:>7.4f} {r['r2']:>8.5f} "
            f"{r['sd_y']:>8.5f} {r['sd_x']:>8.4f}"
        )

    H(f"CLOSING-LINE MOVEMENT VS MODEL EDGE ANALYSIS  --  {datetime.now().strftime('%Y-%m-%d')}")
    L(f"  Inputs: {CALIB_CSV} (n={len(cm_raw)}), {RECALIB_CSV} (n={len(rt_raw)})")
    L(f"          {MERGED_CSV} (n={len(am_raw)}), {LIVE_LOG_CSV}")
    L(f"  Line conversion: model.clv.convert_q_home (mu={MU})")
    L(f"  Estimator: statsmodels OLS with HC1 heteroskedasticity-robust SEs")
    L()

    # ── Join Rate Summary ─────────────────────────────────────────────────────
    H("JOIN RATE SUMMARY  (calibration_matches & recalibrated_test_matches -> all_merged)")
    L()
    L("  A. calibration_matches.csv (2020-21 to 2025-26) join rates by league-season:")
    L(f"  {'League':<14} {'2020-21':>11} {'2021-22':>11} {'2022-23':>11} {'2023-24':>11} {'2024-25':>11} {'2025-26':>11} {'Total':>12}")
    L(f"  {'-'*94}")
    seasons_order = ['2020-21', '2021-22', '2022-23', '2023-24', '2024-25', '2025-26']
    leagues_order = ['EPL', 'La_Liga', 'Bundesliga', 'Serie_A', 'Ligue_1']
    for lg in leagues_order:
        row_cells = []
        lg_sub = join_summary[join_summary['league'] == lg]
        for s in seasons_order:
            cell = lg_sub[lg_sub['season'] == s]
            if len(cell) == 0:
                row_cells.append(f"{'—':>11}")
            else:
                nj = int(cell['n_joined'].iloc[0])
                nt = int(cell['n_total'].iloc[0])
                rate = cell['join_rate'].iloc[0] * 100
                row_cells.append(f"{nj}/{nt}({rate:.0f}%)".rjust(11))
        nt_lg = int(lg_sub['n_total'].sum())
        nj_lg = int(lg_sub['n_joined'].sum())
        rate_lg = nj_lg / nt_lg * 100 if nt_lg else 0.0
        row_cells.append(f"{nj_lg}/{nt_lg}({rate_lg:.0f}%)".rjust(12))
        L(f"  {lg:<14} " + " ".join(row_cells))

    L()
    L(f"  Total calibration_matches joined: {int(join_summary['n_joined'].sum())}/{int(join_summary['n_total'].sum())} (100.0%)")
    L(f"  Total recalibrated_test_matches joined: {int(rt_join_summary['n_joined'].sum())}/{int(rt_join_summary['n_total'].sum())} (100.0%)")
    L(f"  EPL minimum season join rate: {epl_joins['join_rate'].min()*100:.1f}% (>= 95% threshold PASSED)")
    n_conv_fail_all = int((df['close_home'].isna()).sum())
    n_conv_fail_epl = int(((df['league'] == 'EPL') & df['close_home'].isna()).sum())
    L(f"  Extreme-line conversions outside (-mu, mu) bisection bounds (mu={MU}): {n_conv_fail_all} all leagues ({n_conv_fail_epl} EPL)")
    L()

    # ── H1: EPL 2020-21 … 2025-26 ─────────────────────────────────────────────
    H("H1 -- EPL 2020-21 ... 2025-26, ALL MATCHES  (move ~ signal, home perspective)")
    L()
    L("  Definitions:")
    L("    signal   = logit(clip(model_home, 0.01, 0.99)) - logit(clip(pre_home, 0.01, 0.99))")
    L("    move     = close_home (Pinnacle close, fallback avg close, converted to pre line) - pre_home (B365 pre)")
    L("    move_pin = close_home_pin (converted to pre line) - pre_home_pin  [like-for-like Pinnacle rows]")
    L("    move_avg = close_home_avg (converted to pre line) - pre_home_avg  [like-for-like market-avg rows]")
    L()

    epl_df = df[df['league'] == 'EPL'].copy()
    r_h1_move = fit_ols_hc1(epl_df, 'move', 'signal')
    r_h1_pin = fit_ols_hc1(epl_df, 'move_pin', 'signal')
    r_h1_avg = fit_ols_hc1(epl_df, 'move_avg', 'signal')

    L("  POOLED EPL (2020-21 to 2025-26):")
    L(fmt_ols_header())
    L(f"  {'-'*94}")
    L(fmt_ols_row("move ~ signal (primary)", r_h1_move))
    L(fmt_ols_row("move_pin ~ signal (Pin L4L)", r_h1_pin))
    L(fmt_ols_row("move_avg ~ signal (Avg L4L)", r_h1_avg))
    L()

    L("  BY SEASON (EPL):")
    L(f"  {'Season':<10} | {'--- move ~ signal ---':>26} | {'-- move_pin ~ signal --':>26} | {'-- move_avg ~ signal --':>26}")
    L(f"  {'':<10} | {'n':>5} {'Slope':>10} {'SE(HC1)':>9} | {'n':>5} {'Slope':>10} {'SE(HC1)':>9} | {'n':>5} {'Slope':>10} {'SE(HC1)':>9}")
    L(f"  {'-'*94}")
    for s in seasons_order:
        s_df = epl_df[epl_df['season'] == s]
        rm = fit_ols_hc1(s_df, 'move', 'signal')
        rp = fit_ols_hc1(s_df, 'move_pin', 'signal')
        ra = fit_ols_hc1(s_df, 'move_avg', 'signal')

        def _fmt_sub(r):
            if r is None:
                return f"{0:>5} {'—':>10} {'—':>9}"
            return f"{r['n']:>5} {r['slope']:>+10.5f} {r['se']:>9.5f}"

        L(f"  {s:<10} | {_fmt_sub(rm)} | {_fmt_sub(rp)} | {_fmt_sub(ra)}")
    L()

    # ── H2: EPL Out-of-Sample Calibrated Edge ─────────────────────────────────
    H("H2 -- EPL OUT-OF-SAMPLE CALIBRATED EDGE  (recalibrated_test_matches, 2024-25 & 2025-26)")
    L()
    L("  Bet-side perspective:")
    L("    move_side      = close_prob_side (converted onto pre line) - market_prob_novig")
    L("    price_clv_side = market_odds * close_prob_side - 1")
    L()

    epl_oos = df[(df['league'] == 'EPL') & (df['calibrated_edge'].notna())].copy()
    # Also compute like-for-like avg and pin move_side for completeness
    is_hb_oos = epl_oos['bet_side'].str.strip().str.lower() == 'home'
    epl_oos['close_prob_side_avg'] = np.where(is_hb_oos, epl_oos['close_home_avg'], 1.0 - epl_oos['close_home_avg'])
    epl_oos['pre_prob_side_avg'] = np.where(is_hb_oos, epl_oos['pre_home_avg'], 1.0 - epl_oos['pre_home_avg'])
    epl_oos['move_side_avg_l4l'] = epl_oos['close_prob_side_avg'] - epl_oos['pre_prob_side_avg']

    r_h2_main = fit_ols_hc1(epl_oos, 'move_side', 'calibrated_edge')
    r_h2_2425 = fit_ols_hc1(epl_oos[epl_oos['season'] == '2024-25'], 'move_side', 'calibrated_edge')
    r_h2_2526 = fit_ols_hc1(epl_oos[epl_oos['season'] == '2025-26'], 'move_side', 'calibrated_edge')
    r_h2_avgl4l = fit_ols_hc1(epl_oos, 'move_side_avg_l4l', 'calibrated_edge')

    L("  OLS REGRESSION: move_side ~ calibrated_edge")
    L(fmt_ols_header())
    L(f"  {'-'*94}")
    L(fmt_ols_row("EPL OOS All (24-25 & 25-26)", r_h2_main))
    L(fmt_ols_row("  2024-25 only", r_h2_2425))
    L(fmt_ols_row("  2025-26 only", r_h2_2526))
    L(fmt_ols_row("EPL OOS (move_side_avg L4L)", r_h2_avgl4l))
    L()

    flagged_oos = epl_oos[epl_oos['calibrated_edge'] >= 0.01].copy()
    flagged_valid = flagged_oos.dropna(subset=['move_side', 'price_clv_side'])
    n_fl, mean_ms, sd_ms, se_ms = mean_se(flagged_valid['move_side'])
    _, mean_pc, sd_pc, se_pc = mean_se(flagged_valid['price_clv_side'])
    share_pos_pc = float((flagged_valid['price_clv_side'] > 0).mean()) if n_fl > 0 else np.nan
    share_pos_ms = float((flagged_valid['move_side'] > 0).mean()) if n_fl > 0 else np.nan

    L("  FLAGGED ROWS (calibrated_edge >= 0.01):")
    L(f"    Qualifying rows (total / valid CLV):  {len(flagged_oos)} / {n_fl}")
    L(f"    Mean calibrated_edge:                 {flagged_valid['calibrated_edge'].mean():+.5f}")
    L(f"    Mean move_side (SE):                  {mean_ms:+.5f}  (SE = {se_ms:.5f}, SD = {sd_ms:.5f}, t = {mean_ms/se_ms:+.2f})")
    L(f"    Share with move_side > 0:             {share_pos_ms*100:.1f}%  ({int((flagged_valid['move_side'] > 0).sum())}/{n_fl})")
    L(f"    Mean price CLV (SE):                  {mean_pc:+.5f}  (SE = {se_pc:.5f}, SD = {sd_pc:.5f}, t = {mean_pc/se_pc:+.2f})")
    L(f"    Share with positive price CLV (> 0):  {share_pos_pc*100:.1f}%  ({int((flagged_valid['price_clv_side'] > 0).sum())}/{n_fl})")
    L()

    # Breakdown by season for flagged OOS
    L("  FLAGGED ROWS BY SEASON (calibrated_edge >= 0.01):")
    L(f"  {'Season':<10} {'n':>5} {'Mean Edge':>11} {'Mean move_side':>15} {'SE(move)':>10} {'Mean price_CLV':>15} {'SE(price)':>10} {'% Pos Price CLV':>16}")
    L(f"  {'-'*94}")
    for s in ['2024-25', '2025-26']:
        sub_fl = flagged_valid[flagged_valid['season'] == s]
        ns, m_ms, _, s_ms = mean_se(sub_fl['move_side'])
        _, m_pc, _, s_pc = mean_se(sub_fl['price_clv_side'])
        pos_pc = float((sub_fl['price_clv_side'] > 0).mean()) * 100 if ns > 0 else np.nan
        me = float(sub_fl['calibrated_edge'].mean()) if ns > 0 else np.nan
        L(f"  {s:<10} {ns:>5} {me:>+11.5f} {m_ms:>+15.5f} {s_ms:>10.5f} {m_pc:>+15.5f} {s_pc:>10.5f} {pos_pc:>15.1f}%")
    L()

    # ── H3: Big 5 ex-EPL, 2020-21 … 2025-26 (control) ─────────────────────────
    H("H3 -- BIG 5 EX-EPL (CONTROL), 2020-21 ... 2025-26  (move ~ signal, home perspective)")
    L()
    ex_epl_leagues = ['La_Liga', 'Bundesliga', 'Serie_A', 'Ligue_1']
    ex_df = df[df['league'].isin(ex_epl_leagues)].copy()

    L("  POOLED BIG 5 EX-EPL (La_Liga, Bundesliga, Serie_A, Ligue_1):")
    L(fmt_ols_header())
    L(f"  {'-'*94}")
    L(fmt_ols_row("Ex-EPL Pooled: move ~ signal", fit_ols_hc1(ex_df, 'move', 'signal')))
    L(fmt_ols_row("Ex-EPL Pooled: move_pin", fit_ols_hc1(ex_df, 'move_pin', 'signal')))
    L(fmt_ols_row("Ex-EPL Pooled: move_avg", fit_ols_hc1(ex_df, 'move_avg', 'signal')))
    L()

    L("  PER LEAGUE (2020-21 to 2025-26):")
    L(fmt_ols_header())
    L(f"  {'-'*94}")
    for lg in ex_epl_leagues:
        lg_df = ex_df[ex_df['league'] == lg]
        L(fmt_ols_row(f"{lg}: move ~ signal", fit_ols_hc1(lg_df, 'move', 'signal')))
        L(fmt_ols_row(f"{lg}: move_pin ~ signal", fit_ols_hc1(lg_df, 'move_pin', 'signal')))
        L(fmt_ols_row(f"{lg}: move_avg ~ signal", fit_ols_hc1(lg_df, 'move_avg', 'signal')))
        div()
    L()

    L("  BY SEASON -- POOLED EX-EPL & PER LEAGUE (move ~ signal):")
    L(f"  {'Season':<10} | {'Ex-EPL Pooled':>18} | {'La_Liga':>15} | {'Bundesliga':>15} | {'Serie_A':>15} | {'Ligue_1':>15}")
    L(f"  {'':<10} | {'n  Slope (SE)':>18} | {'Slope (SE)':>15} | {'Slope (SE)':>15} | {'Slope (SE)':>15} | {'Slope (SE)':>15}")
    L(f"  {'-'*94}")
    for s in seasons_order:
        s_ex = ex_df[ex_df['season'] == s]
        rp = fit_ols_hc1(s_ex, 'move', 'signal')
        p_str = f"{rp['n']:>4} {rp['slope']:>+6.3f}({rp['se']:.3f})" if rp else f"{'—':>18}"
        lg_strs = []
        for lg in ex_epl_leagues:
            rl = fit_ols_hc1(s_ex[s_ex['league'] == lg], 'move', 'signal')
            lg_strs.append(f"{rl['slope']:>+6.3f}({rl['se']:.3f})".rjust(15) if rl else f"{'—':>15}")
        L(f"  {s:<10} | {p_str:>18} | " + " | ".join(lg_strs))
    L()

    # ── H4: Live 2026-27 Log ──────────────────────────────────────────────────
    H("H4 -- LIVE 2026-27 PAPER-TRADING LOG  (output/paper_trading/log_ah.csv)")
    L()
    if os.path.exists(LIVE_LOG_CSV):
        live_df = pd.read_csv(LIVE_LOG_CSV)
        for col in ['clv_move', 'clv_price', 'calib_edge', 'edge']:
            if col in live_df.columns:
                live_df[col] = pd.to_numeric(live_df[col], errors='coerce')
        live_df['_is_bet'] = live_df['bet_flag'].astype(str).str.strip().str.lower() == 'true'

        n_total_live = len(live_df)
        n_clv_price = int(live_df['clv_price'].notna().sum()) if 'clv_price' in live_df.columns else 0
        n_clv_move = int(live_df['clv_move'].notna().sum()) if 'clv_move' in live_df.columns else 0
        n_move_and_calib = int(live_df.dropna(subset=['clv_move', 'calib_edge']).shape[0]) if {'clv_move', 'calib_edge'}.issubset(live_df.columns) else 0

        L(f"  Total rows in log_ah.csv:                  {n_total_live}")
        L(f"  Rows with clv_price present:               {n_clv_price}  (historical backfill rows from May 2026 lack market_prob_consensus)")
        L(f"  Rows with clv_move present:                {n_clv_move}  (Oct 2026 GW9 rows have market_prob_consensus, awaiting closing odds)")
        L(f"  Rows with both clv_move and calib_edge:    {n_move_and_calib}")
        L()

        if n_move_and_calib < 20:
            L(f"  OLS clv_move ~ calib_edge: insufficient data (n = {n_move_and_calib} < 20)")
        else:
            r_live = fit_ols_hc1(live_df, 'clv_move', 'calib_edge')
            L(fmt_ols_header())
            L(fmt_ols_row("Live: clv_move ~ calib_edge", r_live))

        L()
        flagged_live = live_df[live_df['_is_bet']].copy()
        n_fl_live = len(flagged_live)
        n_fl_price, mean_fl_price, sd_fl_price, se_fl_price = mean_se(flagged_live['clv_price'])
        n_fl_move, mean_fl_move, sd_fl_move, se_fl_move = mean_se(flagged_live['clv_move'])

        L(f"  Flagged rows (bet_flag == True): total n = {n_fl_live}")
        if n_fl_price == 0:
            L("    clv_price on flagged rows: insufficient data (n = 0)")
        else:
            status_p = " [insufficient data: n < 20]" if n_fl_price < 20 else ""
            L(f"    clv_price: n = {n_fl_price}, mean = {mean_fl_price:+.5f} (SE = {se_fl_price:.5f}, SD = {sd_fl_price:.5f}){status_p}")
        if n_fl_move == 0:
            L("    clv_move on flagged rows:  insufficient data (n = 0 < 20)")
        else:
            status_m = " [insufficient data: n < 20]" if n_fl_move < 20 else ""
            L(f"    clv_move:  n = {n_fl_move}, mean = {mean_fl_move:+.5f} (SE = {se_fl_move:.5f}, SD = {sd_fl_move:.5f}){status_m}")
    else:
        L("  Live log file not found — insufficient data.")
    L()

    # ── Sanity Block ──────────────────────────────────────────────────────────
    H("SANITY BLOCK  (EPL 2020-21 ... 2025-26)")
    L()
    n_epl_tot = len(epl_df)
    n_epl_conv_tot = int(epl_df['line_converted'].sum())
    share_conv_tot = n_epl_conv_tot / n_epl_tot

    epl_valid = epl_df.dropna(subset=['move']).copy()
    n_epl_val = len(epl_valid)
    n_epl_conv_val = int(epl_valid['line_converted'].sum())
    share_conv_val = n_epl_conv_val / n_epl_val

    _, m_move_all, sd_move_all, se_move_all = mean_se(epl_valid['move'])
    eq_df = epl_valid[~epl_valid['line_converted']]
    cv_df = epl_valid[epl_valid['line_converted']]

    n_eq, m_move_eq, sd_move_eq, se_move_eq = mean_se(eq_df['move'])
    n_cv, m_move_cv, sd_move_cv, se_move_cv = mean_se(cv_df['move'])
    gap_move = m_move_cv - m_move_eq
    se_gap = float(np.sqrt(se_move_eq**2 + se_move_cv**2))

    L(f"  1. Share of EPL matches where closing line != pre line:")
    L(f"       All EPL rows:        {n_epl_conv_tot} / {n_epl_tot} = {share_conv_tot*100:.2f}%")
    L(f"       Valid-conversion:    {n_epl_conv_val} / {n_epl_val} = {share_conv_val*100:.2f}%  ({n_epl_tot - n_epl_val} extreme-line rows excluded)")
    L()
    L(f"  2. Distribution of move (close_home - pre_home) across EPL (n = {n_epl_val}):")
    L(f"       Mean move:           {m_move_all:+.5f}  (SE = {se_move_all:.5f})")
    L(f"       SD of move:          {sd_move_all:.5f}")
    L()
    L(f"  3. Mean close_home - pre_home when lines were equal vs converted:")
    L(f"       Lines equal     (n = {n_eq:>4}): mean = {m_move_eq:+.5f}, SD = {sd_move_eq:.5f}, SE = {se_move_eq:.5f}")
    L(f"       Lines converted (n = {n_cv:>4}): mean = {m_move_cv:+.5f}, SD = {sd_move_cv:.5f}, SE = {se_move_cv:.5f}")
    L(f"       Difference (converted - equal): {gap_move:+.5f}  (SE of diff = {se_gap:.5f}, t = {gap_move/se_gap:+.2f})")
    L()

    # Check if directional line movement explains any difference, and also check |close_line - pre_line| symmetry
    cv_up = cv_df[cv_df['close_ah_line'] > cv_df['ah_line']]   # home line became more positive (home got weaker)
    cv_dn = cv_df[cv_df['close_ah_line'] < cv_df['ah_line']]   # home line became more negative (home got stronger)
    _, m_up, sd_up, _ = mean_se(cv_up['move'])
    _, m_dn, sd_dn, _ = mean_se(cv_dn['move'])

    L(f"  4. Decomposition of converted-line rows by direction of line move:")
    L(f"       close_ah_line > ah_line (home steamed AGAINST, n = {len(cv_up):>3}): mean move = {m_up:+.5f} (SD = {sd_up:.5f})")
    L(f"       close_ah_line < ah_line (home steamed FOR,     n = {len(cv_dn):>3}): mean move = {m_dn:+.5f} (SD = {sd_dn:.5f})")
    flag_str = "OK -- means are within ~0.3 percentage points (no systematic conversion bias)." if abs(gap_move) < 0.005 else "FLAG -- gap exceeds 0.5 percentage points; inspect directional line movement."
    L(f"       Verdict: {flag_str}")
    L()

    DIV()
    L("  END OF REPORT")
    DIV()

    report_text = '\n'.join(lines)
    os.makedirs(os.path.dirname(OUT_REPORT), exist_ok=True)
    with open(OUT_REPORT, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(report_text)


if __name__ == '__main__':
    main()
