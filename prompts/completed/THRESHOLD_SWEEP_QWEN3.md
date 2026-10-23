# Qwen3-Coder Prompt — scripts/threshold_sweep.py

## How to run
1. Press Windows key, type `Terminal`, press Enter
2. Type: `ollama run qwen3-coder:30b-16k`
3. Wait for the `>>>` prompt
4. Paste everything below the --- line

---

/no_think

Write a new Python file: `scripts/threshold_sweep.py`

This script runs all match predictions once, stores the raw edge values for every match, then sweeps across multiple edge thresholds to find the optimal threshold for each market — without re-running the expensive Poisson calculations multiple times.

---

## Context

### Existing interfaces you must use exactly

`model/poisson.compute_match_probs(home_attack, home_defence, away_attack, away_defence, home_advantage)` returns a dict with keys including `prob_home_win`, `prob_draw`, `prob_away_win`, `prob_over_25`, `prob_under_25`, `goal_grid`.

`model/markets.py` exports:
- `predict_1x2(probs, odds_home, odds_draw, odds_away, edge_threshold=0.05)` — returns dict with `edge_home`, `edge_draw`, `edge_away`, `best_outcome`, `best_edge`, `best_odds`, `should_bet`, `ev`
- `predict_over_under(probs, odds_over, odds_under, edge_threshold=0.05)` — returns dict with `edge_over`, `implied_over`, `model_prob_over`, `should_bet`, `ev`, `odds_over`
- `predict_asian_handicap(probs, ah_line, odds_ah_home, odds_ah_away, edge_threshold=0.05)` — returns dict with `edge_ah_home`, `edge_ah_away`, `best_side`, `best_edge`, `best_odds`, `should_bet`, `ev`, `p_ah_home`, `p_push`, `p_ah_away`
- `compute_ah_probs(goal_grid, ah_line)` — returns `{p_home, p_push, p_away}`

### Data files
- `data/processed/ratings.csv` — columns: `date, league, season, home_team, away_team, home_attack, home_defence, away_attack, away_defence`
- `data/processed/all_merged.csv` — columns include: `date, league, season, home_team, away_team, home_goals, away_goals, odds_home, odds_draw, odds_away, odds_over25, odds_under25, ah_line, odds_ah_home, odds_ah_away`
- `config/leagues.yaml` — has `home_advantage_xg` per league nested under `leagues` key

### Test seasons to use
`['2023-24', '2024-25', '2025-26']`

### AH actual outcome helper
Use this exact function (already tested and correct):
```python
from math import floor, ceil

def compute_actual_ah_result(margin, ah_line):
    is_quarter = (ah_line * 2) % 1 != 0
    if not is_quarter:
        if margin > -ah_line: return 'home_win'
        elif margin == -ah_line: return 'push'
        else: return 'away_win'
    else:
        l1 = floor(ah_line * 2) / 2
        l2 = ceil(ah_line * 2) / 2
        def get_res(line):
            if margin > -line: return 'home_win'
            if margin == -line: return 'push'
            return 'away_win'
        res1, res2 = get_res(l1), get_res(l2)
        if res1 == res2: return res1
        results_set = {res1, res2}
        if 'push' in results_set:
            if 'home_win' in results_set: return 'half_win'
            if 'away_win' in results_set: return 'half_loss'
            return 'push'
        if 'home_win' in results_set and 'away_win' in results_set: return 'push'
        return res1
```

---

## What to build

### Step 1: Load and join data (same as multi_market_engine.py)

Load ratings and merged CSVs. Filter merged to test seasons. Inner join on `date, league, season, home_team, away_team`. Drop rows missing any of: `odds_home, odds_draw, odds_away, odds_over25, odds_under25, ah_line, odds_ah_home, odds_ah_away`.

Load `config/leagues.yaml` and build:
```python
leagues_ha = {league: data.get('home_advantage_xg', 0.0) for league, data in config['leagues'].items()}
```

### Step 2: Run all predictions once, store raw edge values

For every match, call `compute_match_probs` and both market functions with `edge_threshold=0.0` (so every match is "flagged" — we want raw edges, not filtered ones).

Store a record per match with:
```python
{
    'league': str,
    'season': str,
    'home_team': str,
    'away_team': str,
    # O/U 2.5
    'edge_ou': float,           # raw edge (no threshold applied)
    'odds_ou': float,           # odds_over25
    'pnl_ou_win': float,        # odds_over25 - 1  (profit if correct)
    'actual_ou': int,           # 1 if over 2.5 goals, 0 if under
    # Asian Handicap
    'edge_ah': float,           # best_edge (home or away, whichever is higher)
    'odds_ah': float,           # best_odds
    'best_side_ah': str,        # 'home' or 'away'
    'ah_line': float,
    'actual_ah': str,           # result of compute_actual_ah_result
}
```

For AH P&L at a given threshold, use this logic:
```python
def ah_pnl(actual_ah, best_side, odds):
    # Flip result if betting away
    result = actual_ah
    if best_side == 'away':
        flip = {'home_win': 'away_win', 'away_win': 'home_win', 'push': 'push',
                'half_win': 'half_loss', 'half_loss': 'half_win'}
        result = flip[actual_ah]
    if result == 'home_win': return odds - 1
    if result == 'push': return 0.0
    if result == 'away_win': return -1.0
    if result == 'half_win': return (odds - 1) * 0.5
    if result == 'half_loss': return -0.5
    return 0.0
```

### Step 3: Sweep thresholds

Thresholds to test: `[0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.12, 0.15]`

For each threshold and each market (O/U, AH), compute:
- Bets flagged (where edge >= threshold)
- Bets as % of total matches
- Hit rate (wins / non-push bets)
- Total P&L
- ROI = total_pnl / num_bets * 100

Compute this for TWO slices:
1. **All leagues combined**
2. **EPL only**

### Step 4: Output format

Print and save to `output/backtest_results/threshold_sweep.txt`:

```
==============================================================
  THRESHOLD SWEEP — O/U 2.5 (OVER) — ALL LEAGUES
==============================================================
Threshold  Bets    Bets%   Hit%    ROI
  3%       XXXX    XX.X%   XX.X%   +X.X%
  4%       XXXX    XX.X%   XX.X%   +X.X%
  5%       XXXX    XX.X%   XX.X%   +X.X%
  ...

==============================================================
  THRESHOLD SWEEP — O/U 2.5 (OVER) — EPL ONLY
==============================================================
[same format]

==============================================================
  THRESHOLD SWEEP — ASIAN HANDICAP — ALL LEAGUES
==============================================================
[same format]

==============================================================
  THRESHOLD SWEEP — ASIAN HANDICAP — EPL ONLY
==============================================================
[same format]

==============================================================
  SEASON-BY-SEASON — EPL ASIAN HANDICAP (at 8% threshold)
==============================================================
Season      Bets    Hit%    ROI
2023-24     XXX     XX.X%   +X.X%
2024-25     XXX     XX.X%   +X.X%
2025-26     XXX     XX.X%   +X.X%
```

The season-by-season breakdown at 8% is fixed — always show it at 8% regardless of what the sweep finds. This is the key consistency check.

---

## Constraints
- `temperature: 0.2`
- `num_predict: 4096`
- Run from project root (`cd` to project dir before running)
- `if __name__ == '__main__':` block just calls the main function and prints "Sweep complete. Results saved to output/backtest_results/threshold_sweep.txt"
- Do not modify any existing file
- Output only the complete `scripts/threshold_sweep.py` file, nothing else
