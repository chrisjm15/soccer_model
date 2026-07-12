"""
scripts/calibration_backtest.py

Calibration backtest: run the AH model over all historical matches without
an edge threshold, and produce tables showing where the model is over- or
under-confident relative to actual AH coverage rates.

Hard rules:
  - Does NOT modify model/ or backtest/multi_market_engine.py
  - Reuses compute_match_probs, compute_ah_probs, compute_actual_ah_result read-only
  - All model probabilities use pre-match ratings from data/processed/ratings.csv

Scoring convention (documented here — both sides of every calibration
comparison must use the same convention):

  actual_score: Win=1.0, HalfWin=0.75, Push=0.5, HalfLoss=0.25, Loss=0.0
    "Win" means the selected bet side won.

  model_prob: E[actual_score] under the Poisson goal grid.
    Formula: p_bet_side + 0.5 * p_push
    - Half lines (p_push=0): reduces to p_bet_side (plain win probability).
    - Whole lines: adds p_push * 0.5 to reflect the 0.5 partial credit for a push.
    - Quarter lines: compute_ah_probs() internally averages two adjacent sub-lines,
      producing a p_push that encodes the push-at-half-stake effect. The formula
      p_bet_side + 0.5*p_push is the correct E[actual_score] for all line types
      (verified algebraically: for -1.75 = avg(-1.5,-2.0) with margin=2 half-win,
      the formula gives P(margin>=3) + 0.75*P(margin=2), matching the settlement).

  The prompt states "for quarter lines, the average of the two half-line win
  probabilities gives this." This is correct when neither sub-line can push
  (both are half-lines). When one sub-line is a whole-line (can push), the
  two-term formula above is needed. Both cases are handled by the single
  p_bet_side + 0.5*p_push formula.

  market_prob_novig: (1/odds_side) / (1/odds_ah_home + 1/odds_ah_away)
    This is the implied probability for the bet side, vig removed.

  edge: model_prob_win_only - market_prob_novig
    Where model_prob_win_only = p_bet_side (not adjusted for push).
    Consistent with how predict_asian_handicap() in model/markets.py computes edge,
    so bet_side selection matches the engine.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import yaml
from pathlib import Path

from model.poisson import compute_match_probs
from model.markets import compute_ah_probs
from backtest.multi_market_engine import compute_actual_ah_result

# ---------------------------------------------------------------------------
# Lookup tables for actual_score from bet perspective
# compute_actual_ah_result returns a string from HOME perspective.
# ---------------------------------------------------------------------------
_HOME_BET_SCORE = {
    'home_win':  1.0,
    'half_win':  0.75,
    'push':      0.5,
    'half_loss': 0.25,
    'away_win':  0.0,
}
_AWAY_BET_SCORE = {
    'home_win':  0.0,   # home won → away bet lost
    'half_win':  0.25,  # home half-won → away bet half-lost
    'push':      0.5,
    'half_loss': 0.75,  # home half-lost → away bet half-won
    'away_win':  1.0,   # away won → away bet won
}

_PNL_MULTIPLIER = {1.0: 1.0, 0.75: 0.5, 0.5: 0.0, 0.25: -0.5, 0.0: -1.0}


def _pnl_flat10(actual_score, odds):
    """P&L on a flat £10 stake."""
    mult = _PNL_MULTIPLIER[actual_score]
    if mult > 0:
        return round((odds - 1) * 10 * mult, 2)
    else:
        return round(10 * mult, 2)


def _pinnacle_novig(ph, pd_, pa):
    """No-vig 1X2 Pinnacle probabilities (returns None triple if any are NaN/missing)."""
    try:
        if any(pd.isna(x) for x in [ph, pd_, pa]):
            return None, None, None
        ph, pd_, pa = float(ph), float(pd_), float(pa)
        overround = 1.0/ph + 1.0/pd_ + 1.0/pa
        return (1.0/ph)/overround, (1.0/pd_)/overround, (1.0/pa)/overround
    except (TypeError, ValueError, ZeroDivisionError):
        return None, None, None


def run_calibration_backtest(
    ratings_path='data/processed/ratings.csv',
    merged_path='data/processed/all_merged.csv',
    leagues_config_path='config/leagues.yaml',
    output_dir='output/backtest_results',
):
    print("=" * 70)
    print("CALIBRATION BACKTEST")
    print("=" * 70)

    # --- Load data ---
    merged = pd.read_csv(merged_path)
    ratings = pd.read_csv(ratings_path)
    with open(leagues_config_path, 'r') as f:
        leagues_config = yaml.safe_load(f)

    leagues_ha = {
        league: data.get('home_advantage_xg', 0.0)
        for league, data in leagues_config['leagues'].items()
    }

    merged['date'] = pd.to_datetime(merged['date'])
    ratings['date'] = pd.to_datetime(ratings['date'])

    total_merged = len(merged)
    print(f"\nall_merged.csv rows: {total_merged}")

    # --- Merge ratings onto match data (inner join — only rows with pre-match ratings) ---
    df = merged.merge(
        ratings,
        on=['date', 'league', 'season', 'home_team', 'away_team'],
        how='inner',
    )
    after_merge = len(df)
    print(f"Rows after inner join with ratings: {after_merge}  (dropped {total_merged - after_merge} with no ratings)")

    # --- Drop rows missing required AH data or scoreline ---
    required = ['ah_line', 'odds_ah_home', 'odds_ah_away', 'home_goals', 'away_goals']
    before_drop = len(df)
    df = df.dropna(subset=required).copy()
    dropped_odds = before_drop - len(df)

    print(f"Dropped (missing AH odds or goals): {dropped_odds}")
    print(f"Rows to process: {len(df)}")

    # Sanity check 1: row count
    if not (8000 <= len(df) <= 13000):
        print(f"SANITY FAIL: unexpected row count {len(df)} (expected 8,000–13,000) — stopping.")
        sys.exit(1)

    # --- Main loop ---
    records = []
    for _, row in df.iterrows():
        ha = leagues_ha.get(row['league'], 0.0)

        probs = compute_match_probs(
            home_attack=float(row['home_attack']),
            home_defence=float(row['home_defence']),
            away_attack=float(row['away_attack']),
            away_defence=float(row['away_defence']),
            home_advantage=ha,
        )

        ah_line      = float(row['ah_line'])
        odds_ah_home = float(row['odds_ah_home'])
        odds_ah_away = float(row['odds_ah_away'])

        ah_probs = compute_ah_probs(probs['goal_grid'], ah_line)
        p_home = ah_probs['p_home']
        p_push = ah_probs['p_push']
        p_away = ah_probs['p_away']

        # No-vig implied probabilities for edge calculation
        overround   = 1.0 / odds_ah_home + 1.0 / odds_ah_away
        impl_home   = (1.0 / odds_ah_home) / overround
        impl_away   = (1.0 / odds_ah_away) / overround

        # Edge uses p_bet_side (win-only), same as predict_asian_handicap() in the engine
        edge_home = p_home - impl_home
        edge_away = p_away - impl_away

        # Bet side: best edge (same logic as engine)
        if edge_home >= edge_away:
            bet_side         = 'home'
            market_odds      = odds_ah_home
            market_prob_novig = impl_home
            edge             = edge_home
            # E[actual_score] for home bet
            model_prob       = p_home + 0.5 * p_push
        else:
            bet_side         = 'away'
            market_odds      = odds_ah_away
            market_prob_novig = impl_away
            edge             = edge_away
            # E[actual_score] for away bet
            model_prob       = p_away + 0.5 * p_push

        # Settle using engine's function (home perspective result string)
        margin    = int(row['home_goals']) - int(row['away_goals'])
        ah_result = compute_actual_ah_result(margin, ah_line)

        # Convert to bet-perspective score
        if bet_side == 'home':
            actual_score = _HOME_BET_SCORE[ah_result]
        else:
            actual_score = _AWAY_BET_SCORE[ah_result]

        pnl = _pnl_flat10(actual_score, market_odds)

        # Pinnacle 1X2 no-vig (reference only — not AH, just for context/future factor work)
        pin_h, pin_d, pin_a = _pinnacle_novig(
            row.get('pinnacle_home'),
            row.get('pinnacle_draw'),
            row.get('pinnacle_away'),
        )

        records.append({
            'date':              row['date'].strftime('%Y-%m-%d'),
            'league':            row['league'],
            'season':            row['season'],
            'home_team':         row['home_team'],
            'away_team':         row['away_team'],
            'home_goals':        int(row['home_goals']),
            'away_goals':        int(row['away_goals']),
            'home_xg':           row['home_xg'],
            'away_xg':           row['away_xg'],
            'ah_line':           ah_line,
            'bet_side':          bet_side,
            'model_prob':        round(model_prob, 6),
            'market_odds':       round(market_odds, 4),
            'market_prob_novig': round(market_prob_novig, 6),
            'edge':              round(edge, 6),
            'pinnacle_home_novig': round(pin_h, 6) if pin_h is not None else '',
            'pinnacle_draw_novig': round(pin_d, 6) if pin_d is not None else '',
            'pinnacle_away_novig': round(pin_a, 6) if pin_a is not None else '',
            'ah_result':         ah_result,   # home-perspective string from compute_actual_ah_result
            'actual_score':      actual_score, # bet-perspective score: Win=1.0 ... Loss=0.0
            'pnl_flat10':        pnl,
        })

    results = pd.DataFrame(records)

    # ---- SANITY CHECKS ----
    print("\n" + "=" * 70)
    print("SANITY CHECKS")
    print("=" * 70)

    # Check actual_score values
    valid_scores = {0.0, 0.25, 0.5, 0.75, 1.0}
    bad = results[~results['actual_score'].isin(valid_scores)]
    if len(bad) > 0:
        print(f"SANITY FAIL: {len(bad)} rows with unexpected actual_score values")
        print(bad[['date','home_team','away_team','ah_result','actual_score']].head())
        sys.exit(1)
    print(f"  actual_score values: {sorted(results['actual_score'].unique())} — all valid")

    # Check probability ranges
    if results['model_prob'].min() <= 0 or results['model_prob'].max() >= 1:
        print(f"SANITY FAIL: model_prob out of (0,1): min={results['model_prob'].min():.6f}, max={results['model_prob'].max():.6f}")
        sys.exit(1)
    if results['market_prob_novig'].min() <= 0 or results['market_prob_novig'].max() >= 1:
        print(f"SANITY FAIL: market_prob_novig out of (0,1)")
        sys.exit(1)
    print(f"  model_prob range: ({results['model_prob'].min():.4f}, {results['model_prob'].max():.4f}) — valid")
    print(f"  market_prob_novig range: ({results['market_prob_novig'].min():.4f}, {results['market_prob_novig'].max():.4f}) — valid")

    # Row count summary
    print(f"\n  Total rows in calibration dataset: {len(results)}")
    print(f"  Dropped (no ratings or AH data): {total_merged - len(results)}")

    # Cross-check: EPL 2023-24 to 2025-26, edge >= 5%
    # Should be in the same ballpark as multi_market_report.txt EPL AH ROI (+6.5%, 504 bets)
    xcheck = results[
        (results['league'] == 'EPL') &
        (results['season'].isin(['2023-24', '2024-25', '2025-26'])) &
        (results['edge'] >= 0.05)
    ]
    if len(xcheck) > 0:
        xcheck_roi = xcheck['pnl_flat10'].sum() / (len(xcheck) * 10) * 100
        print(f"\n  Cross-check (EPL 2023-26, edge>=5%): {len(xcheck)} bets, ROI={xcheck_roi:+.1f}%")
        print(f"  Reference (multi_market_report.txt): 504 bets, ROI=+6.5%")
        diff = abs(xcheck_roi - 6.5)
        if diff > 25:
            print(f"  SANITY WARN: ROI differs by {diff:.1f}pp — check for inconsistency with engine.")
            print(f"  NOTE: slight differences are expected (this script only requires AH odds,")
            print(f"  while the engine also requires 1X2 and O/U odds, so match counts may differ).")
        else:
            print(f"  Cross-check PASSED (within 25pp of engine reference)")
    else:
        print("  SANITY WARN: no EPL 2023-26 edge>=5% bets found — check data.")

    # Lookahead note (ratings are pre-match by construction)
    print(f"\n  Lookahead safety: ratings.csv provides pre-match EMA values.")
    print(f"  No date filtering applied here — the ratings engine handles this.")
    print(f"  Ratings date range: {ratings['date'].min().strftime('%Y-%m-%d')} to {ratings['date'].max().strftime('%Y-%m-%d')}")

    # ---- SAVE CSV ----
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    csv_path = output_path / 'calibration_matches.csv'
    results.to_csv(csv_path, index=False)
    print(f"\nPer-match CSV saved: {csv_path}  ({len(results)} rows)")

    # ---- GENERATE REPORT ----
    _write_report(results, output_path / 'calibration_report.txt')

    return results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _table_stats(df):
    """n, mean_model_prob, mean_actual_score, gap_pp (model−actual), flat_roi%"""
    n = len(df)
    if n == 0:
        return 0, float('nan'), float('nan'), float('nan'), float('nan')
    mmp  = df['model_prob'].mean()
    mas  = df['actual_score'].mean()
    gap  = (mmp - mas) * 100   # positive = model overconfident
    roi  = df['pnl_flat10'].sum() / (n * 10) * 100
    return n, mmp, mas, gap, roi


def _write_report(results, report_path):
    results = results.copy()

    # Derived columns for bucketing
    results['disagreement'] = results['model_prob'] - results['market_prob_novig']
    results['abs_line']     = results['ah_line'].abs()

    prob_bins = [
        ('50-55%', 0.50, 0.55),
        ('55-60%', 0.55, 0.60),
        ('60-65%', 0.60, 0.65),
        ('65-70%', 0.65, 0.70),
        ('70-75%', 0.70, 0.75),
        ('75-80%', 0.75, 0.80),
        ('80%+',   0.80, 1.01),
    ]
    line_bins = [
        ('|line|<=0.5',  0.00, 0.5001),
        ('0.75-1.25',    0.75, 1.2501),
        ('1.5-2.0',      1.50, 2.0001),
        ('>=2.25',       2.25, 99.0),
    ]
    dis_order  = ['<2%', '2-5%', '5-10%', '>10%']

    def prob_zone(mp):
        for label, lo, hi in prob_bins:
            if lo <= mp < hi:
                return label
        return 'other'

    def line_zone(al):
        for label, lo, hi in line_bins:
            if lo <= al < hi:
                return label
        return 'other'

    def dis_zone(d):
        d = abs(d)  # use absolute disagreement — we always bet best edge side
        if d < 0.02: return '<2%'
        if d < 0.05: return '2-5%'
        if d < 0.10: return '5-10%'
        return '>10%'

    results['prob_zone']   = results['model_prob'].apply(prob_zone)
    results['line_zone']   = results['abs_line'].apply(line_zone)
    results['dis_zone']    = results['disagreement'].apply(dis_zone)

    lines_out = []
    W = 90

    def banner(title):
        lines_out.append('=' * W)
        lines_out.append(f'  {title}')
        lines_out.append('=' * W)

    def section(title):
        lines_out.append(f'\n{"-" * W}')
        lines_out.append(f'  {title}')
        lines_out.append('-' * W)

    def fmt_row(cells, widths):
        return '  ' + '  '.join(str(c).ljust(w) for c, w in zip(cells, widths))

    def table1_2(subset):
        """Tables 1 and 2: prob zones and line sizes."""
        hdr = ['Zone', 'N', 'ModelProb%', 'Actual%', 'Gap(pp)', 'FlatROI%']
        wds = [12, 6, 11, 9, 9, 9]
        lines_out.append(fmt_row(hdr, wds))
        lines_out.append('  ' + '-' * 70)

        section('TABLE 1 — BY MODEL PROBABILITY ZONE')
        lines_out.append('  (all selected bets, no edge threshold — full probability spectrum)')
        lines_out.append(fmt_row(hdr, wds))
        lines_out.append('  ' + '-' * 70)
        for label, lo, hi in prob_bins:
            sub = subset[(subset['model_prob'] >= lo) & (subset['model_prob'] < hi)]
            n, mmp, mas, gap, roi = _table_stats(sub)
            lines_out.append(fmt_row([
                label, n,
                f'{mmp*100:.1f}' if n else '-',
                f'{mas*100:.1f}' if n else '-',
                f'{gap:+.1f}'    if n else '-',
                f'{roi:+.1f}%'   if n else '-',
            ], wds))

        section('TABLE 2 — BY ABSOLUTE LINE SIZE')
        lines_out.append(fmt_row(hdr, wds))
        lines_out.append('  ' + '-' * 70)
        for label, lo, hi in line_bins:
            sub = subset[(subset['abs_line'] >= lo) & (subset['abs_line'] < hi)]
            n, mmp, mas, gap, roi = _table_stats(sub)
            lines_out.append(fmt_row([
                label, n,
                f'{mmp*100:.1f}' if n else '-',
                f'{mas*100:.1f}' if n else '-',
                f'{gap:+.1f}'    if n else '-',
                f'{roi:+.1f}%'   if n else '-',
            ], wds))

    def table3(subset):
        """Zone × line-size cross-tab (n and gap only)."""
        section('TABLE 3 — ZONE × LINE-SIZE CROSS-TAB  (n | gap in pp, model − actual)')
        lines_out.append('  Positive gap = model overconfident. This is the money table: shows where the model breaks.')
        line_labels = [l for l, _, _ in line_bins]
        col_w = 20
        hdr = ['ProbZone'.ljust(12)] + [l.ljust(col_w) for l in line_labels]
        lines_out.append('  ' + '  '.join(hdr))
        lines_out.append('  ' + '-' * (12 + (col_w + 2) * len(line_bins)))
        for plabel, plo, phi in prob_bins:
            psub = subset[(subset['model_prob'] >= plo) & (subset['model_prob'] < phi)]
            cells = [plabel.ljust(12)]
            for llabel, llo, lhi in line_bins:
                s = psub[(psub['abs_line'] >= llo) & (psub['abs_line'] < lhi)]
                n, _, _, gap, _ = _table_stats(s)
                cell = f'n={n} | {gap:+.1f}pp' if n else 'n=0'
                cells.append(cell.ljust(col_w))
            lines_out.append('  ' + '  '.join(cells))

    def table4(subset):
        """Disagreement test — the key edge-validity test."""
        section('TABLE 4 — DISAGREEMENT TEST  (|model_prob − market_prob_novig|)')
        lines_out.append('  KEY QUESTION: when model disagrees with market, does the actual outcome')
        lines_out.append('  track the MODEL (edge is real) or the MARKET (model is miscalibrated)?')
        lines_out.append('  If edge is real => actual_score should rise with disagreement, ROI positive.')
        lines_out.append('')
        hdr = ['Disagree', 'N', 'ModelProb%', 'MktProb%', 'Actual%', 'Gap(pp)', 'FlatROI%']
        wds = [10, 6, 11, 10, 9, 9, 9]
        lines_out.append(fmt_row(hdr, wds))
        lines_out.append('  ' + '-' * 75)
        for bucket in dis_order:
            sub = subset[subset['dis_zone'] == bucket]
            n, mmp, mas, gap, roi = _table_stats(sub)
            mkt = sub['market_prob_novig'].mean() if n > 0 else float('nan')
            lines_out.append(fmt_row([
                bucket, n,
                f'{mmp*100:.1f}' if n else '-',
                f'{mkt*100:.1f}' if n else '-',
                f'{mas*100:.1f}' if n else '-',
                f'{gap:+.1f}'    if n else '-',
                f'{roi:+.1f}%'   if n else '-',
            ], wds))

    def table5(subset):
        """By season."""
        section('TABLE 5 — BY SEASON  (calibration drift over time)')
        hdr = ['Season', 'N', 'ModelProb%', 'Actual%', 'Gap(pp)', 'FlatROI%']
        wds = [10, 6, 11, 9, 9, 9]
        lines_out.append(fmt_row(hdr, wds))
        lines_out.append('  ' + '-' * 65)
        for season in sorted(subset['season'].unique()):
            sub = subset[subset['season'] == season]
            n, mmp, mas, gap, roi = _table_stats(sub)
            lines_out.append(fmt_row([
                season, n,
                f'{mmp*100:.1f}', f'{mas*100:.1f}',
                f'{gap:+.1f}', f'{roi:+.1f}%',
            ], wds))

    for label, subset in [('ALL LEAGUES', results), ('EPL ONLY', results[results['league'] == 'EPL'])]:
        banner(f'CALIBRATION REPORT — {label}')
        lines_out.append(f'  Matches: {len(subset)} | Date generated: 2026-07-12')
        lines_out.append(f'  Seasons: 2020-21 through 2025-26 | No edge threshold applied')
        lines_out.append(f'  model_prob = E[actual_score] = p_bet_side + 0.5*p_push (see scoring convention at top of script)')
        lines_out.append(f'  actual_score: Win=1.0, HalfWin=0.75, Push=0.5, HalfLoss=0.25, Loss=0.0 (bet perspective)')
        lines_out.append('')
        table1_2(subset)
        table3(subset)
        table4(subset)
        table5(subset)
        lines_out.append('\n')

    report_text = '\n'.join(lines_out)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"Calibration report saved: {report_path}")

    # Print report to console (encode to ASCII-safe output for Windows terminals)
    print("\n" + "=" * 70)
    print("CALIBRATION REPORT OUTPUT")
    print("=" * 70)
    safe_text = report_text.encode('ascii', errors='replace').decode('ascii')
    print(safe_text)


if __name__ == '__main__':
    run_calibration_backtest()
