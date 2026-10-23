# Prompt: btts.py — BTTS Market Predictions

## How to run this
1. Open your terminal and run: `ollama run qwen3-coder:30b-16k`
2. Set model options when prompted:
   - `temperature: 0.2`
   - `num_predict: 4096`
3. Paste everything from the **PROMPT START** line to the **PROMPT END** line.

---

## PROMPT START — COPY EVERYTHING BELOW THIS LINE

/no_think

You are writing a single Python module: `model/btts.py`. Your job is ONLY to write this one file. Do not write any other files.

---

## What this module does

This module takes pre-computed match ratings and produces BTTS (Both Teams To Score) predictions. It wraps the Poisson probability model and adds:
- Edge calculation (model probability vs market implied probability)
- Bet flagging (when edge exceeds a threshold)
- A batch function to run predictions across a full DataFrame

---

## Dependencies

This module imports from `model/poisson.py`, which is already written. The import is:

```python
from model.poisson import compute_match_probs
```

The `compute_match_probs` function signature:
```python
def compute_match_probs(
    home_attack: float,
    home_defence: float,
    away_attack: float,
    away_defence: float,
    home_advantage: float = 0.0,
    max_goals: int = 8
) -> dict:
```

It returns a dict with keys including: `lambda_home`, `lambda_away`, `prob_btts_yes`, `prob_btts_no`, `prob_home_win`, `prob_draw`, `prob_away_win`, `prob_over_25`, `prob_under_25`.

---

## Constants (at top of file, configurable)

```python
ASSUMED_BTTS_ODDS = 1.90        # Used when no market odds available (typical bookmaker price)
DEFAULT_EDGE_THRESHOLD = 0.05   # 5% minimum edge to flag as a bet
```

---

## Core function: predict_match

```python
def predict_match(
    home_attack: float,
    home_defence: float,
    away_attack: float,
    away_defence: float,
    home_advantage: float = 0.0,
    btts_odds_yes: float = ASSUMED_BTTS_ODDS,
    edge_threshold: float = DEFAULT_EDGE_THRESHOLD
) -> dict:
```

**Steps inside this function:**

1. Call `compute_match_probs(home_attack, home_defence, away_attack, away_defence, home_advantage)` to get probabilities.

2. Compute the implied probability from the market odds:
   ```
   implied_prob = 1.0 / btts_odds_yes
   ```

3. Compute the edge:
   ```
   edge = prob_btts_yes - implied_prob
   ```

4. Flag whether to bet:
   ```
   should_bet = (edge >= edge_threshold)
   ```

5. Compute the expected value (EV) of a 1-unit bet at those odds:
   ```
   expected_value = prob_btts_yes * (btts_odds_yes - 1.0) - (1.0 - prob_btts_yes) * 1.0
   ```
   This is: (prob of winning * profit) - (prob of losing * stake). Positive EV means the bet has positive expected return.

6. Return a dict:
```python
{
    'lambda_home': float,
    'lambda_away': float,
    'prob_btts_yes': float,
    'prob_btts_no': float,
    'implied_prob': float,
    'edge': float,
    'expected_value': float,
    'should_bet': bool,
    'btts_odds_yes': float,
    'prob_home_win': float,
    'prob_draw': float,
    'prob_away_win': float,
    'prob_over_25': float,
    'prob_under_25': float,
}
```

---

## Batch function: run_predictions

```python
def run_predictions(
    ratings_df: pd.DataFrame,
    home_advantage_by_league: dict,
    btts_odds_yes: float = ASSUMED_BTTS_ODDS,
    edge_threshold: float = DEFAULT_EDGE_THRESHOLD
) -> pd.DataFrame:
```

**Inputs:**
- `ratings_df` — DataFrame with columns: `date`, `league`, `season`, `home_team`, `away_team`, `home_attack`, `home_defence`, `away_attack`, `away_defence`
  - This is the output of `model/ratings.py`
- `home_advantage_by_league` — dict mapping league name to home advantage xG value, e.g.:
  ```python
  {'EPL': 0.0, 'La_Liga': 0.0, 'Bundesliga': 0.0, 'Serie_A': 0.0, 'Ligue_1': 0.0}
  ```
  (Home advantage is set to 0.0 by default because it is already embedded in the home/away split ratings. Pass non-zero values to tune later.)
- `btts_odds_yes` — assumed market odds (default 1.90)
- `edge_threshold` — minimum edge to flag (default 0.05)

**Steps:**
1. For each row in `ratings_df`, look up the league's home advantage from `home_advantage_by_league` (default 0.0 if league not found).
2. Call `predict_match` with the row's ratings and the league's home advantage.
3. Build an output row that includes all original columns from `ratings_df` plus all keys from `predict_match`'s return dict.
4. Return the full DataFrame of predictions.

**Do not modify `ratings_df` in place. Return a new DataFrame.**

---

## Main block

```python
if __name__ == '__main__':
    import pandas as pd

    # Standalone test — simulate two matches
    test_matches = [
        {
            'date': '2024-01-15', 'league': 'EPL', 'season': '2023-24',
            'home_team': 'Arsenal', 'away_team': 'Chelsea',
            'home_attack': 2.1, 'home_defence': 1.0,
            'away_attack': 1.5, 'away_defence': 1.3,
        },
        {
            'date': '2024-01-15', 'league': 'EPL', 'season': '2023-24',
            'home_team': 'Burnley', 'away_team': 'Brentford',
            'home_attack': 0.9, 'home_defence': 1.8,
            'away_attack': 1.4, 'away_defence': 1.5,
        },
    ]
    df = pd.DataFrame(test_matches)
    home_adv = {'EPL': 0.0}

    results = run_predictions(df, home_adv)
    for _, row in results.iterrows():
        print(f"{row['home_team']} vs {row['away_team']}")
        print(f"  lambda_home={row['lambda_home']:.3f}, lambda_away={row['lambda_away']:.3f}")
        print(f"  P(BTTS Yes)={row['prob_btts_yes']:.3f}, implied={row['implied_prob']:.3f}, edge={row['edge']:+.3f}")
        print(f"  EV={row['expected_value']:+.4f}, Bet={row['should_bet']}")
        print()
```

---

## Implementation notes

- Use `pandas` for the DataFrame work.
- The function must not crash if `home_advantage_by_league` does not contain a key for a given league — use `.get(league, 0.0)`.
- Avoid iterrows in `run_predictions` if possible — but correctness over performance. If you use iterrows, that is fine.

---

## PROMPT END — STOP COPYING HERE
