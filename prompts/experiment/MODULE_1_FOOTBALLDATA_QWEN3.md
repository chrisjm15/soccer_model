/no_think

# Module 1 — football-data.co.uk Loader
**LLM:** Qwen3-Coder 30B (`qwen3-coder:30b-16k`)
**Output file:** `experiment/load_footballdata.py`
**Experiment:** Scandinavian Expansion — standalone research project

---

## Task

Write a self-contained Python script at `experiment/load_footballdata.py` that downloads match data from football-data.co.uk and saves it as clean CSV files with a standardised schema.

The script handles **two different URL patterns** — one for proxy leagues (standard format, one file per season) and one for Scandinavian target leagues (new format, all seasons in a single file).

Do NOT import from any other file in this project. This script is fully standalone.

---

## Leagues to Download

### Proxy Leagues — Standard URL Pattern
These use: `https://www.football-data.co.uk/mmz4281/{season_code}/{league_code}.csv`

| League | Code | Seasons available |
|---|---|---|
| English Championship | E1 | 2000-01 to 2024-25 |
| Dutch Eredivisie | N1 | 2000-01 to 2024-25 |
| Belgian Pro League | B1 | 2000-01 to 2024-25 |
| Portuguese Primeira Liga | P1 | 2000-01 to 2024-25 |
| Scottish Premiership | SC0 | 2000-01 to 2024-25 |
| Turkish Super Lig | T1 | 2017-18 to 2024-25 |

Season codes for the URL (season label → URL code):
```
2000-01 → 0001
2001-02 → 0102
2002-03 → 0203
2003-04 → 0304
2004-05 → 0405
2005-06 → 0506
2006-07 → 0607
2007-08 → 0708
2008-09 → 0809
2009-10 → 0910
2010-11 → 1011
2011-12 → 1112
2012-13 → 1213
2013-14 → 1314
2014-15 → 1415
2015-16 → 1516
2016-17 → 1617
2017-18 → 1718
2018-19 → 1819
2019-20 → 1920
2020-21 → 2021
2021-22 → 2122
2022-23 → 2223
2023-24 → 2324
2024-25 → 2425
```

### Scandinavian Target Leagues — New URL Pattern
These use: `https://www.football-data.co.uk/new/{league_code}.csv`
(Single file per league, all seasons combined, includes a "Season" column.)

| League | Code |
|---|---|
| Finland Veikkausliiga | FIN |
| Sweden Allsvenskan | SWE |
| Norway Eliteserien | NOR |
| Denmark Superliga | DNK |

---

## Output Files

### Proxy leagues
One file per league per season:
```
data/proxy/{league_code}_{season_label}_footballdata.csv
```
Example: `data/proxy/E1_2022-23_footballdata.csv`

### Scandinavian leagues
One file per league per season (split from the combined download):
```
data/scandinavian/{league_code}_{season_label}_footballdata.csv
```
Example: `data/scandinavian/SWE_2023_footballdata.csv`

Note: Scandinavian season labels use a single year (e.g. "2023"), not a hyphenated range, because they run on a calendar year.

---

## Output Schema (same for both proxy and Scandinavian)

Each output CSV must have exactly these columns, in this order:

```
date, home_team, away_team,
home_goals, away_goals, ht_home_goals, ht_away_goals,
home_shots, away_shots, home_sot, away_sot,
home_corners, away_corners, home_fouls, away_fouls,
home_yellow, away_yellow, home_red, away_red,
odds_home, odds_draw, odds_away,
odds_btts_yes, odds_btts_no,
odds_over25, odds_under25,
odds_ah_line, odds_ah_home, odds_ah_away,
league, season
```

### Column mapping from football-data.co.uk raw columns

| Output column | Raw column | Notes |
|---|---|---|
| date | Date | Parse as date, output as YYYY-MM-DD string |
| home_team | HomeTeam | |
| away_team | AwayTeam | |
| home_goals | FTHG | |
| away_goals | FTAG | |
| ht_home_goals | HTHG | |
| ht_away_goals | HTAG | |
| home_shots | HS | |
| away_shots | AS | |
| home_sot | HST | |
| away_sot | AST | |
| home_corners | HC | |
| away_corners | AC | |
| home_fouls | HF | |
| away_fouls | AF | |
| home_yellow | HY | |
| away_yellow | AY | |
| home_red | HR | |
| away_red | AR | |
| odds_home | B365H | Use B365 as primary. Fall back to AvgH if B365H missing. |
| odds_draw | B365D | Fall back to AvgD |
| odds_away | B365A | Fall back to AvgA |
| odds_btts_yes | (none) | Output NaN — not reliably available. Will be derived from scorelines. |
| odds_btts_no | (none) | Output NaN — same reason. |
| odds_over25 | B365>2.5 | Fall back to Avg>2.5 |
| odds_under25 | B365<2.5 | Fall back to Avg<2.5 |
| odds_ah_line | AHh | The handicap line value |
| odds_ah_home | B365AHH | Fall back to AvgAHH |
| odds_ah_away | B365AHA | Fall back to AvgAHA |
| league | (added) | The league code string, e.g. "E1" |
| season | (added) | The season label string, e.g. "2022-23" |

If a raw column is missing entirely from the CSV (some leagues lack shot data in early seasons), output NaN for that column — do not drop the row.

---

## Logic Requirements

### Date parsing
football-data.co.uk uses inconsistent date formats across seasons. Handle all of:
- `DD/MM/YY` (e.g. 05/08/23)
- `DD/MM/YYYY` (e.g. 05/08/2023)

Use `pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")` and format output as `YYYY-MM-DD`.

### Row filtering
Drop rows where Date, HomeTeam, or AwayTeam is null. These are blank footer rows that sometimes appear in football-data.co.uk files.

### Odds fallback logic
For each odds column, try the primary column first. If it's missing or all-NaN, try the fallback. If both missing, output NaN.

### Scandinavian season splitting
The new-format CSVs include a "Season" column with values like "2023" or "2023/2024". Normalise to a single year label:
- If the value is already a 4-digit year (e.g. "2023"), use as-is.
- If it's in "YYYY/YYYY" format, take the first year.
Split the combined dataframe into one file per season after normalisation.

### Rate limiting
Sleep 1.5 seconds between requests. Print progress to console (`Fetching E1 2022-23...`).

### Error handling
If a URL returns a non-200 status or the file is empty, print a warning and continue. Do not crash. Record failed downloads in a list and print a summary at the end.

### Directory creation
Create output directories if they don't exist (`os.makedirs(..., exist_ok=True)`).

---

## Script Entry Point

The script should be runnable directly:
```
python experiment/load_footballdata.py
```

It should also accept optional CLI arguments:
- `--leagues E1 N1` — only download specific proxy leagues (default: all)
- `--seasons 2022-23 2023-24` — only download specific seasons (default: all)
- `--scandinavian-only` — skip proxy leagues, only download Scandinavian leagues
- `--proxy-only` — skip Scandinavian leagues, only download proxy leagues

---

## Expected Console Output

```
=== football-data.co.uk Loader ===
Fetching proxy leagues...
  E1 2000-01... 378 rows
  E1 2001-02... 391 rows
  ...
  T1 2017-18... 306 rows
  ...

Fetching Scandinavian leagues...
  FIN (all seasons)... splitting into 14 season files
  SWE (all seasons)... splitting into 14 season files
  ...

=== Summary ===
Proxy leagues: 142 files, 48,231 rows total
Scandinavian leagues: 52 files, 14,890 rows total
Failed downloads: none

Output: data/proxy/ and data/scandinavian/
```

---

## Validation Checks (run at end of script)

After all files are saved, run these checks and print results:

1. **Row count sanity:** Championship seasons should have 552 rows (46 games × 12... no, 24 teams × 23 home games = 552). Flag any season file with fewer than 100 rows as suspicious.
2. **Shot data coverage:** For each league, print the percentage of rows where `home_shots` is not NaN. Early seasons may be 0% — that is expected and fine, but it should be visible.
3. **Odds coverage:** For each league, print the percentage of rows where `odds_home` is not NaN.
4. **Date range:** Print the earliest and latest date in each league's data.

---

## Colab QC Instructions

After running the script, verify in Colab:

```python
import pandas as pd

# Check a proxy league
df = pd.read_csv("data/proxy/E1_2022-23_footballdata.csv")
print(df.shape)           # Should be ~552 rows, 32 columns
print(df.columns.tolist())  # Verify schema matches spec
print(df.head(3))
print(df.isnull().sum())  # Check which columns have NaNs

# Verify no shot data in very early seasons (expected)
df_old = pd.read_csv("data/proxy/E1_2000-01_footballdata.csv")
print(df_old["home_shots"].isna().all())  # May be True — fine

# Check a Scandinavian league
df_scand = pd.read_csv("data/scandinavian/SWE_2023_footballdata.csv")
print(df_scand.shape)
print(df_scand["season"].unique())  # Should be ["2023"]
print(df_scand[["date","home_team","away_team","home_goals","away_goals","odds_home"]].head(5))
```

Expected: E1 2022-23 has ~552 rows. Scandinavian files have 180-240 rows per season (16-18 teams). All files have the 32-column schema regardless of which columns are NaN.
