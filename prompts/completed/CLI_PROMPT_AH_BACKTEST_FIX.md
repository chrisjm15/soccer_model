# CLI Prompt — Fix AH Backtest Calculation

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

Read `CLAUDE.md` and `SESSION_LOG_COWORK.md` before doing anything.

There is a bug in the AH (Asian Handicap) backtest that needs to be found and fixed. **Chris has no coding background. Fix all errors automatically. Commit and push when done.**

---

### What we know is wrong

Two symptoms confirmed by data analysis:

1. **Brier score = 0.0000** in `output/backtest_results/multi_market_report.txt` for the AH market. A Brier score of exactly zero is mathematically impossible — it means the AH Brier score calculation is broken (likely dividing by zero, comparing wrong columns, or returning a default).

2. **Win rate of 93.3% for high-confidence bets (135 bets)** in the EPL AH backtest. This is statistically impossible and indicates the AH P&L calculation has a systematic error — most likely it is using `odds_ah_home` for all bets regardless of which side (home or away) was actually bet.

### Suspected root cause

In `data/processed/all_merged.csv`, there are two AH odds columns: `odds_ah_home` and `odds_ah_away`. The backtest needs to use the correct odds for the side that was bet:
- If the model bets the **home side** (prob_ah_home > 0.5), use `odds_ah_home`
- If the model bets the **away side** (prob_ah_away > 0.5), use `odds_ah_away`

The bug is probably that the backtest always uses one of these (likely `odds_ah_home`) regardless of bet side, which inflates P&L when the home side wins and understates it when the away side wins.

---

### What to do

**Step 1 — Read these files in full before touching anything:**
- `backtest/multi_market_engine.py`
- `backtest/metrics.py`
- `output/backtest_results/multi_market_report.txt`
- First 5 rows of `output/backtest_results/multi_market_predictions.csv`

**Step 2 — Trace the AH logic:**

Find where in `multi_market_engine.py`:
- The AH bet side is determined (home vs away)
- The odds for the bet side are looked up
- The P&L for the bet is calculated (win/loss/push/half-win/half-loss)
- The result (`actual_ah`) is determined from the actual scoreline and AH line

Print your findings before making any changes.

**Step 3 — Fix the bug(s):**

The fix should ensure:
- Bet side is correctly determined: bet home if `prob_ah_home > prob_ah_away`, else bet away
- Odds used match the bet side: `odds_ah_home` if betting home, `odds_ah_away` if betting away
- P&L is calculated correctly for all AH result types (win, loss, push, half-win, half-loss)
- The `actual_ah` result correctly reflects whether the BET WON (not just what the scoreline was)

**Step 4 — Fix the Brier score calculation:**

In `backtest/metrics.py`, find the AH Brier score calculation and fix it. The Brier score for AH should be:
```
BS = mean((prob_bet_side - outcome)^2)
```
Where `prob_bet_side` is the model's probability for the side that was bet, and `outcome` is 1 if that bet won, 0 if it lost (exclude pushes from this calculation).

**Step 5 — Re-run the backtest:**

```
python run.py backtest
```

Or whatever command re-generates `multi_market_predictions.csv` and `multi_market_report.txt`. Check:
- Brier score is now a real number (expected range: 0.20–0.28 for a reasonable model)
- Win rates by confidence band look sensible (should track with confidence — higher confidence = higher win rate)
- EPL AH ROI figure changes — note what it was before (nominally +7.1%) and what it is after

**Step 6 — Report findings:**

Print:
- What the bug was (exactly which line(s) of code were wrong)
- EPL AH ROI before and after the fix
- New Brier score for AH
- Win rate by confidence band after fix (to confirm it now makes sense)
- Whether the +7.1% EPL AH ROI holds up or was an artefact of the bug

---

### After fixing

Commit and push:
```
git add -A
git commit -m "Fix AH backtest: correct bet-side odds lookup and Brier score calculation"
git push
```
