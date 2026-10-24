import requests
import time
import pandas as pd
from datetime import datetime, timezone, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed — fall back to system environment variables


def fetch_league_odds(
    api_key: str,
    sport_key: str,
    league_name: str,
    regions: str = 'uk'
) -> list[dict]:
    """
    Fetches upcoming over/under 2.5 goals odds for one league.
    Returns list of match dicts with odds data.
    Logs remaining API credits after the call.

    Note: The free API tier supports the 'totals' (over/under) market but not 'btts'.
    We use over 2.5 goals odds as the comparable market for our Poisson model predictions.
    """
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        'apiKey': api_key,
        'regions': regions,
        'markets': 'totals',
        'dateFormat': 'iso',
        'oddsFormat': 'decimal'
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        remaining = response.headers.get('X-Requests-Remaining')
        if remaining:
            print(f"  [{league_name}] API credits remaining: {remaining}")

        data = response.json()
        matches = []
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=7)

        for match in data:
            commence_time = match.get('commence_time')
            if not commence_time:
                continue
            commence_dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
            if commence_dt > cutoff:
                continue  # Skip fixtures beyond 7-day window
            date = commence_dt.date().isoformat()

            over25_prices = []
            under25_prices = []
            bookmakers_count = 0

            for bookmaker in match.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    if market.get('key') != 'totals':
                        continue

                    over_price = None
                    under_price = None
                    for outcome in market.get('outcomes', []):
                        # Only use the 2.5 line (ignore 1.5, 3.5, etc.)
                        if outcome.get('point') != 2.5:
                            continue
                        name = outcome.get('name')
                        price = outcome.get('price')
                        if name == 'Over' and price is not None:
                            over_price = price
                        elif name == 'Under' and price is not None:
                            under_price = price

                    if over_price is not None and under_price is not None:
                        over25_prices.append(over_price)
                        under25_prices.append(under_price)
                        bookmakers_count += 1

            if not over25_prices:
                continue

            matches.append({
                'date': date,
                'league': league_name,
                'home_team': match.get('home_team'),
                'away_team': match.get('away_team'),
                'over25_odds': sum(over25_prices) / len(over25_prices),
                'under25_odds': sum(under25_prices) / len(under25_prices),
                'over25_odds_best': max(over25_prices),
                'n_bookmakers': bookmakers_count
            })

        return matches

    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            print(f"ERROR: Invalid API key for {league_name}")
        elif response.status_code == 422:
            msg = response.json().get('message', str(e))
            print(f"ERROR: {league_name} — {msg}")
        else:
            print(f"ERROR: HTTP {response.status_code} for {league_name}: {e}")
        return []
    except Exception as e:
        print(f"ERROR: Failed to fetch odds for {league_name}: {e}")
        return []


def fetch_all_leagues_odds(
    api_key: str,
    leagues_config: dict,
    delay_seconds: float = 1.0
) -> pd.DataFrame:
    """
    Fetches upcoming over/under 2.5 goals odds for all leagues.

    Args:
        api_key: The Odds API key
        leagues_config: dict loaded from leagues.yaml, keyed by league name.
                        Each league must have an 'odds_api_sport_key' field.
        delay_seconds: Wait time between league API calls (default 1s)

    Returns:
        DataFrame with columns: date, league, home_team, away_team,
        over25_odds, under25_odds, over25_odds_best, n_bookmakers
    """
    all_matches = []

    for league_name, league_info in leagues_config.items():
        sport_key = league_info.get('odds_api_sport_key')
        if not sport_key:
            print(f"WARNING: No sport key found for {league_name}, skipping...")
            continue

        print(f"Fetching odds for {league_name}...")
        matches = fetch_league_odds(api_key, sport_key, league_name)
        all_matches.extend(matches)
        time.sleep(delay_seconds)

    if not all_matches:
        return pd.DataFrame()

    return pd.DataFrame(all_matches)


from model.calibration import select_main_line

AU_BOOKMAKERS = {
    'bet365_au', 'betfair_ex_au', 'betr_au', 'betright', 'bluebet', 'boombet',
    'dabble_au', 'ladbrokes_au', 'neds', 'palmerbet', 'playup', 'pointsbetau',
    'sportsbet', 'tab', 'tabtouch', 'topsport', 'unibet', 'unibet_au'
}


def fetch_epl_ah_odds(
    api_key: str,
    sport_key: str,
    league_name: str,
    regions: str = 'uk,au,eu'
) -> list[dict]:
    """
    Fetches upcoming Asian Handicap (spreads) odds for one league.
    Returns list of match dicts with AH odds data on the main Asian line.
    Prints raw first-match bookmaker data to verify AH fields are present.
    """
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        'apiKey': api_key,
        'regions': regions,
        'markets': 'spreads',
        'dateFormat': 'iso',
        'oddsFormat': 'decimal'
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        remaining = response.headers.get('X-Requests-Remaining')
        if remaining:
            print(f"  [{league_name}] API credits remaining: {remaining}")

        data = response.json()

        all_bookmaker_keys = set()
        for m in data:
            for b in m.get('bookmakers', []):
                all_bookmaker_keys.add(b.get('key'))
        bet365_present = any(str(k).startswith('bet365') for k in all_bookmaker_keys if k)
        print(f"  [The Odds API] bet365 present in response: {bet365_present}")

        # Print raw first match for verification
        if data:
            first = data[0]
            print(f"\n  [DEBUG] Raw AH fields from first API match ({first.get('home_team')} vs {first.get('away_team')}):")
            bookmakers = first.get('bookmakers', [])
            if bookmakers:
                bk = bookmakers[0]
                print(f"    Bookmaker: {bk.get('key')}")
                for mkt in bk.get('markets', []):
                    print(f"    Market key: {mkt.get('key')}")
                    for oc in mkt.get('outcomes', [])[:4]:
                        print(f"      {oc.get('name')}: price={oc.get('price')}, point={oc.get('point')}")
            else:
                print(f"    No bookmakers returned for this match")
            print()

        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=7)
        matches = []

        for match in data:
            commence_time = match.get('commence_time')
            if not commence_time:
                continue
            commence_dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
            if commence_dt > cutoff:
                continue
            match_date = commence_dt.date().isoformat()

            home_name = match.get('home_team')
            away_name = match.get('away_team')

            # Collect AH prices per line: {line: {'book_prices': [(home_p, away_p)], 'bookmakers': [key]}}
            ah_data = {}
            for bookmaker in match.get('bookmakers', []):
                bk_key = bookmaker.get('key')
                for market in bookmaker.get('markets', []):
                    if market.get('key') != 'spreads':
                        continue
                    outcomes = market.get('outcomes', [])
                    home_oc = next((o for o in outcomes if o.get('name') == home_name), None)
                    away_oc = next((o for o in outcomes if o.get('name') == away_name), None)
                    if not home_oc or not away_oc:
                        continue
                    line = home_oc.get('point')
                    if line is None:
                        continue
                    h_price = home_oc.get('price')
                    a_price = away_oc.get('price')
                    if h_price is None or a_price is None:
                        continue
                    line = float(line)
                    if line not in ah_data:
                        ah_data[line] = {'book_prices': [], 'bookmakers': []}
                    ah_data[line]['book_prices'].append((float(h_price), float(a_price)))
                    ah_data[line]['bookmakers'].append(bk_key)

            if not ah_data:
                continue

            # Select the main Asian line (consensus no-vig closest to 0.5)
            line_to_prices = {l: info['book_prices'] for l, info in ah_data.items()}
            main_line, _ = select_main_line(line_to_prices)
            pairs = ah_data[main_line]['book_prices']
            bks = ah_data[main_line]['bookmakers']

            best_home_idx = max(range(len(pairs)), key=lambda i: pairs[i][0])
            best_away_idx = max(range(len(pairs)), key=lambda i: pairs[i][1])
            odds_ah_home_best = pairs[best_home_idx][0]
            odds_ah_away_best = pairs[best_away_idx][1]
            best_home_book = bks[best_home_idx]
            best_away_book = bks[best_away_idx]

            au_pairs = [
                pairs[i] for i, bk in enumerate(bks)
                if bk in AU_BOOKMAKERS or str(bk).endswith('_au')
            ]
            if au_pairs:
                best_au_home = max(p[0] for p in au_pairs)
                best_au_away = max(p[1] for p in au_pairs)
            else:
                best_au_home = ''
                best_au_away = ''

            matches.append({
                'date': match_date,
                'league': league_name,
                'home_team': home_name,
                'away_team': away_name,
                'ah_line': float(main_line),
                'odds_ah_home_best': odds_ah_home_best,
                'odds_ah_away_best': odds_ah_away_best,
                'best_home_book': best_home_book,
                'best_away_book': best_away_book,
                'best_au_home': best_au_home,
                'best_au_away': best_au_away,
                'book_prices': pairs,
                'bookmakers': bks,
                'n_bookmakers': len(pairs)
            })

        return matches

    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            print(f"ERROR: Invalid API key for {league_name}")
        elif response.status_code == 422:
            msg = response.json().get('message', str(e))
            print(f"ERROR: {league_name} — {msg}")
        else:
            print(f"ERROR: HTTP {response.status_code} for {league_name}: {e}")
        return []
    except Exception as e:
        print(f"ERROR: Failed to fetch AH odds for {league_name}: {e}")
        return []


if __name__ == '__main__':
    import yaml
    import os

    with open('config/leagues.yaml', 'r') as f:
        config = yaml.safe_load(f)

    api_key = os.environ.get('ODDS_API_KEY')
    if not api_key:
        print("ERROR: Set the ODDS_API_KEY environment variable first.")
        print("  Windows PowerShell: $env:ODDS_API_KEY = 'your_key_here'")
        exit(1)

    leagues = config['leagues']
    df = fetch_all_leagues_odds(api_key, leagues)

    if df.empty:
        print("No upcoming matches found (leagues may be between gameweeks).")
    else:
        print(f"\nFound {len(df)} upcoming matches with over/under 2.5 odds:")
        print(df.to_string(index=False))
