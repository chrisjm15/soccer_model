# Qwen3-Coder Prompt — model/markets.py

## How to run
1. Press Windows key, type `Terminal`, press Enter
2. Type: `ollama run qwen3-coder:30b-16k`
3. Wait for the `>>>` prompt
4. Paste everything below the --- line

---

/no_think

Write a new Python file: `model/markets.py`

This file adds market prediction functions for 1X2, Over/Under 2.5, and Asian Handicap. It sits alongside the existing `model/btts.py` and uses the same `compute_match_probs()` output from `model/poisson.py`.

---

## Context you need

`model/poisson.py` exports `compute_match_probs()` which returns this dict:

```python
{
    'lambda_home': float,
    'lambda_away': float,
    'prob_home_win': float,
    'prob_draw': float,
    'prob_away_win': float,
    'prob_over_25': float,
    'prob_under_25': float,
    'prob_btts_yes': float,
    'prob_btts_no': float,
    'goal_grid': list[list[float]]  # grid[h][a] = P(home=h, away=a), normalised, max_goals=8
}
```

The `goal_grid` is indexed `grid[home_goals][away_goals]` from 0 to 8.

Historical data columns available for backtesting (all 100% filled):
- `odds_home`, `odds_draw`, `odds_away` — B365 1X2 odds
- `odds_over25`, `odds_under25` — B365 O/U 2.5 odds
- `ah_line` — Asian handicap line from home team's perspective (e.g. -1.0 means home gives 1 goal, +0.5 means home receives 0.5 goals)
- `odds_ah_home`, `odds_ah_away` — AH odds for home and away

---

## What to build

### Function 1: `compute_ah_probs(goal_grid, ah_line)`

Computes Asian Handicap probabilities for the home team at a given line.

```python
def compute_ah_probs(goal_grid: list, ah_line: float) -> dict:
    """
    Returns P(AH home wins), P(push), P(AH away wins) for a given handicap line.

    ah_line is from the home team's perspective:
      -1.0 = home gives 1 goal (needs to win by 2+ to win AH)
      +0.5 = home receives 0.5 goal (wins AH if match result is home win or draw)

    Handles three line types:
      - Half lines (-0.5, -1.5, 2.5 etc): no push possible
      - Whole lines (-1.0, -2.0, 1.0 etc): push when margin == |line|
      - Quarter lines (-0.25, -0.75, -1.25, -1.75 etc): split stake
        A quarter line is the average of two adjacent half/whole lines.
        e.g. -1.75 = average of -1.5 and -2.0
        Return weighted average of those two lines' outcomes.

    Returns:
        {
            'p_home': float,   # P(AH home wins)
            'p_push': float,   # P(push / stake returned) — 0.0 for half lines
            'p_away': float,   # P(AH away wins)
        }
    """
```

Logic for whole/half lines:
- Let `margin = home_goals - away_goals`
- Home wins AH if: `margin > -ah_line` (e.g. ah_line=-1.0 → margin > 1 → margin >= 2)
- Push (whole lines only) if: `margin == -ah_line` (e.g. ah_line=-1.0 → margin == 1)
- Away wins AH if: `margin < -ah_line`

For quarter lines: detect by checking if `(ah_line * 4) % 2 == 1` (i.e. not divisible by 0.5). Split into two adjacent lines and average the results.

---

### Function 2: `predict_1x2`

```python
def predict_1x2(
    probs: dict,
    odds_home: float,
    odds_draw: float,
    odds_away: float,
    edge_threshold: float = 0.05
) -> dict:
    """
    Predicts 1X2 market edge.

    For each outcome, edge = model_prob - implied_prob (where implied = 1/odds).
    Flag the single best-edge outcome if it exceeds edge_threshold.
    If multiple outcomes exceed threshold, flag only the highest-edge one.

    Returns:
        {
            'edge_home': float,
            'edge_draw': float,
            'edge_away': float,
            'best_outcome': str,       # 'home', 'draw', 'away', or None
            'best_edge': float,        # edge of best_outcome (or 0.0)
            'best_odds': float,        # odds of best_outcome (or None)
            'best_model_prob': float,  # model prob of best_outcome (or None)
            'should_bet': bool,
            'ev': float,               # EV of best_outcome per unit staked (or 0.0)
        }
    """
```

EV formula: `ev = model_prob * (odds - 1) - (1 - model_prob)`

---

### Function 3: `predict_over_under`

```python
def predict_over_under(
    probs: dict,
    odds_over: float,
    odds_under: float,
    edge_threshold: float = 0.05
) -> dict:
    """
    Predicts Over/Under 2.5 market edge.
    Only considers betting Over (consistent with current model approach).

    Returns:
        {
            'edge_over': float,
            'implied_over': float,
            'model_prob_over': float,
            'should_bet': bool,
            'ev': float,
            'odds_over': float,
        }
    """
```

---

### Function 4: `predict_asian_handicap`

```python
def predict_asian_handicap(
    probs: dict,
    ah_line: float,
    odds_ah_home: float,
    odds_ah_away: float,
    edge_threshold: float = 0.05
) -> dict:
    """
    Predicts Asian Handicap market edge for home and away sides.

    Uses compute_ah_probs() internally.

    For edge calculation with push, use:
        ev_home = p_home * (odds_ah_home - 1) - p_away
        ev_away = p_away * (odds_ah_away - 1) - p_home
        (push contributes 0 EV — stake returned)

    For implied prob comparison, treat as two-outcome market:
        implied_home = 1 / odds_ah_home
        edge_home = p_home - implied_home   [approximation, ignoring push]

    Flag the best side if edge >= threshold.

    Returns:
        {
            'p_ah_home': float,
            'p_push': float,
            'p_ah_away': float,
            'edge_ah_home': float,
            'edge_ah_away': float,
            'best_side': str,        # 'home', 'away', or None
            'best_edge': float,
            'best_odds': float,
            'should_bet': bool,
            'ev': float,
            'ah_line': float,
        }
    """
```

---

## Full file structure

```python
"""
model/markets.py — Market prediction output layers.

Uses output from model.poisson.compute_match_probs().
Provides prediction functions for 1X2, Over/Under 2.5, and Asian Handicap.
"""
from model.poisson import compute_match_probs

DEFAULT_EDGE_THRESHOLD = 0.05


def compute_ah_probs(goal_grid: list, ah_line: float) -> dict:
    ...

def predict_1x2(probs, odds_home, odds_draw, odds_away, edge_threshold=DEFAULT_EDGE_THRESHOLD) -> dict:
    ...

def predict_over_under(probs, odds_over, odds_under, edge_threshold=DEFAULT_EDGE_THRESHOLD) -> dict:
    ...

def predict_asian_handicap(probs, ah_line, odds_ah_home, odds_ah_away, edge_threshold=DEFAULT_EDGE_THRESHOLD) -> dict:
    ...


if __name__ == '__main__':
    # Self-test: one match, all three markets
    probs = compute_match_probs(
        home_attack=1.8, home_defence=1.2,
        away_attack=1.2, away_defence=1.6,
        home_advantage=0.15
    )

    r1x2 = predict_1x2(probs, odds_home=2.10, odds_draw=3.40, odds_away=3.60)
    rou = predict_over_under(probs, odds_over=1.85, odds_under=2.00)
    rah = predict_asian_handicap(probs, ah_line=-0.5, odds_ah_home=1.95, odds_ah_away=1.95)

    print("=== 1X2 ===")
    print(f"  edge home={r1x2['edge_home']:+.3f}, draw={r1x2['edge_draw']:+.3f}, away={r1x2['edge_away']:+.3f}")
    print(f"  best={r1x2['best_outcome']}, edge={r1x2['best_edge']:+.3f}, should_bet={r1x2['should_bet']}")

    print("=== O/U 2.5 ===")
    print(f"  model_prob_over={rou['model_prob_over']:.3f}, implied={rou['implied_over']:.3f}")
    print(f"  edge={rou['edge_over']:+.3f}, should_bet={rou['should_bet']}")

    print("=== Asian Handicap (-0.5) ===")
    print(f"  p_home={rah['p_ah_home']:.3f}, p_push={rah['p_push']:.3f}, p_away={rah['p_ah_away']:.3f}")
    print(f"  edge_home={rah['edge_ah_home']:+.3f}, best={rah['best_side']}, should_bet={rah['should_bet']}")

    # Sanity check: AH probs sum to 1
    assert abs(rah['p_ah_home'] + rah['p_push'] + rah['p_ah_away'] - 1.0) < 1e-6, "AH probs must sum to 1"
    print("\nAll checks passed.")
```

---

## Constraints
- `temperature: 0.2`
- `num_predict: 4096`
- No external dependencies beyond standard library and `model/poisson.py`
- All functions must work correctly with the full quarter-line AH logic
- Do not modify `model/poisson.py` or any other existing file
- Output only the complete `model/markets.py` file, nothing else
