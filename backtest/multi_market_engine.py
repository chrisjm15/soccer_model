import pandas as pd
import numpy as np
import yaml
import os
from pathlib import Path
from math import floor, ceil
from model.poisson import compute_match_probs
from model.markets import (
    predict_1x2,
    predict_over_under,
    predict_asian_handicap,
    compute_ah_probs
)

def compute_actual_ah_result(margin, ah_line):
    """
    Computes the outcome of an Asian Handicap bet given the goal margin.
    margin = home_goals - away_goals
    ah_line: the handicap applied to the home team (e.g., -1.5, -1.75)
    """
    # Check if it's a quarter line (e.g., -1.75 or -1.25)
    # We use the logic that quarter lines are between two half-lines.
    # We identify the two halves by finding the nearest 0.5 increments.
    is_quarter = (ah_line * 2) % 1 != 0

    if not is_quarter:
        # Standard half or whole line
        if margin > -ah_line:
            return 'home_win'
        elif margin == -ah_line:
            return 'push'
        else:
            return 'away_win'
    else:
        # Split the quarter line into its two constituent half lines
        # e.g., -1.75 becomes -1.5 and -2.0
        l1 = floor(ah_line * 2) / 2
        l2 = ceil(ah_line * 2) / 2

        # Helper to get win/loss/push for a single line
        def get_res(line):
            if margin > -line: return 'home_win'
            if margin == -line: return 'push'
            return 'away_win'

        res1 = get_res(l1)
        res2 = get_res(l2)

        if res1 == res2:
            return res1

        # Check for half-win / half-loss / push (net zero)
        # One side is win, one side is push -> half_win
        # One side is loss, one side is push -> half_loss
        # One side is win, one side is loss -> push (net zero)

        results_set = {res1, res2}
        if 'push' in results_set:
            if 'home_win' in results_set and 'away_win' in results_set:
                return 'push' # Should not happen with one being push
            if 'home_win' in results_set:
                return 'half_win'
            if 'away_win' in results_set:
                return 'half_loss'
            return 'push'

        if 'home_win' in results_set and 'away_win' in results_set:
            return 'push'

        return res1 # Fallback

def run_multi_market_backtest(
    ratings_path: str = 'data/processed/ratings.csv',
    merged_path: str = 'data/processed/all_merged.csv',
    leagues_config_path: str = 'config/leagues.yaml',
    train_seasons: list = None,
    test_seasons: list = None,
    edge_threshold: float = 0.05,
    output_dir: str = 'output/backtest_results'
) -> dict:
    if train_seasons is None:
        train_seasons = ['2020-21', '2021-22', '2022-23']
    if test_seasons is None:
        test_seasons = ['2023-24', '2024-25', '2025-26']

    # Step 1: Load data
    ratings = pd.read_csv(ratings_path)
    merged = pd.read_csv(merged_path)
    with open(leagues_config_path, 'r') as f:
        leagues_config = yaml.safe_load(f)

    leagues_ha = {league: data.get('home_advantage_xg', 0.0) for league, data in leagues_config['leagues'].items()}

    # Step 2: Filter to test seasons and Join
    merged['date'] = pd.to_datetime(merged['date'])
    ratings['date'] = pd.to_datetime(ratings['date'])

    # Filter merged data for test seasons
    test_df = merged[merged['season'].isin(test_seasons)].copy()

    # Join ratings to merged data
    # We join on date, league, season, home_team, away_team
    test_df = test_df.merge(
        ratings,
        on=['date', 'league', 'season', 'home_team', 'away_team'],
        how='inner'
    )

    # Drop rows with missing odds
    required_odds = ['odds_home', 'odds_draw', 'odds_away', 'odds_over25',
'odds_under25', 'ah_line', 'odds_ah_home', 'odds_ah_away']
    initial_count = len(test_df)
    test_df = test_df.dropna(subset=required_odds)
    dropped_odds = initial_count - len(test_df)
    if dropped_odds > 0:
        print(f"Warning: Dropped {dropped_odds} rows due to missing odds.")

    # Prepare storage for results
    results_list = []

    # Step 3: Iterate and Predict
    for idx, row in test_df.iterrows():
        ha = leagues_ha.get(row['league'], 0.0)

        probs = compute_match_probs(
            home_attack=row['home_attack'],
            home_defence=row['home_defence'],
            away_attack=row['away_attack'],
            away_defence=row['away_defence'],
            home_advantage=ha
        )

        # Market Predictions
        r_1x2 = predict_1x2(probs, row['odds_home'], row['odds_draw'],
row['odds_away'], edge_threshold)
        r_ou  = predict_over_under(probs, row['odds_over25'],
row['odds_under25'], edge_threshold)
        r_ah  = predict_asian_handicap(probs, row['ah_line'],
row['odds_ah_home'], row['odds_ah_away'], edge_threshold)

        # Step 4: Actual Outcomes
        # 1X2
        actual_result = 'home' if row['home_goals'] > row['away_goals'] else ('draw' if row['home_goals'] == row['away_goals'] else 'away')

        # O/U 2.5
        actual_over25 = 1 if (row['home_goals'] + row['away_goals']) > 2 else 0

        # AH
        margin = row['home_goals'] - row['away_goals']
        ah_result = compute_actual_ah_result(margin, row['ah_line'])

        # Step 5: P&L Computation
        pnl_1x2 = 0.0
        should_bet_1x2 = False
        prob_1x2_outcome = 0.0 # for Brier
        if r_1x2['should_bet']:
            should_bet_1x2 = True
            if actual_result == r_1x2['best_outcome']:
                pnl_1x2 = r_1x2['best_odds'] - 1
            else:
                pnl_1x2 = -1.0
            # Brier component: prob of the actual outcome
            # Since we don't know which outcome happened in the dict, we find it in probs
            if actual_result == 'home': prob_1x2_outcome = probs['prob_home_win']
            elif actual_result == 'draw': prob_1x2_outcome = probs['prob_draw']
            else: prob_1x2_outcome = probs['prob_away_win']
        else:
            # For Brier on all matches, we need the prob of the actual result
            if actual_result == 'home': prob_1x2_outcome = probs['prob_home_win']
            elif actual_result == 'draw': prob_1x2_outcome = probs['prob_draw']
            else: prob_1x2_outcome = probs['prob_away_win']

        pnl_ou = 0.0
        should_bet_ou = False
        prob_ou_outcome = 0.0
        if r_ou['should_bet']:
            should_bet_ou = True
            if actual_over25 == 1:
                pnl_ou = r_ou['odds_over'] - 1
            else:
                pnl_ou = -1.0
            prob_ou_outcome = probs['prob_over_25'] if actual_over25 == 1 else (1 - probs['prob_over_25'])
        else:
            prob_ou_outcome = probs['prob_over_25'] if actual_over25 == 1 else (1 - probs['prob_over_25'])

        pnl_ah = 0.0
        should_bet_ah = False
        prob_ah_outcome = 0.0
        if r_ah['should_bet']:
            should_bet_ah = True
            side = r_ah['best_side']
            odds = r_ah['best_odds']

            if side == 'home':
                bet_result = ah_result
            else:
                flip = {'home_win': 'away_win', 'away_win': 'home_win', 'push': 'push',
                        'half_win': 'half_loss', 'half_loss': 'half_win'}
                bet_result = flip[ah_result]

            if bet_result == 'home_win':
                pnl_ah = odds - 1
            elif bet_result == 'push':
                pnl_ah = 0.0
            elif bet_result == 'away_win':
                pnl_ah = -1.0
            elif bet_result == 'half_win':
                pnl_ah = (odds - 1) * 0.5
            elif bet_result == 'half_loss':
                pnl_ah = -0.5

            if side == 'home':
                prob_ah_outcome = r_ah['p_ah_home']
            else:
                prob_ah_outcome = r_ah['p_ah_away']
        else:
            if r_ah['p_ah_home'] >= r_ah['p_ah_away']:
                prob_ah_outcome = r_ah['p_ah_home']
            else:
                prob_ah_outcome = r_ah['p_ah_away']

        # Store record
        results_list.append({
            'date': row['date'],
            'league': row['league'],
            'season': row['season'],
            'home_team': row['home_team'],
            'away_t': row['away_team'],
            'home_goals': row['home_goals'],
            'away_goals': row['away_goals'],
            'actual_1x2': actual_result,
            'actual_ou': actual_over25,
            'actual_ah': ah_result,
            'pnl_1x2': pnl_1x2,
            'pnl_ou': pnl_ou,
            'pnl_ah': pnl_ah,
            'should_bet_1x2': should_bet_1x2,
            'should_bet_ou': should_bet_ou,
            'should_bet_ah': should_bet_ah,
            'prob_1x2': prob_1x2_outcome,
            'prob_ou': prob_ou_outcome,
            'prob_ah': prob_ah_outcome,
            'odds_1x2': r_1x2['best_odds'] if should_bet_1x2 else None,
            'odds_ou': r_ou['odds_over'] if should_bet_ou else None,
            'odds_ah': r_ah['best_odds'] if should_bet_ah else None,
            'ah_line': row['ah_line']
        })

    results_df = pd.DataFrame(results_list)

    # Step 6: Compute Metrics
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    def get_market_stats(df, market_type):
        if market_type == '1X2':
            bets = df[df['should_bet_1x2']]
            if len(bets) == 0: return None
            # Hit rate: exclude pushes (though 1X2 has no push in the 'result' sense unless we count draw)
            # The prompt says "excluding pushes". In 1X2, 'draw' is an outcome, not a push.
            # We'll treat 'draw' as a standard outcome.
            wins = bets[bets['pnl_1x2'] > 0]
            hit_rate = (len(wins) / len(bets)) * 100
            total_pnl = bets['pnl_1x2'].sum()
            roi = (total_pnl / len(bets)) * 100
            avg_odds = bets['odds_1x2'].mean()
            breakeven = (1 / avg_odds * 100) if avg_odds else 0
            brier = ((df['prob_1x2'] - (df['pnl_1x2'] > 0).astype(float))**2).mean()
            return {'bets': len(bets), 'hit': hit_rate, 'pnl': total_pnl, 'roi': roi, 'breakeven': breakeven, 'brier': brier, 'raw': bets}

        elif market_type == 'OU':
            bets = df[df['should_bet_ou']]
            if len(bets) == 0: return None
            wins = bets[bets['pnl_ou'] > 0]
            hit_rate = (len(wins) / len(bets)) * 100
            total_pnl = bets['pnl_ou'].sum()
            roi = (total_pnl / len(bets)) * 100
            avg_odds = bets['odds_ou'].mean()
            breakeven = (1 / avg_odds * 100) if avg_odds else 0
            brier = ((df['prob_ou'] - (df['pnl_ou'] > 0).astype(float))**2).mean()
            return {'bets': len(bets), 'hit': hit_rate, 'pnl': total_pnl, 'roi': roi, 'breakeven': breakeven, 'brier': brier, 'raw': bets}

        elif market_type == 'AH':
            bets = df[df['should_bet_ah']]
            if len(bets) == 0: return None
            # Exclude pushes from hit rate denominator
            # In AH, a 'push' is when pnl == 0.
            non_push_bets = bets[bets['pnl_ah'] != 0]
            wins = bets[bets['pnl_ah'] > 0]
            hit_rate = (len(wins) / len(non_push_bets)) * 100 if len(non_push_bets) > 0 else 0
            total_pnl = bets['pnl_ah'].sum()
            roi = (total_pnl / len(bets)) * 100
            avg_odds = bets['odds_ah'].mean()
            breakeven = (1 / avg_odds * 100) if avg_odds else 0
            brier = ((non_push_bets['prob_ah'] - (non_push_bets['pnl_ah'] > 0).astype(float))**2).mean() if len(non_push_bets) > 0 else float('nan')
            return {'bets': len(bets), 'hit': hit_rate, 'pnl': total_pnl, 'roi': roi, 'breakeven': breakeven, 'brier': brier, 'raw': bets}

    stats_1x2 = get_market_stats(results_df, '1X2')
    stats_ou = get_market_stats(results_df, 'OU')
    stats_ah = get_market_stats(results_df, 'AH')

    # Step 7: Save Outputs
    results_df.to_csv(output_path / 'multi_market_predictions.csv', index=False)

    with open(output_path / 'multi_market_report.txt', 'w') as f:
        f.write("==============================================================\n")
        f.write("  MULTI-MARKET BACKTEST RESULTS\n")
        f.write("============================================================\n")
        f.write(f"Test period: {test_seasons[0]} to {test_seasons[-1]}\n")
        f.write(f"Total matches evaluated: {len(results_df)}\n\n")

        for name, s in [('1X2', stats_1x2), ('Over/Under 2.5 (Over only)', stats_ou), ('Asian Handicap (best side)', stats_ah)]:
            if s is None: continue
            f.write(f"--------------------------------------------------\n")
            f.write(f"MARKET: {name}\n")
            f.write(f"--------------------------------------------------\n")
            f.write(f"Total bets: {s['bets']} ({s['bets']/len(results_df)*100:.1f}% of matches)\n")
            f.write(f"Hit rate:   {s['hit']:.1f}%  (break-can: {s['breakeven']:.1f}%)\n")
            f.write(f"Total P&L:  {s['pnl']:+.2f} units\n")
            f.write(f"ROI:        {s['roi']:+.1f}%\n")
            f.write(f"Brier score: {s['brier']:.4f}\n\n")

            f.write(f"By league:\n")
            for l, group in s['raw'].groupby('league'):
                l_bets = len(group)
                l_pnl = group['pnl_1x2' if name=='1X2' else ('pnl_ou' if name.startswith('Over') else 'pnl_ah')].sum()
                # Simplified ROI for group
                l_roi = (l_pnl / l_bets) * 100
                f.write(f"  {l:<15}: {l_bets} bets, ROI={l_roi:+.1f}%\n")

            f.write(f"\nBy season:\n")
            for sea, group in s['raw'].groupby('season'):
                sea_bets = len(group)
                sea_pnl = group['pnl_1x2' if name=='1X2' else ('pnl_ou' if name.startswith('Over') else 'pnl_ah')].sum()
                sea_roi = (sea_pnl / sea_bets) * 100
                f.write(f"  {sea}: {sea_bets} bets, ROI={sea_roi:+.1f}%\n")
            f.write(f"\n")

        f.write(f"============================================================\n")
        f.write(f"SUMMARY COMPARISON\n")
        f.write(f"=============================================================\n")
        f.write(f"{'Market':<18} {'Bets':<8} {'Hit%':<8} {'ROI':<10} {'Brier':<8}\n")
        for name, s in [('1X2', stats_1x0 := stats_1x2), ('Over/Under 2.5', stats_ou), ('Asian Handicap', stats_ah)]:
            if s:
                f.write(f"{name:<18} {s['bets']:<8} {s['hit']:>5.1f}%  {s['roi']:>+7.1f}%  {s['brier']:>7.4f}\n")
        f.write(f"=============================================================\n")

    return {"status": "success", "matches": len(results_df)}

if __name__ == '__main__':
    run_multi_market_backtest()
    print("Backtest complete. Results saved to output/backtest_results/")