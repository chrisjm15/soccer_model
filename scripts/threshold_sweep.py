import os
import pandas as pd
import yaml
from math import floor, ceil
from model.poisson import compute_match_probs
from model.markets import predict_1x2, predict_over_under, predict_asian_handicap, compute_ah_probs
# Helper function to compute actual AH result
def compute_actual_ah_result(margin, ah_line):
    is_quarter = (ah_line * 2) % 1 != 0
    if not is_quarter:
        if margin > -ah_line: return 'home_win'
        elif margin == -ah_line: return 'push'
        else: return 'away_win'
    else:
        l1 = floor(ah_line * 2) / 2
        l2 = ceil(ah_line * 2) / 2
        def get_res(line):
            if margin > -line: return 'home_win'
            if margin == -line: return 'push'
            return 'away_win'
        res1, res2 = get_res(l1), get_res(l2)
        if res1 == res2: return res1
        results_set = {res1, res2}
        if 'push' in results_set:
            if 'home_win' in results_set: return 'half_win'
            if 'away_win' in results_set: return 'half_loss'
            return 'push'
        if 'home_win' in results_set and 'away_win' in results_set: return 'push'
        return res1

# AH P&L computation
def ah_pnl(actual_ah, best_side, odds):
    result = actual_ah
    if best_side == 'away':
        flip = {'home_win': 'away_win', 'away_win': 'home_win', 'push': 'push',
                'half_win': 'half_loss', 'half_loss': 'half_win'}
        result = flip[actual_ah]
    if result == 'home_win': return odds - 1
    if result == 'push': return 0.0
    if result == 'away_win': return -1.0
    if result == 'half_win': return (odds - 1) * 0.5
    if result == 'half_loss': return -0.5
    return 0.0

def main():
    # Load config
    with open('config/leagues.yaml', 'r') as f:
        config = yaml.safe_load(f)
    leagues_ha = {league: data.get('home_advantage_xg', 0.0) for league, data in
config['leagues'].items()}

    # Load data
    ratings = pd.read_csv('data/processed/ratings.csv')
    merged = pd.read_csv('data/processed/all_merged.csv')

    # Filter test seasons
    test_seasons = ['2023-24', '2024-25', '2025-26']
    merged = merged[merged['season'].isin(test_seasons)]

    # Inner join on key fields
    df = pd.merge(ratings, merged, on=['date', 'league', 'season', 'home_team',
'away_team'], how='inner')

    # Drop rows with missing odds
    df = df.dropna(subset=[
        'odds_home', 'odds_draw', 'odds_away',
        'odds_over25', 'odds_under25',
        'ah_line', 'odds_ah_home', 'odds_ah_away'
    ])

    records = []

    for _, row in df.iterrows():
        league = row['league']
        season = row['season']
        home_team = row['home_team']
        away_team = row['away_team']
        home_attack = row['home_attack']
        home_defence = row['home_defence']
        away_attack = row['away_attack']
        away_defence = row['away_defence']
        odds_home = row['odds_home']
        odds_draw = row['odds_draw']
        odds_away = row['odds_away']
        odds_over25 = row['odds_over25']
        odds_under25 = row['odds_under25']
        ah_line = row['ah_line']
        odds_ah_home = row['odds_ah_home']
        odds_ah_away = row['odds_ah_away']
        home_goals = row['home_goals']
        away_goals = row['away_goals']

        # Compute match probabilities
        probs = compute_match_probs(
            home_attack=home_attack,
            home_defence=home_defence,
            away_attack=away_attack,
            away_defence=away_defence,
            home_advantage=leagues_ha[league]
        )

        # Compute 1x2 edges
        pred_1x2 = predict_1x2(
            probs=probs,
            odds_home=odds_home,
            odds_draw=odds_draw,
            odds_away=odds_away,
            edge_threshold=0.0
        )

        # Compute Over/Under edges
        pred_ou = predict_over_under(
            probs=probs,
            odds_over=odds_over25,
            odds_under=odds_under25,
            edge_threshold=0.0
        )

        # Compute AH edges
        pred_ah = predict_asian_handicap(
            probs=probs,
            ah_line=ah_line,
            odds_ah_home=odds_ah_home,
            odds_ah_away=odds_ah_away,
            edge_threshold=0.0
        )

        # Compute actual outcomes
        goal_diff = home_goals - away_goals
        actual_ou = 1 if (home_goals + away_goals) > 2.5 else 0
        actual_ah = compute_actual_ah_result(goal_diff, ah_line)

        # Store record
        records.append({
            'league': league,
            'season': season,
            'home_team': home_team,
            'away_team': away_team,
            'edge_ou': pred_ou['edge_over'],
            'odds_ou': odds_over25,
            'pnl_ou_win': odds_over25 - 1,
            'actual_ou': actual_ou,
            'edge_ah': pred_ah['best_edge'],
            'odds_ah': pred_ah['best_odds'],
            'best_side_ah': pred_ah['best_side'],
            'ah_line': ah_line,
            'actual_ah': actual_ah
        })

    df_records = pd.DataFrame(records)

    # Thresholds to test
    thresholds = [0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.12, 0.15]

    # Initialize results dict
    results = {}

    # Process for all leagues and EPL only
    for league_filter in ['all', 'EPL']:
        if league_filter == 'EPL':
            df_filtered = df_records[df_records['league'] == 'EPL']
        else:
            df_filtered = df_records.copy()

        # Over/Under 2.5 results
        ou_results = []
        for th in thresholds:
            bets = df_filtered[df_filtered['edge_ou'] >= th]
            total_bets = len(bets)
            if total_bets == 0:
                ou_results.append({
                    'threshold': th,
                    'bets': 0,
                    'bets_pct': 0.0,
                    'hit_pct': 0.0,
                    'roi': 0.0
                })
                continue

            wins = sum(1 for _, r in bets.iterrows() if r['actual_ou'] == 1)
            total_pnl = sum(
                r['pnl_ou_win'] if r['actual_ou'] == 1 else -1.0
                for _, r in bets.iterrows()
            )
            hit_rate = wins / total_bets * 100
            roi = (total_pnl / total_bets) * 100 if total_bets > 0 else 0.0

            ou_results.append({
                'threshold': th,
                'bets': total_bets,
                'bets_pct': total_bets / len(df_filtered) * 100,
                'hit_pct': hit_rate,
                'roi': roi
            })

        # Asian Handicap results
        ah_results = []
        for th in thresholds:
            bets = df_filtered[df_filtered['edge_ah'] >= th]
            total_bets = len(bets)
            if total_bets == 0:
                ah_results.append({
                    'threshold': th,
                    'bets': 0,
                    'bets_pct': 0.0,
                    'hit_pct': 0.0,
                    'roi': 0.0
                })
                continue

            total_pnl = 0
            wins = 0
            for _, r in bets.iterrows():
                pnl = ah_pnl(r['actual_ah'], r['best_side_ah'], r['odds_ah'])
                total_pnl += pnl
                if pnl > 0: wins += 1

            hit_rate = wins / total_bets * 100 if total_bets > 0 else 0.0
            roi = (total_pnl / total_bets) * 100 if total_bets > 0 else 0.0

            ah_results.append({
                'threshold': th,
                'bets': total_bets,
                'bets_pct': total_bets / len(df_filtered) * 100,
                'hit_pct': hit_rate,
                'roi': roi
            })

        results[f'ou_{league_filter}'] = ou_results
        results[f'ah_{league_filter}'] = ah_results

    # Season-by-season for EPL at 8% threshold
    epl_ah_8 = []
    for season in test_seasons:
        df_season = df_records[(df_records['league'] == 'EPL') & (df_records['season'] == season)]
        bets = df_season[df_season['edge_ah'] >= 0.08]
        total_bets = len(bets)
        if total_bets == 0:
            epl_ah_8.append({
                'season': season,
                'bets': 0,
                'hit_pct': 0.0,
                'roi': 0.0
            })
            continue

        total_pnl = 0
        wins = 0
        for _, r in bets.iterrows():
            pnl = ah_pnl(r['actual_ah'], r['best_side_ah'], r['odds_ah'])
            total_pnl += pnl
            if pnl > 0: wins += 1

        hit_rate = wins / total_bets * 100 if total_bets > 0 else 0.0
        roi = (total_pnl / total_bets) * 100 if total_bets > 0 else 0.0

        epl_ah_8.append({
            'season': season,
            'bets': total_bets,
            'hit_pct': hit_rate,
            'roi': roi
        })

    results['epl_ah_8'] = epl_ah_8

    # Format output
    output_lines = []
    output_lines.append("==============================================================")
    output_lines.append("  THRESHOLD SWEEP — O/U 2.5 (OVER) — ALL LEAGUES")
    output_lines.append("==============================================================")
    output_lines.append("Threshold  Bets    Bets%   Hit%    ROI")
    for res in results['ou_all']:
        output_lines.append(f"  {res['threshold']*100:2.0f}%     {res['bets']:4d}   {res['bets_pct']:5.1f}%   {res['hit_pct']:5.1f}%   {res['roi']:6.2f}%")

    output_lines.append("")
    output_lines.append("==============================================================")
    output_lines.append("  THRESHOLD SWEEP — O/U 2.5 (OVER) — EPL ONLY")
    output_lines.append("==============================================================")
    output_lines.append("Threshold  Bets    Bets%   Hit%    ROI")
    for res in results['ou_EPL']:
        output_lines.append(f"  {res['threshold']*100:2.0f}%     {res['bets']:4d}   {res['bets_pct']:5.1f}%   {res['hit_pct']:5.1f}%   {res['roi']:6.2f}%")

    output_lines.append("")
    output_lines.append("==============================================================")
    output_lines.append("  THRESHOLD SWEEP — ASIAN HANDICAP — ALL LEAGUES")
    output_lines.append("==============================================================")
    output_lines.append("Threshold  Bets    Bets%   Hit%    ROI")
    for res in results['ah_all']:
        output_lines.append(f"  {res['threshold']*100:2.0f}%     {res['bets']:4d}   {res['bets_pct']:5.1f}%   {res['hit_pct']:5.1f}%   {res['roi']:6.2f}%")

    output_lines.append("")
    output_lines.append("==============================================================")
    output_lines.append("  THRESHOLD SWEEP — ASIAN HANDICAP — EPL ONLY")
    output_lines.append("==============================================================")
    output_lines.append("Threshold  Bets    Bets%   Hit%    ROI")
    for res in results['ah_EPL']:
        output_lines.append(f"  {res['threshold']*100:2.0f}%     {res['bets']:4d}   {res['bets_pct']:5.1f}%   {res['hit_pct']:5.1f}%   {res['roi']:6.2f}%")

    output_lines.append("")
    output_lines.append("==============================================================")
    output_lines.append("  SEASON-BY-SEASON — EPL ASIAN HANDICAP (at 8% threshold)")
    output_lines.append("==============================================================")
    output_lines.append("Season      Bets    Hit%    ROI")
    for res in results['epl_ah_8']:
        output_lines.append(f"{res['season']:9s} {res['bets']:5d}   {res['hit_pct']:5.1f}%   {res['roi']:6.2f}%")

    # Ensure output directory exists
    os.makedirs('output/backtest_results', exist_ok=True)

    # Write to file
    with open('output/backtest_results/threshold_sweep.txt', 'w') as f:
        for line in output_lines:
            f.write(line + '\n')

    print("Sweep complete. Results saved to output/backtest_results/threshold_sweep.txt")


if __name__ == '__main__':
    main()