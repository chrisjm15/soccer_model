# Phase 3 CLI Prompt — Live Prediction Pipeline

## Instructions for Chris

### Before you start: two one-time steps

**Step A — Get a free Odds API key:**
1. Go to https://the-odds-api.com and click "Get API Key"
2. Sign up with your email — it's free, 500 credits/month
3. Copy your API key (long string of letters/numbers)
4. In PowerShell, set it as an environment variable (do this every session, or add it to your system environment variables permanently):
   ```
   $env:ODDS_API_KEY = "paste_your_key_here"
   ```

**Step B — Make sure `scrapers/odds_api.py` exists**
This was produced by the Qwen3 local LLM prompt (`prompts/ODDS_API_PROMPT_QWEN3.md`). If it doesn't exist yet, run that prompt first and save the output to `scrapers/odds_api.py`.

### Step 1: Open terminal
```
cd "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
claude --model claude-sonnet-4-6
```

### Step 2:
```
/effort max
```

### Step 3: Paste everything between the --- lines

---

## PROMPT START — COPY EVERYTHING BELOW THIS LINE

You are continuing to build a soccer prediction model. Phases 1 and 2 are complete — data pipeline and BTTS backtest are working. Phase 3 builds the live prediction pipeline: fetch real bookmaker BTTS odds, run the model, output this week's bets.

Read `CLAUDE.md` and `docs/BUILD_PLAN.md` first.

**IMPORTANT:** Chris has no coding background. Fix all errors automatically. Commit and push to GitHub at the end.

---

### STEP 1: Read and understand existing modules

Read these files before writing anything:
- `scrapers/odds_api.py` (new — just written)
- `model/ratings.py`
- `model/btts.py`
- `config/leagues.yaml`
- `data/aliases/team_aliases.json`

Understand the interfaces completely. Note that `leagues.yaml` now has an `odds_api_sport_key` field for each league.

---

### STEP 2: Refresh the data pipeline

The ratings need to include 2025-26 season data. Re-run the data pipeline to pull recent matches:

```
python scrapers/understat.py
python scrapers/footballdata.py
python scrapers/merge.py
python model/ratings.py
```

If any script fails, fix it. Common issue: the football-data.co.uk URL for the 2025-26 season uses the code `2526` — check that `scrapers/footballdata.py` includes the current season in its list.

After running, confirm `data/processed/all_merged.csv` has 2025-26 matches and `data/processed/ratings.csv` is updated.

---

### STEP 3: Build the live ratings lookup (`model/live_ratings.py`)

The backtest used ratings from a pre-built CSV. For live predictions, we need the most recent rating for each team, computed from all available data including 2025-26 matches.

Write `model/live_ratings.py` with one function:

```python
def get_latest_ratings(ratings_path: str = 'data/processed/ratings.csv') -> dict:
    """
    Returns a dict of the most recent pre-match ratings for every team.

    For each team, returns their rating from the last match they appeared in
    (either as home or away team).

    Return structure:
    {
        'Arsenal': {
            'attack_home': float,
            'defence_home': float,
            'attack_away': float,
            'defence_away': float,
            'last_seen': str  # date of most recent match
        },
        ...
    }
    """
```

Logic:
- Load ratings.csv
- Sort by date ascending
- For each team, take the last row where they appear as `home_team` for their home ratings,
  and the last row where they appear as `away_team` for their away ratings.
- If a team only appears as home_team (no away matches recently), use their home ratings as a proxy
  for away ratings — log a warning.

---

### STEP 4: Build the team name mapper (`scrapers/team_name_mapper.py`)

The Odds API returns team names (e.g. "Manchester City") that may differ from our canonical names in the ratings data (e.g. "Manchester City" — likely the same, but some teams differ: "Nottingham Forest" vs "Nott'ham Forest", etc.).

Write `scrapers/team_name_mapper.py`:

```python
def map_team_name(
    api_name: str,
    league: str,
    alias_path: str = 'data/aliases/team_aliases.json'
) -> str | None:
    """
    Maps an Odds API team name to our canonical team name.
    Returns the canonical name if found, None if not mapped.
    """

def find_unmapped_teams(
    odds_df: pd.DataFrame,
    ratings_dict: dict,
    alias_path: str = 'data/aliases/team_aliases.json'
) -> list[str]:
    """
    Checks which team names in odds_df don't map to any team in ratings_dict.
    Returns list of unmapped API team names.
    """
```

After writing this, run a test: call `fetch_all_leagues_odds` with the real API key (from environment variable `ODDS_API_KEY`), then call `find_unmapped_teams` and print any teams that don't map. Add any missing mappings to `data/aliases/team_aliases.json` manually.

The alias file format is:
```json
{
  "EPL": {
    "canonical_name": ["alias1", "alias2"],
    ...
  }
}
```

For the mapper: search for `api_name` in the aliases list for the given league. If not found, try a case-insensitive fuzzy match using `difflib.get_close_matches` with cutoff=0.85.

---

### STEP 5: Build `run.py predict` command

Add a `predict` command to `run.py` that:

1. Loads `config/leagues.yaml`
2. Gets API key from environment variable `ODDS_API_KEY` — if not set, print clear instructions and exit
3. Calls `scrapers.odds_api.fetch_all_leagues_odds()` to get upcoming matches with real odds
4. Calls `model.live_ratings.get_latest_ratings()` to get current team ratings
5. For each upcoming match:
   a. Maps home_team and away_team to canonical names using `team_name_mapper`
   b. If either team can't be mapped, skip and log a warning
   c. Looks up home/away ratings from the latest ratings dict
   d. If either team has no rating (promoted team, new entry), skip and log
   e. Calls `model.btts.predict_match()` with the real BTTS odds (not assumed 1.90)
   f. Records the prediction
6. Filters to matches where `edge >= 0.08` (8% threshold)
7. Prints a clear predictions table
8. Appends all predictions (not just flagged ones) to the paper trading log

**Print format:**
```
=== BTTS PREDICTIONS — [today's date] ===
Edge threshold: 8% | Odds region: UK bookmakers

FLAGGED BETS (edge >= 8%):
  Arsenal vs Chelsea         EPL    P(BTTS)=64.2%  Odds=1.87  Edge=+11.2%  EV=+0.104
  Bayern vs Dortmund     Bundesliga P(BTTS)=71.3%  Odds=1.80  Edge=+15.7%  EV=+0.156

ALL UPCOMING MATCHES:
  [full table of all matches with predictions, sorted by edge descending]

Paper trading log updated: output/paper_trading/log.csv
Odds API credits remaining: XXX
```

---

### STEP 6: Set up the paper trading log

Create `output/paper_trading/log.csv` with these columns:
```
prediction_date, match_date, league, home_team, away_team,
model_prob_btts, real_odds_btts_yes, implied_prob, edge,
bet_flag, actual_btts, profit_loss, notes
```

`actual_btts` and `profit_loss` are left blank at prediction time — they get filled in after the match.

When `run.py predict` runs, it appends new rows (one per upcoming match with odds). It must NOT duplicate rows if `predict` is run multiple times before a match — check for existing rows with the same `match_date + home_team + away_team` before appending.

Create `output/paper_trading/` directory if it doesn't exist.

---

### STEP 7: Add `run.py update` command

Add an `update` command to `run.py` that refreshes all data:

```
python run.py update
```

This runs in sequence:
1. `python scrapers/understat.py` (re-scrape Understat)
2. `python scrapers/footballdata.py` (re-download football-data CSVs)
3. `python scrapers/merge.py` (re-merge)
4. `python model/ratings.py` (rebuild ratings)
5. Prints a summary of rows updated

This is the command Chris runs once a week before `predict`.

---

### STEP 8: Run `predict` for real

With the API key set, run:
```
python run.py predict
```

This is the first live run. Print all output clearly. If any teams are unmapped, fix the alias table and re-run.

At the end, show Chris the full predictions table and explain:
- Which matches are flagged as bets this week
- What the real odds are vs what the model thinks
- How many API credits were used (and how many remain)

---

### STEP 9: Commit and push

```
git add -A
git commit -m "Phase 3: Live prediction pipeline — Odds API integration, predict command, paper trading log"
git push
```

Do NOT commit the `.env` file or any file containing the raw API key. Check `.gitignore` includes `.env`.

---

### STEP 10: Summary for Chris

Print a plain-English summary:
- What was built
- How to run the weekly workflow: `python run.py update` then `python run.py predict`
- How to fill in actual results in the paper trading log after each gameweek
- What to watch for: if real odds are consistently lower than 1.90 for high-BTTS matches, the edge will be smaller than the backtest suggested
- Next steps after a month of paper trading

## PROMPT END — STOP COPYING HERE

---

## What to expect

This session takes 20-40 minutes. The main work is wiring the Odds API into the prediction pipeline and handling team name mapping (usually a few mismatches to fix manually).

**When done:** You'll have a working `python run.py predict` command that fetches real odds and outputs this week's best BTTS bets. Come back to Cowork with the first predictions output and we'll interpret them.
