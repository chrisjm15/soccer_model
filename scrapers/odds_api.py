import requests
import time
import pandas as pd
from datetime import datetime

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
    Fetches upcoming BTTS odds for one league.
    Returns list of match dicts with odds data.
    Logs remaining API credits after the call.
    """
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        'apiKey': api_key,
        'regions': regions,
        'markets': 'btts',
        'dateFormat': 'iso',
        'oddsFormat': 'decimal'
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        # Log remaining credits
        remaining = response.headers.get('X-Requests-Remaining')
        if remaining:
            print(f"API credits remaining after {league_name}: {remaining}")

        data = response.json()
        matches = []

        for match in data:
            # Extract date from commence_time
            commence_time = match.get('commence_time')
            if not commence_time:
                continue
            date = datetime.fromisoformat(
                commence_time.replace('Z', '+00:00')
            ).date().isoformat()

            # Collect BTTS odds from bookmakers
            btts_yes_prices = []
            btts_no_prices = []
            bookmakers_count = 0

            for bookmaker in match.get('bookmakers', []):
                # Find BTTS market
                btts_market = None
                for market in bookmaker.get('markets', []):
                    if market.get('key') == 'btts':
                        btts_market = market
                        break

                if not btts_market:
                    continue

                # Extract Yes and No prices
                yes_price = None
                no_price = None
                for outcome in btts_market.get('outcomes', []):
                    name = outcome.get('name')
                    price = outcome.get('price')
                    if name == 'Yes' and price is not None:
                        yes_price = price
                    elif name == 'No' and price is not None:
                        no_price = price

                # Only count bookmaker if both prices are available
                if yes_price is not None and no_price is not None:
                    btts_yes_prices.append(yes_price)
                    btts_no_prices.append(no_price)
                    bookmakers_count += 1

            # Skip matches with no valid bookmakers
            if not btts_yes_prices or not btts_no_prices:
                continue

            matches.append({
                'date': date,
                'league': league_name,
                'home_team': match.get('home_team'),
                'away_team': match.get('away_team'),
                'btts_odds_yes': sum(btts_yes_prices) / len(btts_yes_prices),
                'btts_odds_no': sum(btts_no_prices) / len(btts_no_prices),
                'btts_odds_yes_best': max(btts_yes_prices),
                'n_bookmakers': bookmakers_count
            })

        return matches

    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            print(f"ERROR: Invalid API key for {league_name}")
        elif response.status_code == 422:
            print(f"ERROR: Invalid sport key '{sport_key}' for {league_name}")
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
    Fetches upcoming BTTS odds for all leagues.

    Args:
        api_key: The Odds API key
        leagues_config: dict loaded from leagues.yaml, keyed by league name.
                        Each league must have an 'odds_api_sport_key' field.
        delay_seconds: Wait time between league API calls (default 1s)

    Returns:
        DataFrame with columns: date, league, home_team, away_team,
        btts_odds_yes, btts_odds_no, btts_odds_yes_best, n_bookmakers
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
        print(f"Found {len(df)} upcoming matches with BTTS odds:")
        print(df.to_string(index=False))
