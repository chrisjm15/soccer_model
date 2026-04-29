import os
import pandas as pd
import yaml
from model.btts import run_predictions


def run_backtest(
    ratings_path: str = 'data/processed/ratings.csv',
    merged_path: str = 'data/processed/all_merged.csv',
    leagues_config_path: str = 'config/leagues.yaml',
    train_seasons: list = None,
    test_seasons: list = None,
    edge_threshold: float = 0.05,
    assumed_btts_odds: float = 1.90,
    output_path: str = 'output/backtest_results/predictions.csv'
) -> pd.DataFrame:
    """
    Runs the full backtest. Returns a DataFrame with one row per test-period match,
    including model predictions and actual outcomes.
    Saves results to output_path.
    """
    if train_seasons is None:
        train_seasons = ['2020-21', '2021-22', '2022-23']
    if test_seasons is None:
        test_seasons = ['2023-24', '2024-25']

    # Load config for home advantage values
    with open(leagues_config_path, 'r') as f:
        config = yaml.safe_load(f)
    home_advantage_by_league = {
        league: data.get('home_advantage_xg', 0.0)
        for league, data in config['leagues'].items()
    }

    # Load ratings (pre-match, lookahead-safe)
    ratings_df = pd.read_csv(ratings_path)
    ratings_df['date'] = pd.to_datetime(ratings_df['date'])

    # Load truth data (actual scorelines)
    merged_df = pd.read_csv(merged_path)
    merged_df['date'] = pd.to_datetime(merged_df['date'])

    # Keep only the columns we need from merged_df to avoid column clashes
    truth_cols = ['date', 'league', 'season', 'home_team', 'away_team', 'home_goals', 'away_goals']
    truth_df = merged_df[truth_cols].copy()

    # Run predictions on ALL ratings rows first
    all_predictions = run_predictions(
        ratings_df=ratings_df,
        home_advantage_by_league=home_advantage_by_league,
        btts_odds_yes=assumed_btts_odds,
        edge_threshold=edge_threshold
    )

    # Filter to test period only
    test_predictions = all_predictions[
        all_predictions['season'].isin(test_seasons)
    ].copy()

    # Merge in actual scorelines
    merge_keys = ['date', 'league', 'season', 'home_team', 'away_team']
    test_predictions = test_predictions.merge(truth_df, on=merge_keys, how='left')

    # Compute actual BTTS outcome
    test_predictions['actual_btts'] = (
        (test_predictions['home_goals'] >= 1) & (test_predictions['away_goals'] >= 1)
    ).astype(int)

    # Check for unmatched rows
    n_missing = test_predictions['home_goals'].isna().sum()
    if n_missing > 0:
        print(f"WARNING: {n_missing} test rows could not be matched to actual scorelines.")

    # Save output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    test_predictions.to_csv(output_path, index=False)

    print(f"Backtest complete.")
    print(f"  Train seasons : {train_seasons}")
    print(f"  Test seasons  : {test_seasons}")
    print(f"  Test matches  : {len(test_predictions)}")
    print(f"  Flagged bets  : {test_predictions['should_bet'].sum()}")
    print(f"  Results saved : {output_path}")

    return test_predictions


if __name__ == '__main__':
    df = run_backtest()
    print(df[['date', 'league', 'home_team', 'away_team', 'prob_btts_yes', 'should_bet', 'actual_btts']].head(10).to_string(index=False))
