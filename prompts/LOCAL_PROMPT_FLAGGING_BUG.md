/no_think

# Local LLM Prompt — Fix Flagging Logic Inconsistency
**Model:** Qwen3 8B (`qwen3:8b-16k`)
**File:** `run.py` only
**Colab QC:** Yes — run predict and verify no bet is flagged when API odds < min odds

---

## Context

In `run.py`, the predict command flags bets using `result['should_bet']` from `model/markets.py`. Separately, it calculates and displays a `min_odds` figure (line 258: `1.0 / (model_prob - 0.07)`). These two checks use different edge formulas and can disagree — producing flagged bets where the API odds shown are actually *below* the displayed min odds.

Example from a real run:
```
API odds: 1.30  |  Min odds to bet: 1.33  |  Edge: +10.0%   *** BET
```
This bet should not be flagged — the available odds (1.30) don't meet the minimum (1.33).

---

## What to fix

**Only edit `run.py`.** Do not touch `model/markets.py`.

After the predict loop builds `pred_df` and before printing the FLAGGED BETS section, add a post-filter that overrides `bet_flag` to `False` for any row where `odds_ah < min_odds`.

Specifically, around line 213–215 where `pred_df` is sorted and `flagged` is computed, add:

```python
# Post-filter: suppress flags where API odds don't meet the minimum required
pred_df['min_odds_required'] = 1.0 / (pred_df['model_prob_ah'] - EDGE_THRESHOLD)
pred_df.loc[pred_df['odds_ah'] < pred_df['min_odds_required'], 'bet_flag'] = False
flagged = pred_df[pred_df['bet_flag']]
```

This makes the flagging and the min odds display self-consistent: a bet is only flagged if the API odds actually support the edge claim.

---

## Also fix: don't log suppressed bets to the paper trading CSV

After the post-filter, make sure only `bet_flag=True` rows are written to `output/paper_trading/log_ah.csv`. Check around lines 289–310 where the CSV is updated — confirm it uses `pred_df['bet_flag']` or `flagged` (not the original `result['should_bet']`) to decide what to log.

---

## Verification

Run in plain Windows Terminal (not Claude Code CLI):
```
python run.py predict
```

Check the output:
- No flagged bet should have API odds below its own min odds
- The output line `API odds: X.XX | Min odds to bet: Y.YY` should always have X.XX >= Y.YY for flagged bets
- The total flagged count may drop — that's expected and correct

---

## After verifying

Commit:
```
git add run.py
git commit -m "Fix flagging bug: suppress bets where API odds < min odds required"
git push
```
