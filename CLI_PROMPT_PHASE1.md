# Phase 1 CLI Prompt — Data Pipeline

## Instructions for Chris

### Step 1: Open your terminal (Command Prompt or PowerShell) and paste this:
```
cd "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
claude --model claude-opus-4-6
```

### Step 2: Once Claude Code opens, paste this:
```
/effort max
```

### Step 3: Paste the entire prompt below (everything inside the --- lines):

---

## PROMPT START — COPY EVERYTHING BELOW THIS LINE

You are building Phase 1 of a soccer prediction model. This session sets up the GitHub repo, project structure, data scrapers, and data pipeline.

Read `BUILD_PLAN.md` and `CLAUDE.md` in this folder first — they contain the full plan and governance rules. Then execute the steps below.

**IMPORTANT:** Chris has no coding background. If anything fails, explain what went wrong in plain English and fix it. Do not ask Chris to debug anything manually. Commit and push to GitHub at the end.

---

### STEP 1: Create GitHub repo and project structure

Create a new GitHub repo called `soccer_model` under the `chrisjm15` account. Use the `gh` CLI tool:

```
gh repo create chrisjm15/soccer_model --public --clone=false
git init
git remote add origin https://github.com/chrisjm15/soccer_model.git
```

If `gh` is not installed, install it first. If authentication is needed, walk Chris through it step by step.

Create this folder structure:

```
soccer_model/
├── CLAUDE.md              (copy from this folder's CLAUDE.md, adapt for the repo)
├── README.md              (brief project description)
├── requirements.txt       (Python dependencies)
├── config/
│   └── leagues.yaml       (league definitions)
├── data/
│   ├── raw/               (downloaded/scraped data goes here)
│   ├── processed/         (cleaned merged data goes here)
│   └── aliases/           (team name mapping tables)
├── scrapers/
│   ├── __init__.py
│   ├── understat.py       (Big 5 xG scraper)
│   └── footballdata.py    (football-data.co.uk CSV loader)
├── model/                 (empty for now — Phase 2)
│   └── __init__.py
├── backtest/              (empty for now — Phase 2)
│   └── __init__.py
├── output/
│   └── predictions/       (empty for now)
└── run.py                 (placeholder entry point)
```

Add a `.gitignore` that excludes:
- `data/raw/` (large files, re-downloadable)
- `data/processed/` (derived, re-buildable)
- `__pycache__/`
- `*.pyc`
- `.env`
- `venv/`

### STEP 2: Python dependencies

Create `requirements.txt` with:
```
requests>=2.31.0
beautifulsoup4>=4.12.0
pandas>=2.1.0
pyarrow>=14.0.0
pyyaml>=6.0
lxml>=4.9.0
```

Install them:
```
pip install -r requirements.txt
```

### STEP 3: League configuration

Create `config/leagues.yaml`:
```yaml
leagues:
  EPL:
    name: "English Premier League"
    understat_name: "EPL"
    footballdata_code: "E0"
    country: "England"
    seasons_available:
      start: "2014-15"
    season_type: "winter"  # Aug-May

  La_Liga:
    name: "La Liga"
    understat_name: "La_liga"
    footballdata_code: "SP1"
    country: "Spain"
    seasons_available:
      start: "2014-15"
    season_type: "winter"

  Bundesliga:
    name: "Bundesliga"
    understat_name: "Bundesliga"
    footballdata_code: "D1"
    country: "Germany"
    seasons_available:
      start: "2014-15"
    season_type: "winter"

  Serie_A:
    name: "Serie A"
    understat_name: "Serie_A"
    footballdata_code: "I1"
    country: "Italy"
    seasons_available:
      start: "2014-15"
    season_type: "winter"

  Ligue_1:
    name: "Ligue 1"
    understat_name: "Ligue_1"
    footballdata_code: "F1"
    country: "France"
    seasons_available:
      start: "2014-15"
    season_type: "winter"
```

Note: Verify the exact `understat_name` values by checking Understat's URL structure (e.g., `https://understat.com/league/EPL/2024`). Adjust if the site uses different slugs.

### STEP 4: Build the Understat scraper (`scrapers/understat.py`)

Build a scraper that:

1. **Fetches match-level data from Understat** for each Big 5 league, for seasons 2020-21 through 2025-26 (current season). Understat stores data as JSON embedded in their HTML pages.

2. **For each match, extract:**
   - Date
   - Home team name, Away team name
   - Home goals, Away goals
   - Home xG, Away xG
   - Home xGA, Away xGA (which is just the opponent's xG, but store it explicitly for clarity)

3. **Understat's data structure:** The league page (e.g., `https://understat.com/league/EPL/2024`) contains a JavaScript variable `datesData` (or similar) with JSON match data. Parse this from the page source — do NOT try to use a non-existent API.

4. **Rate limiting:** Wait at least 2 seconds between page requests. Be respectful.

5. **Output:** Save one CSV per league-season in `data/raw/understat/`, e.g., `data/raw/understat/EPL_2024.csv`. Also save the combined data as `data/raw/understat/all_matches.csv`.

6. **Error handling:** If a page fails to load, log the error, skip it, and continue. Print a summary at the end of how many matches were scraped per league-season.

7. **Make it runnable** with: `python scrapers/understat.py`

**IMPORTANT:** Before writing the scraper, first manually fetch ONE page (EPL 2024) and inspect the actual HTML/JSON structure to confirm the variable name and data format. Do not guess. Adjust the parser to match what you actually find.

### STEP 5: Build the football-data.co.uk loader (`scrapers/footballdata.py`)

Build a loader that:

1. **Downloads CSV files from football-data.co.uk** for the Big 5 leagues, seasons 2020-21 through 2024-25. The URL pattern is:
   - `https://www.football-data.co.uk/mmz4281/YYMM/CODE.csv`
   - Where YYMM is the season (e.g., `2425` for 2024-25) and CODE is the league code from the config (E0, SP1, D1, I1, F1)
   - Historical seasons may use a different path: `https://www.football-data.co.uk/mmz4281/YYMM/CODE.csv`

2. **Verify the actual URL format** by first trying to download one file manually and checking it works. The URL format has changed over the years — confirm current structure.

3. **For each match, extract:**
   - Date, HomeTeam, AwayTeam
   - FTHG (Full Time Home Goals), FTAG (Full Time Away Goals), FTR (Full Time Result: H/D/A)
   - HS (Home Shots), AS (Away Shots), HST (Home Shots on Target), AST (Away Shots on Target)
   - HC (Home Corners), AC (Away Corners)
   - HF (Home Fouls), AF (Away Fouls)
   - HY (Home Yellow Cards), AY (Away Yellow Cards), HR (Home Red Cards), AR (Away Red Cards)
   - Referee
   - Odds columns: B365H, B365D, B365A (Bet365 WDL odds). Also look for: BbAHh (Asian Handicap), BbOU (Over/Under), and any BTTS columns. **Log which odds columns actually exist** — we need to know this for backtesting.

4. **Output:** Save one CSV per league-season in `data/raw/footballdata/`, plus combined `data/raw/footballdata/all_matches.csv`.

5. **Make it runnable** with: `python scrapers/footballdata.py`

**NOTE on referee data:** The briefing doc notes that non-English leagues may not have referee data in football-data.co.uk CSVs. Log which leagues have the Referee column and which don't.

### STEP 6: Team name alias table

Team names differ between sources. For example:
- Understat: "Manchester United" vs football-data: "Man United"
- Understat: "Paris Saint-Germain" vs football-data: "Paris SG"

Build `data/aliases/team_aliases.json` that maps team names between sources. Approach:

1. After scraping both sources, extract the unique team names from each source per league.
2. Attempt automatic matching (fuzzy string matching using difflib or similar).
3. Log any unmatched teams that need manual review.
4. Output the alias file as JSON: `{ "league": { "canonical_name": ["alias1", "alias2", ...] } }`

This does NOT need to be perfect in this session. Get the obvious ones right, log the rest. We'll fix edge cases when we see merge failures.

### STEP 7: Data merge and normalisation

Build a merge script (`scrapers/merge.py` or a function in a utils module) that:

1. Loads Understat data and football-data.co.uk data for the same league-season.
2. Joins on: date + home team + away team (using the alias table to normalise team names).
3. Outputs one merged CSV/Parquet per league-season in `data/processed/`, containing all columns from both sources.
4. **Logs merge quality:**
   - How many matches in each source
   - How many matched successfully
   - How many orphans (in one source but not the other) — list them
5. **Validates:** For matched rows, check that the scoreline agrees between sources. Flag any mismatches.

Output the final merged schema as documented in BUILD_PLAN.md Phase 1.

### STEP 8: Run everything and validate

1. Run the Understat scraper: `python scrapers/understat.py`
2. Run the football-data loader: `python scrapers/footballdata.py`
3. Run the merge: `python scrapers/merge.py`
4. Print a summary report:
   - Matches scraped per league-season from each source
   - Merge success rate per league-season
   - Any team name mismatches that need manual fixing
   - Which odds columns are available (especially BTTS odds)
   - Spot-check: pick 3 random EPL matches from 2024-25, print their full merged row, and verify xG values look reasonable (typically 0.5–3.5 range)

### STEP 9: Commit and push to GitHub

```
git add -A
git commit -m "Phase 1: Data pipeline - Understat scraper, football-data loader, merge engine"
git branch -M main
git push -u origin main
```

If the push fails due to authentication, explain to Chris how to set up a GitHub personal access token or SSH key, step by step.

### STEP 10: Write a summary

After everything is done, print a clear summary:
- What was built
- How many total matches are in the merged dataset
- Any issues or manual fixes needed
- What Phase 2 will build on top of this data

## PROMPT END — STOP COPYING HERE

---

## What to expect

This session will probably take 15-30 minutes. Claude Code will:
1. Create the project folders and files
2. Write the Python scripts
3. Run the scrapers (this is the slow part — it's downloading data from websites)
4. Merge the data
5. Push everything to GitHub

**If something fails:** Claude Code should fix it automatically. If it asks you a question, answer it. If it gets stuck, copy the error message and bring it back to this Cowork session — we'll troubleshoot.

**When it's done:** You should see a GitHub repo at `https://github.com/chrisjm15/soccer_model` with code and a summary of how many matches were scraped. Come back to this Cowork session with the summary and we'll plan Phase 2.
