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
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    from model.live_ratings import get_latest_ratings
    from model.poisson import compute_match_probs
    from model.markets import compute_ah_probs
    from model.calibration import consensus_novig, calibrated_ah_decision, calibrate_m1
    from scrapers.odds_api import fetch_epl_ah_odds
    from scrapers.team_name_mapper import map_team_name, find_unmapped_teams

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

    # --- Load EPL config & calibration config ---
    with open('config/leagues.yaml', 'r') as f:
        config = yaml.safe_load(f)

    epl_config = config['leagues'].get('EPL')
    if not epl_config:
        print("ERROR: EPL not found in config/leagues.yaml")
        sys.exit(1)

    epl_sport_key = epl_config.get('odds_api_sport_key', 'soccer_epl')

    with open('config/calibration.yaml', 'r') as f:
        calib_cfg = yaml.safe_load(f)['epl_ah']

    coefs = calib_cfg['m3']
    m1_coefs = calib_cfg['m1']
    edge_threshold = float(calib_cfg.get('edge_threshold', 0.01))
    market_prob_range = calib_cfg['market_prob_range']
    promoted_min_matches = int(calib_cfg.get('promoted_min_matches', 10))
    coef_fit_date = calib_cfg.get('fit_date', '')

    # --- Identify promoted teams & matches played this season ---
    merged_all = pd.read_csv('data/processed/all_merged.csv')
    epl_all = merged_all[merged_all['league'] == 'EPL']
    teams_2526 = set(epl_all[epl_all['season'] == '2025-26']['home_team']).union(
        set(epl_all[epl_all['season'] == '2025-26']['away_team'])
    )
    teams_2627 = set(epl_all[epl_all['season'] == '2026-27']['home_team']).union(
        set(epl_all[epl_all['season'] == '2026-27']['away_team'])
    )
    promoted_teams = teams_2627 - teams_2526

    epl_2627 = epl_all[epl_all['season'] == '2026-27']
    matches_played = {}
    for team in teams_2627:
        count = len(epl_2627[(epl_2627['home_team'] == team) | (epl_2627['away_team'] == team)])
        matches_played[team] = count

    # --- Fetch EPL AH odds ---
    print("Fetching EPL Asian Handicap odds from The Odds API...")
    print(f"Target market: spreads (Asian Handicap) | EPL only | {edge_threshold*100:.1f}% calibrated edge threshold")
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
        book_prices = row['book_prices']

        ah_probs = compute_ah_probs(probs['goal_grid'], ah_line)
        novig_home = consensus_novig(book_prices)

        decision = calibrated_ah_decision(
            p_home=ah_probs['p_home'],
            p_push=ah_probs['p_push'],
            p_away=ah_probs['p_away'],
            novig_home=novig_home,
            coefs=coefs,
            threshold=edge_threshold,
        )

        bet_side = decision['bet_side']
        bet_odds = odds_ah_home if bet_side == 'home' else odds_ah_away
        best_book = row.get('best_home_book', '') if bet_side == 'home' else row.get('best_away_book', '')
        raw_au = row.get('best_au_home', '') if bet_side == 'home' else row.get('best_au_away', '')
        best_au_price = round(float(raw_au), 3) if (raw_au != '' and pd.notna(raw_au)) else ''
        break_even_odds = 1.0 / decision['calib_prob'] if decision['calib_prob'] > 0 else 999.0

        # M1-only calibrated prob (diagnostic)
        calib_prob_m1 = calibrate_m1(decision['market_prob'], m1_coefs)

        # Guards
        veto_notes = []
        market_prob = decision['market_prob']
        if market_prob < market_prob_range[0] or market_prob > market_prob_range[1]:
            veto_notes.append('out_of_range')

        home_promoted = (canonical_home in promoted_teams and matches_played.get(canonical_home, 0) < promoted_min_matches)
        away_promoted = (canonical_away in promoted_teams and matches_played.get(canonical_away, 0) < promoted_min_matches)
        if home_promoted or away_promoted:
            veto_notes.append('promoted_veto')

        if veto_notes:
            bet_flag = False
            notes = '; '.join(veto_notes)
        else:
            bet_flag = decision['should_bet']
            notes = ''

        predictions.append({
            'prediction_date': today,
            'match_date': row['date'],
            'league': 'EPL',
            'home_team': canonical_home,
            'away_team': canonical_away,
            'ah_line': ah_line,
            'bet_side': bet_side,
            'model_prob_ah': round(decision['model_prob'], 4),
            'odds_ah': round(bet_odds, 3),
            'odds_ah_home_at_bet': round(odds_ah_home, 3),
            'odds_ah_away_at_bet': round(odds_ah_away, 3),
            'implied_prob': round(1.0 / bet_odds, 4),
            'edge': round(decision['calib_edge'], 4),
            'bet_flag': bet_flag,
            'actual_home_goals': '',
            'actual_away_goals': '',
            'actual_ah_result': '',
            'profit_loss': '',
            'notes': notes,
            'market_prob_consensus': round(decision['market_prob'], 4),
            'calib_prob': round(decision['calib_prob'], 4),
            'calib_edge': round(decision['calib_edge'], 4),
            'calib_prob_m1_only': round(calib_prob_m1, 4),
            'n_books': len(book_prices),
            'coef_fit_date': coef_fit_date,
            'best_book': best_book,
            'best_au_price': best_au_price,
            'closing_line': '',
            'closing_odds': '',
            'clv': '',
            'break_even_odds': break_even_odds,
            'prob_home_win': round(probs['prob_home_win'], 4),
            'prob_draw': round(probs['prob_draw'], 4),
            'prob_away_win': round(probs['prob_away_win'], 4),
        })

    if not predictions:
        print("\nNo predictions could be generated (all teams unmapped or unrated).")
        sys.exit(0)

    pred_df = pd.DataFrame(predictions)
    pred_df = pred_df.sort_values(['match_date', 'edge'], ascending=[True, False]).reset_index(drop=True)

    flagged = pred_df[pred_df['bet_flag']]

    print(f"\n{'='*90}")
    print(f"=== EPL ASIAN HANDICAP PREDICTIONS - {today} ===")
    print(f"Threshold: {edge_threshold*100:.1f}% calibrated edge | Market: Asian Handicap | Best price execution")
    print(f"{'='*90}")

    if len(flagged) > 0:
        print(f"\nFLAGGED BETS (calibrated edge >= {edge_threshold*100:.1f}%):")
        print(f"  NOTE: Odds shown are best available from UK + AU + EU bookmakers via The Odds API.")
        print()
        for _, r in flagged.iterrows():
            side_str = 'Home' if r['bet_side'] == 'home' else 'Away'
            bet_team = r['home_team'] if r['bet_side'] == 'home' else r['away_team']
            ah = float(r['ah_line'])
            if r['bet_side'] == 'away':
                display_line = -ah
            else:
                display_line = ah

            if display_line == 0.0:
                outcome_desc = f"{bet_team} win (draw = stake returned)"
            elif display_line == -0.25:
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

            au_str = f"{float(r['best_au_price']):.2f}" if r['best_au_price'] != '' else 'None (no AU book on line)'
            print(f"  {'='*70}")
            print(f"  {r['match_date']}  {r['home_team']} vs {r['away_team']}")
            print(f"  BET:             {bet_team} AH {display_line:+.2f} ({side_str} side)")
            print(f"  OUTCOME:         {outcome_desc}")
            print(f"  Best Price:      {r['odds_ah']:.2f} ({r['best_book']})  |  Best AU Price: {au_str}  |  Break-Even Odds: {r['break_even_odds']:.2f}")
            print(f"  Calib P:         {r['calib_prob']*100:.2f}%  |  Market P: {r['market_prob_consensus']*100:.2f}%  |  Raw Model P: {r['model_prob_ah']*100:.2f}%")
            print(f"  Calibrated Edge: {r['calib_edge']*100:+.2f}%")
            print()
    else:
        print(f"\nFLAGGED BETS: None this week (no EPL match exceeded {edge_threshold*100:.1f}% calibrated edge without veto)")

    print(f"\nALL EPL MATCHES THIS WEEK ({len(pred_df)} total), sorted by date then edge:")
    print(
        f"  {'Date':<12} {'Home':<20} {'Away':<20} "
        f"{'AH':>6} {'Side':>5} {'CalibP':>8} {'MktP':>8} {'Edge':>7} {'Best':>6} {'Book':<14} {'AU':>6} {'BreakEv':>8} {'Signal':>9} {'Notes':<15}"
    )
    print(f"  {'-'*148}")
    for _, r in pred_df.iterrows():
        signal = '*** BET' if r['bet_flag'] else 'No Bet'
        side_str = 'Home' if r['bet_side'] == 'home' else 'Away'
        notes_str = r['notes'] if r['notes'] else ''
        au_col = f"{float(r['best_au_price']):>6.2f}" if r['best_au_price'] != '' else f"{'':>6}"
        print(
            f"  {r['match_date']:<12} {r['home_team'][:20]:<20} {r['away_team'][:20]:<20} "
            f"{r['ah_line']:>+6.2f} {side_str:>5} {r['calib_prob']*100:>7.2f}% {r['market_prob_consensus']*100:>7.2f}% "
            f"{r['calib_edge']*100:>+6.2f}% {r['odds_ah']:>6.2f} {str(r['best_book'])[:14]:<14} {au_col} {r['break_even_odds']:>8.2f}   {signal:<7} {notes_str:<15}"
        )

    # --- Paper trading log (AH) ---
    log_cols = [
        'prediction_date', 'match_date', 'league', 'home_team', 'away_team',
        'ah_line', 'bet_side', 'model_prob_ah', 'odds_ah',
        'odds_ah_home_at_bet', 'odds_ah_away_at_bet',
        'implied_prob', 'edge',
        'bet_flag', 'actual_home_goals', 'actual_away_goals', 'actual_ah_result', 'profit_loss', 'notes',
        'market_prob_consensus', 'calib_prob', 'calib_edge', 'calib_prob_m1_only',
        'n_books', 'coef_fit_date',
        'best_book', 'best_au_price',
        'closing_line', 'closing_odds', 'clv',
    ]
    log_path = 'output/paper_trading/log_ah.csv'
    os.makedirs('output/paper_trading', exist_ok=True)

    if os.path.exists(log_path):
        existing = pd.read_csv(log_path, dtype=str, keep_default_na=False)
        all_cols = list(existing.columns)
        for col in log_cols:
            if col not in all_cols:
                existing[col] = ''
                all_cols.append(col)
        existing_keys = set(
            zip(existing['match_date'], existing['home_team'], existing['away_team'])
        )
        new_rows = pred_df[
            ~pred_df.apply(
                lambda r: (r['match_date'], r['home_team'], r['away_team']) in existing_keys,
                axis=1
            )
        ].copy()
        if len(new_rows) > 0:
            for col in all_cols:
                if col not in new_rows.columns:
                    new_rows[col] = ''
            combined = pd.concat([existing[all_cols], new_rows[all_cols].astype(str)], ignore_index=True)
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
    from model.clv import clv_for_row

    log_path = 'output/paper_trading/log_ah.csv'
    scores_path = 'data/processed/all_merged.csv'
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    if not os.path.exists(log_path):
        print(f"No paper trading log found at {log_path}")
        print("Run 'python run.py predict' first.")
        sys.exit(0)

    log_df = pd.read_csv(log_path, dtype=str, keep_default_na=False)
    existing_cols = list(log_df.columns)
    required_cols = [
        'actual_home_goals', 'actual_away_goals', 'actual_ah_result', 'profit_loss', 'notes',
        'odds_ah_home_at_bet', 'odds_ah_away_at_bet',
        'closing_line', 'closing_odds', 'clv',
        'closing_home_odds', 'closing_away_odds', 'closing_source',
        'closing_prob_bet_side', 'clv_move', 'clv_price', 'clv_line_converted',
    ]
    for col in required_cols:
        if col not in existing_cols:
            log_df[col] = ''
            existing_cols.append(col)

    scores_df = pd.read_csv(scores_path)
    scores_df['_date'] = pd.to_datetime(scores_df['date'])
    scores_df['_home'] = scores_df['home_team'].str.lower().str.strip()
    scores_df['_away'] = scores_df['away_team'].str.lower().str.strip()

    unsettled_mask = log_df['actual_ah_result'].isna() | (log_df['actual_ah_result'].str.strip() == '')
    settled_this_run = []
    not_found = []

    bet_mask = log_df['bet_flag'].str.strip().str.lower() == 'true'
    for i in log_df[unsettled_mask & bet_mask].index:
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

    # --- CLV and score back-fill for ALL log rows (idempotent) ---
    clv_cols_to_reset = [
        'closing_line', 'closing_odds', 'clv',
        'closing_home_odds', 'closing_away_odds', 'closing_source',
        'closing_prob_bet_side', 'clv_move', 'clv_price', 'clv_line_converted',
    ]

    def _valid_odd(val):
        if pd.isna(val) or str(val).strip() == '':
            return None
        try:
            f = float(val)
            return f if f > 1.0 else None
        except (TypeError, ValueError):
            return None

    for i in log_df.index:
        for c in clv_cols_to_reset:
            log_df.at[i, c] = ''

        row = log_df.loc[i]
        home = row['home_team'].strip()
        away = row['away_team'].strip()
        match_date = pd.to_datetime(row['match_date'])
        bet_side = row['bet_side'].strip().lower()
        is_bet = str(row['bet_flag']).strip().lower() == 'true'

        hits = scores_df[
            (scores_df['_home'] == home.lower()) &
            (scores_df['_away'] == away.lower()) &
            (scores_df['_date'] >= match_date - timedelta(days=1)) &
            (scores_df['_date'] <= match_date + timedelta(days=1))
        ]
        if hits.empty:
            continue

        sr = hits.iloc[0]

        # Non-bet rows: fill actual_home_goals / actual_away_goals when score is known;
        # leave actual_ah_result and profit_loss untouched (blank for non-bets).
        if not is_bet and pd.notna(sr.get('home_goals')) and pd.notna(sr.get('away_goals')):
            if str(log_df.at[i, 'actual_home_goals']).strip() == '':
                log_df.at[i, 'actual_home_goals'] = str(int(sr['home_goals']))
            if str(log_df.at[i, 'actual_away_goals']).strip() == '':
                log_df.at[i, 'actual_away_goals'] = str(int(sr['away_goals']))

        if pd.isna(sr.get('close_ah_line')) or str(sr.get('close_ah_line')).strip() == '':
            continue

        close_line = float(sr['close_ah_line'])

        pin_h = _valid_odd(sr.get('close_pin_ah_home'))
        pin_a = _valid_odd(sr.get('close_pin_ah_away'))
        avg_h = _valid_odd(sr.get('close_avg_ah_home'))
        avg_a = _valid_odd(sr.get('close_avg_ah_away'))

        if pin_h is not None and pin_a is not None:
            closing_source = 'pinnacle'
            close_oh, close_oa = pin_h, pin_a
        elif avg_h is not None and avg_a is not None:
            closing_source = 'avg'
            close_oh, close_oa = avg_h, avg_a
        else:
            continue

        mpc_raw = str(row.get('market_prob_consensus', '')).strip()
        mpc = float(mpc_raw) if (mpc_raw != '' and mpc_raw.lower() != 'nan') else None

        clv_res = clv_for_row(
            bet_side=bet_side,
            bet_line=float(row['ah_line']),
            bet_odds=float(row['odds_ah']),
            bet_market_prob=mpc,
            close_line=close_line,
            close_home_odds=close_oh,
            close_away_odds=close_oa,
        )

        if clv_res['closing_prob_bet_side'] is None:
            continue

        closing_odds_side = close_oh if bet_side == 'home' else close_oa
        log_df.at[i, 'closing_line'] = str(round(close_line, 4))
        log_df.at[i, 'closing_home_odds'] = str(round(close_oh, 4))
        log_df.at[i, 'closing_away_odds'] = str(round(close_oa, 4))
        log_df.at[i, 'closing_odds'] = str(round(closing_odds_side, 4))
        log_df.at[i, 'closing_source'] = closing_source
        log_df.at[i, 'closing_prob_bet_side'] = str(round(clv_res['closing_prob_bet_side'], 6))
        log_df.at[i, 'clv_move'] = (
            str(round(clv_res['clv_move'], 6)) if clv_res['clv_move'] is not None else ''
        )
        log_df.at[i, 'clv_price'] = (
            str(round(clv_res['clv_price'], 6)) if clv_res['clv_price'] is not None else ''
        )
        log_df.at[i, 'clv'] = log_df.at[i, 'clv_price']
        log_df.at[i, 'clv_line_converted'] = str(clv_res['line_converted'])

    log_df = log_df[existing_cols]
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

    bet_mask = log_df['bet_flag'].str.strip().str.lower() == 'true'
    settled_all = log_df[
        bet_mask &
        log_df['actual_ah_result'].notna() &
        (log_df['actual_ah_result'].str.strip() != '')
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

    # CLV summary (bets and all rows)
    has_clv_mask = log_df['clv_price'].notna() & (log_df['clv_price'].str.strip() != '')
    conv_mask = log_df['clv_line_converted'].str.strip().str.lower() == 'true'

    total_rows = len(log_df)
    total_bets_all = int(bet_mask.sum())
    all_with_clv = int(has_clv_mask.sum())
    bets_with_clv = int((bet_mask & has_clv_mask).sum())
    conv_all = int((has_clv_mask & conv_mask).sum())
    conv_bets = int((bet_mask & has_clv_mask & conv_mask).sum())

    clv_price_bets = pd.to_numeric(log_df.loc[bet_mask, 'clv_price'], errors='coerce').dropna()
    clv_move_bets = pd.to_numeric(log_df.loc[bet_mask, 'clv_move'], errors='coerce').dropna()
    clv_move_all = pd.to_numeric(log_df['clv_move'], errors='coerce').dropna()

    print(f"\nCLV SUMMARY (closing line value vs football-data.co.uk closing odds):")
    print(f"  Rows with CLV:             bets {bets_with_clv}/{total_bets_all}  |  all rows {all_with_clv}/{total_rows}")
    print(f"  Rows with line converted:  bets {conv_bets}/{bets_with_clv}  |  all rows {conv_all}/{all_with_clv}")
    if len(clv_price_bets) > 0:
        mean_cp = float(clv_price_bets.mean())
        print(f"  Mean clv_price (bets):     {mean_cp*100:+.2f}% ({mean_cp:+.4f}, n={len(clv_price_bets)})")
    else:
        print(f"  Mean clv_price (bets):     N/A (n=0)")
    if len(clv_move_bets) > 0:
        mean_cm_b = float(clv_move_bets.mean())
        print(f"  Mean clv_move (bets):      {mean_cm_b*100:+.2f}pp ({mean_cm_b:+.4f}, n={len(clv_move_bets)})")
    else:
        print(f"  Mean clv_move (bets):      N/A (n=0)")
    if len(clv_move_all) > 0:
        mean_cm_a = float(clv_move_all.mean())
        print(f"  Mean clv_move (all rows):  {mean_cm_a*100:+.2f}pp ({mean_cm_a:+.4f}, n={len(clv_move_all)})")
    else:
        print(f"  Mean clv_move (all rows):  N/A (n=0)")

    print(f"\nPaper trading log updated: {log_path}")
    print(f"{'='*64}\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py <command>")
        print("Commands:")
        print("  backtest   Run historical backtest and print metrics")
        print("  update     Re-scrape all data and rebuild ratings (run weekly)")
        print("  predict    Fetch live EPL odds and generate calibrated Asian Handicap predictions")
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
