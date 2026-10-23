# Gemma Prompt — backtest/multi_market_engine.py

## How to run
1. Press Windows key, type `Terminal`, press Enter
2. Type: `ollama run gemma4:26b-16k`
3. Wait for the `>>>` prompt
4. Paste everything below the --- line

## Important
Run this AFTER `model/markets.py` has been created by Qwen3-Coder.

---

Write a new Python file: `backtest/multi_market_engine.py`

This file runs a historical backtest comparing three markets — 1X2, Over/Under 2.5, and Asian Handicap — against real historical odds. It uses the existing ratings and merged data already in the project.

---

## Existing files to understand

### data/processed/ratings.csv
Columns include: `date, league, season, home_team, away_team, home_attack, home_defence, away_attack, away_defence`
Pre-match ratings, lookahead-safe (computed using only data available before each match).

### data/processed/all_merged.csv  
All matches with actual results AND real historical odds. Key columns:
- `date, league, season, home_team, away_team`
- `home_goals, away_goals`
- `odds_home, odds_draw, odds_away` — 1X2 odds
- `odds_over25, odds_under25` — O/U 2.5 odds
- `ah_line, odds_ah_home, odds_ah_away` — Asian Handicap odds and line
- `home_corners, away_corners, home_yellow, away_yellow` (not needed here)

### config/leagues.yaml
Has `home_advantage_xg` per league. Load with yaml.safe_load().

### model/markets.py (newly created by Qwen3)
Exports:
- `compute_ah_probs(goal_grid, ah_line) -> dict`
- `predict_1x2(probs, odds_home, odds_draw, odds_away, edge_threshold) -> dict`
- `predict_over_under(probs, odds_over, odds_under, edge_threshold) -> dict`
- `predict_asian_handicap(probs, ah_line, odds_ah_home, odds_ah_away, edge_threshold) -> dict`

### model/poisson.py
Exports `compute_match_probs(home_attack, home_defence, away_attack, away_defence, home_advantage) -> dict`

---

## What to build

### Main function: `run_multi_market_backtest()`

```python
def run_multi_market_backtest(
    ratings_path: str = 'data/processed/ratings.csv',
    merged_path: str = 'data/processed/all_merged.csv',
    leagues_config_path: str = 'config/leagues.yaml',
    train_seasons: list = None,     # default: ['2020-21','2021-22','2022-23']
    test_seasons: list = None,      # default: ['2023-24','2024-25','2025-26']
    edge_threshold: float = 0.05,
    output_dir: str = 'output/backtest_results'
) -> dict:
```

### Step-by-step logic

**Step 1: Load data**
- Load ratings.csv and all_merged.csv
- Load leagues.yaml for home_advantage_xg per league
- Parse dates

**Step 2: Filter to test seasons**
- Only run predictions on matches in test_seasons
- Join ratings to merged data on: date + league + season + home_team + away_team
- Drop rows with no rating (unmatched teams)
- Drop rows with any null odds (odds_home, odds_over25, ah_line, odds_ah_home, odds_ah_away must all be present)

**Step 3: For each match, run all three market predictions**

```python
for each matched row:
    probs = compute_match_probs(
        home_attack=row.home_attack,
        home_defence=row.home_defence,
        away_attack=row.away_attack,
        away_defence=row.away_defence,
        home_advantage=home_advantage_by_league[row.league]
    )

    r_1x2 = predict_1x2(probs, row.odds_home, row.odds_draw, row.odds_away, edge_threshold)
    r_ou  = predict_over_under(probs, row.odds_over25, row.odds_under25, edge_threshold)
    r_ah  = predict_asian_handicap(probs, row.ah_line, row.odds_ah_home, row.odds_ah_away, edge_threshold)
```

**Step 4: Compute actual outcomes for each market**

```python
# 1X2
actual_result = 'home' if home_goals > away_goals else ('draw' if home_goals == away_goals else 'away')

# O/U 2.5
actual_over25 = 1 if (home_goals + away_goals) > 2 else 0

# AH — compute whether home team won/pushed/lost at the historical ah_line
# Use compute_ah_probs logic in reverse: compare actual margin to line
margin = home_goals - away_goals
ah_result = compute_actual_ah_result(margin, ah_line)
# Returns: 'home_win', 'push', 'away_win'
```

Write a helper function `compute_actual_ah_result(margin, ah_line)`:
- For half lines: 'home_win' if margin > -ah_line, else 'away_win'
- For whole lines: 'home_win' if margin > -ah_line, 'push' if margin == -ah_line, else 'away_win'
- For quarter lines (e.g. -1.75 = split between -1.5 and -2.0):
  - Compute result for each half separately
  - If both halves are the same result: return that result
  - If one is win and one is push: return 'half_win'
  - If one is loss and one is push: return 'half_loss'
  - If one is win and one is loss: return 'push' (net zero)

**Step 5: Compute P&L for each market**

For 1X2 bets (flat $1 stake on each flagged bet):
```python
if r_1x2['should_bet']:
    if actual_result == r_1x2['best_outcome']:
        pnl_1x2 = r_1x2['best_odds'] - 1   # win
    else:
        pnl_1x2 = -1.0                       # loss
```

For O/U 2.5 bets:
```python
if r_ou['should_bet']:
    if actual_over25 == 1:
        pnl_ou = r_ou['odds_over'] - 1
    else:
        pnl_ou = -1.0
```

For AH bets (handle push and half-win/half-loss):
```python
if r_ah['should_bet']:
    side = r_ah['best_side']
    odds = r_ah['best_odds']
    
    # Determine which AH result applies to our bet side
    if side == 'home':
        bet_result = ah_result  # 'home_win', 'push', 'away_win', 'half_win', 'half_loss'
    else:
        # Flip result for away bet
        flip = {'home_win': 'away_win', 'away_win': 'home_win', 'push': 'push',
                'half_win': 'half_loss', 'half_loss': 'half_win'}
        bet_result = flip[ah_result]
    
    if bet_result == 'home_win':
        pnl_ah = odds - 1
    elif bet_result == 'push':
        pnl_ah = 0.0
    elif bet_result == 'away_win':
        pnl_ah = -1.0
    elif bet_result == 'half_win':
        pnl_ah = (odds - 1) * 0.5    # half stake wins, half returned
    elif bet_result == 'half_loss':
        pnl_ah = -0.5                  # half stake loses, half returned
```

**Step 6: Compute and print metrics for each market**

For each market, compute:
- Total bets flagged
- Hit rate (% of flagged bets that won, excluding pushes)
- Total P&L (sum of pnl)
- ROI = total P&L / total bets * 100
- Break-even hit rate = 1 / average_odds
- Brier score for the relevant probability (model_prob vs actual outcome)
- Results by league
- Results by season

**Step 7: Save outputs**

1. `output/backtest_results/multi_market_predictions.csv` — one row per match, all three markets' predictions and P&L
2. `output/backtest_results/multi_market_report.txt` — formatted text report

---

## Report format

```
==================================================
  MULTI-MARKET BACKTEST RESULTS
==================================================
Test period: 2023-24 to 2025-26
Total matches evaluated: XXXX

--------------------------------------------------
MARKET: 1X2
--------------------------------------------------
Total bets: XXXX (XX.X% of matches)
Hit rate:   XX.X%  (break-even: XX.X%)
Total P&L:  +XXX.XX units
ROI:        +XX.X%
Brier score: X.XXXX

By league:
  EPL        : XXX bets, hit=XX.X%, ROI=XX.X%
  ...

By season:
  2023-24: XXX bets, hit=XX.X%, ROI=XX.X%
  ...

--------------------------------------------------
MARKET: Over/Under 2.5 (Over only)
--------------------------------------------------
[same format]

--------------------------------------------------
MARKET: Asian Handicap (best side)
--------------------------------------------------
[same format — note: pushes excluded from hit rate denominator]

==================================================
SUMMARY COMPARISON
==================================================
Market          Bets    Hit%   ROI      Brier
1X2             XXXX   XX.X%  +XX.X%   X.XXXX
Over/Under 2.5  XXXX   XX.X%  +XX.X%   X.XXXX
Asian Handicap  XXXX   XX.X%  +XX.X%   X.XXXX

Best market by ROI: [market name]
==================================================
```

---

## Constraints
- `temperature: 0.2`
- `num_predict: 4096`
- Brier score formula: `mean((model_prob - actual_outcome)^2)` over all matches (not just flagged)
- ROI = total_pnl / num_bets (not num_matches)
- Do not modify any existing files
- Handle missing odds rows gracefully (skip with a warning count)
- The `if __name__ == '__main__':` block should simply call `run_multi_market_backtest()` and print done
- Output only the complete `backtest/multi_market_engine.py` file, nothing else
