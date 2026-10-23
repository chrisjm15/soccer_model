# Prompt: poisson.py — Scoring Probability Model

## How to run this
1. Open your terminal and run: `ollama run gemma4:26b-16k`
2. Set model options when prompted:
   - `temperature: 0.2`
   - `num_predict: 4096`
3. Paste everything from the **PROMPT START** line to the **PROMPT END** line.

> **Why Gemma for this module?** The Poisson math must be correct. Gemma 4 26B is used for correctness-critical modules.

---

## PROMPT START — COPY EVERYTHING BELOW THIS LINE

You are writing a single Python module: `model/poisson.py`. This is a pure math module — no file I/O. Your job is ONLY to write this one file. Do not write any other files.

---

## What this module does

Given two teams' attack and defence ratings (in xG per match), it computes:
1. Expected goals (λ) for each team
2. A full goal probability grid (home_goals × away_goals)
3. Market probabilities: BTTS Yes/No, Home Win/Draw/Away Win, Over 2.5/Under 2.5

This module is called once per match by the BTTS prediction module.

---

## Inputs (all floats, all in xG per match units)

- `home_attack` — home team's home attack rating (how many xG they generate at home)
- `home_defence` — home team's home defence rating (how many xG they concede at home)
- `away_attack` — away team's away attack rating (how many xG they generate away)
- `away_defence` — away team's away defence rating (how many xG they concede away)
- `home_advantage` — optional float, additive xG bump for home team (default 0.0; already partially baked into ratings, so use sparingly)
- `max_goals` — maximum goals per team to compute in grid (default 8; grid is (max_goals+1) × (max_goals+1))

---

## Lambda computation

```
lambda_home = (home_attack + away_defence) / 2.0 + home_advantage
lambda_away = (away_attack + home_defence) / 2.0
```

Rationale: λ_home averages what the home team tends to score at home and what the away team tends to concede away. This blends both teams' contributions.

Clamp both lambdas to a minimum of 0.1 to avoid degenerate Poisson distributions.

---

## Goal probability grid

The model uses **independent Poisson** for each team:

```
P(home = h) = poisson_pmf(h, lambda_home)
P(away = a) = poisson_pmf(a, lambda_away)
P(home = h, away = a) = P(home = h) * P(away = a)
```

Build a (max_goals+1) × (max_goals+1) matrix where `grid[h][a]` = P(home scores h, away scores a).

**Normalise the grid** so it sums to 1.0. This corrects for the truncation at max_goals.

---

## Market probabilities

From the normalised grid, compute:

**BTTS:**
```
P(BTTS Yes) = sum of grid[h][a] for all h >= 1 and a >= 1
P(BTTS No)  = 1 - P(BTTS Yes)
```

**Win/Draw/Loss:**
```
P(Home Win) = sum of grid[h][a] for all h > a
P(Draw)     = sum of grid[h][a] for all h == a
P(Away Win) = sum of grid[h][a] for all h < a
```

**Over/Under 2.5 goals:**
```
P(Over 2.5)  = sum of grid[h][a] for all h + a > 2
P(Under 2.5) = sum of grid[h][a] for all h + a <= 2
```

---

## Return value

The function returns a dict:

```python
{
    'lambda_home': float,
    'lambda_away': float,
    'prob_btts_yes': float,
    'prob_btts_no': float,
    'prob_home_win': float,
    'prob_draw': float,
    'prob_away_win': float,
    'prob_over_25': float,
    'prob_under_25': float,
    'goal_grid': list  # (max_goals+1) x (max_goals+1) nested list, normalised
}
```

All probabilities must be between 0.0 and 1.0. The three market pairs (btts, wdl, o/u) must each sum to 1.0 within floating point tolerance.

---

## Code structure

```python
import math
from typing import Optional

def poisson_pmf(k: int, lam: float) -> float:
    """Poisson probability mass function: P(X = k) given rate lam."""
    # Use math.exp and math.factorial. Handle edge cases (k < 0, lam <= 0).

def compute_match_probs(
    home_attack: float,
    home_defence: float,
    away_attack: float,
    away_defence: float,
    home_advantage: float = 0.0,
    max_goals: int = 8
) -> dict:
    """
    Compute match outcome probabilities using independent Poisson model.
    
    Returns dict with lambda_home, lambda_away, prob_btts_yes, prob_btts_no,
    prob_home_win, prob_draw, prob_away_win, prob_over_25, prob_under_25, goal_grid.
    """

if __name__ == '__main__':
    # --- Test 1: Symmetric match ---
    result = compute_match_probs(
        home_attack=1.6, home_defence=1.3,
        away_attack=1.3, away_defence=1.6,
        home_advantage=0.0
    )
    print("Test 1 — Symmetric-ish match:")
    print(f"  lambda_home = {result['lambda_home']:.4f}, lambda_away = {result['lambda_away']:.4f}")
    print(f"  P(BTTS Yes) = {result['prob_btts_yes']:.4f}  (expected ~0.48-0.56)")
    print(f"  P(Home Win) = {result['prob_home_win']:.4f}")
    print(f"  P(Draw)     = {result['prob_draw']:.4f}")
    print(f"  P(Away Win) = {result['prob_away_win']:.4f}")
    print(f"  WDL sum     = {result['prob_home_win'] + result['prob_draw'] + result['prob_away_win']:.6f}  (must be 1.0)")
    print(f"  P(Over 2.5) = {result['prob_over_25']:.4f}")

    # --- Test 2: High-scoring match ---
    result2 = compute_match_probs(
        home_attack=2.0, home_defence=2.0,
        away_attack=2.0, away_defence=2.0,
    )
    print("\nTest 2 — High-scoring match (lambda ~2.0 each):")
    print(f"  P(BTTS Yes) = {result2['prob_btts_yes']:.4f}  (expected ~0.73)")
    # P(BTTS Yes) = (1 - e^-2.0)^2 = (1 - 0.1353)^2 = 0.8647^2 = 0.748
    
    # --- Test 3: Defensive match ---
    result3 = compute_match_probs(
        home_attack=1.0, home_defence=0.8,
        away_attack=0.8, away_defence=1.0,
    )
    print("\nTest 3 — Defensive match (lambda ~0.9 each):")
    print(f"  P(BTTS Yes) = {result3['prob_btts_yes']:.4f}  (expected ~0.33)")
    # P(BTTS Yes) = (1 - e^-0.9)^2 = (1 - 0.4066)^2 = 0.5934^2 = 0.352

    # --- Test 4: Verify all probs in [0,1] and sums correct ---
    for test_name, res in [('T1', result), ('T2', result2), ('T3', result3)]:
        btts_sum = res['prob_btts_yes'] + res['prob_btts_no']
        wdl_sum = res['prob_home_win'] + res['prob_draw'] + res['prob_away_win']
        ou_sum = res['prob_over_25'] + res['prob_under_25']
        assert abs(btts_sum - 1.0) < 1e-6, f"{test_name} BTTS sums to {btts_sum}"
        assert abs(wdl_sum - 1.0) < 1e-6, f"{test_name} WDL sums to {wdl_sum}"
        assert abs(ou_sum - 1.0) < 1e-6, f"{test_name} O/U sums to {ou_sum}"
    print("\nAll sum checks passed.")
```

---

## Implementation notes

- Do NOT use scipy. Use only Python standard library (`math` module) so there are no external dependencies.
- The `poisson_pmf` function must handle `k=0` correctly: `P(X=0) = e^(-lam)`.
- Use `math.lgamma` for large factorials if needed (more numerically stable than `math.factorial` for large k).
- The grid normalisation step: after building the raw grid, divide every cell by the total sum.
- All probabilities in the returned dict must be computed from the normalised grid (not directly from the lambda formulas), to ensure internal consistency.

---

## PROMPT END — STOP COPYING HERE
