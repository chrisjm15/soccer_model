"""
scripts/soft_league_calibration.py

Soft-league calibration & line-movement test across 8 soft leagues:
  - Proxy leagues (AH + 1X2, pre-closing odds): B1, N1, P1, T1, E1
  - Scandinavian leagues (1X2 only, closing odds): DNK, SWE, NOR

Read-only on inputs. Writes:
  - output/backtest_results/soft_calibration_matches.csv
  - output/backtest_results/soft_calibration_report.txt
"""
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.genmod.families import Binomial

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from model.poisson import compute_match_probs
from model.markets import compute_ah_probs
from model.clv import novig_home, convert_q_home
from backtest.multi_market_engine import compute_actual_ah_result

warnings.filterwarnings('ignore')

# ---------------------------------------------------------------------------
# Configuration & Constants
# ---------------------------------------------------------------------------
MERGED_PATH = 'data/processed/soft_merged.csv'
RATINGS_PATH = 'data/processed/soft_ratings.csv'
EPL_CLV_MATCHES_PATH = 'output/backtest_results/clv_edge_matches.csv'

OUT_MATCHES_PATH = 'output/backtest_results/soft_calibration_matches.csv'
OUT_REPORT_PATH = 'output/backtest_results/soft_calibration_report.txt'

PROXY_LEAGUES = ['B1', 'N1', 'P1', 'T1', 'E1']
SCAND_LEAGUES = ['DNK', 'SWE', 'NOR']
ALL_LEAGUES = PROXY_LEAGUES + SCAND_LEAGUES

WARMUP_SEASON = {
    'B1': '2023-24',
    'N1': '2023-24',
    'P1': '2023-24',
    'T1': '2023-24',
    'E1': '2023-24',
    'DNK': '2022',
    'SWE': '2023',
    'NOR': '2023',
}

EVAL_SEASONS = {
    'B1': ['2024-25', '2025-26'],
    'N1': ['2024-25', '2025-26'],
    'P1': ['2024-25', '2025-26'],
    'T1': ['2024-25', '2025-26'],
    'E1': ['2024-25', '2025-26'],
    'DNK': ['2023', '2024', '2025'],
    'SWE': ['2024', '2025', '2026'],
    'NOR': ['2024', '2025', '2026'],
}

MIN_EXPERIENCE = 10
CLIP_LO, CLIP_HI = 0.01, 0.99
THRESHOLDS = [0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05]
N_BOOT = 1000
SEED = 42
MU = 2.8

_HOME_BET_SCORE = {
    'home_win':  1.0,
    'half_win':  0.75,
    'push':      0.5,
    'half_loss': 0.25,
    'away_win':  0.0,
}
_AWAY_BET_SCORE = {
    'home_win':  0.0,
    'half_win':  0.25,
    'push':      0.5,
    'half_loss': 0.75,
    'away_win':  1.0,
}
_PNL_MULTIPLIER = {1.0: 1.0, 0.75: 0.5, 0.5: 0.0, 0.25: -0.5, 0.0: -1.0}


def _pnl_flat10_ah(actual_score: float, odds: float) -> float:
    mult = _PNL_MULTIPLIER[actual_score]
    if mult > 0:
        return round((odds - 1.0) * 10.0 * mult, 2)
    return round(10.0 * mult, 2)


def _pnl_flat10_1x2(actual: int, odds: float) -> float:
    if actual == 1:
        return round(10.0 * (odds - 1.0), 2)
    return -10.0


def safe_novig(h, a):
    try:
        return novig_home(h, a)
    except (ValueError, TypeError):
        return np.nan


# ---------------------------------------------------------------------------
# Regression & Metric Helpers (exact match to recalibration_test.py)
# ---------------------------------------------------------------------------
def fit_model(y, X):
    """Fractional logit via GLM Binomial, robust HC1 standard errors."""
    glm = sm.GLM(y.values.astype(float), X.values.astype(float), family=Binomial())
    try:
        result = glm.fit(cov_type='HC1')
    except TypeError:
        result = glm.fit()
        result = result.get_robustcov_results(cov_type='HC1')
    result._xnames = list(X.columns)
    return result


def fit_model_clustered(y, X, groups):
    """Fractional logit via GLM Binomial, cluster-robust SEs by match."""
    glm = sm.GLM(y.values.astype(float), X.values.astype(float), family=Binomial())
    result = glm.fit(cov_type='cluster', cov_kwds={'groups': np.asarray(groups)})
    result._xnames = list(X.columns)
    return result


def log_loss_frac(y, p):
    p = np.clip(np.asarray(p, dtype=float), 1e-9, 1.0 - 1e-9)
    y = np.asarray(y, dtype=float)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def brier_score(y, p):
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    return float(np.mean((y - p) ** 2))


def bootstrap_roi_ci(pnl_arr, n_boot=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    n = len(pnl_arr)
    if n == 0:
        return np.nan, np.nan
    boot = [
        rng.choice(pnl_arr, size=n, replace=True).sum() / (n * 10.0) * 100.0
        for _ in range(n_boot)
    ]
    return float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def build_design_matrices(df_sub, add_league_dummies=False, league_categories=None):
    """Build X_m1 and X_m3 design matrices with optional league dummy intercepts."""
    X_base = pd.DataFrame({'const': np.ones(len(df_sub), dtype=float)}, index=df_sub.index)
    if add_league_dummies:
        if league_categories is None:
            league_categories = sorted(df_sub['league'].unique())
        # Use first league as reference category
        for lg in league_categories[1:]:
            X_base[f'lg_{lg}'] = (df_sub['league'] == lg).astype(float)

    X_m1 = X_base.copy()
    X_m1['logit_market'] = df_sub['logit_market'].astype(float)

    X_m3 = X_base.copy()
    X_m3['logit_market'] = df_sub['logit_market'].astype(float)
    X_m3['logit_model'] = df_sub['logit_model'].astype(float)
    return X_m1, X_m3


def extract_m1_m3_stats(df_sub, add_league_dummies=False):
    y = df_sub['actual_score']
    X_m1, X_m3 = build_design_matrices(df_sub, add_league_dummies=add_league_dummies)
    m1 = fit_model(y, X_m1)
    m3 = fit_model(y, X_m3)

    p_m1 = m1.predict(X_m1.values.astype(float))
    p_m3 = m3.predict(X_m3.values.astype(float))
    ll_m1 = log_loss_frac(y, p_m1)
    ll_m3 = log_loss_frac(y, p_m3)
    ll_mkt_raw = log_loss_frac(y, df_sub['market_prob_c'])

    idx_mkt_m1 = m1._xnames.index('logit_market')
    idx_mkt_m3 = m3._xnames.index('logit_market')
    idx_mod_m3 = m3._xnames.index('logit_model')

    return {
        'n': int(len(df_sub)),
        'm1_b_mkt': float(m1.params[idx_mkt_m1]),
        'm1_se_mkt': float(m1.bse[idx_mkt_m1]),
        'm1_p_mkt': float(m1.pvalues[idx_mkt_m1]),
        'm3_b_mkt': float(m3.params[idx_mkt_m3]),
        'm3_se_mkt': float(m3.bse[idx_mkt_m3]),
        'm3_p_mkt': float(m3.pvalues[idx_mkt_m3]),
        'm3_b_mod': float(m3.params[idx_mod_m3]),
        'm3_se_mod': float(m3.bse[idx_mod_m3]),
        'm3_p_mod': float(m3.pvalues[idx_mod_m3]),
        'll_mkt_raw': ll_mkt_raw,
        'll_m1': ll_m1,
        'll_m3': ll_m3,
        'd_ll': ll_m3 - ll_m1,
    }


def fit_ols_signal(df_sub):
    """Fit (a) move_avg ~ signal and (b) move_avg ~ logit_model_home + logit_pre_home_avg (HC1)."""
    d = df_sub.dropna(subset=['move_avg', 'signal', 'logit_model_home', 'logit_pre_home_avg']).copy()
    n = len(d)
    if n < 5:
        return None
    y = d['move_avg'].values.astype(float)

    # Spec (a): move_avg ~ signal
    Xa = sm.add_constant(d['signal'].values.astype(float))
    ra = sm.OLS(y, Xa).fit(cov_type='HC1')

    # Spec (b): move_avg ~ logit_model_home + logit_pre_home_avg
    Xb = sm.add_constant(d[['logit_model_home', 'logit_pre_home_avg']].values.astype(float))
    rb = sm.OLS(y, Xb).fit(cov_type='HC1')

    return {
        'n': int(n),
        'a_coef': float(ra.params[1]),
        'a_se': float(ra.bse[1]),
        'a_t': float(ra.tvalues[1]),
        'a_p': float(ra.pvalues[1]),
        'b_mod_coef': float(rb.params[1]),
        'b_mod_se': float(rb.bse[1]),
        'b_mod_t': float(rb.tvalues[1]),
        'b_mod_p': float(rb.pvalues[1]),
        'b_pre_coef': float(rb.params[2]),
        'b_pre_se': float(rb.bse[2]),
        'b_pre_t': float(rb.tvalues[2]),
        'b_pre_p': float(rb.pvalues[2]),
    }


def main():
    # -----------------------------------------------------------------------
    # 1. Load soft_merged.csv and soft_ratings.csv
    # -----------------------------------------------------------------------
    merged = pd.read_csv(MERGED_PATH)
    ratings = pd.read_csv(RATINGS_PATH)

    merged['season'] = merged['season'].astype(str).str.strip()
    ratings['season'] = ratings['season'].astype(str).str.strip()
    merged['date_dt'] = pd.to_datetime(merged['date'])
    ratings['date_dt'] = pd.to_datetime(ratings['date'])

    # Compute prior match count in soft_ratings.csv for each row (before that match)
    team_counts = {}
    home_prior = []
    away_prior = []
    for _, r in ratings.iterrows():
        ht = r['home_team']
        at = r['away_team']
        home_prior.append(team_counts.get(ht, 0))
        away_prior.append(team_counts.get(at, 0))
        team_counts[ht] = team_counts.get(ht, 0) + 1
        team_counts[at] = team_counts.get(at, 0) + 1

    ratings['home_prior_matches'] = home_prior
    ratings['away_prior_matches'] = away_prior

    # -----------------------------------------------------------------------
    # 2. Sample Filters (in exact order)
    # -----------------------------------------------------------------------
    # Filter 1: Inner join soft_merged <-> soft_ratings on date, league, season, home_team, away_team
    df_f1 = merged.merge(
        ratings.drop(columns=['date']),
        on=['date_dt', 'league', 'season', 'home_team', 'away_team'],
        how='inner',
    )

    # Filter 2: Warm-up excluded (drop each league's first xG season)
    def is_eval_season(row):
        return row['season'] in EVAL_SEASONS.get(row['league'], [])

    df_f2 = df_f1[df_f1.apply(is_eval_season, axis=1)].copy()

    # Filter 3: Experience guard (both teams >= 10 earlier rows in soft_ratings.csv)
    df_f3 = df_f2[
        (df_f2['home_prior_matches'] >= MIN_EXPERIENCE) &
        (df_f2['away_prior_matches'] >= MIN_EXPERIENCE)
    ].copy()

    # Filter 4: Market data present (and valid decimal odds > 1.0)
    ah_req = ['ah_line', 'odds_ah_home', 'odds_ah_away', 'home_goals', 'away_goals']
    x2_req = ['odds_home', 'odds_draw', 'odds_away', 'home_goals', 'away_goals']

    df_f4_ah = df_f3[df_f3['league'].isin(PROXY_LEAGUES)].dropna(subset=ah_req).copy()
    df_f4_ah = df_f4_ah[(df_f4_ah['odds_ah_home'] > 1.0) & (df_f4_ah['odds_ah_away'] > 1.0)].copy()

    df_f4_1x2 = df_f3.dropna(subset=x2_req).copy()
    df_f4_1x2 = df_f4_1x2[
        (df_f4_1x2['odds_home'] > 1.0) &
        (df_f4_1x2['odds_draw'] > 1.0) &
        (df_f4_1x2['odds_away'] > 1.0)
    ].copy()

    # Build filter summary per league-season (covering all xG league-seasons in F1)
    filter_rows = []
    stop_filter3_triggered = False
    for lg in ALL_LEAGUES:
        lg_f1 = df_f1[df_f1['league'] == lg]
        for ssn in sorted(lg_f1['season'].unique()):
            n_m = int(((merged['league'] == lg) & (merged['season'] == ssn)).sum())
            n1 = int(((df_f1['league'] == lg) & (df_f1['season'] == ssn)).sum())
            n2 = int(((df_f2['league'] == lg) & (df_f2['season'] == ssn)).sum())
            n3 = int(((df_f3['league'] == lg) & (df_f3['season'] == ssn)).sum())
            n4_ah = int(((df_f4_ah['league'] == lg) & (df_f4_ah['season'] == ssn)).sum())
            n4_1x2 = int(((df_f4_1x2['league'] == lg) & (df_f4_1x2['season'] == ssn)).sum())

            lost_f3_pct = ((n2 - n3) / n2 * 100.0) if n2 > 0 else 0.0
            if n2 > 0 and lost_f3_pct > 25.0:
                stop_filter3_triggered = True
                print(f"STOP CONDITION TRIGGERED: {lg} {ssn} lost {lost_f3_pct:.2f}% (>25%) at Filter 3!")

            filter_rows.append({
                'league': lg,
                'season': ssn,
                'is_eval': n2 > 0,
                'n_merged': n_m,
                'n_f1_rated': n1,
                'n_f2_eval': n2,
                'n_f3_exp': n3,
                'lost_f3_pct': lost_f3_pct,
                'n_f4_ah': n4_ah,
                'n_f4_1x2': n4_1x2,
            })

    if stop_filter3_triggered:
        sys.exit(1)

    # -----------------------------------------------------------------------
    # 3. Compute match probabilities and build per-match-per-market rows
    # -----------------------------------------------------------------------
    # Pre-compute Poisson match probs for all rows in df_f3
    match_probs_cache = {}
    for idx, row in df_f3.iterrows():
        probs = compute_match_probs(
            home_attack=float(row['home_attack']),
            home_defence=float(row['home_defence']),
            away_attack=float(row['away_attack']),
            away_defence=float(row['away_defence']),
            home_advantage=0.0,
        )
        match_probs_cache[idx] = probs

    records = []

    # --- AH Market Rows (Proxy leagues only) ---
    for idx, row in df_f4_ah.iterrows():
        probs = match_probs_cache[idx]
        ah_line = float(row['ah_line'])
        odds_ah_home = float(row['odds_ah_home'])
        odds_ah_away = float(row['odds_ah_away'])

        ah_probs = compute_ah_probs(probs['goal_grid'], ah_line)
        p_home = ah_probs['p_home']
        p_push = ah_probs['p_push']
        p_away = ah_probs['p_away']

        overround = 1.0 / odds_ah_home + 1.0 / odds_ah_away
        impl_home = (1.0 / odds_ah_home) / overround
        impl_away = (1.0 / odds_ah_away) / overround

        edge_home = p_home - impl_home
        edge_away = p_away - impl_away

        if edge_home >= edge_away:
            bet_side = 'home'
            market_odds = odds_ah_home
            market_prob_novig = impl_home
            edge = edge_home
            model_prob = p_home + 0.5 * p_push
        else:
            bet_side = 'away'
            market_odds = odds_ah_away
            market_prob_novig = impl_away
            edge = edge_away
            model_prob = p_away + 0.5 * p_push

        margin = int(row['home_goals']) - int(row['away_goals'])
        ah_result = compute_actual_ah_result(margin, ah_line)
        actual_score = _HOME_BET_SCORE[ah_result] if bet_side == 'home' else _AWAY_BET_SCORE[ah_result]
        pnl = _pnl_flat10_ah(actual_score, market_odds)

        # Line-movement columns (for D5, home perspective)
        model_home = model_prob if bet_side == 'home' else (1.0 - model_prob)
        pre_home_avg = safe_novig(row.get('avg_ah_home'), row.get('avg_ah_away'))
        close_raw_avg_home = safe_novig(row.get('close_avg_ah_home'), row.get('close_avg_ah_away'))
        c_line = row.get('close_ah_line')
        if pd.notna(close_raw_avg_home) and pd.notna(c_line):
            c_conv = convert_q_home(close_raw_avg_home, float(c_line), ah_line, mu=MU)
            close_home_avg = c_conv if c_conv is not None else np.nan
        else:
            close_home_avg = np.nan

        move_avg = (close_home_avg - pre_home_avg) if (pd.notna(close_home_avg) and pd.notna(pre_home_avg)) else np.nan

        records.append({
            'match_id': int(idx),
            'date': row['date'],
            'league': row['league'],
            'season': row['season'],
            'home_team': row['home_team'],
            'away_team': row['away_team'],
            'market': 'AH',
            'odds_timing': row['odds_timing'],
            'home_prior_matches': int(row['home_prior_matches']),
            'away_prior_matches': int(row['away_prior_matches']),
            'home_goals': int(row['home_goals']),
            'away_goals': int(row['away_goals']),
            'home_xg': float(row['home_xg']),
            'away_xg': float(row['away_xg']),
            'home_attack': float(row['home_attack']),
            'home_defence': float(row['home_defence']),
            'away_attack': float(row['away_attack']),
            'away_defence': float(row['away_defence']),
            'lambda_home': float(probs['lambda_home']),
            'lambda_away': float(probs['lambda_away']),
            'prob_home_win': float(probs['prob_home_win']),
            'prob_draw': float(probs['prob_draw']),
            'prob_away_win': float(probs['prob_away_win']),
            'ah_line': ah_line,
            'odds_ah_home': odds_ah_home,
            'odds_ah_away': odds_ah_away,
            'p_ah_home': float(p_home),
            'p_ah_push': float(p_push),
            'p_ah_away': float(p_away),
            'novig_ah_home': float(impl_home),
            'novig_ah_away': float(impl_away),
            'odds_home': row.get('odds_home', np.nan),
            'odds_draw': row.get('odds_draw', np.nan),
            'odds_away': row.get('odds_away', np.nan),
            'market_prob_H': np.nan,
            'market_prob_D': np.nan,
            'market_prob_A': np.nan,
            'bet_side': bet_side,
            'model_prob': round(model_prob, 6),
            'market_odds': round(market_odds, 4),
            'market_prob_novig': round(market_prob_novig, 6),
            'edge': round(edge, 6),
            'ah_result': ah_result,
            'actual_score': actual_score,
            'pnl_flat10': pnl,
            'avg_ah_home': row.get('avg_ah_home', np.nan),
            'avg_ah_away': row.get('avg_ah_away', np.nan),
            'close_ah_line': row.get('close_ah_line', np.nan),
            'close_avg_ah_home': row.get('close_avg_ah_home', np.nan),
            'close_avg_ah_away': row.get('close_avg_ah_away', np.nan),
            'model_home': model_home,
            'pre_home_avg': pre_home_avg,
            'close_home_avg': close_home_avg,
            'move_avg': move_avg,
        })

    # --- 1X2 Market Rows (All 8 leagues) ---
    stacked_1x2_records = []
    for idx, row in df_f4_1x2.iterrows():
        probs = match_probs_cache[idx]
        oh = float(row['odds_home'])
        od = float(row['odds_draw'])
        oa = float(row['odds_away'])

        overround = 1.0 / oh + 1.0 / od + 1.0 / oa
        mkt_H = (1.0 / oh) / overround
        mkt_D = (1.0 / od) / overround
        mkt_A = (1.0 / oa) / overround

        mod_H = float(probs['prob_home_win'])
        mod_D = float(probs['prob_draw'])
        mod_A = float(probs['prob_away_win'])

        edge_H = mod_H - mkt_H
        edge_D = mod_D - mkt_D
        edge_A = mod_A - mkt_A

        # Ties -> H, then D
        if edge_H >= edge_D and edge_H >= edge_A:
            chosen = 'H'
            model_prob = mod_H
            market_prob_novig = mkt_H
            market_odds = oh
            edge = edge_H
        elif edge_D >= edge_A:
            chosen = 'D'
            model_prob = mod_D
            market_prob_novig = mkt_D
            market_odds = od
            edge = edge_D
        else:
            chosen = 'A'
            model_prob = mod_A
            market_prob_novig = mkt_A
            market_odds = oa
            edge = edge_A

        hg = int(row['home_goals'])
        ag = int(row['away_goals'])
        actual_outcome = 'H' if hg > ag else ('D' if hg == ag else 'A')
        actual_score = 1.0 if chosen == actual_outcome else 0.0
        pnl = _pnl_flat10_1x2(int(actual_score), market_odds)

        records.append({
            'match_id': int(idx),
            'date': row['date'],
            'league': row['league'],
            'season': row['season'],
            'home_team': row['home_team'],
            'away_team': row['away_team'],
            'market': '1X2',
            'odds_timing': row['odds_timing'],
            'home_prior_matches': int(row['home_prior_matches']),
            'away_prior_matches': int(row['away_prior_matches']),
            'home_goals': hg,
            'away_goals': ag,
            'home_xg': float(row['home_xg']),
            'away_xg': float(row['away_xg']),
            'home_attack': float(row['home_attack']),
            'home_defence': float(row['home_defence']),
            'away_attack': float(row['away_attack']),
            'away_defence': float(row['away_defence']),
            'lambda_home': float(probs['lambda_home']),
            'lambda_away': float(probs['lambda_away']),
            'prob_home_win': mod_H,
            'prob_draw': mod_D,
            'prob_away_win': mod_A,
            'ah_line': row.get('ah_line', np.nan),
            'odds_ah_home': row.get('odds_ah_home', np.nan),
            'odds_ah_away': row.get('odds_ah_away', np.nan),
            'p_ah_home': np.nan,
            'p_ah_push': np.nan,
            'p_ah_away': np.nan,
            'novig_ah_home': np.nan,
            'novig_ah_away': np.nan,
            'odds_home': oh,
            'odds_draw': od,
            'odds_away': oa,
            'market_prob_H': round(mkt_H, 6),
            'market_prob_D': round(mkt_D, 6),
            'market_prob_A': round(mkt_A, 6),
            'bet_side': chosen,
            'model_prob': round(model_prob, 6),
            'market_odds': round(market_odds, 4),
            'market_prob_novig': round(market_prob_novig, 6),
            'edge': round(edge, 6),
            'ah_result': actual_outcome,
            'actual_score': actual_score,
            'pnl_flat10': pnl,
            'avg_ah_home': row.get('avg_ah_home', np.nan),
            'avg_ah_away': row.get('avg_ah_away', np.nan),
            'close_ah_line': row.get('close_ah_line', np.nan),
            'close_avg_ah_home': row.get('close_avg_ah_home', np.nan),
            'close_avg_ah_away': row.get('close_avg_ah_away', np.nan),
            'model_home': np.nan,
            'pre_home_avg': np.nan,
            'close_home_avg': np.nan,
            'move_avg': np.nan,
        })

        for out_code, mod_p, mkt_p in [('H', mod_H, mkt_H), ('D', mod_D, mkt_D), ('A', mod_A, mkt_A)]:
            stacked_1x2_records.append({
                'match_id': int(idx),
                'league': row['league'],
                'season': row['season'],
                'outcome': out_code,
                'model_prob': mod_p,
                'market_prob_novig': mkt_p,
                'actual_score': 1.0 if actual_outcome == out_code else 0.0,
            })

    matches_df = pd.DataFrame(records)

    # Add clipped probs and logits
    matches_df['model_prob_c'] = matches_df['model_prob'].clip(CLIP_LO, CLIP_HI)
    matches_df['market_prob_c'] = matches_df['market_prob_novig'].clip(CLIP_LO, CLIP_HI)
    matches_df['logit_model'] = np.log(matches_df['model_prob_c'] / (1.0 - matches_df['model_prob_c']))
    matches_df['logit_market'] = np.log(matches_df['market_prob_c'] / (1.0 - matches_df['market_prob_c']))

    # For D5 on AH rows:
    ah_mask = matches_df['market'] == 'AH'
    m_home_c = matches_df.loc[ah_mask, 'model_home'].clip(CLIP_LO, CLIP_HI)
    p_home_avg_c = matches_df.loc[ah_mask, 'pre_home_avg'].clip(CLIP_LO, CLIP_HI)
    matches_df.loc[ah_mask, 'logit_model_home'] = np.log(m_home_c / (1.0 - m_home_c))
    matches_df.loc[ah_mask, 'logit_pre_home_avg'] = np.log(p_home_avg_c / (1.0 - p_home_avg_c))
    matches_df.loc[ah_mask, 'signal'] = (
        matches_df.loc[ah_mask, 'logit_model_home'] - matches_df.loc[ah_mask, 'logit_pre_home_avg']
    )

    os.makedirs(os.path.dirname(OUT_MATCHES_PATH), exist_ok=True)
    matches_df.to_csv(OUT_MATCHES_PATH, index=False)
    print(f"Saved {OUT_MATCHES_PATH} ({len(matches_df)} rows)")

    # -----------------------------------------------------------------------
    # 4. Part D1 — Sanity & Stop Condition Check
    # -----------------------------------------------------------------------
    df_1x2 = matches_df[matches_df['market'] == '1X2'].copy()
    df_ah = matches_df[matches_df['market'] == 'AH'].copy()

    d1_rows = []
    stop_d1_triggered = False
    for lg in ALL_LEAGUES:
        for ssn in EVAL_SEASONS[lg]:
            sub = df_1x2[(df_1x2['league'] == lg) & (df_1x2['season'] == ssn)]
            if len(sub) == 0:
                continue
            mean_lh = float(sub['lambda_home'].mean())
            mean_la = float(sub['lambda_away'].mean())
            mean_gh = float(sub['home_goals'].mean())
            mean_ga = float(sub['away_goals'].mean())
            mean_xgh = float(sub['home_xg'].mean())
            mean_xga = float(sub['away_xg'].mean())

            pred_tot = mean_lh + mean_la
            act_tot = mean_gh + mean_ga
            tot_diff = pred_tot - act_tot

            if abs(tot_diff) > 0.5:
                stop_d1_triggered = True
                print(
                    f"STOP CONDITION TRIGGERED (D1): {lg} {ssn} |pred_tot ({pred_tot:.3f}) - act_tot ({act_tot:.3f})| = {abs(tot_diff):.3f} > 0.5"
                )

            # 3-outcome Brier score (mean across H, D, A of (p_i - y_i)^2, and sum across H, D, A)
            y_H = (sub['home_goals'] > sub['away_goals']).astype(float).values
            y_D = (sub['home_goals'] == sub['away_goals']).astype(float).values
            y_A = (sub['home_goals'] < sub['away_goals']).astype(float).values

            brier3_mod = float(np.mean(
                (sub['prob_home_win'].values - y_H) ** 2 +
                (sub['prob_draw'].values - y_D) ** 2 +
                (sub['prob_away_win'].values - y_A) ** 2
            ) / 3.0)
            brier3_mkt = float(np.mean(
                (sub['market_prob_H'].values - y_H) ** 2 +
                (sub['market_prob_D'].values - y_D) ** 2 +
                (sub['market_prob_A'].values - y_A) ** 2
            ) / 3.0)

            brier_chosen_mod = brier_score(sub['actual_score'].values, sub['model_prob'].values)
            brier_chosen_mkt = brier_score(sub['actual_score'].values, sub['market_prob_novig'].values)

            d1_rows.append({
                'league': lg,
                'season': ssn,
                'n': len(sub),
                'lam_h': mean_lh,
                'lam_a': mean_la,
                'pred_tot': pred_tot,
                'act_h': mean_gh,
                'act_a': mean_ga,
                'act_tot': act_tot,
                'tot_diff': tot_diff,
                'xg_h': mean_xgh,
                'xg_a': mean_xga,
                'xg_tot': mean_xgh + mean_xga,
                'brier3_mod': brier3_mod,
                'brier3_mkt': brier3_mkt,
                'brier_ch_mod': brier_chosen_mod,
                'brier_ch_mkt': brier_chosen_mkt,
            })

    if stop_d1_triggered:
        sys.exit(1)

    # -----------------------------------------------------------------------
    # 5. Part D2 — AH, M1 and M3 (Proxy Leagues)
    # -----------------------------------------------------------------------
    d2_by_league = {}
    for lg in PROXY_LEAGUES:
        d2_by_league[lg] = extract_m1_m3_stats(df_ah[df_ah['league'] == lg], add_league_dummies=False)
    d2_pooled = extract_m1_m3_stats(df_ah, add_league_dummies=True)

    d2_by_season_pooled = {}
    for ssn in ['2024-25', '2025-26']:
        d2_by_season_pooled[ssn] = extract_m1_m3_stats(df_ah[df_ah['season'] == ssn], add_league_dummies=True)

    d2_by_lg_ssn = {}
    for lg in PROXY_LEAGUES:
        for ssn in EVAL_SEASONS[lg]:
            sub = df_ah[(df_ah['league'] == lg) & (df_ah['season'] == ssn)]
            d2_by_lg_ssn[(lg, ssn)] = extract_m1_m3_stats(sub, add_league_dummies=False)

    # -----------------------------------------------------------------------
    # 6. Part D3 — 1X2, M1 and M3 (All 8 Leagues + Stacked Robustness)
    # -----------------------------------------------------------------------
    d3_by_league = {}
    for lg in ALL_LEAGUES:
        d3_by_league[lg] = extract_m1_m3_stats(df_1x2[df_1x2['league'] == lg], add_league_dummies=False)

    df_1x2_proxy = df_1x2[df_1x2['league'].isin(PROXY_LEAGUES)].copy()
    df_1x2_scand = df_1x2[df_1x2['league'].isin(SCAND_LEAGUES)].copy()

    d3_pooled_proxy = extract_m1_m3_stats(df_1x2_proxy, add_league_dummies=True)
    d3_pooled_scand = extract_m1_m3_stats(df_1x2_scand, add_league_dummies=True)
    d3_pooled_all8 = extract_m1_m3_stats(df_1x2, add_league_dummies=True)

    d3_by_season_proxy = {}
    for ssn in ['2024-25', '2025-26']:
        d3_by_season_proxy[ssn] = extract_m1_m3_stats(
            df_1x2_proxy[df_1x2_proxy['season'] == ssn], add_league_dummies=True
        )

    d3_by_season_scand = {}
    for ssn in ['2023', '2024', '2025', '2026']:
        sub = df_1x2_scand[df_1x2_scand['season'] == ssn]
        has_mult_lg = sub['league'].nunique() > 1
        d3_by_season_scand[ssn] = extract_m1_m3_stats(sub, add_league_dummies=has_mult_lg)

    d3_by_lg_ssn = {}
    for lg in ALL_LEAGUES:
        for ssn in EVAL_SEASONS[lg]:
            sub = df_1x2[(df_1x2['league'] == lg) & (df_1x2['season'] == ssn)]
            d3_by_lg_ssn[(lg, ssn)] = extract_m1_m3_stats(sub, add_league_dummies=False)

    # Stacked 1X2 robustness (3 outcomes per match, cluster-robust SEs by match_id)
    stacked_df = pd.DataFrame(stacked_1x2_records)
    stacked_df['model_prob_c'] = stacked_df['model_prob'].clip(CLIP_LO, CLIP_HI)
    stacked_df['market_prob_c'] = stacked_df['market_prob_novig'].clip(CLIP_LO, CLIP_HI)
    stacked_df['logit_model'] = np.log(stacked_df['model_prob_c'] / (1.0 - stacked_df['model_prob_c']))
    stacked_df['logit_market'] = np.log(stacked_df['market_prob_c'] / (1.0 - stacked_df['market_prob_c']))

    def extract_stacked_stats(st_sub, add_league_dummies=False):
        y = st_sub['actual_score']
        X_m1, X_m3 = build_design_matrices(st_sub, add_league_dummies=add_league_dummies)
        m1 = fit_model_clustered(y, X_m1, st_sub['match_id'])
        m3 = fit_model_clustered(y, X_m3, st_sub['match_id'])
        idx_mkt = m3._xnames.index('logit_market')
        idx_mod = m3._xnames.index('logit_model')
        ll_m1 = log_loss_frac(y, m1.predict(X_m1.values.astype(float)))
        ll_m3 = log_loss_frac(y, m3.predict(X_m3.values.astype(float)))
        return {
            'n_matches': int(st_sub['match_id'].nunique()),
            'n_rows': int(len(st_sub)),
            'b_mkt': float(m3.params[idx_mkt]),
            'se_mkt': float(m3.bse[idx_mkt]),
            'p_mkt': float(m3.pvalues[idx_mkt]),
            'b_mod': float(m3.params[idx_mod]),
            'se_mod': float(m3.bse[idx_mod]),
            'p_mod': float(m3.pvalues[idx_mod]),
            'll_m1': ll_m1,
            'll_m3': ll_m3,
            'd_ll': ll_m3 - ll_m1,
        }

    d3_stacked_proxy = extract_stacked_stats(
        stacked_df[stacked_df['league'].isin(PROXY_LEAGUES)], add_league_dummies=True
    )
    d3_stacked_scand = extract_stacked_stats(
        stacked_df[stacked_df['league'].isin(SCAND_LEAGUES)], add_league_dummies=True
    )
    d3_stacked_all8 = extract_stacked_stats(stacked_df, add_league_dummies=True)
    d3_stacked_by_lg = {
        lg: extract_stacked_stats(stacked_df[stacked_df['league'] == lg], add_league_dummies=False)
        for lg in ALL_LEAGUES
    }

    # -----------------------------------------------------------------------
    # 7. Part D4 — Out-of-Sample Threshold Sweep
    # -----------------------------------------------------------------------
    def run_oos_group(df_group, is_train_fn, add_league_dummies=True):
        tr = df_group[df_group.apply(is_train_fn, axis=1)].copy().reset_index(drop=True)
        te = df_group[~df_group.apply(is_train_fn, axis=1)].copy().reset_index(drop=True)

        cats = sorted(df_group['league'].unique())
        _, X_tr_m3 = build_design_matrices(tr, add_league_dummies=add_league_dummies, league_categories=cats)
        _, X_te_m3 = build_design_matrices(te, add_league_dummies=add_league_dummies, league_categories=cats)

        m3_tr = fit_model(tr['actual_score'], X_tr_m3)
        te['calib_prob'] = np.clip(m3_tr.predict(X_te_m3.values.astype(float)), 1e-7, 1.0 - 1e-7)
        te['calibrated_edge'] = te['calib_prob'] - te['market_prob_c']

        idx_mkt = m3_tr._xnames.index('logit_market')
        idx_mod = m3_tr._xnames.index('logit_model')

        sweep_rows = []
        for thr in THRESHOLDS:
            bets = te[te['calibrated_edge'] >= thr]
            n = len(bets)
            if n == 0:
                sweep_rows.append({
                    'thr': thr, 'n': 0, 'mean_edge': np.nan,
                    'act_score': np.nan, 'roi': np.nan, 'ci_lo': np.nan, 'ci_hi': np.nan,
                })
            else:
                roi = float(bets['pnl_flat10'].sum() / (n * 10.0) * 100.0)
                lo, hi = bootstrap_roi_ci(bets['pnl_flat10'].values)
                sweep_rows.append({
                    'thr': thr,
                    'n': int(n),
                    'mean_edge': float(bets['calibrated_edge'].mean() * 100.0),
                    'act_score': float(bets['actual_score'].mean()),
                    'roi': roi,
                    'ci_lo': lo,
                    'ci_hi': hi,
                })

        return {
            'n_train': len(tr),
            'n_test': len(te),
            'tr_b_mkt': float(m3_tr.params[idx_mkt]),
            'tr_se_mkt': float(m3_tr.bse[idx_mkt]),
            'tr_p_mkt': float(m3_tr.pvalues[idx_mkt]),
            'tr_b_mod': float(m3_tr.params[idx_mod]),
            'tr_se_mod': float(m3_tr.bse[idx_mod]),
            'tr_p_mod': float(m3_tr.pvalues[idx_mod]),
            'll_te_mkt': log_loss_frac(te['actual_score'], te['market_prob_c']),
            'll_te_m3': log_loss_frac(te['actual_score'], te['calib_prob']),
            'sweep': sweep_rows,
        }

    # Earliest evaluation season per league:
    # Proxy: 2024-25 (train) -> 2025-26 (test)
    # Scand: per-league earliest eval season (DNK 2023, SWE 2024, NOR 2024) -> later seasons
    # Also compute Scand alternative split: train <= 2024 (DNK 2023-2024, SWE/NOR 2024) -> test >= 2025
    is_earliest_eval = lambda r: r['season'] == EVAL_SEASONS[r['league']][0]
    is_scand_le_2024 = lambda r: r['season'] in ('2023', '2024')

    d4_proxy_ah_dum = run_oos_group(df_ah, is_earliest_eval, add_league_dummies=True)
    d4_proxy_ah_nodum = run_oos_group(df_ah, is_earliest_eval, add_league_dummies=False)

    d4_proxy_1x2_dum = run_oos_group(df_1x2_proxy, is_earliest_eval, add_league_dummies=True)
    d4_proxy_1x2_nodum = run_oos_group(df_1x2_proxy, is_earliest_eval, add_league_dummies=False)

    d4_scand_1x2_dum = run_oos_group(df_1x2_scand, is_earliest_eval, add_league_dummies=True)
    d4_scand_1x2_nodum = run_oos_group(df_1x2_scand, is_earliest_eval, add_league_dummies=False)
    d4_scand_1x2_cal24 = run_oos_group(df_1x2_scand, is_scand_le_2024, add_league_dummies=True)

    # -----------------------------------------------------------------------
    # 8. Part D5 — Line-Movement Test (Proxy Leagues AH + EPL Benchmark)
    # -----------------------------------------------------------------------
    d5_by_league = {}
    for lg in PROXY_LEAGUES:
        d5_by_league[lg] = fit_ols_signal(df_ah[df_ah['league'] == lg])
    d5_pooled = fit_ols_signal(df_ah)

    # Pooled with league dummy intercepts as robustness
    d_ah_valid = df_ah.dropna(subset=['move_avg', 'signal', 'logit_model_home', 'logit_pre_home_avg']).copy()
    X_d5a_fe = pd.DataFrame({'const': 1.0}, index=d_ah_valid.index)
    for lg in PROXY_LEAGUES[1:]:
        X_d5a_fe[f'lg_{lg}'] = (d_ah_valid['league'] == lg).astype(float)
    X_d5b_fe = X_d5a_fe.copy()
    X_d5a_fe['signal'] = d_ah_valid['signal'].astype(float)
    X_d5b_fe['logit_model_home'] = d_ah_valid['logit_model_home'].astype(float)
    X_d5b_fe['logit_pre_home_avg'] = d_ah_valid['logit_pre_home_avg'].astype(float)

    ra_fe = sm.OLS(d_ah_valid['move_avg'].values.astype(float), X_d5a_fe.values.astype(float)).fit(cov_type='HC1')
    rb_fe = sm.OLS(d_ah_valid['move_avg'].values.astype(float), X_d5b_fe.values.astype(float)).fit(cov_type='HC1')
    idx_sig_fe = list(X_d5a_fe.columns).index('signal')
    idx_mod_fe = list(X_d5b_fe.columns).index('logit_model_home')
    idx_pre_fe = list(X_d5b_fe.columns).index('logit_pre_home_avg')
    d5_pooled_fe = {
        'n': int(len(d_ah_valid)),
        'a_coef': float(ra_fe.params[idx_sig_fe]),
        'a_se': float(ra_fe.bse[idx_sig_fe]),
        'a_t': float(ra_fe.tvalues[idx_sig_fe]),
        'a_p': float(ra_fe.pvalues[idx_sig_fe]),
        'b_mod_coef': float(rb_fe.params[idx_mod_fe]),
        'b_mod_se': float(rb_fe.bse[idx_mod_fe]),
        'b_mod_t': float(rb_fe.tvalues[idx_mod_fe]),
        'b_mod_p': float(rb_fe.pvalues[idx_mod_fe]),
        'b_pre_coef': float(rb_fe.params[idx_pre_fe]),
        'b_pre_se': float(rb_fe.bse[idx_pre_fe]),
        'b_pre_t': float(rb_fe.tvalues[idx_pre_fe]),
        'b_pre_p': float(rb_fe.pvalues[idx_pre_fe]),
    }

    # EPL 2024-25 + 2025-26 benchmark from output/backtest_results/clv_edge_matches.csv
    epl_clv = pd.read_csv(EPL_CLV_MATCHES_PATH)
    epl_sub = epl_clv[
        (epl_clv['league'] == 'EPL') &
        (epl_clv['season'].isin(['2024-25', '2025-26']))
    ].copy()
    epl_m_c = epl_sub['model_home'].clip(CLIP_LO, CLIP_HI)
    epl_p_avg_c = epl_sub['pre_home_avg'].clip(CLIP_LO, CLIP_HI)
    epl_sub['logit_model_home'] = np.log(epl_m_c / (1.0 - epl_m_c))
    epl_sub['logit_pre_home_avg'] = np.log(epl_p_avg_c / (1.0 - epl_p_avg_c))
    epl_sub['signal'] = epl_sub['logit_model_home'] - epl_sub['logit_pre_home_avg']
    d5_epl_bench = fit_ols_signal(epl_sub)

    # -----------------------------------------------------------------------
    # 9. Format and Save Report
    # -----------------------------------------------------------------------
    lines = []
    W = 108

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

    H(f"SOFT-LEAGUE CALIBRATION & LINE-MOVEMENT REPORT  --  {datetime.now().strftime('%Y-%m-%d')}")
    L("  Leagues: Proxy (B1, N1, P1, T1, E1; AH + 1X2, pre-closing) | Scandinavian (DNK, SWE, NOR; 1X2, closing)")
    L(f"  Inputs:  {MERGED_PATH} (12,869 rows), {RATINGS_PATH} (7,841 xG rated rows)")
    L(f"  Outputs: {OUT_MATCHES_PATH} ({len(matches_df)} match-market rows)")
    L()

    # --- Part C Sample Filters ---
    H("PART C -- SAMPLE FILTERS (PER LEAGUE-SEASON)")
    L("  Order of filters:")
    L("    1. Rated rows: inner join soft_merged <-> soft_ratings on (date, league, season, home_team, away_team)")
    L("    2. Warm-up excluded: drop first xG season per league (proxy 2023-24; DNK 2022; SWE/NOR 2023)")
    L("    3. Experience guard: drop match if either team has < 10 earlier rows in soft_ratings.csv")
    L("    4. Market data present: AH (ah_line, odds_ah_home, odds_ah_away) | 1X2 (odds_home, odds_draw, odds_away)")
    L()
    L(f"  {'League':<6} {'Season':<8} {'Period':<8} | {'Merged':>6} {'F1:Rated':>8} {'F2:Eval':>8} {'F3:Exp>=10':>10} {'F3 Lost%':>9} | {'F4:AH':>7} {'F4:1X2':>7}")
    div()
    tot_m = tot_f1 = tot_f2 = tot_f3 = tot_ah = tot_1x2 = 0
    for r in filter_rows:
        p_lbl = 'EVAL' if r['is_eval'] else 'WARMUP'
        lost_s = f"{r['lost_f3_pct']:>8.2f}%" if r['is_eval'] else f"{'—':>9}"
        ah_s = f"{r['n_f4_ah']:>7d}" if r['league'] in PROXY_LEAGUES else f"{'—':>7}"
        L(f"  {r['league']:<6} {r['season']:<8} {p_lbl:<8} | {r['n_merged']:>6d} {r['n_f1_rated']:>8d} {r['n_f2_eval']:>8d} {r['n_f3_exp']:>10d} {lost_s} | {ah_s} {r['n_f4_1x2']:>7d}")
        tot_m += r['n_merged']
        tot_f1 += r['n_f1_rated']
        tot_f2 += r['n_f2_eval']
        tot_f3 += r['n_f3_exp']
        tot_ah += r['n_f4_ah']
        tot_1x2 += r['n_f4_1x2']
    div()
    tot_lost_pct = (tot_f2 - tot_f3) / tot_f2 * 100.0 if tot_f2 else 0.0
    L(f"  {'TOTAL':<6} {'(xG ssns)':<8} {'':<8} | {tot_m:>6d} {tot_f1:>8d} {tot_f2:>8d} {tot_f3:>10d} {tot_lost_pct:>8.2f}% | {tot_ah:>7d} {tot_1x2:>7d}")
    L(f"  Max Filter 3 loss across evaluation league-seasons: {max(r['lost_f3_pct'] for r in filter_rows if r['is_eval']):.2f}% (Stop threshold: 25.0% -- PASSED)")
    L()

    # --- Part D1 Sanity ---
    H("PART D1 -- SANITY CHECKS (PER EVALUATION LEAGUE-SEASON)")
    L("  1X2 Brier (3-way) = mean over matches of [(p_H - y_H)^2 + (p_D - y_D)^2 + (p_A - y_A)^2] / 3")
    L("  1X2 Brier (chosen) = mean over matches of (p_chosen - y_chosen)^2")
    L()
    L(f"  {'League':<6} {'Season':<8} {'n':>4} | {'lam_H':>6} {'lam_A':>6} {'lam_Tot':>7} | {'Goal_H':>6} {'Goal_A':>6} {'Goal_Tot':>8} {'Diff':>7} | {'xG_H':>6} {'xG_A':>6} | {'Brier3 Mod/Mkt':>17} | {'BrierCh Mod/Mkt':>17}")
    div()
    for r in d1_rows:
        b3_s = f"{r['brier3_mod']:.4f}/{r['brier3_mkt']:.4f}"
        bc_s = f"{r['brier_ch_mod']:.4f}/{r['brier_ch_mkt']:.4f}"
        L(
            f"  {r['league']:<6} {r['season']:<8} {r['n']:>4d} | "
            f"{r['lam_h']:>6.3f} {r['lam_a']:>6.3f} {r['pred_tot']:>7.3f} | "
            f"{r['act_h']:>6.3f} {r['act_a']:>6.3f} {r['act_tot']:>8.3f} {r['tot_diff']:>+7.3f} | "
            f"{r['xg_h']:>6.3f} {r['xg_a']:>6.3f} | {b3_s:>17} | {bc_s:>17}"
        )
    div()
    max_tot_diff = max(abs(r['tot_diff']) for r in d1_rows)
    mkt_wins_all = all(r['brier3_mkt'] < r['brier3_mod'] for r in d1_rows)
    L(f"  Max |mean predicted total goals - mean actual goals|: {max_tot_diff:.3f} (Stop threshold: 0.500 -- PASSED)")
    L(f"  Market 1X2 Brier beats Model 1X2 Brier in all {len(d1_rows)}/{len(d1_rows)} league-seasons: {mkt_wins_all}")
    L()

    # Helper to format M1/M3 table rows
    def fmt_m1_m3_header():
        return (
            f"  {'Subset / Spec':<22} {'n':>5} | {'M1 b_mkt (SE, p)':>24} | "
            f"{'M3 b_mkt (SE, p)':>24} | {'M3 b_model (SE, p)':>26} | {'LL_M1':>8} {'LL_M3':>8} {'dLL':>9}"
        )

    def fmt_m1_m3_row(label, s):
        m1_mkt = f"{s['m1_b_mkt']:+.3f} ({s['m1_se_mkt']:.3f}, {s['m1_p_mkt']:.3f})"
        m3_mkt = f"{s['m3_b_mkt']:+.3f} ({s['m3_se_mkt']:.3f}, {s['m3_p_mkt']:.3f})"
        m3_mod = f"{s['m3_b_mod']:+.4f} ({s['m3_se_mod']:.4f}, {s['m3_p_mod']:.4f})"
        return (
            f"  {label:<22} {s['n']:>5d} | {m1_mkt:>24} | {m3_mkt:>24} | {m3_mod:>26} | "
            f"{s['ll_m1']:>8.5f} {s['ll_m3']:>8.5f} {s['d_ll']:>+9.5f}"
        )

    # --- Part D2 AH M1 & M3 ---
    H("PART D2 -- ASIAN HANDICAP: M1 AND M3 FRACTIONAL LOGIT (PROXY LEAGUES, EVAL SEASONS)")
    L("  M1: actual_score ~ const (+ league dummies if pooled) + logit(market_prob_novig)")
    L("  M3: actual_score ~ const (+ league dummies if pooled) + logit(market_prob_novig) + logit(model_prob)")
    L("  Standard errors: HC1 robust. b_model > 0 => model adds information beyond market.")
    L()
    L("  A. PER LEAGUE AND POOLED (2024-25 + 2025-26):")
    L(fmt_m1_m3_header())
    div()
    for lg in PROXY_LEAGUES:
        L(fmt_m1_m3_row(f"{lg} (24-25 + 25-26)", d2_by_league[lg]))
    div()
    L(fmt_m1_m3_row("POOLED Proxy-5 (FE)", d2_pooled))
    L()

    L("  B. M3 BY EVALUATION SEASON (POOLED & PER LEAGUE):")
    L(fmt_m1_m3_header())
    div()
    for ssn in ['2024-25', '2025-26']:
        L(fmt_m1_m3_row(f"Pooled {ssn} (FE)", d2_by_season_pooled[ssn]))
    div()
    for lg in PROXY_LEAGUES:
        for ssn in EVAL_SEASONS[lg]:
            L(fmt_m1_m3_row(f"{lg} {ssn}", d2_by_lg_ssn[(lg, ssn)]))
    L()

    # --- Part D3 1X2 M1 & M3 ---
    H("PART D3 -- 1X2 MARKET: M1 AND M3 LOGIT (ALL 8 LEAGUES, CHOSEN OUTCOME & STACKED ROBUSTNESS)")
    L("  Chosen outcome = argmax_{i in H,D,A} (model_i - market_i). Proxy odds = pre_closing; Scand odds = closing.")
    L()
    L("  A. CHOSEN-OUTCOME ROWS -- PER LEAGUE AND POOLED GROUPS:")
    L(fmt_m1_m3_header())
    div()
    for lg in PROXY_LEAGUES:
        L(fmt_m1_m3_row(f"{lg} (pre_closing)", d3_by_league[lg]))
    div()
    L(fmt_m1_m3_row("POOLED Proxy-5 (FE)", d3_pooled_proxy))
    div()
    for lg in SCAND_LEAGUES:
        L(fmt_m1_m3_row(f"{lg} (closing)", d3_by_league[lg]))
    div()
    L(fmt_m1_m3_row("POOLED Scand-3 (FE)", d3_pooled_scand))
    L(fmt_m1_m3_row("POOLED All-8 (FE)", d3_pooled_all8))
    L()

    L("  B. CHOSEN-OUTCOME M3 BY EVALUATION SEASON:")
    L(fmt_m1_m3_header())
    div()
    for ssn in ['2024-25', '2025-26']:
        L(fmt_m1_m3_row(f"Proxy-5 {ssn} (FE)", d3_by_season_proxy[ssn]))
    for ssn in ['2023', '2024', '2025', '2026']:
        L(fmt_m1_m3_row(f"Scand-3 {ssn}", d3_by_season_scand[ssn]))
    div()
    for lg in ALL_LEAGUES:
        for ssn in EVAL_SEASONS[lg]:
            L(fmt_m1_m3_row(f"{lg} {ssn}", d3_by_lg_ssn[(lg, ssn)]))
    L()

    L("  C. ROBUSTNESS: STACKED 1X2 (ALL 3 OUTCOMES PER MATCH, CLUSTER-ROBUST SEs BY MATCH):")
    L(f"  {'Group / League':<22} {'Matches':>7} {'Rows':>6} | {'M3 b_mkt (SE, p)':>26} | {'M3 b_model (SE, p)':>28} | {'LL_M1':>8} {'LL_M3':>8} {'dLL':>9}")
    div()
    for lbl, st in [
        ('POOLED Proxy-5 (FE)', d3_stacked_proxy),
        ('POOLED Scand-3 (FE)', d3_stacked_scand),
        ('POOLED All-8 (FE)', d3_stacked_all8),
    ]:
        bmkt = f"{st['b_mkt']:+.3f} ({st['se_mkt']:.3f}, {st['p_mkt']:.3f})"
        bmod = f"{st['b_mod']:+.4f} ({st['se_mod']:.4f}, {st['p_mod']:.4f})"
        L(f"  {lbl:<22} {st['n_matches']:>7d} {st['n_rows']:>6d} | {bmkt:>26} | {bmod:>28} | {st['ll_m1']:>8.5f} {st['ll_m3']:>8.5f} {st['d_ll']:>+9.5f}")
    div()
    for lg in ALL_LEAGUES:
        st = d3_stacked_by_lg[lg]
        bmkt = f"{st['b_mkt']:+.3f} ({st['se_mkt']:.3f}, {st['p_mkt']:.3f})"
        bmod = f"{st['b_mod']:+.4f} ({st['se_mod']:.4f}, {st['p_mod']:.4f})"
        L(f"  {lg:<22} {st['n_matches']:>7d} {st['n_rows']:>6d} | {bmkt:>26} | {bmod:>28} | {st['ll_m1']:>8.5f} {st['ll_m3']:>8.5f} {st['d_ll']:>+9.5f}")
    L()

    # --- Part D4 Out-of-Sample Threshold Sweep ---
    H("PART D4 -- OUT-OF-SAMPLE THRESHOLD SWEEP (TRAIN ON EARLIEST EVAL SEASON, TEST ON LATER ONES)")
    L("  calibrated_edge = calib_prob (M3) - market_prob_c")
    L("  Bootstrap 95% CI: 1,000 resamples, seed=42 (same as recalibration_test.py).")
    L()

    def print_d4_block(title, res, roi_note=""):
        L(f"  {title}")
        L(
            f"    Train n={res['n_train']} | Test n={res['n_test']} | "
            f"Train M3: b_mkt={res['tr_b_mkt']:+.4f} (SE={res['tr_se_mkt']:.4f}, p={res['tr_p_mkt']:.4f}), "
            f"b_model={res['tr_b_mod']:+.4f} (SE={res['tr_se_mod']:.4f}, p={res['tr_p_mod']:.4f})"
        )
        L(f"    Test Log-Loss: Market={res['ll_te_mkt']:.5f} vs M3={res['ll_te_m3']:.5f} (dLL={res['ll_te_m3']-res['ll_te_mkt']:+.5f})")
        hdr_roi = f"ROI ({roi_note})" if roi_note else "ROI"
        L(f"    {'Threshold':>10} {'N Bets':>8} {'MeanEdge':>10} {'ActScore':>10} {hdr_roi:>22} {'95% Bootstrap CI':>22}")
        L(f"    {'-'*86}")
        for r in res['sweep']:
            if r['n'] == 0:
                L(f"    {r['thr']*100:>9.1f}% {0:>8d} {'—':>10} {'—':>10} {'—':>22} {'—':>22}")
            else:
                roi_s = f"{r['roi']:+.2f}%" + (f" ({roi_note})" if roi_note else "")
                ci_s = f"[{r['ci_lo']:+.2f}%, {r['ci_hi']:+.2f}%]"
                L(f"    {r['thr']*100:>9.1f}% {r['n']:>8d} {r['mean_edge']:>9.2f}% {r['act_score']:>10.3f} {roi_s:>22} {ci_s:>22}")
        L()

    print_d4_block("1. PROXY-AH (Train: 2024-25, Test: 2025-26) -- Pooled M3 with league dummies:", d4_proxy_ah_dum)
    print_d4_block("   PROXY-AH (Train: 2024-25, Test: 2025-26) -- Pooled M3 without league dummies:", d4_proxy_ah_nodum)
    print_d4_block("2. PROXY-1X2 (Train: 2024-25, Test: 2025-26) -- Pooled M3 with league dummies:", d4_proxy_1x2_dum)
    print_d4_block("   PROXY-1X2 (Train: 2024-25, Test: 2025-26) -- Pooled M3 without league dummies:", d4_proxy_1x2_nodum)
    print_d4_block(
        "3. SCAND-1X2 (Train: earliest eval season per league [DNK 2023, SWE/NOR 2024]; Test: later eval seasons) -- M3 with league dummies:",
        d4_scand_1x2_dum,
        roi_note="at closing prices",
    )
    print_d4_block(
        "   SCAND-1X2 (Train: earliest eval season per league; Test: later eval seasons) -- M3 without league dummies:",
        d4_scand_1x2_nodum,
        roi_note="at closing prices",
    )
    print_d4_block(
        "   SCAND-1X2 ALT SPLIT (Train: 2023-2024, Test: 2025-2026) -- M3 with league dummies:",
        d4_scand_1x2_cal24,
        roi_note="at closing prices",
    )

    # --- Part D5 Line Movement Test ---
    H("PART D5 -- LINE-MOVEMENT TEST (PROXY LEAGUES AH + EPL 2024-25/2025-26 BENCHMARK)")
    L("  Home perspective (model.clv, mu=2.8):")
    L("    move_avg = close_home_avg (market-avg closing no-vig converted onto pre line) - pre_home_avg (market-avg pre no-vig)")
    L("    signal   = logit(clip(model_home, 0.01, 0.99)) - logit(clip(pre_home_avg, 0.01, 0.99))")
    L("  Specifications (OLS, HC1 SEs):")
    L("    (a) move_avg ~ signal")
    L("    (b) move_avg ~ logit(model_home) + logit(pre_home_avg)   [artefact control]")
    L()
    L(
        f"  {'League / Group':<24} {'n':>5} | {'--- (a) move_avg ~ signal ---':>34} | "
        f"{'--- (b) model term (artefact ctrl) ---':>38}"
    )
    L(
        f"  {'':<24} {'':>5} | {'Coef':>10} {'SE(HC1)':>9} {'t':>7} {'p':>7} | "
        f"{'b_model':>10} {'SE(HC1)':>9} {'t':>7} {'p':>7}"
    )
    div()

    def fmt_d5_row(label, r):
        if r is None:
            return f"  {label:<24} {'—':>5}"
        return (
            f"  {label:<24} {r['n']:>5d} | "
            f"{r['a_coef']:>+10.5f} {r['a_se']:>9.5f} {r['a_t']:>+7.2f} {r['a_p']:>7.4f} | "
            f"{r['b_mod_coef']:>+10.5f} {r['b_mod_se']:>9.5f} {r['b_mod_t']:>+7.2f} {r['b_mod_p']:>7.4f}"
        )

    for lg in PROXY_LEAGUES:
        L(fmt_d5_row(f"{lg} (24-25 + 25-26)", d5_by_league[lg]))
    div()
    L(fmt_d5_row("POOLED Proxy-5 (OLS)", d5_pooled))
    L(fmt_d5_row("POOLED Proxy-5 (w/ FE)", d5_pooled_fe))
    div()
    L(fmt_d5_row("EPL 24-25 + 25-26 (Bench)", d5_epl_bench))
    L()

    L("  Full Spec (b) details (including coefficient on logit(pre_home_avg)):")
    L(f"  {'League / Group':<24} {'n':>5} | {'b_model':>10} {'SE':>9} {'t':>7} {'p':>7} | {'b_pre_avg':>10} {'SE':>9} {'t':>7} {'p':>7}")
    div()
    for lbl, r in (
        [(f"{lg} (24-25 + 25-26)", d5_by_league[lg]) for lg in PROXY_LEAGUES]
        + [
            ("POOLED Proxy-5 (OLS)", d5_pooled),
            ("POOLED Proxy-5 (w/ FE)", d5_pooled_fe),
            ("EPL 24-25 + 25-26 (Bench)", d5_epl_bench),
        ]
    ):
        if r is None:
            continue
        L(
            f"  {lbl:<24} {r['n']:>5d} | "
            f"{r['b_mod_coef']:>+10.5f} {r['b_mod_se']:>9.5f} {r['b_mod_t']:>+7.2f} {r['b_mod_p']:>7.4f} | "
            f"{r['b_pre_coef']:>+10.5f} {r['b_pre_se']:>9.5f} {r['b_pre_t']:>+7.2f} {r['b_pre_p']:>7.4f}"
        )
    L()
    DIV()
    L("  END OF REPORT")
    DIV()

    report_text = '\n'.join(lines)
    os.makedirs(os.path.dirname(OUT_REPORT_PATH), exist_ok=True)
    with open(OUT_REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"Saved {OUT_REPORT_PATH}")
    print()
    print(report_text.encode('ascii', errors='replace').decode('ascii'))


if __name__ == '__main__':
    main()
