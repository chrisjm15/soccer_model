import pandas as pd
import numpy as np


def compute_metrics(predictions_df: pd.DataFrame) -> dict:
    """
    Takes the backtest output DataFrame and computes performance metrics.

    Required columns: prob_btts_yes, actual_btts, edge, should_bet, btts_odds_yes
    Returns a dict of metrics.
    """
    df = predictions_df.dropna(subset=['actual_btts', 'prob_btts_yes']).copy()
    flagged = df[df['should_bet'] == True].copy()

    assumed_odds = df['btts_odds_yes'].iloc[0] if len(df) > 0 else 1.90
    implied_prob = 1.0 / assumed_odds

    # --- Brier Score ---
    brier_all = float(np.mean((df['prob_btts_yes'] - df['actual_btts']) ** 2))
    brier_flagged = (
        float(np.mean((flagged['prob_btts_yes'] - flagged['actual_btts']) ** 2))
        if len(flagged) > 0 else None
    )
    brier_baseline = float(np.mean((implied_prob - df['actual_btts']) ** 2))

    # --- Hit rate ---
    hit_rate = float(flagged['actual_btts'].mean()) if len(flagged) > 0 else None

    # --- ROI simulation (flat 1 unit staking) ---
    if len(flagged) > 0:
        profits = flagged['actual_btts'].apply(
            lambda x: (assumed_odds - 1.0) if x == 1 else -1.0
        )
        total_profit = float(profits.sum())
        total_staked = len(flagged)
        roi_pct = (total_profit / total_staked) * 100.0
    else:
        total_profit = 0.0
        total_staked = 0
        roi_pct = None

    # --- Calibration bins ---
    bins = np.linspace(0, 1, 11)
    calibration = []
    for i in range(len(bins) - 1):
        lo, hi = bins[i], bins[i + 1]
        mask = (df['prob_btts_yes'] >= lo) & (df['prob_btts_yes'] < hi)
        subset = df[mask]
        if len(subset) == 0:
            calibration.append({
                'bin_low': lo, 'bin_high': hi,
                'n': 0, 'mean_pred': None, 'actual_rate': None
            })
        else:
            calibration.append({
                'bin_low': lo, 'bin_high': hi,
                'n': len(subset),
                'mean_pred': float(subset['prob_btts_yes'].mean()),
                'actual_rate': float(subset['actual_btts'].mean())
            })

    # --- By league ---
    by_league = {}
    for league, grp in df.groupby('league'):
        fl = grp[grp['should_bet'] == True]
        n_bets = len(fl)
        if n_bets > 0:
            fl_profits = fl['actual_btts'].apply(
                lambda x: (assumed_odds - 1.0) if x == 1 else -1.0
            )
            league_roi = float((fl_profits.sum() / n_bets) * 100.0)
            league_hit = float(fl['actual_btts'].mean())
        else:
            league_roi = None
            league_hit = None
        by_league[league] = {
            'n_matches': len(grp),
            'n_bets': n_bets,
            'hit_rate': league_hit,
            'roi_pct': league_roi,
            'brier_score': float(np.mean((grp['prob_btts_yes'] - grp['actual_btts']) ** 2))
        }

    # --- By season ---
    by_season = {}
    for season, grp in df.groupby('season'):
        fl = grp[grp['should_bet'] == True]
        n_bets = len(fl)
        if n_bets > 0:
            fl_profits = fl['actual_btts'].apply(
                lambda x: (assumed_odds - 1.0) if x == 1 else -1.0
            )
            season_roi = float((fl_profits.sum() / n_bets) * 100.0)
            season_hit = float(fl['actual_btts'].mean())
        else:
            season_roi = None
            season_hit = None
        by_season[season] = {
            'n_matches': len(grp),
            'n_bets': n_bets,
            'hit_rate': season_hit,
            'roi_pct': season_roi,
            'brier_score': float(np.mean((grp['prob_btts_yes'] - grp['actual_btts']) ** 2))
        }

    return {
        'n_matches': len(df),
        'n_bets': total_staked,
        'brier_all': brier_all,
        'brier_flagged': brier_flagged,
        'brier_baseline': brier_baseline,
        'hit_rate': hit_rate,
        'total_profit': total_profit,
        'total_staked': total_staked,
        'roi_pct': roi_pct,
        'assumed_odds': assumed_odds,
        'implied_prob': implied_prob,
        'calibration': calibration,
        'by_league': by_league,
        'by_season': by_season,
    }


def print_metrics_report(metrics: dict) -> str:
    """Print a readable summary of the metrics to stdout. Also returns the report as a string."""
    lines = []

    def p(line=''):
        lines.append(line)
        print(line)

    assumed_odds = metrics['assumed_odds']
    implied_pct = metrics['implied_prob'] * 100.0
    n_matches = metrics['n_matches']
    n_bets = metrics['n_bets']
    bet_pct = (n_bets / n_matches * 100.0) if n_matches > 0 else 0.0

    p("=" * 50)
    p("  BTTS MODEL BACKTEST RESULTS")
    p("=" * 50)
    seasons = sorted(metrics['by_season'].keys())
    if seasons:
        p(f"Test period: {seasons[0]} to {seasons[-1]}")
    p(f"Total matches: {n_matches} | Flagged as bets: {n_bets} ({bet_pct:.1f}%)")

    p()
    p("OVERALL CALIBRATION (BRIER SCORE)")
    p(f"  All matches    : {metrics['brier_all']:.4f}  (lower is better)")
    p(f"  Naive baseline : {metrics['brier_baseline']:.4f}  (always predict {metrics['implied_prob']:.4f})")
    delta = metrics['brier_all'] - metrics['brier_baseline']
    direction = "better" if delta < 0 else "worse"
    p(f"  vs baseline    : {delta:+.4f}  ({direction} than naive)")
    if metrics['brier_flagged'] is not None:
        p(f"  Flagged bets   : {metrics['brier_flagged']:.4f}")

    p()
    p(f"BETTING PERFORMANCE (assumed odds {assumed_odds:.2f})")
    if n_bets > 0:
        hit_pct = metrics['hit_rate'] * 100.0
        p(f"  Total bets     : {n_bets}")
        p(f"  Hit rate       : {hit_pct:.1f}%  (break-even: {implied_pct:.1f}%)")
        p(f"  Total P&L      : {metrics['total_profit']:+.2f} units")
        p(f"  ROI            : {metrics['roi_pct']:+.1f}%")
        if metrics['roi_pct'] > 0:
            p(f"  Verdict        : Positive signal — model edges above implied probability on flagged bets")
        else:
            p(f"  Verdict        : Negative ROI — model is not finding value at this threshold")
    else:
        p("  No bets flagged at current edge threshold.")

    p()
    p("CALIBRATION (model predicted prob vs actual BTTS rate)")
    for b in metrics['calibration']:
        if b['n'] == 0:
            continue
        lo_pct = b['bin_low'] * 100
        hi_pct = b['bin_high'] * 100
        pred_pct = b['mean_pred'] * 100
        act_pct = b['actual_rate'] * 100
        p(f"  {lo_pct:3.0f}–{hi_pct:3.0f}%:  predicted={pred_pct:.1f}%,  actual={act_pct:.1f}%  (n={b['n']})")

    p()
    p("BY LEAGUE")
    for league, lg in sorted(metrics['by_league'].items()):
        if lg['n_bets'] > 0:
            roi_str = f"{lg['roi_pct']:+.1f}%"
            hit_str = f"{lg['hit_rate'] * 100:.1f}%"
        else:
            roi_str = "  n/a"
            hit_str = "  n/a"
        p(f"  {league:<12}: {lg['n_matches']} matches, {lg['n_bets']} bets, hit={hit_str}, ROI={roi_str}")

    p()
    p("BY SEASON")
    for season, sg in sorted(metrics['by_season'].items()):
        if sg['n_bets'] > 0:
            roi_str = f"{sg['roi_pct']:+.1f}%"
            hit_str = f"{sg['hit_rate'] * 100:.1f}%"
        else:
            roi_str = "  n/a"
            hit_str = "  n/a"
        p(f"  {season}: {sg['n_matches']} matches, {sg['n_bets']} bets, hit={hit_str}, ROI={roi_str}")

    p("=" * 50)

    return '\n'.join(lines)
