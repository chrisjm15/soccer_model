# Shim: asyncio.coroutine was removed in Python 3.11 but ratelimiter (a
# fotmob-api dependency) still uses it. Patch it back before the import.
import asyncio
if not hasattr(asyncio, 'coroutine'):
    import functools
    def _coroutine_shim(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    asyncio.coroutine = _coroutine_shim

from fotmob_api import FotmobAPI
import requests_cache
import pandas as pd
import json, time, io
from pathlib import Path
import argparse

# ── UPDATE THESE after running --discover ──
FOTMOB_LEAGUE_IDS = {
    'E1':  None,   # English Championship
    'N1':  None,   # Dutch Eredivisie
    'B1':  None,   # Belgian Pro League
    'P1':  None,   # Portuguese Primeira Liga
    'SC0': None,   # Scottish Premiership
    'T1':  None,   # Turkish Süper Lig
    'SWE': None,   # Sweden Allsvenskan
    'NOR': None,   # Norway Eliteserien
    'DNK': None,   # Denmark Superliga
    'FIN': None,   # Finland Veikkausliiga
}

# Name variants used during discovery matching (case-insensitive)
LEAGUE_SEARCH_NAMES = {
    'E1':  ['championship', 'efl championship'],
    'N1':  ['eredivisie'],
    'B1':  ['jupiler pro league', 'belgian pro league', 'first division a'],
    'P1':  ['liga portugal', 'primeira liga', 'liga nos'],
    'SC0': ['scottish premiership', 'premiership'],
    'T1':  ['süper lig', 'super lig', 'trendyol süper lig'],
    'SWE': ['allsvenskan'],
    'NOR': ['eliteserien'],
    'DNK': ['superliga', 'danish superliga'],
    'FIN': ['veikkausliiga'],
}

PROXY_LEAGUES = ['E1', 'N1', 'B1', 'P1', 'SC0', 'T1']
SCAND_LEAGUES = ['SWE', 'NOR', 'DNK', 'FIN']

# Calendar-year leagues (season string is just '2023', not '2022-2023')
# SWE, NOR, FIN use calendar year. DNK uses European split-year format.
CALENDAR_YEAR_LEAGUES = {'SWE', 'NOR', 'FIN'}

PROXY_SEASONS = [
    '2014-2015', '2015-2016', '2016-2017', '2017-2018', '2018-2019',
    '2019-2020', '2020-2021', '2021-2022', '2022-2023', '2023-2024', '2024-2025'
]
SCAND_SEASONS = [
    '2014', '2015', '2016', '2017', '2018', '2019',
    '2020', '2021', '2022', '2023', '2024', '2025'
]

OUTPUT_COLUMNS = [
    'date', 'home_team', 'away_team',
    'home_shots', 'away_shots',
    'home_sot', 'away_sot',
    'home_corners', 'away_corners',
    'home_fouls', 'away_fouls',
    'home_yellow', 'away_yellow',
    'home_red', 'away_red',
    'home_xg', 'away_xg',
    'league', 'season',
]

STAT_MAP = {
    # shots on target
    'shots on target':      ('home_sot', 'away_sot'),
    'shots on goal':        ('home_sot', 'away_sot'),
    'on target':            ('home_sot', 'away_sot'),
    'shot on target':       ('home_sot', 'away_sot'),
    # shots
    'shots':                ('home_shots', 'away_shots'),
    'total shots':          ('home_shots', 'away_shots'),
    'shot attempts':        ('home_shots', 'away_shots'),
    # corners
    'corners':              ('home_corners', 'away_corners'),
    'corner kicks':         ('home_corners', 'away_corners'),
    # fouls
    'fouls':                ('home_fouls', 'away_fouls'),
    'fouls committed':      ('home_fouls', 'away_fouls'),
    # yellow cards
    'yellow cards':         ('home_yellow', 'away_yellow'),
    'yellow card':          ('home_yellow', 'away_yellow'),
    # red cards
    'red cards':            ('home_red', 'away_red'),
    'red card':             ('home_red', 'away_red'),
    # xG
    'expected goals':       ('home_xg', 'away_xg'),
    'xg':                   ('home_xg', 'away_xg'),
    'xgoals':               ('home_xg', 'away_xg'),
    'expected goals (xg)':  ('home_xg', 'away_xg'),
}

XG_COLS = {'home_xg', 'away_xg'}


def to_fotmob_season(league_code, season):
    """
    Convert season string to FotMob API format.
    European format: '2022-2023' -> '2022/2023'   (proxy leagues + DNK)
    Calendar format: '2023'      -> '2023'          (SWE, NOR, FIN)
    Do NOT apply the same format to all leagues — route by league code.
    """
    if league_code in CALENDAR_YEAR_LEAGUES:
        return season  # '2023' stays '2023'
    else:
        return season.replace('-', '/')  # '2022-2023' -> '2022/2023'


def _extract_first_match_id(fixtures):
    """Try multiple structural patterns to find the first match ID."""
    # Pattern A: list of dicts with 'id' key
    if isinstance(fixtures, list):
        for item in fixtures:
            if isinstance(item, dict):
                mid = item.get('id') or item.get('matchId') or item.get('eventId')
                if mid:
                    return mid
    # Pattern B: dict with a known container key
    if isinstance(fixtures, dict):
        for key in ('fixtures', 'matches', 'allMatches', 'events', 'data', 'items'):
            if key in fixtures:
                inner = fixtures[key]
                if isinstance(inner, list) and inner:
                    first = inner[0]
                    if isinstance(first, dict):
                        return first.get('id') or first.get('matchId') or first.get('eventId')
    # Pattern C: recursive search one level deeper
    if isinstance(fixtures, dict):
        for val in fixtures.values():
            if isinstance(val, list) and val:
                first = val[0]
                if isinstance(first, dict):
                    mid = first.get('id') or first.get('matchId') or first.get('eventId')
                    if mid:
                        return mid
    return None


def _extract_all_match_ids(fixtures):
    """Extract all match IDs from the fixtures response. Deduplicates."""
    ids = []

    def search(obj, depth=0):
        if depth > 5:
            return
        if isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict):
                    mid = item.get('id') or item.get('matchId') or item.get('eventId')
                    if mid and isinstance(mid, (int, str)):
                        ids.append(mid)
                    else:
                        search(item, depth + 1)
        elif isinstance(obj, dict):
            for key in ('fixtures', 'matches', 'allMatches', 'events', 'data', 'items'):
                if key in obj:
                    search(obj[key], depth + 1)

    search(fixtures)
    return list(dict.fromkeys(ids))  # preserve order, remove duplicates


def _extract_stats_dict(details):
    """
    Extract per-team stats from get_match_details() response.
    FotMob match stats are typically under one of:
      details['content']['stats']['Periods']['All']['stats']
      details['matchFacts']['stats']
      details['stats']
    Each stat entry is typically one of:
      {'title': 'Shots on Target', 'home': '5', 'away': '3'}
      {'name': 'Shots on Target', 'home': {'total': 5}, 'away': {'total': 3}}
      {'stats': [...]} -- nested further
    Use .get() for EVERY dict access -- never use [] on API response data.
    """
    stats_list = None

    # Path 1: content.stats.Periods.All.stats
    try:
        stats_list = (
            details.get('content', {})
                   .get('stats', {})
                   .get('Periods', {})
                   .get('All', {})
                   .get('stats')
        )
    except (AttributeError, TypeError):
        pass

    # Path 2: matchFacts.stats
    if not stats_list:
        try:
            stats_list = details.get('matchFacts', {}).get('stats')
        except (AttributeError, TypeError):
            pass

    # Path 3: top-level stats
    if not stats_list:
        stats_list = details.get('stats') if isinstance(details, dict) else None

    # Path 4: recursive search for a 'stats' list anywhere in first 3 levels
    if not stats_list:
        def find_stats(obj, depth=0):
            if depth > 3 or not isinstance(obj, dict):
                return None
            for k, v in obj.items():
                if k == 'stats' and isinstance(v, list) and len(v) > 2:
                    return v
                if isinstance(v, dict):
                    result = find_stats(v, depth + 1)
                    if result is not None:
                        return result
            return None
        stats_list = find_stats(details)

    if not stats_list or not isinstance(stats_list, list):
        return {}

    result = {}
    for item in stats_list:
        if not isinstance(item, dict):
            continue

        # Stat name -- try multiple key names
        name = (
            item.get('title') or item.get('name') or
            item.get('type') or item.get('key') or ''
        ).lower().strip()
        if not name:
            continue

        # Home/away values -- handle multiple structures
        home_raw = item.get('home', '')
        away_raw = item.get('away', '')

        def parse_val(v):
            """Extract numeric string from various value shapes."""
            if isinstance(v, str):
                return v.strip()
            if isinstance(v, (int, float)):
                return str(v)
            if isinstance(v, dict):
                # {'total': 5} or {'value': '5'} or {'stat': 5}
                inner = v.get('total') or v.get('value') or v.get('stat') or v.get('count')
                return str(inner) if inner is not None else ''
            return ''

        result[name] = (parse_val(home_raw), parse_val(away_raw))

    return result


def _extract_match_meta(details):
    """
    Extract date (YYYY-MM-DD string), home_team, away_team from match details.
    Use .get() for every dict access -- never use [] on API response data.
    """
    date_str = None
    home_team = None
    away_team = None

    general = details.get('general', {}) or {}
    header = details.get('header', {}) or {}

    # Date -- try multiple paths
    for section in (general, details):
        if not date_str and isinstance(section, dict):
            date_str = (
                section.get('matchTimeUTC') or
                section.get('matchTime') or
                section.get('localGameTime') or
                section.get('date')
            )

    # Teams -- try 'homeTeam'/'awayTeam' or 'home'/'away' at multiple levels
    for section in (general, header, details):
        if not isinstance(section, dict):
            continue
        home_obj = section.get('homeTeam') or section.get('home')
        away_obj = section.get('awayTeam') or section.get('away')
        if isinstance(home_obj, dict) and not home_team:
            home_team = home_obj.get('name') or home_obj.get('shortName') or home_obj.get('longName')
        if isinstance(away_obj, dict) and not away_team:
            away_team = away_obj.get('name') or away_obj.get('shortName') or away_obj.get('longName')

    # Parse date to YYYY-MM-DD -- always use strftime, never return the raw string
    if date_str:
        try:
            date_parsed = pd.to_datetime(date_str, utc=True).strftime('%Y-%m-%d')
        except Exception:
            try:
                date_parsed = pd.to_datetime(date_str).strftime('%Y-%m-%d')
            except Exception:
                date_parsed = str(date_str)[:10]  # last resort: take first 10 chars
    else:
        date_parsed = None

    return date_parsed, home_team, away_team


def _build_row(details, league_code, season):
    """Build a single output row from match details."""
    date_str, home_team, away_team = _extract_match_meta(details)
    stats_dict = _extract_stats_dict(details)

    # Start with all columns as None
    row = {col: None for col in OUTPUT_COLUMNS}
    row['date'] = date_str
    row['home_team'] = home_team
    row['away_team'] = away_team
    row['league'] = league_code
    row['season'] = season

    # Map stats using STAT_MAP
    for stat_name, (home_raw, away_raw) in stats_dict.items():
        if stat_name not in STAT_MAP:
            continue
        home_col, away_col = STAT_MAP[stat_name]
        is_xg = home_col in XG_COLS

        def to_num(val, as_float):
            try:
                f = float(val)
                return f if as_float else int(f)
            except (ValueError, TypeError):
                return None

        row[home_col] = to_num(home_raw, is_xg)
        row[away_col] = to_num(away_raw, is_xg)

    return row


def run_discover(api):
    """
    Find FotMob league IDs for our 10 target leagues.
    Saves:
      data/fotmob_cache/all_leagues.csv      -- full searchable league list
      data/fotmob_cache/diagnostic.json      -- raw match detail JSON for one match
    """
    print("=== FotMob Discovery ===\n")

    # Fetch all leagues
    all_leagues_raw = api.get_league_all()

    # Flatten to list of {id, name, country} -- handle multiple response shapes
    league_rows = []

    def flatten_leagues(obj):
        if isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict):
                    lid = item.get('id') or item.get('leagueId') or item.get('league_id')
                    name = item.get('name') or item.get('leagueName') or item.get('league_name') or ''
                    country = item.get('country') or item.get('ccode') or item.get('countryCode') or ''
                    if lid and name:
                        league_rows.append({'id': str(lid), 'name': name, 'country': country})
        elif isinstance(obj, dict):
            for v in obj.values():
                if isinstance(v, (list, dict)):
                    flatten_leagues(v)

    flatten_leagues(all_leagues_raw)
    df_leagues = pd.DataFrame(league_rows).drop_duplicates(subset='id')
    df_leagues.to_csv('data/fotmob_cache/all_leagues.csv', index=False)
    print(f"Saved {len(df_leagues)} leagues to data/fotmob_cache/all_leagues.csv\n")

    # Auto-match our target leagues by name
    print("=== Auto-matched League IDs (VERIFY THESE -- update FOTMOB_LEAGUE_IDS) ===")
    first_found_id = None
    first_found_code = None
    for code, name_variants in LEAGUE_SEARCH_NAMES.items():
        mask = df_leagues['name'].str.lower().str.strip().isin(name_variants)
        matches = df_leagues[mask]
        if not matches.empty:
            for _, row in matches.iterrows():
                print(f"  {code}: id={row['id']}  name='{row['name']}' country='{row['country']}'")
            if first_found_id is None:
                first_found_id = matches.iloc[0]['id']
                first_found_code = code
        else:
            print(f"  {code}: *** NO MATCH -- search all_leagues.csv manually ***")

    # Fetch one match and dump raw JSON
    if first_found_id:
        print(f"\nFetching diagnostic match from {first_found_code} (id={first_found_id})...")
        try:
            fixtures = api.get_fixtures(first_found_id, '2024/2025')
            match_id = _extract_first_match_id(fixtures)
            if match_id:
                details = api.get_match_details(match_id)
                with open('data/fotmob_cache/diagnostic.json', 'w', encoding='utf-8') as f:
                    json.dump(details, f, indent=2, ensure_ascii=False)
                top_keys = list(details.keys()) if isinstance(details, dict) else type(details).__name__
                print(f"Saved raw JSON to data/fotmob_cache/diagnostic.json")
                print(f"Top-level keys: {top_keys}")
            else:
                print("Could not extract a match ID from fixtures response")
                with open('data/fotmob_cache/diagnostic_fixtures.json', 'w', encoding='utf-8') as f:
                    json.dump(fixtures, f, indent=2, ensure_ascii=False)
                print("Saved raw fixtures response to data/fotmob_cache/diagnostic_fixtures.json")
        except Exception as e:
            print(f"Diagnostic fetch failed: {e}")
    else:
        print("\nNo leagues matched -- open all_leagues.csv and find IDs manually")

    print("\n=== Next steps ===")
    print("1. Update FOTMOB_LEAGUE_IDS in this script with the IDs shown above")
    print("2. Open data/fotmob_cache/diagnostic.json to see the match data structure")
    print("3. Run: python experiment/load_fotmob.py --diagnose")


def run_diagnose(api):
    """
    Verify stats extraction on one match using the current FOTMOB_LEAGUE_IDS.
    Run this after --discover and after updating FOTMOB_LEAGUE_IDS.
    """
    code, league_id = next(
        ((c, lid) for c, lid in FOTMOB_LEAGUE_IDS.items() if lid is not None),
        (None, None)
    )
    if league_id is None:
        print("ERROR: No league IDs set. Run --discover first, then update FOTMOB_LEAGUE_IDS.")
        return

    print(f"Diagnosing {code} (id={league_id})...")
    fotmob_season = to_fotmob_season(code, '2024-2025' if code in PROXY_LEAGUES else '2024')
    fixtures = api.get_fixtures(league_id, fotmob_season)
    match_id = _extract_first_match_id(fixtures)
    if not match_id:
        print("Could not extract match ID. Check diagnostic_fixtures.json.")
        with open('data/fotmob_cache/diagnostic_fixtures.json', 'w') as f:
            json.dump(fixtures, f, indent=2)
        return

    print(f"Match ID: {match_id}")
    details = api.get_match_details(match_id)
    date_str, home_team, away_team = _extract_match_meta(details)
    stats_dict = _extract_stats_dict(details)

    print(f"Date: {date_str}  Home: {home_team}  Away: {away_team}")
    print(f"Stats found ({len(stats_dict)} entries):")
    for k, (h, a) in stats_dict.items():
        marker = ' checkmark' if k in STAT_MAP else ''
        print(f"  '{k}': home={h}, away={a}{marker}")

    print("\nMapped stats:")
    row = _build_row(details, 'DIAG', 'diag')
    for col in OUTPUT_COLUMNS:
        if col not in ('league', 'season'):
            print(f"  {col}: {row.get(col)}")


def scrape_league_season(api, league_code, league_id, season, output_dir, failures):
    fotmob_season = to_fotmob_season(league_code, season)

    # Fetch fixture list
    try:
        fixtures = api.get_fixtures(league_id, fotmob_season)
    except Exception as e:
        failures.append({
            'league': league_code, 'season': season,
            'match_url': 'fixtures', 'reason': str(e)
        })
        print(f"  ERROR fetching fixtures: {e}")
        return None

    match_ids = _extract_all_match_ids(fixtures)
    if not match_ids:
        failures.append({
            'league': league_code, 'season': season,
            'match_url': 'fixtures', 'reason': 'no match IDs found'
        })
        print(f"  No match IDs found")
        return None

    print(f"  {len(match_ids)} matches found")
    rows = []
    missing = 0
    for i, match_id in enumerate(match_ids):
        try:
            details = api.get_match_details(match_id)
        except Exception as e:
            failures.append({
                'league': league_code, 'season': season,
                'match_url': str(match_id), 'reason': str(e)
            })
            missing += 1
            continue

        stats_dict = _extract_stats_dict(details)
        if len(stats_dict) < 3:
            failures.append({
                'league': league_code, 'season': season,
                'match_url': str(match_id), 'reason': f'only {len(stats_dict)} stats found'
            })
            missing += 1
            # Still build a row -- it will have NaN stats but valid date/teams

        row = _build_row(details, league_code, season)
        rows.append(row)

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{len(match_ids)}]...")

    if not rows:
        return None

    # Build DataFrame -- columns were already set correctly in _build_row
    # Rename columns BEFORE reindex if needed (here they are already correct)
    df = pd.DataFrame(rows)
    df = df.reindex(columns=OUTPUT_COLUMNS)

    # Final date format pass -- always use strftime, never return raw string
    if df['date'].notna().any():
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')

    output_path = Path(output_dir) / f"{league_code}_{season}_fotmob.csv"
    df.to_csv(output_path, index=False)
    print(f"  Saved: {output_path} ({len(df)} rows, {missing} missing)")
    return df


def parse_args():
    parser = argparse.ArgumentParser(description='FotMob stats + xG loader')
    parser.add_argument('--discover', action='store_true',
                        help='Find league IDs and save diagnostic JSON')
    parser.add_argument('--diagnose', action='store_true',
                        help='Verify stats extraction on one match')
    parser.add_argument('--leagues', nargs='+',
                        help='Specific league codes (e.g. E1 SWE)')
    parser.add_argument('--seasons', nargs='+',
                        help='Specific seasons (e.g. 2022-2023 2023)')
    parser.add_argument('--proxy-only', action='store_true',
                        help='Proxy leagues only')
    parser.add_argument('--scandinavian-only', action='store_true',
                        help='Scandinavian leagues only')
    parser.add_argument('--no-cache', action='store_true',
                        help='Bypass disk cache')
    return parser.parse_args()


def main():
    args = parse_args()

    # Directories -- inside main(), never at module level
    Path('data/proxy').mkdir(parents=True, exist_ok=True)
    Path('data/scandinavian').mkdir(parents=True, exist_ok=True)
    Path('data/fotmob_cache').mkdir(parents=True, exist_ok=True)

    # Disk cache -- inside main(), never at module level
    if not args.no_cache:
        requests_cache.install_cache(
            'data/fotmob_cache/fotmob_cache',
            backend='sqlite',
            expire_after=None,
        )

    api = FotmobAPI()

    if args.discover:
        run_discover(api)
        return

    if args.diagnose:
        run_diagnose(api)
        return

    # Select leagues to run
    if args.leagues:
        league_list = args.leagues
    elif args.proxy_only:
        league_list = PROXY_LEAGUES
    elif args.scandinavian_only:
        league_list = SCAND_LEAGUES
    else:
        league_list = PROXY_LEAGUES + SCAND_LEAGUES

    # Validate: check all selected leagues have IDs set
    missing_ids = [c for c in league_list if FOTMOB_LEAGUE_IDS.get(c) is None]
    if missing_ids:
        print(f"ERROR: No FotMob ID set for: {missing_ids}")
        print("Run --discover first, then update FOTMOB_LEAGUE_IDS.")
        return

    failures = []
    total_rows = 0
    files_written = 0

    print("=== FotMob Stats Loader ===\n")
    for league_code in league_list:
        league_id = FOTMOB_LEAGUE_IDS[league_code]
        output_dir = 'data/proxy' if league_code in PROXY_LEAGUES else 'data/scandinavian'
        seasons = args.seasons if args.seasons else (
            PROXY_SEASONS if league_code in PROXY_LEAGUES else SCAND_SEASONS
        )
        for season in seasons:
            print(f"{league_code} {season}:")
            df = scrape_league_season(api, league_code, league_id, season, output_dir, failures)
            if df is not None:
                total_rows += len(df)
                files_written += 1

    # Save failure log
    if failures:
        pd.DataFrame(failures).to_csv('data/fotmob_cache/failures.csv', index=False)
        print(f"\nFailure log: data/fotmob_cache/failures.csv ({len(failures)} entries)")

    print(f"\n=== Summary ===")
    print(f"  Files written:    {files_written}")
    print(f"  Total rows:       {total_rows:,}")
    print(f"  Failures logged:  {len(failures)}")


if __name__ == '__main__':
    main()
