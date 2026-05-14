"""
Module 1 — football-data.co.uk Loader
Scandinavian Expansion experiment. Standalone — no imports from project.

Downloads match data for:
  - Proxy leagues (E1, N1, B1, P1, SC0, T1) via mmz4281 season-by-season URLs
  - Scandinavian leagues (FIN, SWE, NOR, DNK) via new/ combined-file URLs

Output: data/proxy/{league}_{season}_footballdata.csv
        data/scandinavian/{league}_{season}_footballdata.csv
"""

import io
import os
import time
import argparse
from collections import defaultdict

import requests
import pandas as pd

# === Configuration ===

PROXY_LEAGUES = {
    'E1':  'English Championship',
    'N1':  'Dutch Eredivisie',
    'B1':  'Belgian Pro League',
    'P1':  'Portuguese Primeira Liga',
    'SC0': 'Scottish Premiership',
    'T1':  'Turkish Super Lig',
}

# T1 only has data from 2017-18 onward
PROXY_LEAGUE_FIRST_SEASON = {
    'T1': '2017-18',
}

SCANDINAVIAN_LEAGUES = {
    'FIN': 'Finland Veikkausliiga',
    'SWE': 'Sweden Allsvenskan',
    'NOR': 'Norway Eliteserien',
    'DNK': 'Denmark Superliga',
}

SEASON_CODES = {
    '2000-01': '0001', '2001-02': '0102', '2002-03': '0203',
    '2003-04': '0304', '2004-05': '0405', '2005-06': '0506',
    '2006-07': '0607', '2007-08': '0708', '2008-09': '0809',
    '2009-10': '0910', '2010-11': '1011', '2011-12': '1112',
    '2012-13': '1213', '2013-14': '1314', '2014-15': '1415',
    '2015-16': '1516', '2016-17': '1617', '2017-18': '1718',
    '2018-19': '1819', '2019-20': '1920', '2020-21': '2021',
    '2021-22': '2122', '2022-23': '2223', '2023-24': '2324',
    '2024-25': '2425',
}

ALL_PROXY_SEASONS = list(SEASON_CODES.keys())

OUTPUT_SCHEMA = [
    'date', 'home_team', 'away_team',
    'home_goals', 'away_goals', 'ht_home_goals', 'ht_away_goals',
    'home_shots', 'away_shots', 'home_sot', 'away_sot',
    'home_corners', 'away_corners', 'home_fouls', 'away_fouls',
    'home_yellow', 'away_yellow', 'home_red', 'away_red',
    'odds_home', 'odds_draw', 'odds_away',
    'odds_btts_yes', 'odds_btts_no',
    'odds_over25', 'odds_under25',
    'odds_ah_line', 'odds_ah_home', 'odds_ah_away',
    'league', 'season',
]

# Raw column → output column (stats)
STATS_COLUMN_MAP = {
    'HomeTeam': 'home_team',
    'AwayTeam':  'away_team',
    'FTHG':      'home_goals',
    'FTAG':      'away_goals',
    'HTHG':      'ht_home_goals',
    'HTAG':      'ht_away_goals',
    'HS':        'home_shots',
    'AS':        'away_shots',
    'HST':       'home_sot',
    'AST':       'away_sot',
    'HC':        'home_corners',
    'AC':        'away_corners',
    'HF':        'home_fouls',
    'AF':        'away_fouls',
    'HY':        'home_yellow',
    'AY':        'away_yellow',
    'HR':        'home_red',
    'AR':        'away_red',
    'AHh':       'odds_ah_line',
}

# Odds columns: (primary, fallback, output name)
ODDS_MAP = [
    ('B365H',    'AvgH',    'odds_home'),
    ('B365D',    'AvgD',    'odds_draw'),
    ('B365A',    'AvgA',    'odds_away'),
    ('B365>2.5', 'Avg>2.5', 'odds_over25'),
    ('B365<2.5', 'Avg<2.5', 'odds_under25'),
    ('B365AHH',  'AvgAHH',  'odds_ah_home'),
    ('B365AHA',  'AvgAHA',  'odds_ah_away'),
]


# === Helpers ===

def fetch_csv(url, session):
    """Fetch a URL and return a DataFrame, or None on failure."""
    try:
        resp = session.get(url, timeout=30)
        if resp.status_code != 200:
            print(f"    WARNING: HTTP {resp.status_code} — {url}")
            return None
        if len(resp.content) < 100:
            print(f"    WARNING: Empty response — {url}")
            return None
        return pd.read_csv(io.StringIO(resp.text), encoding='utf-8-sig', low_memory=False, on_bad_lines='skip')
    except Exception as e:
        print(f"    WARNING: {e} — {url}")
        return None


def parse_dates(series):
    """Parse DD/MM/YY or DD/MM/YYYY dates to YYYY-MM-DD strings."""
    parsed = pd.to_datetime(series, dayfirst=True, errors='coerce')
    return parsed.dt.strftime('%Y-%m-%d')


def apply_column_map(df):
    """Rename raw columns to output schema names."""
    rename = {k: v for k, v in STATS_COLUMN_MAP.items() if k in df.columns}
    return df.rename(columns=rename)


def resolve_odds(df):
    """Apply primary→fallback odds logic and rename to output names."""
    for primary, fallback, output_name in ODDS_MAP:
        if primary in df.columns:
            col = pd.to_numeric(df[primary], errors='coerce')
            if fallback in df.columns:
                col = col.fillna(pd.to_numeric(df[fallback], errors='coerce'))
            df[output_name] = col
        elif fallback in df.columns:
            df[output_name] = pd.to_numeric(df[fallback], errors='coerce')
        else:
            df[output_name] = pd.NA
    return df


def to_output_schema(df, league, season):
    """Final cleanup: set metadata columns, reindex to output schema."""
    df['date'] = parse_dates(df['Date']) if 'Date' in df.columns else pd.NA
    df['league'] = league
    df['season'] = season
    df['odds_btts_yes'] = pd.NA
    df['odds_btts_no'] = pd.NA
    df = apply_column_map(df)
    df = resolve_odds(df)
    return df.reindex(columns=OUTPUT_SCHEMA)


def save(df, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


def normalize_scand_season(season_str):
    """'2023/2024' → '2023', '2023' → '2023'."""
    s = str(season_str)
    return s.split('/')[0].strip()


# === Main processors ===

def process_proxy_league(league_code, seasons, session, output_dir, failed):
    total_rows = 0
    first_season = PROXY_LEAGUE_FIRST_SEASON.get(league_code)
    season_list = list(SEASON_CODES.keys())

    for season in seasons:
        # Respect per-league start date
        if first_season and season_list.index(season) < season_list.index(first_season):
            continue

        url = f"https://www.football-data.co.uk/mmz4281/{SEASON_CODES[season]}/{league_code}.csv"
        print(f"    Fetching {league_code} {season}...", end=' ', flush=True)
        df = fetch_csv(url, session)

        if df is None:
            failed.append(f"{league_code} {season}")
            print("FAILED")
            time.sleep(1.5)
            continue

        df = df.dropna(subset=['Date', 'HomeTeam', 'AwayTeam'])
        if df.empty:
            print("0 rows (skipped)")
            time.sleep(1.5)
            continue

        df = to_output_schema(df, league_code, season)
        path = os.path.join(output_dir, f"{league_code}_{season}_footballdata.csv")
        save(df, path)
        rows = len(df)
        total_rows += rows
        print(f"{rows} rows")
        time.sleep(1.5)

    return total_rows


def normalise_new_format_columns(df):
    """
    football-data.co.uk 'new' format uses different column names.
    Rename them to match the standard proxy format so the rest of the
    pipeline can treat both identically.

    Key differences in new format:
    - Team columns: Home/Away instead of HomeTeam/AwayTeam
    - Goals: HG/AG instead of FTHG/FTAG
    - Odds: B365CH/AvgCH etc. (closing) instead of B365H/AvgH
    - No O/U or AH odds available — those stay NaN
    """
    rename = {
        'Home':   'HomeTeam',
        'Away':   'AwayTeam',
        'HG':     'FTHG',
        'AG':     'FTAG',
        'Res':    'FTR',
        # Closing 1X2 odds → standard names our ODDS_MAP expects
        'B365CH': 'B365H',
        'B365CD': 'B365D',
        'B365CA': 'B365A',
        'AvgCH':  'AvgH',
        'AvgCD':  'AvgD',
        'AvgCA':  'AvgA',
    }
    return df.rename(columns={k: v for k, v in rename.items() if k in df.columns})


def process_scandinavian_league(league_code, session, output_dir, failed):
    url = f"https://www.football-data.co.uk/new/{league_code}.csv"
    print(f"    Fetching {league_code} (all seasons)...", end=' ', flush=True)
    df = fetch_csv(url, session)

    if df is None:
        failed.append(league_code)
        print("FAILED")
        return 0

    if 'Season' not in df.columns:
        print("WARNING: no Season column — cannot split")
        failed.append(f"{league_code} (no Season column)")
        return 0

    # Normalise column names from new format to standard format
    df = normalise_new_format_columns(df)

    df = df.dropna(subset=['Date', 'HomeTeam', 'AwayTeam'])
    seasons = df['Season'].unique()
    print(f"splitting into {len(seasons)} season files")

    total_rows = 0
    for raw_season in seasons:
        season_label = normalize_scand_season(raw_season)
        sdf = df[df['Season'] == raw_season].copy()
        if sdf.empty:
            continue
        sdf = to_output_schema(sdf, league_code, season_label)
        path = os.path.join(output_dir, f"{league_code}_{season_label}_footballdata.csv")
        save(sdf, path)
        rows = len(sdf)
        total_rows += rows
        print(f"      {season_label}: {rows} rows")

    return total_rows


# === Validation ===

def validate(proxy_dir, scand_dir):
    print("\n=== Validation ===")

    def load_dir(d):
        files = []
        if os.path.exists(d):
            for f in sorted(os.listdir(d)):
                if f.endswith('.csv'):
                    files.append(os.path.join(d, f))
        return files

    proxy_files = load_dir(proxy_dir)
    scand_files = load_dir(scand_dir)
    all_files = proxy_files + scand_files

    if not all_files:
        print("  No output files found.")
        return

    # 1. Row count sanity
    print("\n  Row count (files with <100 rows flagged):")
    for f in all_files:
        df = pd.read_csv(f)
        label = os.path.basename(f).replace('_footballdata.csv', '')
        if len(df) < 100:
            print(f"    ⚠  {label}: {len(df)} rows")

    # 2. Shot data coverage per league
    print("\n  Shot data coverage (% of rows with home_shots not null):")
    shot_by_league = defaultdict(list)
    for f in all_files:
        df = pd.read_csv(f)
        league = os.path.basename(f).split('_')[0]
        if 'home_shots' in df.columns and len(df) > 0:
            pct = df['home_shots'].notna().mean() * 100
            shot_by_league[league].append(pct)
    for league, pcts in sorted(shot_by_league.items()):
        print(f"    {league}: {sum(pcts)/len(pcts):.0f}% avg across {len(pcts)} seasons")

    # 3. Odds coverage per league
    print("\n  Odds coverage (% of rows with odds_home not null):")
    odds_by_league = defaultdict(list)
    for f in all_files:
        df = pd.read_csv(f)
        league = os.path.basename(f).split('_')[0]
        if 'odds_home' in df.columns and len(df) > 0:
            pct = df['odds_home'].notna().mean() * 100
            odds_by_league[league].append(pct)
    for league, pcts in sorted(odds_by_league.items()):
        print(f"    {league}: {sum(pcts)/len(pcts):.0f}% avg")

    # 4. Date range per league
    print("\n  Date range per league:")
    dates_by_league = defaultdict(list)
    for f in all_files:
        df = pd.read_csv(f)
        league = os.path.basename(f).split('_')[0]
        if 'date' in df.columns:
            dates = pd.to_datetime(df['date'], errors='coerce').dropna()
            if not dates.empty:
                dates_by_league[league].append((dates.min(), dates.max()))
    for league, ranges in sorted(dates_by_league.items()):
        earliest = min(r[0] for r in ranges)
        latest   = max(r[1] for r in ranges)
        print(f"    {league}: {earliest.date()} → {latest.date()}")

    print(f"\n  Proxy files: {len(proxy_files)}")
    print(f"  Scandinavian files: {len(scand_files)}")


# === Entry point ===

def main():
    parser = argparse.ArgumentParser(description='Download football-data.co.uk match CSVs')
    parser.add_argument('--leagues', nargs='+', help='Proxy league codes to download (default: all)')
    parser.add_argument('--seasons', nargs='+', help='Seasons to download, e.g. 2022-23 (default: all)')
    parser.add_argument('--proxy-only', action='store_true')
    parser.add_argument('--scandinavian-only', action='store_true')
    args = parser.parse_args()

    if args.proxy_only and args.scandinavian_only:
        print("Error: cannot use --proxy-only and --scandinavian-only together.")
        return

    proxy_dir = os.path.join('data', 'proxy')
    scand_dir = os.path.join('data', 'scandinavian')

    proxy_leagues = args.leagues if args.leagues else list(PROXY_LEAGUES.keys())
    seasons       = args.seasons if args.seasons else ALL_PROXY_SEASONS

    session  = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    failed   = []
    proxy_rows = 0
    scand_rows = 0

    print("=== football-data.co.uk Loader ===\n")

    if not args.scandinavian_only:
        print("Fetching proxy leagues...")
        for code in proxy_leagues:
            if code not in PROXY_LEAGUES:
                print(f"  Unknown league code: {code} — skipping")
                continue
            print(f"  {code} ({PROXY_LEAGUES[code]}):")
            proxy_rows += process_proxy_league(code, seasons, session, proxy_dir, failed)

    if not args.proxy_only:
        print("\nFetching Scandinavian leagues...")
        for code in SCANDINAVIAN_LEAGUES:
            print(f"  {code} ({SCANDINAVIAN_LEAGUES[code]}):")
            scand_rows += process_scandinavian_league(code, session, scand_dir, failed)
            time.sleep(1.5)

    print(f"\n=== Summary ===")
    print(f"  Proxy rows downloaded:       {proxy_rows:,}")
    print(f"  Scandinavian rows downloaded: {scand_rows:,}")
    if failed:
        print(f"  Failed downloads ({len(failed)}):")
        for f in failed:
            print(f"    - {f}")
    else:
        print(f"  Failed downloads: none")

    validate(proxy_dir, scand_dir)


if __name__ == '__main__':
    main()
