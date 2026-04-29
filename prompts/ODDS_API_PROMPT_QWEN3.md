# Prompt: odds_api.py — The Odds API Integration

## Before you run this prompt

You need a free API key from The Odds API. Do this once:
1. Go to https://the-odds-api.com
2. Click "Get API Key" — the free tier gives 500 credits/month
3. Copy the API key — it looks like a long string of letters and numbers

## How to run this prompt
1. Open your terminal and run: `ollama run qwen3-coder:30b-16k`
2. Set model options:
   - `/set parameter temperature 0.2`
   - `/set parameter num_predict 8192`
3. Paste everything from **PROMPT START** to **PROMPT END**

---

## PROMPT START — COPY EVERYTHING BELOW THIS LINE

/no_think

You are writing a single Python module: `scrapers/odds_api.py`. Your job is ONLY to write this one file. Do not write any other files.

---

## What this module does

It connects to The Odds API (https://api.the-odds-api.com) and fetches upcoming BTTS (Both Teams To Score) odds for soccer matches. This is used to get real bookmaker odds before each gameweek so the model can compare its predictions against market prices.

---

## API details

**Base URL:** `https://api.the-odds-api.com/v4/sports/{sport_key}/odds`

**Query parameters:**
- `apiKey` — the user's API key (passed as argument, never hardcoded)
- `regions` — always use `'uk'` (UK bookmakers have best BTTS coverage)
- `markets` — always use `'btts'`
- `dateFormat` — always use `'iso'`
- `oddsFormat` — always use `'decimal'`

**Example URL:**
```
https://api.the-odds-api.com/v4/sports/soccer_epl/odds?apiKey=YOUR_KEY&regions=uk&markets=btts&dateFormat=iso&oddsFormat=decimal
```

**Response structure (JSON):**
```json
[
  {
    "id": "abc123",
    "sport_key": "soccer_epl",
    "commence_time": "2025-05-03T14:00:00Z",
    "home_team": "Arsenal",
    "away_team": "Chelsea",
    "bookmakers": [
      {
        "key": "bet365",
        "title": "Bet365",
        "markets": [
          {
            "key": "btts",
            "outcomes": [
              {"name": "Yes", "price": 1.87},
              {"name": "No", "price": 1.95}
            ]
          }
        ]
      },
      {
        "key": "williamhill",
        "title": "William Hill",
        "markets": [
          {
            "key": "btts",
            "outcomes": [
              {"name": "Yes", "price": 1.85},
              {"name": "No", "price": 2.00}
            ]
          }
        ]
      }
    ]
  }
]
```

---

## What the module must do

**1. For each match, extract odds from all available bookmakers and compute the average:**
```
btts_yes_avg = mean of all "Yes" prices across bookmakers
btts_no_avg  = mean of all "No" prices across bookmakers
```
Also record `btts_yes_best` (the highest available Yes price) and `btts_no_best`.

**2. Handle missing data gracefully:**
- Some matches may have no bookmakers with BTTS odds — skip them, do not crash.
- If a bookmaker has the btts market but is missing the "Yes" or "No" outcome — skip that bookmaker for that match.

**3. Rate limiting:** Wait 1 second between API calls (one call per league).

**4. Credits tracking:** The API returns remaining credits in the response headers as `X-Requests-Remaining`. Log this after each call so the user knows how many credits are left.

---

## Output schema

Each match row must contain:
- `date` — match date as string (YYYY-MM-DD), extracted from `commence_time`
- `league` — our league key (e.g. "EPL"), passed in by the caller
- `home_team` — as returned by the API
- `away_team` — as returned by the API
- `btts_odds_yes` — average BTTS Yes odds across bookmakers (float)
- `btts_odds_no` — average BTTS No odds across bookmakers (float)
- `btts_odds_yes_best` — best (highest) BTTS Yes price available (float)
- `n_bookmakers` — how many bookmakers contributed to the average (int)

---

## Code structure

```python
import requests
import time
import pandas as pd
from datetime import datetime

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

if __name__ == '__main__':
    import yaml
    import os

    # Load config
    with open('config/leagues.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Get API key from environment variable
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
```

---

## Implementation notes

- Use the `requests` library only. No async.
- The API returns HTTP 401 for invalid API keys — handle this and print a clear error message.
- The API returns HTTP 422 if the sport_key is wrong — handle and log which league failed.
- Do NOT raise exceptions — log errors and continue to the next league.
- Parse `commence_time` (ISO format like "2025-05-03T14:00:00Z") to extract just the date part (YYYY-MM-DD).

---

## PROMPT END — STOP COPYING HERE
