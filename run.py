"""Soccer prediction model — entry point."""
import sys
import os
import subprocess
import yaml
from datetime import date, datetime, timezone, timedelta


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
    from model.markets import predict_asian_handicap
    from scrapers.odds_api import fetch_epl_ah_odds
    from scrapers.team_name_mapper import map_team_name, find_unmapped_teams

    EDGE_THRESHOLD = 0.07
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')  # GMT date

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

    # --- Load EPL config ---
    with open('config/leagues.yaml', 'r') as f:
        config = yaml.safe_load(f)

    epl_config = config['leagues'].get('EPL')
    if not epl_config:
        print("ERROR: EPL not found in config/leagues.yaml")
        sys.exit(1)

    epl_sport_key = epl_config.get('odds_api_sport_key', 'soccer_epl')

    # --- Fetch EPL AH odds ---
    print("Fetching EPL Asian Handicap odds from The Odds API...")
    print("Target market: spreads (Asian Handicap) | EPL only | 7% edge threshold")
    print("")
    matches_raw = fetch_epl_ah_odds(api_key, epl_sport_key, 'EPL')

    if not matches_raw:
        print("\nNo EPL Asian Handicap odds found.")
        print("Possible reasons:")
        print("  - No EPL fixtures in the next 7 days")
        print("  - AH (spreads) market not available on your API tier")
        print("  - No UK/AU bookmakers returned AH lines for EPL this week")
        print("")
        print("The Odds API free tier does include spreads — if this persists, check API key and credits.")
        sys.exit(0)

    odds_df = pd.DataFrame(matches_raw)
    print(f"\nFound {len(odds_df)} EPL matches with AH odds.\n")

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
    predictions = []

    for _, row in odds_df.iterrows():
        api_home = row['home_team']
        api_away = row['away_team']

        canonical_home = map_team_name(api_home, 'EPL')
        canonical_away = map_team_name(api_away, 'EPL')

        if canonical_home not in ratings:
            print(f"  SKIP (no rating): EPL — '{api_home}' -> '{canonical_home}'")
            continue
        if canonical_away not in ratings:
            print(f"  SKIP (no rating): EPL — '{api_away}' -> '{canonical_away}'")
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

        ah_line = float(row['ah_line'])
        odds_ah_home = float(row['odds_ah_home_best'])
        odds_ah_away = float(row['odds_ah_away_best'])

        result = predict_asian_handicap(
            probs=probs,
            ah_line=ah_line,
            odds_ah_home=odds_ah_home,
            odds_ah_away=odds_ah_away,
            edge_threshold=EDGE_THRESHOLD
        )

        # Display the side with the highest edge (regardless of threshold)
        if result['edge_ah_home'] >= result['edge_ah_away']:
            display_side = 'home'
            display_prob = result['p_ah_home']
            display_odds = odds_ah_home
            display_edge = result['edge_ah_home']
        else:
            display_side = 'away'
            display_prob = result['p_ah_away']
            display_odds = odds_ah_away
            display_edge = result['edge_ah_away']

        # For flagged bets, use the official best_side and best_odds from predict_asian_handicap
        bet_side = result['best_side'] if result['should_bet'] else display_side
        bet_odds = result['best_odds'] if result['should_bet'] else display_odds

        predictions.append({
            'prediction_date': today,
            'match_date': row['date'],
            'league': 'EPL',
            'home_team': canonical_home,
            'away_team': canonical_away,
            'ah_line': ah_line,
            'bet_side': bet_side,
            'model_prob_ah': round(display_prob, 4),
            'odds_ah': round(bet_odds, 3),
            'implied_prob': round(1.0 / bet_odds, 4),
            'edge': round(display_edge, 4),
            'ev': round(result['ev'], 4),
            'bet_flag': result['should_bet'],
            'prob_home_win': round(probs['prob_home_win'], 4),
            'prob_draw': round(probs['prob_draw'], 4),
            'prob_away_win': round(probs['prob_away_win'], 4),
            'actual_home_goals': '',
            'actual_away_goals': '',
            'actual_ah_result': '',
            'profit_loss': '',
            'notes': '',
        })

    if not predictions:
        print("\nNo predictions could be generated (all teams unmapped or unrated).")
        sys.exit(0)

    pred_df = pd.DataFrame(predictions)
    pred_df = pred_df.sort_values(['match_date', 'edge'], ascending=[True, False]).reset_index(drop=True)

    flagged = pred_df[pred_df['bet_flag']]

    print(f"\n{'='*90}")
    print(f"=== EPL ASIAN HANDICAP PREDICTIONS - {today} ===")
    print(f"Edge threshold: 7% | Market: Asian Handicap | UK + AU bookmakers (best price)")
    print(f"{'='*90}")

    if len(flagged) > 0:
        print(f"\nFLAGGED BETS (edge >= 7%):")
        print(f"  NOTE: Odds shown are best available from UK + AU bookmakers via The Odds API.")
        print(f"  Min odds = minimum you should accept on Sportsbet/Ladbrokes to preserve 7% edge.")
        print()
        for _, r in flagged.iterrows():
            side_str = 'Home' if r['bet_side'] == 'home' else 'Away'
            bet_team = r['home_team'] if r['bet_side'] == 'home' else r['away_team']
            ah = float(r['ah_line'])
            # AH line is from home team's perspective. Away side gets the opposite line.
            if r['bet_side'] == 'away':
                display_line = -ah
            else:
                display_line = ah
            # Human-readable outcome description
            if display_line == -0.25:
                outcome_desc = f"{bet_team} win (half-stake refunded if draw)"
            elif display_line == 0.25:
                outcome_desc = f"{bet_team} win or draw (half-stake lost if draw)"
            elif display_line == -0.5:
                outcome_desc = f"{bet_team} win"
            elif display_line == 0.5:
                outcome_desc = f"{bet_team} win or draw"
            elif display_line == -0.75:
                outcome_desc = f"{bet_team} win by 2+ (half-stake wins if win by 1)"
            elif display_line == 0.75:
                outcome_desc = f"{bet_team} win or draw (or lose by 1 for half-stake)"
            elif display_line == -1.0:
                outcome_desc = f"{bet_team} win by 2+ (push if win by exactly 1)"
            elif display_line == 1.0:
                outcome_desc = f"{bet_team} win, draw, or lose by 1 (push if lose by exactly 1)"
            elif display_line < 0:
                outcome_desc = f"{bet_team} win by {abs(display_line):.2f}+ goals"
            else:
                outcome_desc = f"{bet_team} win or draw (or lose by up to {display_line:.2f})"
            # Minimum odds to preserve 7% edge (conservative: ignores overround)
            min_odds = 1.0 / (float(r['model_prob_ah']) - 0.07)
            print(f"  {'='*70}")
            print(f"  {r['match_date']}  {r['home_team']} vs {r['away_team']}")
            print(f"  BET:      {bet_team} AH {display_line:+.2f} ({side_str} side)")
            print(f"  OUTCOME:  {outcome_desc}")
            print(f"  API odds: {r['odds_ah']:.2f}  |  Min odds to bet: {min_odds:.2f}  |  Edge: {r['edge']*100:+.1f}%")
            print(f"  Model P:  {r['model_prob_ah']*100:.1f}% chance of winning this AH bet")
            print()
    else:
        print(f"\nFLAGGED BETS: None this week (no EPL match exceeded 7% edge)")

    print(f"\nALL EPL MATCHES THIS WEEK ({len(pred_df)} total), sorted by date then edge:")
    print(
        f"  {'Date':<12} {'Home':<22} {'Away':<22} "
        f"{'H%':>5} {'D%':>5} {'A%':>5} "
        f"{'AH':>6} {'Side':>5} {'P(side)':>8} {'Odds':>6} {'Edge':>7} {'Signal':>9}"
    )
    print(f"  {'-'*116}")
    for _, r in pred_df.iterrows():
        signal = '*** BET' if r['bet_flag'] else 'No Bet'
        side_str = 'Home' if r['bet_side'] == 'home' else 'Away'
        print(
            f"  {r['match_date']:<12} {r['home_team'][:22]:<22} {r['away_team'][:22]:<22} "
            f"{r['prob_home_win']*100:>4.0f}% {r['prob_draw']*100:>4.0f}% {r['prob_away_win']*100:>4.0f}% "
            f"{r['ah_line']:>+6.2f} {side_str:>5} {r['model_prob_ah']*100:>7.1f}% "
            f"{r['odds_ah']:>6.2f} {r['edge']*100:>+6.1f}%   {signal}"
        )

    # --- Paper trading log (AH) ---
    log_cols = [
        'prediction_date', 'match_date', 'league', 'home_team', 'away_team',
        'ah_line', 'bet_side', 'model_prob_ah', 'odds_ah', 'implied_prob', 'edge',
        'bet_flag', 'actual_home_goals', 'actual_away_goals', 'actual_ah_result', 'profit_loss', 'notes',
    ]
    log_path = 'output/paper_trading/log_ah.csv'
    os.makedirs('output/paper_trading', exist_ok=True)

    if os.path.exists(log_path):
        existing = pd.read_csv(log_path, dtype=str)
        for col in log_cols:
            if col not in existing.columns:
                existing[col] = ''
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

    print(f"\nThis week: {len(flagged)} flagged bets out of {len(pred_df)} EPL matches")
    print(f"{'='*80}\n")


# --- AH settlement helpers ---

def _settle_half(margin):
    if margin > 0:
        return 'Win'
    elif margin == 0:
        return 'Push'
    return 'Loss'


def _combine_quarter(r1, r2):
    if r1 == r2:
        return r1
    pair = {r1, r2}
    if pair == {'Win', 'Push'}:
        return 'Half Win'
    if pair == {'Loss', 'Push'}:
        return 'Half Loss'
    return 'Push'


def _flip(result):
    return {'Win': 'Loss', 'Half Win': 'Half Loss', 'Push': 'Push',
            'Half Loss': 'Half Win', 'Loss': 'Win'}[result]


def _calculate_ah(home_goals, away_goals, ah_line, bet_side, odds, stake=10.0):
    ah = float(ah_line)
    frac = round(abs(ah) % 1, 4)
    margin = home_goals + ah - away_goals

    if frac in (0.25, 0.75):
        home_result = _combine_quarter(_settle_half(margin - 0.25), _settle_half(margin + 0.25))
    else:
        home_result = _settle_half(margin)

    result = home_result if bet_side.lower() == 'home' else _flip(home_result)
    pnl = {'Win': (odds - 1) * stake, 'Half Win': (odds - 1) * stake / 2,
           'Push': 0.0, 'Half Loss': -stake / 2, 'Loss': -stake}[result]
    return result, round(pnl, 2)


def cmd_results():
    import pandas as pd

    log_path = 'output/paper_trading/log_ah.csv'
    scores_path = 'data/processed/all_merged.csv'
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    if not os.path.exists(log_path):
        print(f"No paper trading log found at {log_path}")
        print("Run 'python run.py predict' first.")
        sys.exit(0)

    log_df = pd.read_csv(log_path, dtype=str)
    for col in ['actual_home_goals', 'actual_away_goals', 'actual_ah_result', 'profit_loss', 'notes']:
        if col not in log_df.columns:
            log_df[col] = ''

    scores_df = pd.read_csv(scores_path)
    scores_df['_date'] = pd.to_datetime(scores_df['date'])
    scores_df['_home'] = scores_df['home_team'].str.lower().str.strip()
    scores_df['_away'] = scores_df['away_team'].str.lower().str.strip()

    unsettled_mask = log_df['actual_ah_result'].isna() | (log_df['actual_ah_result'].str.strip() == '')
    settled_this_run = []
    not_found = []

    for i in log_df[unsettled_mask].index:
        row = log_df.loc[i]
        home = row['home_team'].strip()
        away = row['away_team'].strip()
        match_date = pd.to_datetime(row['match_date'])
        ah_line = float(row['ah_line'])
        bet_side = row['bet_side'].strip()
        odds = float(row['odds_ah'])

        hits = scores_df[
            (scores_df['_home'] == home.lower()) &
            (scores_df['_away'] == away.lower()) &
            (scores_df['_date'] >= match_date - timedelta(days=1)) &
            (scores_df['_date'] <= match_date + timedelta(days=1))
        ]

        if hits.empty:
            not_found.append({'home': home, 'away': away, 'date': row['match_date']})
            continue

        sr = hits.iloc[0]
        hg, ag = int(sr['home_goals']), int(sr['away_goals'])
        result, pnl = _calculate_ah(hg, ag, ah_line, bet_side, odds)

        log_df.at[i, 'actual_home_goals'] = str(hg)
        log_df.at[i, 'actual_away_goals'] = str(ag)
        log_df.at[i, 'actual_ah_result'] = result
        log_df.at[i, 'profit_loss'] = str(pnl)
        settled_this_run.append({
            'home': home, 'away': away, 'match_date': row['match_date'],
            'ah_line': ah_line, 'bet_side': bet_side,
            'score': f"{hg}-{ag}", 'result': result, 'pnl': pnl,
        })

    desired_cols = [
        'prediction_date', 'match_date', 'league', 'home_team', 'away_team',
        'ah_line', 'bet_side', 'model_prob_ah', 'odds_ah', 'implied_prob', 'edge', 'bet_flag',
        'actual_home_goals', 'actual_away_goals', 'actual_ah_result', 'profit_loss', 'notes',
    ]
    for col in desired_cols:
        if col not in log_df.columns:
            log_df[col] = ''
    log_df = log_df[[c for c in desired_cols if c in log_df.columns]]
    log_df.to_csv(log_path, index=False)

    print(f"\n{'='*64}")
    print(f"=== PAPER TRADING RESULTS — {today} ===")
    print(f"{'='*64}\n")
    print(f"Settled this run:  {len(settled_this_run)} bet(s)")
    print(f"Could not settle (not yet played or data missing): {len(not_found)} bet(s)\n")

    if settled_this_run:
        print("SETTLED BETS:")
        for s in settled_this_run:
            side_str = s['bet_side'].capitalize()
            pnl_str = f"+${s['pnl']:.2f}" if s['pnl'] >= 0 else f"-${abs(s['pnl']):.2f}"
            print(
                f"  {s['match_date']}  {s['home'][:18]:<18} vs {s['away'][:18]:<18}  "
                f"Score={s['score']}  AH={s['ah_line']:+.2f}  Side={side_str:<5}  "
                f"Result={s['result']:<9}  P&L={pnl_str}"
            )

    if not_found:
        print("\nNOT YET SETTLED:")
        for nf in not_found:
            print(f"  Match not found in scores data — may not be played yet: "
                  f"{nf['home']} vs {nf['away']} on {nf['date']}")

    settled_all = log_df[
        log_df['actual_ah_result'].notna() & (log_df['actual_ah_result'].str.strip() != '')
    ].copy()

    if len(settled_all) > 0:
        settled_all['_pnl'] = pd.to_numeric(settled_all['profit_loss'], errors='coerce').fillna(0)
        total_pnl = float(settled_all['_pnl'].sum())
        total_bets = len(settled_all)
        roi = total_pnl / (total_bets * 10.0) * 100
        rc = settled_all['actual_ah_result'].value_counts()

        pnl_str = f"+${total_pnl:.2f}" if total_pnl >= 0 else f"-${abs(total_pnl):.2f}"
        print(f"\nRUNNING TOTALS (all time, flat $10 stake):")
        print(f"  Total bets settled: {total_bets}")
        print(f"  Wins: {rc.get('Win', 0)}  |  Half Wins: {rc.get('Half Win', 0)}  |  "
              f"Pushes: {rc.get('Push', 0)}  |  "
              f"Half Losses: {rc.get('Half Loss', 0)}  |  Losses: {rc.get('Loss', 0)}")
        print(f"  Total P&L: {pnl_str}")
        print(f"  ROI: {roi:+.1f}%  (P&L / total staked × 100)")

    print(f"\nPaper trading log updated: {log_path}")
    print(f"{'='*64}\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py <command>")
        print("Commands:")
        print("  backtest   Run historical backtest and print metrics")
        print("  update     Re-scrape all data and rebuild ratings (run weekly)")
        print("  predict    Fetch live EPL odds and generate Asian Handicap predictions (7% threshold)")
        print("  results    Settle paper trading bets from scores data and update log")
        sys.exit(1)

    command = sys.argv[1].lower()
    if command == 'backtest':
        cmd_backtest()
    elif command == 'update':
        cmd_update()
    elif command == 'predict':
        cmd_predict()
    elif command == 'results':
        cmd_results()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
