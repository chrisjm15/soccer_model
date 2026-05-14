# experiment/load_sofascore.py
import sys
print(f"DEBUG — running file: {__file__}")
print(f"DEBUG — Python: {sys.executable}")
import argparse
import json
import time
import pandas as pd
from pathlib import Path
from playwright.sync_api import sync_playwright

LEAGUES = {
    'E1':  {'id': 18,  'name': 'Championship',       'type': 'european'},
    'N1':  {'id': 37,  'name': 'Eredivisie',          'type': 'european'},
    'B1':  {'id': 38,  'name': 'Pro League',          'type': 'european'},
    'P1':  {'id': 238, 'name': 'Liga Portugal',       'type': 'european'},
    'SC0': {'id': 36,  'name': 'Premiership',         'type': 'european'},
    'T1':  {'id': 52,  'name': 'Super Lig',           'type': 'european'},
    'SWE': {'id': 40,  'name': 'Allsvenskan',         'type': 'calendar'},
    'NOR': {'id': 20,  'name': 'Eliteserien',         'type': 'calendar'},
    'DNK': {'id': 39,  'name': 'Superliga',           'type': 'danish'},
    'FIN': {'id': 41,  'name': 'Veikkausliiga',       'type': 'calendar'},
}

STAT_MAP = {
    'expectedGoals':    ('home_xg',      'away_xg'),
    'totalShotsOnGoal': ('home_shots',   'away_shots'),
    'shotsOnGoal':      ('home_sot',     'away_sot'),
    'cornerKicks':      ('home_corners', 'away_corners'),
    'fouls':            ('home_fouls',   'away_fouls'),
    'yellowCards':      ('home_yellow',  'away_yellow'),
    'redCards':         ('home_red',     'away_red'),
}

OUTPUT_COLUMNS = ['date', 'home_team', 'away_team', 'home_shots', 'away_shots',
                  'home_sot', 'away_sot', 'home_corners', 'away_corners',
                  'home_fouls', 'away_fouls', 'home_yellow', 'away_yellow',
                  'home_red', 'away_red', 'home_xg', 'away_xg', 'league', 'season']

# FIX 1: Max round caps per league type — prevents infinite loop
MAX_ROUNDS = {
    'european': 60,   # Championship has 46 rounds; 60 gives headroom for playoff fixtures
    'calendar': 35,   # Allsvenskan/Eliteserien typically 30 rounds
    'danish':   45,   # Superliga has ~36 rounds
}

DELAY = 1.0  # seconds between API calls — do NOT reduce below 1.0 (Sofascore will block)


def fetch_json(page, url):
    """Navigate directly to API URL and parse JSON from page body. Returns parsed JSON or None."""
    try:
        response = page.goto(url, wait_until='domcontentloaded', timeout=15000)
        if not response or not response.ok:
            return None
        content = page.inner_text('body')
        return json.loads(content)
    except Exception:
        return None


def parse_season_start_year(name):
    """Extract the start year from a Sofascore season name for sorting.
    '25/26' -> 2025, '88/89' -> 1988, '2026' -> 2026.
    Two-digit years >= 50 are treated as 19xx, < 50 as 20xx.
    """
    year_part = name.strip().split()[-1]
    if '/' in year_part:
        start = int(year_part.split('/')[0])
        return (1900 + start) if start >= 50 else (2000 + start)
    else:
        try:
            return int(year_part)
        except ValueError:
            return 0


def get_seasons(page, tournament_id):
    """Return list of {id, name} dicts for all seasons, most recent first."""
    data = fetch_json(page, f'https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/seasons')
    if not data or 'seasons' not in data:
        return []
    seasons = data['seasons']
    # Sort by actual calendar year — NOT by season ID.
    # Sofascore assigns high IDs to old historical seasons added late to their DB,
    # so ID sort incorrectly picks 1980s seasons over recent ones.
    seasons.sort(key=lambda s: parse_season_start_year(s.get('name', '')), reverse=True)
    return seasons


def get_round_matches(page, tournament_id, season_id, round_num):
    """Return list of event dicts for a round. Returns [] if empty or error."""
    data = fetch_json(page, f'https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{round_num}')
    if not data:
        return []
    return data.get('events', [])


def get_match_stats(page, match_id):
    """Return stats dict {stat_key: (home_val, away_val)} for a match."""
    data = fetch_json(page, f'https://api.sofascore.com/api/v1/event/{match_id}/statistics')
    if not data:
        return {}
    # Use ALL period only
    all_period = next((p for p in data.get('statistics', []) if p.get('period') == 'ALL'), None)
    if not all_period:
        return {}
    stats = {}
    for group in all_period.get('groups', []):
        for item in group.get('statisticsItems', []):
            key = item.get('key')
            if key:
                # Use homeValue/awayValue (numeric) not home/away (string)
                stats[key] = (item.get('homeValue'), item.get('awayValue'))
    return stats


def sofascore_season_to_our_format(season_name, league_type):
    """
    Convert Sofascore season name to our file-naming format.
    'Championship 25/26' -> '2025-2026'
    'Allsvenskan 2026'   -> '2026'
    """
    # Extract the year part (last token)
    year_part = season_name.strip().split()[-1]  # e.g. '25/26' or '2026'

    if '/' in year_part:
        # European format: '25/26' -> '2025-2026'
        start, end = year_part.split('/')
        start_year = int(start) + 2000
        end_year = int(end) + 2000
        result = f"{start_year}-{end_year}"
        print(f"DEBUG season convert: '{season_name}' -> year_part='{year_part}' start={start_year} end={end_year} result='{result}'")
        return result
    else:
        # Calendar format: '2026' -> '2026'
        return year_part


def scrape_season(page, league_code, tournament_id, season_id, season_name, league_type, failures):
    """Scrape all completed matches in a season. Returns (DataFrame, season_str) or None."""
    our_season = sofascore_season_to_our_format(season_name, league_type)
    print(f"  Season: {season_name} -> {our_season}")

    max_round = MAX_ROUNDS.get(league_type, 60)
    rows = []
    round_num = 1
    consecutive_empty = 0
    seen_match_ids = set()  # FIX 2: deduplication

    while True:
        # FIX 1: Hard cap on rounds
        if round_num > max_round:
            print(f"    Reached max round cap ({max_round}) — stopping")
            break

        time.sleep(DELAY)
        events = get_round_matches(page, tournament_id, season_id, round_num)

        if not events:
            consecutive_empty += 1
            if consecutive_empty >= 3:
                break  # 3 empty rounds in a row = end of season data
            round_num += 1
            continue

        consecutive_empty = 0
        ended = [e for e in events if e.get('status', {}).get('description') == 'Ended']
        print(f"    Round {round_num}: {len(ended)}/{len(events)} completed")

        for event in ended:
            match_id = event.get('id')
            if not match_id:
                continue

            # FIX 2: Skip duplicate match IDs
            if match_id in seen_match_ids:
                continue
            seen_match_ids.add(match_id)

            time.sleep(DELAY)
            stats = get_match_stats(page, match_id)

            if not stats:
                failures.append({'league': league_code, 'season': our_season,
                                  'match_id': match_id, 'reason': 'no stats returned'})
                continue

            # Build row — start all values as None
            row = {col: None for col in OUTPUT_COLUMNS}
            row['league'] = league_code
            row['season'] = our_season

            # Date from Unix timestamp
            ts = event.get('startTimestamp')
            if ts:
                row['date'] = pd.to_datetime(ts, unit='s').strftime('%Y-%m-%d')

            # Teams
            row['home_team'] = event.get('homeTeam', {}).get('name')
            row['away_team'] = event.get('awayTeam', {}).get('name')

            # Stats — map keys, never use [] on API data
            for stat_key, (home_col, away_col) in STAT_MAP.items():
                if stat_key not in stats:
                    continue
                home_val, away_val = stats[stat_key]
                is_xg = home_col in ('home_xg', 'away_xg')

                def to_num(v, as_float):
                    try:
                        f = float(v)
                        return round(f, 2) if as_float else int(f)
                    except (TypeError, ValueError):
                        return None

                row[home_col] = to_num(home_val, is_xg)
                row[away_col] = to_num(away_val, is_xg)

            rows.append(row)

        round_num += 1

    if not rows:
        return None

    df = pd.DataFrame(rows)
    df = df.reindex(columns=OUTPUT_COLUMNS)
    return df, our_season


def parse_args():
    parser = argparse.ArgumentParser(description='Sofascore stats + xG loader')
    parser.add_argument('--leagues', nargs='+', help='League codes e.g. E1 N1 SWE')
    parser.add_argument('--current-only', action='store_true',
                        help='Only scrape the most recent season for each league')
    parser.add_argument('--all-seasons', action='store_true',
                        help='Scrape all available seasons')
    parser.add_argument('--seasons-back', type=int, default=None,
                        help='Max number of seasons to scrape (most recent first). e.g. 5')
    return parser.parse_args()


def main():
    args = parse_args()

    # Directories — absolute paths anchored to project root, not Terminal cwd
    project_root = Path(__file__).resolve().parent.parent
    proxy_dir = project_root / 'data' / 'proxy'
    scandinavian_dir = project_root / 'data' / 'scandinavian'
    proxy_dir.mkdir(parents=True, exist_ok=True)
    scandinavian_dir.mkdir(parents=True, exist_ok=True)

    league_list = args.leagues if args.leagues else list(LEAGUES.keys())

    failures = []
    total_files = 0
    total_rows = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Navigate to sofascore.com FIRST — establishes the browser session
        print("Opening Sofascore to establish browser session...")
        page.goto('https://www.sofascore.com', wait_until='domcontentloaded')
        time.sleep(2)  # let session cookies settle
        print("Session ready.\n")

        for league_code in league_list:
            if league_code not in LEAGUES:
                print(f"Unknown league: {league_code}")
                continue

            league = LEAGUES[league_code]
            tournament_id = league['id']
            league_type = league['type']
            output_dir = scandinavian_dir if league_type == 'calendar' else proxy_dir

            print(f"\n{'='*50}")
            print(f"League: {league_code} — {league['name']} (id={tournament_id})")

            # Re-navigate to sofascore.com between leagues to reset session/rate limit
            page.goto('https://www.sofascore.com', wait_until='domcontentloaded')
            time.sleep(5)

            seasons = get_seasons(page, tournament_id)
            if not seasons:
                # One retry after a longer pause
                print(f"  Seasons fetch failed — waiting 30s and retrying...")
                time.sleep(30)
                page.goto('https://www.sofascore.com', wait_until='domcontentloaded')
                time.sleep(5)
                seasons = get_seasons(page, tournament_id)
            if not seasons:
                print(f"  ERROR: could not fetch seasons after retry")
                continue

            # FIX 3: Print the available seasons so you can verify which one is being picked
            print(f"  Available seasons (most recent first): {[s.get('name') for s in seasons[:5]]}")

            # Select which seasons to run
            if args.current_only:
                seasons_to_run = [seasons[0]]  # most recent (sorted above)
            elif args.all_seasons:
                seasons_to_run = seasons[:args.seasons_back] if args.seasons_back else seasons
            else:
                seasons_to_run = [seasons[0]]  # default: current only

            for season in seasons_to_run:
                season_id = season.get('id')
                season_name = season.get('name', '')
                print(f"\n  Processing: {season_name} (id={season_id})")

                result = scrape_season(page, league_code, tournament_id,
                                       season_id, season_name, league_type, failures)
                if result is None:
                    print(f"  No data returned")
                    continue

                df, our_season = result
                output_path = Path(output_dir) / f"{league_code}_{our_season}_sofascore.csv"
                df.to_csv(output_path, index=False)
                print(f"  Saved: {output_path} ({len(df)} rows)")
                total_files += 1
                total_rows += len(df)

        browser.close()

    if failures:
        pd.DataFrame(failures).to_csv('data/sofascore_failures.csv', index=False)
        print(f"\nFailures logged: data/sofascore_failures.csv ({len(failures)} entries)")

    print(f"\n{'='*50}")
    print(f"Done. Files: {total_files}  Rows: {total_rows:,}  Failures: {len(failures)}")


if __name__ == '__main__':
    main()
