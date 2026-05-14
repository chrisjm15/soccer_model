"""
Module 2 — FBref Match Stats Loader
Scandinavian Expansion experiment. Standalone — no imports from project.

Scrapes per-match basic stats (shots, SoT, corners, fouls, cards) from FBref
for proxy leagues and Scandinavian target leagues.

FBref uses Cloudflare protection that blocks automated requests. This script
handles it with a one-time manual step:
  1. A visible browser opens and loads FBref
  2. You solve the "I'm not a robot" challenge (one click)
  3. Script extracts the session cookie and continues automatically
  4. All subsequent pages use that cookie via requests (fast, cacheable)
"""

import argparse
import csv
import os
import time
from datetime import datetime

import pandas as pd
import requests
import requests_cache
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ── League definitions ──────────────────────────────────────────────────────

PROXY_LEAGUES = [
    {'fd_code': 'E1',  'fbref_comp_id': 10,  'season_format': 'european', 'name': 'Championship'},
    {'fd_code': 'N1',  'fbref_comp_id': 23,  'season_format': 'european', 'name': 'Eredivisie'},
    {'fd_code': 'B1',  'fbref_comp_id': 37,  'season_format': 'european', 'name': 'Pro League'},
    {'fd_code': 'P1',  'fbref_comp_id': 32,  'season_format': 'european', 'name': 'Primeira Liga'},
    {'fd_code': 'SC0', 'fbref_comp_id': 40,  'season_format': 'european', 'name': 'Premiership'},
    {'fd_code': 'T1',  'fbref_comp_id': 26,  'season_format': 'european', 'name': 'Süper Lig'},
]

SCAND_LEAGUES = [
    {'fd_code': 'SWE', 'fbref_comp_id': 25,  'season_format': 'calendar', 'name': 'Allsvenskan'},
    {'fd_code': 'NOR', 'fbref_comp_id': 28,  'season_format': 'calendar', 'name': 'Eliteserien'},
    {'fd_code': 'DNK', 'fbref_comp_id': 50,  'season_format': 'european', 'name': 'Superliga'},
    {'fd_code': 'FIN', 'fbref_comp_id': 129, 'season_format': 'calendar', 'name': 'Veikkausliiga'},
]

# Seasons by format — only european-format seasons for european leagues, etc.
PROXY_SEASONS = [
    '2014-2015', '2015-2016', '2016-2017', '2017-2018', '2018-2019',
    '2019-2020', '2020-2021', '2021-2022', '2022-2023', '2023-2024', '2024-2025',
]
SCAND_SEASONS = [
    '2014', '2015', '2016', '2017', '2018', '2019',
    '2020', '2021', '2022', '2023', '2024', '2025',
]

# Output schema — column order enforced at save time
OUTPUT_SCHEMA = [
    'date', 'home_team', 'away_team',
    'home_shots', 'away_shots',
    'home_sot',   'away_sot',
    'home_corners', 'away_corners',
    'home_fouls',   'away_fouls',
    'home_yellow',  'away_yellow',
    'league', 'season',
]

# FBref stat label → (home_col, away_col)
STAT_MAPPING = {
    'shots on target': ('home_sot',     'away_sot'),
    'shots':           ('home_shots',   'away_shots'),
    'fouls':           ('home_fouls',   'away_fouls'),
    'corners':         ('home_corners', 'away_corners'),
    'yellow cards':    ('home_yellow',  'away_yellow'),
    'red cards':       ('home_red',     'away_red'),
}


# ── Cloudflare bypass — solve once, scrape with cookie ───────────────────────

FBREF_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept':          'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer':         'https://fbref.com/',
}


def get_cloudflare_cookies():
    """
    Open a visible browser, wait for the user to solve the Cloudflare challenge,
    then extract and return the session cookies as a dict.

    Only called once at startup. The resulting cookies are reused for every
    subsequent requests.get() call.
    """
    print("\n" + "="*60)
    print("CLOUDFLARE CHALLENGE")
    print("="*60)
    print("A browser window is about to open.")
    print("If you see 'Verify you are human', click the checkbox.")
    print("Once the FBref page loads fully, come back here")
    print("and press ENTER to continue.")
    print("="*60 + "\n")

    cookies = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=FBREF_HEADERS['User-Agent'],
            locale='en-US',
        )
        page = context.new_page()
        page.goto('https://fbref.com/en/', timeout=60000)

        # Poll until Cloudflare clears (title changes from "Just a moment...")
        for _ in range(30):
            title = page.title()
            if 'just a moment' not in title.lower():
                print(f"  Browser cleared. Page title: {title}")
                break
            time.sleep(2)
        else:
            # Fallback: let the user signal manually
            input("  (Auto-detect timed out) Press ENTER once the FBref page has loaded: ")

        # Extract cookies from the browser session
        for cookie in context.cookies():
            cookies[cookie['name']] = cookie['value']

        browser.close()

    if 'cf_clearance' not in cookies:
        print("  WARNING: cf_clearance cookie not found. Scraping may still fail.")
    else:
        print("  cf_clearance cookie obtained. Proceeding with requests.\n")

    return cookies


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def fetch(session, url, delay_secs=5):
    """
    Fetch a URL using a requests.Session (with Cloudflare cookies pre-loaded).
    Sleeps only on live (non-cached) responses.
    Retries once on 429/503.
    """
    try:
        resp = session.get(url, timeout=30)
        if resp.status_code in (429, 503):
            print(f"    Rate limit ({resp.status_code}), waiting 30s and retrying...")
            time.sleep(30)
            resp = session.get(url, timeout=30)
        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}"
        if not getattr(resp, 'from_cache', False):
            time.sleep(delay_secs)
        return resp, None
    except Exception as e:
        return None, str(e)


def make_session(cookies):
    """
    Build a requests.Session with Cloudflare cookies and browser headers.
    requests_cache is already installed globally, so this session is
    automatically cached.
    """
    session = requests.Session()
    session.headers.update(FBREF_HEADERS)
    session.cookies.update(cookies)
    return session


# ── Schedule page parsing ────────────────────────────────────────────────────

def get_matches_from_schedule(session, comp_id, season):
    """
    Fetch the FBref schedule page and return a list of dicts:
      {date, home_team, away_team, match_url}

    Date and teams are taken directly from the schedule table — cleaner and
    more reliable than re-parsing the match report scorebox.
    Returns (matches, error_message).
    """
    url = f"https://fbref.com/en/comps/{comp_id}/{season}/schedule/"
    resp, err = fetch(session, url, delay_secs=3)
    if err:
        return [], err

    soup = BeautifulSoup(resp.text, 'lxml')
    table = soup.find('table', id=lambda x: x and x.startswith('sched_'))
    if not table:
        return [], "No schedule table found on page"

    matches = []
    for row in table.find('tbody').find_all('tr'):
        # Skip spacer rows
        if row.get('class') and 'spacer' in ' '.join(row.get('class', [])):
            continue

        date_cell   = row.find('td', {'data-stat': 'date'})
        home_cell   = row.find('td', {'data-stat': 'home_team'})
        away_cell   = row.find('td', {'data-stat': 'away_team'})
        report_cell = row.find('td', {'data-stat': 'match_report'})

        if not all([date_cell, home_cell, away_cell, report_cell]):
            continue

        report_link = report_cell.find('a')
        if not report_link:
            continue  # Unplayed match — no report yet

        link_text = report_link.get_text(strip=True)
        if link_text.lower() in ('head-to-head', ''):
            continue  # Not a real match report

        raw_date = date_cell.get_text(strip=True)
        date_str = parse_fbref_date(raw_date)
        if not date_str:
            continue  # Unparseable date → skip

        matches.append({
            'date':      date_str,
            'home_team': home_cell.get_text(strip=True),
            'away_team': away_cell.get_text(strip=True),
            'match_url': 'https://fbref.com' + report_link['href'],
        })

    return matches, None


def parse_fbref_date(raw):
    """
    Convert FBref date strings to YYYY-MM-DD.
    FBref schedule tables typically use ISO format: '2022-08-05'
    but occasionally use other formats. Handle both.
    """
    raw = raw.strip()
    if not raw:
        return None
    for fmt in ('%Y-%m-%d', '%B %d, %Y', '%d %B %Y'):
        try:
            return datetime.strptime(raw, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    # Last resort: try pandas
    try:
        return pd.to_datetime(raw, dayfirst=False).strftime('%Y-%m-%d')
    except Exception:
        return None


# ── Match report parsing ─────────────────────────────────────────────────────

def extract_team_stats(soup):
    """
    Extract the team stats table from a match report page.
    Returns a dict of our output column names → integer values, or None.

    FBref match reports have a div#team_stats (or div#div_team_stats) that
    contains a table with rows like:
        <strong>5</strong>  Shots on Target  <strong>3</strong>
    """
    stats_div = soup.find('div', id='div_team_stats') or soup.find('div', id='team_stats')
    if not stats_div:
        return None

    stats = {}
    rows = stats_div.find_all('tr')
    if len(rows) < 3:
        return None

    for row in rows:
        strong_tags = row.find_all('strong')
        if len(strong_tags) != 2:
            continue

        row_text = row.get_text(separator=' ').lower().strip()
        home_val = strong_tags[0].get_text(strip=True)
        away_val = strong_tags[1].get_text(strip=True)

        for label, (home_col, away_col) in STAT_MAPPING.items():
            if label in row_text:
                try:
                    stats[home_col] = int(home_val)
                    stats[away_col] = int(away_val)
                except ValueError:
                    stats[home_col] = None
                    stats[away_col] = None
                break

    if len(stats) < 4:   # Fewer than 2 stat pairs found — not a real stats table
        return None

    return stats


# ── Discovery mode ───────────────────────────────────────────────────────────

def run_discovery(session, leagues):
    print("=== FBref League Discovery ===\n")
    for league in leagues:
        comp_id = league['fbref_comp_id']
        fd_code = league['fd_code']
        name    = league['name']
        # Use a recent season for the test
        season = '2022-2023' if league['season_format'] == 'european' else '2023'
        url = f"https://fbref.com/en/comps/{comp_id}/{season}/schedule/"
        print(f"Checking comp {comp_id} ({fd_code}/{name})...")
        resp, err = fetch(session, url, delay_secs=2)
        if err:
            print(f"  FAILED: {err}\n")
            continue
        soup = BeautifulSoup(resp.text, 'lxml')
        title = soup.find('title')
        print(f"  Title: {title.get_text(strip=True) if title else '(no title)'}")
        matches, merr = get_matches_from_schedule(session, comp_id, season)
        if merr:
            print(f"  Schedule error: {merr}")
        elif matches:
            m = matches[0]
            print(f"  First match: {m['date']}  {m['home_team']} vs {m['away_team']} ✓")
            print(f"  Total matches found: {len(matches)}")
        else:
            print(f"  No matches found — comp ID may be wrong")
        print()
    print("=== Discovery Complete ===")


# ── Main scrape loop ─────────────────────────────────────────────────────────

def seasons_for_league(league, season_filter):
    """Return the correct season list for a league, optionally filtered by CLI args."""
    base = PROXY_SEASONS if league['season_format'] == 'european' else SCAND_SEASONS
    if season_filter:
        return [s for s in base if s in season_filter]
    return base


def main(args):
    # Create cache directory first, then initialise cache
    os.makedirs('data/fbref_cache', exist_ok=True)
    os.makedirs('data/proxy', exist_ok=True)
    os.makedirs('data/scandinavian', exist_ok=True)

    if args.no_cache:
        db = 'data/fbref_cache/fbref_cache.sqlite'
        if os.path.exists(db):
            os.remove(db)
            print("Cache cleared.\n")

    requests_cache.install_cache('data/fbref_cache/fbref_cache', backend='sqlite')

    # Solve Cloudflare challenge once, then use the cookie for all requests
    cf_cookies = get_cloudflare_cookies()
    session = make_session(cf_cookies)

    # Select leagues
    if args.proxy_only:
        leagues = PROXY_LEAGUES
    elif args.scandinavian_only:
        leagues = SCAND_LEAGUES
    else:
        leagues = PROXY_LEAGUES + SCAND_LEAGUES

    if args.leagues:
        leagues = [l for l in leagues if l['fd_code'] in args.leagues]

    # Discovery mode — just verify comp IDs, no data saved
    if args.discover:
        run_discovery(session, leagues)
        return

    print("=== FBref Stats Loader ===\n")

    failures        = []
    total_matches   = 0
    total_missing   = 0
    cache_hits      = 0
    live_requests   = 0

    for league in leagues:
        fd_code   = league['fd_code']
        comp_id   = league['fbref_comp_id']
        is_scand  = league in SCAND_LEAGUES
        out_dir   = 'data/scandinavian' if is_scand else 'data/proxy'

        seasons = seasons_for_league(league, args.seasons)

        for season in seasons:
            print(f"{fd_code} {season} ({league['name']}):")

            matches, err = get_matches_from_schedule(session, comp_id, season)
            if err:
                print(f"  Schedule error: {err}")
                failures.append({'league': fd_code, 'season': season,
                                  'match_url': f"schedule/{comp_id}/{season}",
                                  'reason': err})
                continue
            if not matches:
                print(f"  No matches found (season may not exist on FBref)")
                continue

            print(f"  Schedule: {len(matches)} matches found")

            rows = []
            for i, match in enumerate(matches):
                resp, err = fetch(session, match['match_url'])
                if err:
                    failures.append({'league': fd_code, 'season': season,
                                      'match_url': match['match_url'], 'reason': err})
                    total_missing += 1
                    continue

                if getattr(resp, 'from_cache', False):
                    cache_hits += 1
                else:
                    live_requests += 1

                soup  = BeautifulSoup(resp.text, 'lxml')
                stats = extract_team_stats(soup)

                if not stats:
                    failures.append({'league': fd_code, 'season': season,
                                      'match_url': match['match_url'],
                                      'reason': 'No team stats div found'})
                    total_missing += 1
                    continue

                row = {
                    'date':      match['date'],
                    'home_team': match['home_team'],
                    'away_team': match['away_team'],
                    'league':    fd_code,
                    'season':    season,
                }
                row.update(stats)
                rows.append(row)

                if (i + 1) % 50 == 0:
                    print(f"  {i + 1}/{len(matches)} processed...")

            total_matches += len(matches)

            if rows:
                df = pd.DataFrame(rows).reindex(columns=OUTPUT_SCHEMA)
                out_path = os.path.join(out_dir, f"{fd_code}_{season}_fbref.csv")
                df.to_csv(out_path, index=False)
                print(f"  Saved: {out_path} ({len(df)} rows, {total_missing} missing stats)\n")
            else:
                print(f"  No data saved for {fd_code} {season}\n")

    # Summary
    print("=== Summary ===")
    print(f"  Total matches attempted: {total_matches:,}")
    print(f"  Missing stats:           {total_missing:,}")
    print(f"  Cache hits:              {cache_hits:,}")
    print(f"  Live requests:           {live_requests:,}")

    if failures:
        fail_path = 'data/fbref_cache/failures.csv'
        with open(fail_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['league', 'season', 'match_url', 'reason'])
            writer.writeheader()
            writer.writerows(failures)
        print(f"  Failures ({len(failures)}): saved to {fail_path}")
    else:
        print(f"  Failures: none")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='FBref Match Stats Loader')
    parser.add_argument('--discover',          action='store_true', help='Verify comp IDs only, no data saved')
    parser.add_argument('--leagues',           nargs='+',           help='League FD codes, e.g. E1 SWE')
    parser.add_argument('--seasons',           nargs='+',           help='Seasons, e.g. 2022-2023 2023')
    parser.add_argument('--proxy-only',        action='store_true')
    parser.add_argument('--scandinavian-only', action='store_true')
    parser.add_argument('--no-cache',          action='store_true', help='Clear cache and re-fetch everything')
    args = parser.parse_args()
    main(args)
