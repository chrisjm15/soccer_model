# CLI Prompt — Task 2: Add `run.py results` Command

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

Add a new `python run.py results` command to the project. **Chris has no coding background. Fix all errors automatically. Commit and push when done.**

---

### What this command does

`run.py results` settles all unsettled bets in the paper trading log:

1. Read `output/paper_trading/log_ah.csv` — find all rows where `actual_ah_result` is blank/NaN
2. For each unsettled row, look up the actual match score from `data/processed/all_merged.csv` using `home_team`, `away_team`, and `match_date`
3. Calculate the AH result using the `ah_line` and `bet_side` from the log
4. Calculate P&L at a flat $10 stake per bet
5. Write the results back to `log_ah.csv`
6. Print a summary to the terminal

---

### AH result calculation logic

Given:
- `ah_line`: e.g. +1.0, +0.5, +0.75, -0.5, -1.0, -0.75
- `bet_side`: "Home" or "Away"
- `actual_home_goals` and `actual_away_goals` from the scores data
- Odds: `odds_ah` from the log

Steps:
1. Apply the handicap: if `bet_side` is "Home", add `ah_line` to home goals. If "Away", subtract `ah_line` from home goals (i.e. add `abs(ah_line)` to away goals).
2. Compare adjusted scores:
   - Adjusted home > away → Home wins AH
   - Adjusted home < away → Away wins AH
   - Adjusted home == away → Push (stake returned)

**Quarter-ball lines (0.25, 0.75):** these split the stake into two bets — one on the adjacent half-ball line above and one below. Handle as follows:
- +0.75 = half stake on +0.5, half stake on +1.0
- +0.25 = half stake on 0.0, half stake on +0.5
- -0.75 = half stake on -0.5, half stake on -1.0
- -0.25 = half stake on 0.0, half stake on -0.5

For these, the result can be: "Win", "Half Win", "Push", "Half Loss", "Loss".

**P&L at $10 flat stake:**
- Win: `(odds - 1) * 10`
- Half Win: `(odds - 1) * 5`
- Push: `0`
- Half Loss: `-5`
- Loss: `-10`

Round P&L to 2 decimal places.

---

### Matching bets to scores

In `data/processed/all_merged.csv`, find the row where:
- `home_team` matches the log's `home_team` (exact match, case-insensitive)
- `away_team` matches the log's `away_team` (exact match, case-insensitive)
- `date` is on or within 1 day of the log's `match_date` (to handle any date format differences)

Use columns `home_goals` and `away_goals` (or whatever the actual goal columns are named — check the CSV header and adapt).

If a match cannot be found in the scores data (i.e. the game hasn't been played yet or data isn't updated), leave that row unsettled and print a message: "Match not found in scores data — may not be played yet: [home] vs [away] on [date]"

---

### Output columns to write back to log_ah.csv

For each settled row, update:
- `actual_home_goals`: integer
- `actual_away_goals`: integer
- `actual_ah_result`: "Win" / "Half Win" / "Push" / "Half Loss" / "Loss"
- `profit_loss`: float, e.g. +8.50, -10.00, 0.00

---

### Terminal summary to print

```
=== PAPER TRADING RESULTS — [today's date] ===

Settled this run: X bets
Could not settle (not yet played or data missing): Y bets

SETTLED BETS:
  Everton vs Man City    AH=+1.0  Side=Home  Result=Win      P&L=+$8.73
  Liverpool vs Chelsea   AH=+0.5  Side=Away  Result=Pending  (not yet played)

RUNNING TOTALS (all time):
  Total bets settled: N
  Wins: W  |  Half Wins: HW  |  Pushes: P  |  Half Losses: HL  |  Losses: L
  Total P&L: +$XX.XX
  ROI: X.X%  (P&L / total staked * 100)

Paper trading log updated: output/paper_trading/log_ah.csv
```

---

### Files to read before implementing

- `run.py` — to see how other commands (update, predict) are structured and add `results` in the same style
- `output/paper_trading/log_ah.csv` — check actual column names (adapt if different from spec above)
- `data/processed/all_merged.csv` — check actual column names for teams, date, and goals

---

### After implementing

Run the command:
```
python run.py results
```

Verify the Everton vs Man City result settles correctly:
- Match: Everton 3-3 Man City (May 4, 2026)
- Bet: Everton +1.00 Home → should show **Win**, P&L = +$(odds-1)*10

Then commit and push:
```
git add -A
git commit -m "Add run.py results command for paper trade settlement"
git push
```

---

### Summary for Chris when done

Print:
- How many bets were settled
- The result and P&L for each settled bet
- Running P&L total and ROI
- Any bets that couldn't be settled and why
