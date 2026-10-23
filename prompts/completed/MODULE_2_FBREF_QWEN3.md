/no_think

# Module 2 — FBref Match Stats Loader
**LLM:** Qwen3-Coder 30B (`qwen3-coder:30b-16k`)
**Output file:** `experiment/load_fbref.py`
**Experiment:** Scandinavian Expansion — standalone research project

---

## Task

Write a self-contained Python script at `experiment/load_fbref.py` that scrapes per-match basic stats (shots, SoT, corners, fouls, cards) from FBref for proxy leagues and Scandinavian target leagues.

Do NOT use `soccerdata` — it does not support non-Big-5 leagues. Scrape FBref directly.
Do NOT import from any other file in this project. This script is fully standalone.

---

## How This Script Works

FBref has two relevant page types:

**1. Schedule page** — one per league per season. Lists every match with a link to its match report.
URL format: `https://fbref.com/en/comps/{comp_id}/{season}/schedule/`
Example: `https://fbref.com/en/comps/10/2022-2023/schedule/`

**2. Match report page** — one per match. Contains a "Team Stats" table with shots, corners, fouls, cards for both teams.
URL format: `https://fbref.com/en/matches/{match_hash}/`
Example: `https://fbref.com/en/matches/a1b2c3d4/`

The pipeline:
```
Schedule page → extract match report URLs → scrape each match report → extract team stats table → save CSV
```

---

## Libraries Required

```
pip install cloudscraper requests-cache beautifulsoup4 pandas lxml
```

- `cloudscraper`: handles Cloudflare JS challenge protection on FBref
- `requests_cache`: caches every HTTP response to disk — once a completed match is fetched, it is never re-fetched
- `beautifulsoup4`: HTML parsing
- `pandas`: DataFrame handling and CSV output

---

## Leagues to Scrape

### Proxy Leagues
| League | FD Code | FBref Comp ID | Season format | Notes |
|---|---|---|---|---|
| English Championship | E1 | 10 | `2022-2023` | European calendar |
| Dutch Eredivisie | N1 | 23 | `2022-2023` | European calendar |
| Belgian Pro League | B1 | 37 | `2022-2023` | European calendar |
| Portuguese Primeira Liga | P1 | 32 | `2022-2023` | European calendar |
| Scottish Premiership | SC0 | 40 | `2022-2023` | European calendar |
| Turkish Süper Lig | T1 | 26 | `2022-2023` | European calendar |

### Scandinavian Target Leagues
| League | FD Code | FBref Comp ID | Season format | Notes |
|---|---|---|---|---|
| Sweden Allsvenskan | SWE | 25 | `2023` | Calendar year |
| Norway Eliteserien | NOR | 28 | `2023` | Calendar year |
| Denmark Superliga | DNK | 50 | `2022-2023` | European calendar |
| Finland Veikkausliiga | FIN | 129 | `2023` | Calendar year |

**Important:** The FBref comp IDs above are best estimates. Before scraping, run the discovery step below to verify each one returns the correct league.

---

## Discovery Step (Run This First)

Before scraping data, add a `--discover` CLI flag that:
1. Attempts to fetch the schedule page for each league using the comp ID above
2. Prints the page title and the first 3 matches found
3. Exits without saving any data

This lets us verify comp IDs are correct before a long scrape run. Example output:
```
Checking comp 10 (E1/Championship)...
  Title: 2022-2023 EFL Championship Scores & Fixtures
  First match: 2022-08-05 Coventry City vs Middlesbrough ✓

Checking comp 23 (N1/Eredivisie)...
  Title: 2022-2023 Eredivisie Scores & Fixtures
  First match: 2022-07-29 PSV vs Go Ahead Eagles ✓
```

---

## Seasons to Scrape

### Proxy leagues (European format)
```python
PROXY_SEASONS = [
    '2014-2015', '2015-2016', '2016-2017', '2017-2018', '2018-2019',
    '2019-2020', '2020-2021', '2021-2022', '2022-2023', '2023-2024', '2024-2025'
]
```
Note: FBref may not have stats for all leagues going back to 2014-15. If the schedule page exists but match reports have no team stats table, skip gracefully and record in the failure log.

### Scandinavian leagues (calendar year format)
```python
SCAND_SEASONS = ['2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025']
```

---

## Step 1 — Fetch the Schedule Page

```python
import cloudscraper
import requests_cache

# Install cache — all responses cached to disk indefinitely
requests_cache.install_cache('data/fbref_cache/fbref_cache', backend='sqlite')

scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
)
```

Fetch the schedule page:
```python
url = f"https://fbref.com/en/comps/{comp_id}/{season}/schedule/"
response = scraper.get(url, timeout=30)
```

Parse with BeautifulSoup:
```python
from bs4 import BeautifulSoup
soup = BeautifulSoup(response.text, 'lxml')
```

Find the schedule table. It will have an id starting with `sched_`:
```python
table = soup.find('table', id=lambda x: x and x.startswith('sched_'))
```

Extract match report links from the table. Look for `<td data-stat="match_report">` cells containing an `<a>` tag:
```python
match_urls = []
for row in table.find('tbody').find_all('tr'):
    report_cell = row.find('td', {'data-stat': 'match_report'})
    if report_cell and report_cell.find('a'):
        href = report_cell.find('a')['href']
        match_urls.append('https://fbref.com' + href)
```

Also extract the match date and team names from each row (for validation):
- `td[data-stat="date"]` → match date
- `td[data-stat="home_team"]` → home team name
- `td[data-stat="away_team"]` → away team name

Skip rows where the match report link says "Head-to-Head" instead of "Match Report" — those are future/unplayed matches.

---

## Step 2 — Fetch Each Match Report

For each match report URL:

```python
import time

# Only sleep if response was NOT from cache
response = scraper.get(match_url, timeout=30)
if not getattr(response, 'from_cache', False):
    time.sleep(5)  # 5 second delay for live requests only — cached responses are instant
```

Parse the match report with BeautifulSoup:
```python
soup = BeautifulSoup(response.text, 'lxml')
```

---

## Step 3 — Extract the Team Stats Table

FBref match reports include a "Team Stats" section. Find the div with id `div_team_stats`:
```python
stats_div = soup.find('div', id='team_stats')
```

If `team_stats` div is not found, try `div_team_stats`:
```python
if not stats_div:
    stats_div = soup.find('div', id='div_team_stats')
```

If neither is found, this match has no stats data. Record as missing and continue.

Inside this div, look for table rows. The table structure is:
```
Stat Name | Home Value | Away Value
Shots on Target | 5 | 3
Shots | 12 | 8
Fouls | 14 | 11
Corners | 7 | 4
Yellow Cards | 2 | 1
Red Cards | 0 | 0
```

Parse this table to extract values. Each `<tr>` contains:
- A `<th>` or `<td>` with the stat name
- A `<strong>` (home) and another `<strong>` (away) for values

Example parsing logic:
```python
stats = {}
for row in stats_div.find_all('tr'):
    cells = row.find_all(['th', 'td'])
    strong_tags = row.find_all('strong')
    if len(strong_tags) == 2:
        stat_name = row.get_text(separator=' ').strip()
        # The row text will contain both values and the stat name
        # Strong tags hold the home and away values
        home_val = strong_tags[0].get_text(strip=True)
        away_val = strong_tags[1].get_text(strip=True)
        stats[stat_name] = (home_val, away_val)
```

**Stat name mapping** (FBref label → our column names):
| FBref label | Home column | Away column |
|---|---|---|
| `Shots on Target` | `home_sot` | `away_sot` |
| `Shots` | `home_shots` | `away_shots` |
| `Fouls` | `home_fouls` | `away_fouls` |
| `Corners` | `home_corners` | `away_corners` |
| `Yellow Cards` | `home_yellow` | `away_yellow` |
| `Red Cards` | `home_red` | `away_red` |

FBref stat labels can vary slightly by league. Match case-insensitively and strip whitespace. If a stat label is not found, output NaN for that column.

Also extract the match date and team names from the match report scorebox (as a cross-check against what the schedule page gave us):
```python
# Scorebox is at the top of the match report
scorebox = soup.find('div', class_='scorebox')
```

---

## Output Schema

One row per match:
```
date, home_team, away_team,
home_shots, away_shots,
home_sot, away_sot,
home_corners, away_corners,
home_fouls, away_fouls,
home_yellow, away_yellow,
league, season
```

- `date`: YYYY-MM-DD string
- `home_team`, `away_team`: team names exactly as they appear on FBref — do NOT normalise
- `league`: the FD code (E1, N1, etc.) — not the FBref competition name
- `season`: the FBref season string (e.g. `2022-2023` or `2023`)
- All stat columns: integer or NaN (never float)

---

## Output File Paths

```
data/proxy/{league_fd_code}_{season}_fbref.csv       ← proxy leagues
data/scandinavian/{league_fd_code}_{season}_fbref.csv ← Scandinavian leagues
```

Examples:
```
data/proxy/E1_2022-2023_fbref.csv
data/scandinavian/SWE_2023_fbref.csv
```

---

## Error Handling and Logging

Maintain a failure log list throughout the run. At the end, save it to `data/fbref_cache/failures.csv` with columns: `league, season, match_url, reason`.

Reasons to log (and continue — never crash):
- Schedule page returns non-200 status
- Schedule page has no schedule table
- Match report returns non-200 status
- Match report has no team stats div
- Fewer than 3 stat rows found in team stats table

---

## CLI Arguments

```
python experiment/load_fbref.py                          # All leagues, all seasons
python experiment/load_fbref.py --discover               # Verify comp IDs only, no data saved
python experiment/load_fbref.py --leagues E1 SWE         # Specific leagues
python experiment/load_fbref.py --seasons 2022-2023 2023 # Specific seasons
python experiment/load_fbref.py --proxy-only             # Proxy leagues only
python experiment/load_fbref.py --scandinavian-only      # Scandinavian only
python experiment/load_fbref.py --no-cache               # Bypass cache (re-fetch everything)
```

---

## Console Output Format

```
=== FBref Stats Loader ===

E1 2022-2023 (Championship):
  Schedule: 552 matches found
  Fetching match reports... (cached responses skip delay)
  [============================] 552/552
  Saved: data/proxy/E1_2022-2023_fbref.csv (547 rows, 5 missing stats)

E1 2021-2022:
  ...

=== Summary ===
  Proxy leagues:       6 leagues × 11 seasons = XX files
  Scandinavian:        4 leagues × 12 seasons = XX files
  Total matches:       XX,XXX
  Missing stats:       XXX (saved to data/fbref_cache/failures.csv)
  Cache hits:          XX,XXX (no delay)
  Live requests:       XXX
```

---

## Important Implementation Notes

1. **Cache first, always.** The requests_cache library caches by URL automatically. Check `response.from_cache` — if True, skip the sleep. This makes re-runs and partial runs fast.

2. **FBref returns 429 (rate limit) or 503 occasionally.** If either is received on a live request, sleep 30 seconds and retry once. If it fails again, log it and move on.

3. **FBref stat label variations.** "Shots on Target" might appear as "Shots on Target" or "Shots On Target" or "SoT" depending on the match/league. Match case-insensitively.

4. **Team names from FBref will NOT match football-data.co.uk.** This is intentional. Module 4 handles normalisation. Output team names exactly as FBref provides.

5. **Match reports for future/upcoming matches return a page with no stats.** The absence of `div#team_stats` is the correct way to detect this. Skip and do not log as a failure.

6. **The 5-second delay applies only to live (non-cached) requests.** With a full cache, re-running the script on all leagues/seasons takes seconds.

---

## Colab QC Instructions

After running, verify in Colab. Upload `data/proxy/E1_2022-2023_fbref.csv` and `data/scandinavian/SWE_2023_fbref.csv`.

```python
import pandas as pd

# Proxy league check
df = pd.read_csv("E1_2022-2023_fbref.csv")
print("=== E1 2022-2023 ===")
print(f"Shape: {df.shape}")             # Expect ~552 rows, 15 columns
print(f"Columns: {df.columns.tolist()}")
print(df.head(3))
print(f"\nNull counts:\n{df.isnull().sum()}")
print(f"\nShots range: {df['home_shots'].min()}–{df['home_shots'].max()}")  # Expect 0–30ish
print(f"Corners range: {df['home_corners'].min()}–{df['home_corners'].max()}")  # Expect 0–15ish
```

```python
# Scandinavian check
df_s = pd.read_csv("SWE_2023_fbref.csv")
print("=== SWE 2023 ===")
print(f"Shape: {df_s.shape}")           # Expect ~240 rows
print(f"Season: {df_s['season'].unique()}")   # Should be ['2023']
print(f"League: {df_s['league'].unique()}")   # Should be ['SWE']
print(df_s[['date','home_team','away_team','home_shots','home_sot','home_corners']].head(5))
```

```python
# Cross-check: FBref team names differ from football-data.co.uk — this is expected
fd_df = pd.read_csv("E1_2022-23_footballdata.csv")  # from Module 1
fbref_df = pd.read_csv("E1_2022-2023_fbref.csv")

fd_teams = set(fd_df['home_team'].unique())
fbref_teams = set(fbref_df['home_team'].unique())

print("Teams in FD but not FBref:", fd_teams - fbref_teams)
print("Teams in FBref but not FD:", fbref_teams - fd_teams)
# Some differences expected — Module 4 will map them
```

Expected: E1 2022-23 has ~547 rows with shots between 1–30, corners 0–15. Some rows may have NaN for fouls/corners if FBref's stats table was incomplete for that match. SWE 2023 has ~237 rows. Team name differences between Module 1 and Module 2 outputs are expected and will be fixed in Module 4.

---

## Note on Run Time

The first run will be slow — approximately 5 seconds per uncached match report. Rough estimates:
- Single league, single season (~300 matches): ~25 minutes
- All proxy leagues, all seasons (~18,000 matches): run overnight

**Recommended approach:** Run one league first to verify the script works, then run all leagues overnight with caching enabled.

```
python experiment/load_fbref.py --leagues E1 --seasons 2022-2023
```

Check the output. If it looks correct, run the full scrape:
```
python experiment/load_fbref.py
```
