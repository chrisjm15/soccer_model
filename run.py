"""Soccer prediction model — entry point."""
import sys
import os
import subprocess
import yaml
from datetime import date


def cmd_backtest():
    from backtest.engine import run_backtest
    from backtest.metrics import compute_metrics, print_metrics_report

    with open('config/leagues.yaml', 'r') as f:
        config = yaml.safe_load(f)

    predictions_df = run_backtest(
        ratings_path='data/processed/ratings.csv',
        merged_path='data/processed/all_merged.csv',
        leagues_config_path='config/leagues.yaml',
        output_path='output/backtest_results/predictions.csv'
    )

    metrics = compute_metrics(predictions_df)
    report = print_metrics_report(metrics)

    report_path = 'output/backtest_results/metrics_report.txt'
    os.makedirs('output/backtest_results', exist_ok=True)
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"\nReport saved to {report_path}")


def cmd_update():
    """Re-scrape all data sources and rebuild ratings."""
    steps = [
        ('Scraping Understat xG data...', ['python', 'scrapers/understat.py']),
        ('Downloading football-data.co.uk CSVs...', ['python', 'scrapers/footballdata.py']),
        ('Merging data sources...', ['python', 'scrapers/merge.py']),
        ('Rebuilding ratings...', ['python', 'model/ratings.py']),
    ]

    for label, cmd in steps:
        print(f"\n{'='*60}")
        print(label)
        print('='*60)
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode != 0:
            print(f"ERROR: Step failed — {label}")
            sys.exit(1)

    print(f"\n{'='*60}")
    print("UPDATE COMPLETE")
    print('='*60)
    import pandas as pd
    df = pd.read_csv('data/processed/all_merged.csv')
    ratings = pd.read_csv('data/processed/ratings.csv')
    print(f"  Merged matches: {len(df)}")
    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"  Seasons: {sorted(df['season'].unique())}")
    print(f"  Ratings rows: {len(ratings)}")
    print(f"\nRun 'python run.py predict' to generate this week's bets.")


def cmd_predict():
    import pandas as pd
    from model.live_ratings import get_latest_ratings
    from model.poisson import compute_match_probs
    from scrapers.odds_api import fetch_all_leagues_odds
    from scrapers.team_name_mapper import map_team_name, find_unmapped_teams

    # --- API key ---
    api_key = os.environ.get('ODDS_API_KEY')
    if not api_key:
        print("ERROR: ODDS_API_KEY environment variable is not set.")
        print("")
        print("To fix this:")
        print("  Windows PowerShell:  $env:ODDS_API_KEY = 'your_key_here'")
        print("  Windows CMD:         set ODDS_API_KEY=your_key_here")
        print("")
        print("Get a free key at: https://the-odds-api.com")
        sys.exit(1)

    # --- Load config ---
    with open('config/leagues.yaml', 'r') as f:
        config = yaml.safe_load(f)
    leagues_config = config['leagues']

    # --- Fetch live odds ---
    print("Fetching live odds from The Odds API (over/under 2.5 goals market)...")
    print("Note: BTTS market requires a paid API tier. Using over 2.5 as equivalent free market.")
    print("")
    odds_df = fetch_all_leagues_odds(api_key, leagues_config)

    if odds_df.empty:
        print("\nNo upcoming matches found with odds.")
        print("Leagues may be between gameweeks, or no matches in the next week.")
        sys.exit(0)

    print(f"\nFound {len(odds_df)} upcoming matches.\n")

    # --- Load ratings ---
    ratings = get_latest_ratings('data/processed/ratings.csv')

    # --- Check for unmapped teams ---
    unmapped = find_unmapped_teams(odds_df, ratings)
    if unmapped:
        print("WARNING: The following API team names could not be mapped to rated teams:")
        for u in unmapped:
            print(f"  {u}")
        print("  -> These matches will be skipped. Add missing mappings to data/aliases/team_aliases.json\n")

    # --- Run predictions ---
    EDGE_THRESHOLD = 0.08
    today = date.today().isoformat()
    predictions = []

    for _, row in odds_df.iterrows():
        league = row['league']
        api_home = row['home_team']
        api_away = row['away_team']

        canonical_home = map_team_name(api_home, league)
        canonical_away = map_team_name(api_away, league)

        if canonical_home is None or canonical_home not in ratings:
            print(f"  SKIP (no rating): {league} — '{api_home}'")
            continue
        if canonical_away is None or canonical_away not in ratings:
            print(f"  SKIP (no rating): {league} — '{api_away}'")
            continue

        hr = ratings[canonical_home]
        ar = ratings[canonical_away]

        probs = compute_match_probs(
            home_attack=hr['attack_home'],
            home_defence=hr['defence_home'],
            away_attack=ar['attack_away'],
            away_defence=ar['defence_away'],
            home_advantage=0.0,
        )

        over25_odds = float(row['over25_odds_best'])
        implied_prob_over25 = 1.0 / over25_odds
        edge_over25 = probs['prob_over_25'] - implied_prob_over25
        ev_over25 = (
            probs['prob_over_25'] * (over25_odds - 1.0)
            - (1.0 - probs['prob_over_25']) * 1.0
        )
        bet_flag = edge_over25 >= EDGE_THRESHOLD

        predictions.append({
            'prediction_date': today,
            'match_date': row['date'],
            'league': league,
            'home_team': canonical_home,
            'away_team': canonical_away,
            'model_prob_btts': round(probs['prob_btts_yes'], 4),
            'model_prob_over25': round(probs['prob_over_25'], 4),
            'real_odds_over25': round(over25_odds, 3),
            'n_bookmakers': int(row['n_bookmakers']),
            'implied_prob_over25': round(implied_prob_over25, 4),
            'edge_over25': round(edge_over25, 4),
            'expected_value': round(ev_over25, 4),
            'bet_flag': bet_flag,
            'actual_over25': '',
            'profit_loss': '',
            'notes': '',
        })

    if not predictions:
        print("\nNo predictions could be generated (all teams unmapped or unrated).")
        sys.exit(0)

    pred_df = pd.DataFrame(predictions)
    pred_df = pred_df.sort_values('edge_over25', ascending=False).reset_index(drop=True)

    flagged = pred_df[pred_df['bet_flag']]

    print(f"\n{'='*75}")
    print(f"=== PREDICTIONS — {today} ===")
    print(f"Market: Over 2.5 Goals | Edge threshold: {int(EDGE_THRESHOLD*100)}% | UK bookmakers (best price)")
    print(f"{'='*75}")

    if len(flagged) > 0:
        print(f"\nFLAGGED BETS (edge >= {int(EDGE_THRESHOLD*100)}%):")
        for _, r in flagged.iterrows():
            print(
                f"  {r['home_team'][:20]:<20} vs {r['away_team'][:20]:<20}  "
                f"{r['league']:<12}  "
                f"P(Ov2.5)={r['model_prob_over25']*100:.1f}%  "
                f"Odds={r['real_odds_over25']:.2f}  "
                f"Edge={r['edge_over25']*100:+.1f}%  "
                f"EV={r['expected_value']:+.3f}"
            )
    else:
        print(f"\nFLAGGED BETS: None this week (no match exceeded {int(EDGE_THRESHOLD*100)}% edge)")

    print(f"\nALL UPCOMING MATCHES ({len(pred_df)} total), sorted by edge:")
    print(
        f"  {'Home':<22} {'Away':<22} {'League':<12} "
        f"{'Ov2.5%':>7} {'BTTS%':>6} {'Odds':>6} {'Edge':>7} {'Flag':>8}"
    )
    print(f"  {'-'*95}")
    for _, r in pred_df.iterrows():
        flag = '*** BET' if r['bet_flag'] else ''
        print(
            f"  {r['home_team'][:22]:<22} {r['away_team'][:22]:<22} {r['league']:<12} "
            f"{r['model_prob_over25']*100:>6.1f}% "
            f"{r['model_prob_btts']*100:>5.1f}% "
            f"{r['real_odds_over25']:>6.2f} "
            f"{r['edge_over25']*100:>+6.1f}% "
            f"  {flag}"
        )

    # --- Paper trading log ---
    log_path = 'output/paper_trading/log.csv'
    os.makedirs('output/paper_trading', exist_ok=True)

    log_cols = [
        'prediction_date', 'match_date', 'league', 'home_team', 'away_team',
        'model_prob_btts', 'model_prob_over25', 'real_odds_over25', 'implied_prob_over25',
        'edge_over25', 'bet_flag', 'actual_over25', 'profit_loss', 'notes',
    ]

    if os.path.exists(log_path):
        existing = pd.read_csv(log_path, dtype=str)
        existing_keys = set(
            zip(existing['match_date'], existing['home_team'], existing['away_team'])
        )
        new_rows = pred_df[
            ~pred_df.apply(
                lambda r: (r['match_date'], r['home_team'], r['away_team']) in existing_keys,
                axis=1
            )
        ]
        if len(new_rows) > 0:
            combined = pd.concat([existing, new_rows[log_cols].astype(str)], ignore_index=True)
            combined.to_csv(log_path, index=False)
            print(f"\nPaper trading log updated: {log_path}")
            print(f"  Added {len(new_rows)} new rows ({len(existing)} already existed)")
        else:
            print(f"\nPaper trading log unchanged: all {len(pred_df)} matches already logged")
    else:
        pred_df[log_cols].to_csv(log_path, index=False)
        print(f"\nPaper trading log created: {log_path}")
        print(f"  Logged {len(pred_df)} matches")

    print(f"\nThis week: {len(flagged)} flagged bets out of {len(pred_df)} upcoming matches")
    print(f"{'='*75}\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py <command>")
        print("Commands:")
        print("  backtest   Run historical backtest and print metrics")
        print("  update     Re-scrape all data and rebuild ratings (run weekly)")
        print("  predict    Fetch live odds and generate over 2.5 goals predictions")
        sys.exit(1)

    command = sys.argv[1].lower()
    if command == 'backtest':
        cmd_backtest()
    elif command == 'update':
        cmd_update()
    elif command == 'predict':
        cmd_predict()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
