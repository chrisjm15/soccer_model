# CLI Prompt — Update run.py predict to EPL AH

## How to launch CLI
1. Press Windows key, type `Terminal`, press Enter
2. Paste and press Enter:
   ```
   cd "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
   ```
3. Paste and press Enter:
   ```
   claude --model claude-sonnet-4-6
   ```
4. Type: `/effort max`
5. Paste the prompt below.

---

Read `CLAUDE.md` and `SESSION_LOG_COWORK.md` before making any changes.

The live prediction pipeline in `run.py predict` currently outputs O/U 2.5 predictions. Based on the multi-market backtest, the target market has changed to **EPL Asian Handicap at 7% threshold**. Update the predict command accordingly.

**Chris has no coding background. Fix all errors automatically. Commit and push when done.**

---

### What needs changing

Read these files fully before touching anything:
- `run.py`
- `scrapers/odds_api.py`
- `model/markets.py` (new file — contains `predict_asian_handicap`)
- `model/live_ratings.py`
- `config/leagues.yaml`

---

### Changes required

**1. Filter to EPL only**

In `run.py predict`, after fetching odds from the Odds API, filter to EPL matches only before running any predictions. Skip all other leagues silently.

**2. Use AH market instead of O/U 2.5**

Replace the current O/U 2.5 prediction logic with `predict_asian_handicap` from `model/markets.py`:

```python
from model.markets import predict_asian_handicap

result = predict_asian_handicap(
    probs=probs,
    ah_line=match['ah_line'],        # AH line from odds API
    odds_ah_home=match['odds_ah_home'],
    odds_ah_away=match['odds_ah_away'],
    edge_threshold=0.07              # 7% threshold
)
```

**3. Check Odds API returns AH data for EPL**

Print the raw AH fields from the first EPL match to confirm the Odds API is returning `ah_line`, `odds_ah_home`, `odds_ah_away`. If these fields are missing or named differently, adapt the field names to match what the API actually returns.

If the Odds API does not return AH odds on the free tier, print a clear error message explaining this and stop — do not silently fall back to O/U 2.5.

**4. Update the output table**

New print format:
```
=== EPL ASIAN HANDICAP PREDICTIONS — [today's date] ===
Edge threshold: 7% | Market: Asian Handicap

FLAGGED BETS (edge >= 7%):
  Arsenal vs Chelsea    AH=-0.5  Side=Home  P(AH Home)=58.3%  Odds=1.92  Edge=+9.2%  EV=+0.089
  Liverpool vs Man Utd  AH=-1.0  Side=Home  P(AH Home)=63.1%  Odds=1.88  Edge=+7.8%  EV=+0.075

ALL EPL MATCHES THIS WEEK:
  [full table sorted by edge descending]

Paper trading log updated: output/paper_trading/log.csv
Odds API credits remaining: XXX
```

**5. Update the paper trading log columns**

The current log has BTTS/O/U columns. Update `output/paper_trading/log.csv` to use these columns:
```
prediction_date, match_date, league, home_team, away_team,
ah_line, bet_side, model_prob_ah, odds_ah, implied_prob, edge,
bet_flag, actual_ah_result, profit_loss, notes
```

Do NOT delete existing rows — append new columns or create a new file `output/paper_trading/log_ah.csv` if the column change would break existing data.

**6. Update `run.py update`**

No change needed to the update command — data pipeline stays the same.

---

### After making changes

Run the updated predict command:
```
python run.py predict
```

Verify:
- Only EPL matches appear
- AH line and odds are present
- Edge calculation looks reasonable (most matches near 0%, a few above 7%)
- Paper trading log updated

Then commit and push:
```
git add -A
git commit -m "Switch live predictions to EPL AH at 7% threshold"
git push
```

---

### Summary for Chris when done

Print:
- How many EPL matches were found this week
- How many flagged at 7% threshold
- The flagged bets table
- Whether AH odds are available on the free tier (yes/no)
- Any issues encountered
