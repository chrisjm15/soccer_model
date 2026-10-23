# experiment/load_sofascore.py
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

OUTPUT_COLUMNS = ['date','home_team','away_team','home_shots','away_shots',
                  'home_sot','away_sot','home_corners','away_corners',
                  'home_fouls','away_fouls','home_yellow','away_yellow',
                  'home_red','away_red','home_xg','away_xg','league','season']

DELAY = 0.35  # seconds between API calls — do NOT reduce below 0.3

def fetch_json(page, url):
    """Make a fetch() call inside the browser. Returns parsed JSON or None."""
    # IMPORTANT: use page.evaluate() not requests.get() — auth is handled by
browser
    result = page.evaluate(f"""
        async () => {{
            try {{
                const r = await fetch('{url}', {{headers: {{'Accept':
'application/json'}}, 'credentials': 'include'}})
                if (!r.ok) return null;
                return await r.json();
            }} catch(e) {{
                return null;
            }}
        }}
    """)
    return result

def get_seasons(page, tournament_id):
    """Return list of {{id, name}} dicts for all seasons."""
    data = fetch_json(page,
f'https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/seasons')
    if not data or 'seasons' not in data:
        return []
    return data['seasons']

def get_round_matches(page, tournament_id, season_id, round_num):
    """Return list of event dicts for a round. Returns [] if empty or error."""
    data = fetch_json(page,
f'https://api.sofascore.com/api/v1/unique-tournament/{tournament_id}/season/{seasof'https://api.sofascore.com/api/v1/unique-tournament/{ournament_id}/season/{season_id}/events/round/{round_num}')
    if not data:
        return []
    return data.get('events', [])

def get_match_stats(page, match_id):
    """Return stats dict {{stat_key: (home_val, away_val)}} for a match."""
    data = fetch_json(page,
f'https://api.sofascore.com/api/v1/event/{match_id}/statistics')
    if not data:
        return {}
    # Use ALL period only
    all_period = next((p for p in data.get('statistics', []) if p.get('period')
== 'ALL'), None)
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
    'Championship 25/26' -> '2024-2025'
    'Allsvenskan 2026'   -> '2026'
    """
    import re
    # Extract the year part (last token)
    year_part = season_name.strip().split()[-1]  # e.g. '25/26' or '2026'

    if '/' in year_part:
        # European format: '25/26' -> '2024-2025'
        start, end = year_part.split('/')
        start_year = int(start) + 2000
        end_year = int(end) + 2000
        return f"{start_year}-{end_year}"
    else:
        # Calendar format: '2026' -> '2026'
        return year_part

def scrape_season(page, league_code, tournament_id, season_id, season_name,
league_type, failures):
    """Scrape all completed matches in a season. Returns DataFrame or None."""
    our_season = sofascore_season_to_our_format(season_name, league_type)
    print(f"  Season: {season_name} -> {our_season}")

    rows = []
    round_num = 1
    consecutive_empty = 0

    while True:
        time.sleep(DELAY)
        events = get_round_matches(page, tournament_id, season_id, round_num)

        if not events:
            consecutive_empty += 1
            if consecutive_empty >= 3:
                break  # 3 empty rounds in a row = end of season
            round_num += 1
            continue

        consecutive_empty = 0
        ended = [e for e in events if e.get('status', {}).get('description') ==
'Ended']
        print(f"    Round {round_num}: {len(ended)}/{len(events)} completed")

        for event in ended:
            match_id = event.get('id')
            if not match_id:
                continue

            time.sleep(DELAY)
            stats = get_match_stats(page, match_id)

            if not stats:
                failures.append({'league': league_code, 'season': our_season,
                                  'match_id': match_id, 'reason': 'no stats
returned'})
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
    parser.add_argument('--leagues', nargs='+', help='League codes e.g. E1 N1
SWE')
    parser.add_argument('--current-only', action='store_true',
                        help='Only scrape the most recent season for each
league')
    parser.add_argument('--all-seasons', action='store_true',
                        help='Scrape all available seasons')
    return parser.parse_args()

def main():
    args = parse_args()

    # Directories — inside main(), never at module level
    Path('data/proxy').mkdir(parents=True, exist_ok=True)
    Path('data/scandinavian').mkdir(parents=True, exist_ok=True)

    league_list = args.leagues if args.leagues else list(LEAGUES.keys())

    failures = []
    total_files = 0
    total_rows = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Navigate to sofascore.com FIRST — establishes the browser session
        # ALL API calls made after this will succeed
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
            output_dir = 'data/scandinavian' if league_type == 'calendar' else
'data/proxy'

            print(f"\n{'='*50}")
            print(f"League: {league_code} — {league['name']}
(id={tournament_id})")

            seasons = get_seasons(page, tournament_id)
            if not seasons:
                print(f"  ERROR: could not fetch seasons")
                continue

            # Select which seasons to run
            if args.current_only:
                seasons_to_run = [seasons[0]]  # most recent only
            elif args.all_seasons:
                seasons_to_run = seasons
            else:
                seasons_to_run = [seasons[0]]  # default: current only

            for season in seasons_to_run:
                season_id = season.get('id')
                season_name = season.get('name', '')
                print(f"\n  Processing: {season_name}")

                result = scrape_season(page, league_code, tournament_id,
                                       season_id, season_name, league_type,
failures)
                if result is None:
                    print(f"  No data returned")
                    continue

                df, our_season = result
                output_path = Path(output_dir) /
f"{league_code}_{our_season}_sofascore.csv"
                df.to_csv(output_path, index=False)
                print(f"  Saved: {output_path} ({len(df)} rows)")
                total_files += 1
                total_rows += len(df)

        browser.close()

    if failures:
        pd.DataFrame(failures).to_csv('data/sofascore_failures.csv', index=False)
        print(f"\nFailures logged: data/sofascore_failures.csv ({len(failures)}
entries)")

    print(f"\n{'='*50}")
    print(f"Done. Files: {total_files}  Rows: {total_rows:,}  Failures:
{len(failures)}")

if __name__ == '__main__':
    main()