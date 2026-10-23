# Phase 2 CLI Prompt — BTTS Model Integration + Backtest Engine

## Instructions for Chris

### Step 1: Make sure the three module files already exist

Before running this CLI session, you should have already run the three local LLM prompts:
- `prompts/RATINGS_PROMPT_QWEN3.md` → produced `model/ratings.py`
- `prompts/POISSON_PROMPT_GEMMA.md` → produced `model/poisson.py`
- `prompts/BTTS_PROMPT_QWEN3.md` → produced `model/btts.py`

If those files don't exist yet in the GitHub repo, paste the three local LLM prompts first, run each one, and save the outputs to the right paths.

### Step 2: Open your terminal and paste this:
```
cd "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
claude --model claude-sonnet-4-6
```

### Step 3: Once Claude Code opens, paste this:
```
/effort max
```

### Step 4: Paste the entire prompt below (everything inside the --- lines):

---

## PROMPT START — COPY EVERYTHING BELOW THIS LINE

You are continuing to build a soccer prediction model. Phase 1 (data pipeline) is complete. Phase 2 builds the BTTS model and backtest engine.

Read `CLAUDE.md` and `docs/BUILD_PLAN.md` first. They contain the full architecture and governance rules.

Three module files should already exist at:
- `model/ratings.py`
- `model/poisson.py`
- `model/btts.py`

Read all three before writing anything. Understand their interfaces completely — do not modify them unless they have bugs that prevent the session from working. If you find bugs, fix them and note what was wrong.

**IMPORTANT:** Chris has no coding background. If anything fails, explain what went wrong in plain English and fix it. Do not ask Chris to debug anything manually. Commit and push to GitHub at the end.

---

### STEP 1: Verify the existing modules

1. Read model/ratings.py, model/poisson.py, model/btts.py to understand their interfaces. Then run python model/ratings.py to produce data/processed/ratings.csv. If it fails, fix it before continuing.
---

### STEP 2: Add `__init__.py` files if missing

Ensure `model/__init__.py` exists (can be empty) so the `model` package is importable.

---

### STEP 3: Add home advantage to leagues.yaml

Open `config/leagues.yaml` and add a `home_advantage_xg` field to each league. These are starting values — set all to 0.0 for now (home advantage is already embedded in the home/away rating split). Add a comment explaining this:

```yaml
  EPL:
    home_advantage_xg: 0.0  # Baked into home/away rating split; tune via backtest
```

Add this field to all five leagues.

---

### STEP 4: Build the backtest engine (`backtest/engine.py`)

This is the most important file in this session. The backtest simulates what would have happened if we had used this model historically.

**Backtest design:**

- **Train period:** seasons "2020-21", "2021-22", "2022-23" — ratings are built up but predictions are NOT evaluated
- **Test period:** seasons "2023-24", "2024-25" — these are the seasons we evaluate model performance on

The ratings in `data/processed/ratings.csv` are already lookahead-safe (each row contains pre-match ratings). So the backtest only needs to:
1. Filter predictions to the test period
2. Compare model predictions to actual outcomes
3. Calculate metrics

**What the engine needs:**

Load `data/processed/all_merged.csv` (the truth — actual match outcomes).
Load `data/processed/ratings.csv` (the pre-match ratings from `model/ratings.py`).

Merge them on: `date`, `league`, `season`, `home_team`, `away_team`.

For each merged match row, compute:
1. Whether BTTS actually occurred: `actual_btts = 1 if (home_goals >= 1 and away_goals >= 1) else 0`
2. Run `predict_match` from `model/btts.py` using the pre-match ratings.
3. Store: `prob_btts_yes`, `actual_btts`, `edge`, `should_bet`, `expected_value`

**File structure for `backtest/engine.py`:**

```python
def run_backtest(
    ratings_path: str = 'data/processed/ratings.csv',
    merged_path: str = 'data/processed/all_merged.csv',
    leagues_config_path: str = 'config/leagues.yaml',
    train_seasons: list = None,   # default: ['2020-21', '2021-22', '2022-23']
    test_seasons: list = None,    # default: ['2023-24', '2024-25']
    edge_threshold: float = 0.05,
    assumed_btts_odds: float = 1.90,
    output_path: str = 'output/backtest_results/predictions.csv'
) -> pd.DataFrame:
    """
    Runs the full backtest. Returns a DataFrame with one row per test-period match,
    including model predictions and actual outcomes.
    Saves results to output_path.
    """
```

The function must:
- Load and merge the data
- Run predictions for all test-period matches using `model.btts.run_predictions`
- Add the `actual_btts` column (computed from true scorelines in `all_merged.csv`)
- Save to the output path
- Return the full predictions DataFrame

Create `output/backtest_results/` directory if it doesn't exist.

---

### STEP 5: Build the metrics module (`backtest/metrics.py`)

```python
def compute_metrics(predictions_df: pd.DataFrame) -> dict:
    """
    Takes the backtest output DataFrame and computes performance metrics.
    
    Required columns in predictions_df:
        prob_btts_yes, actual_btts, edge, should_bet, btts_odds_yes
    
    Returns a dict of metrics.
    """
```

**Metrics to compute:**

**1. Brier Score** (measures calibration — lower is better):
```
brier_score = mean((prob_btts_yes - actual_btts)^2)
```
Compute for all matches AND separately for the subset where `should_bet == True`.

Baseline Brier score for reference: always predicting 0.5263 (= 1/1.90) gives a Brier score of approximately `mean((0.5263 - actual_btts)^2)`. Compute this baseline too.

**2. Hit rate** (for flagged bets):
```
hit_rate = sum(actual_btts) / len(flagged_bets)
```
Only for matches where `should_bet == True`.

**3. ROI simulation** (flat staking, 1 unit per bet, at assumed odds of 1.90):
```
profit_per_bet = 0.90 if actual_btts == 1 else -1.0
total_profit = sum(profit_per_bet for flagged bets)
total_staked = count(flagged bets)
roi_pct = (total_profit / total_staked) * 100
```

**4. Calibration bins** (10 equal-width probability bins from 0 to 1):
For each bin, compute mean predicted probability vs actual BTTS rate. This shows if the model is over/underconfident in specific probability ranges.

**5. Breakdown by league:**
For each league, compute: n_matches, n_bets, hit_rate, roi_pct, brier_score.

**6. Breakdown by season:**
For each test season, compute: n_matches, n_bets, hit_rate, roi_pct, brier_score.

```python
def print_metrics_report(metrics: dict) -> None:
    """Print a readable summary of the metrics to stdout."""
```

This function should print clearly formatted output that Chris can read without any coding knowledge. Example format:

```
=== BTTS MODEL BACKTEST RESULTS ===
Test period: 2023-24 to 2024-25
Total matches: X | Matches flagged as bets: Y (Z%)

OVERALL PERFORMANCE
  Brier Score (all matches): 0.XXXX  (baseline: 0.XXXX)
  Brier Score (flagged bets only): 0.XXXX

BETTING PERFORMANCE (at assumed odds 1.90)
  Total bets: Y
  Hit rate: XX.X%  (break-even at assumed odds: 52.6%)
  Total P&L: +/- X.XX units
  ROI: +/- XX.X%

CALIBRATION (model prob vs actual BTTS rate)
  0-10%:  predicted=X.X%, actual=X.X%
  10-20%: ...
  ...

BY LEAGUE
  EPL:         N bets, XX% hit rate, XX.X% ROI
  La_Liga:     ...

BY SEASON
  2023-24:     N bets, XX% hit rate, XX.X% ROI
  2024-25:     ...
```

---

### STEP 6: Update `run.py` with a backtest command

Update `run.py` so it can be run as:
```
python run.py backtest
```

This should:
1. Load `config/leagues.yaml`
2. Run `backtest.engine.run_backtest()`
3. Run `backtest.metrics.compute_metrics()` on the result
4. Run `backtest.metrics.print_metrics_report()`

Also add:
```
python run.py predict
```
(stub only for now — prints "Live predictions coming in Phase 3")

---

### STEP 7: Add requirements

Make sure `requirements.txt` includes all packages used:
```
requests>=2.31.0
beautifulsoup4>=4.12.0
pandas>=2.1.0
pyarrow>=14.0.0
pyyaml>=6.0
lxml>=4.9.0
scipy>=1.11.0
numpy>=1.24.0
```

Run `pip install -r requirements.txt` to ensure they're all available.

---

### STEP 8: Run the full backtest

Execute:
```
python run.py backtest
```

Read and interpret the output. If there are errors, fix them. If the ROI or Brier score looks completely implausible (e.g., negative Brier score, or ROI of +500%), investigate and fix.

---

### STEP 9: Save backtest results

After the backtest runs successfully:
1. Save the output CSV to `output/backtest_results/predictions.csv` (the engine already does this)
2. Save the metrics report to `output/backtest_results/metrics_report.txt` — capture the printed output to a file

Add `output/backtest_results/` to `.gitignore` (it's derived data, like `data/processed/`).

Actually: do NOT gitignore `output/backtest_results/`. Add it to git — these are results worth tracking.

---

### STEP 10: Commit and push

```
git add -A
git commit -m "Phase 2: BTTS model — ratings engine, Poisson model, backtest"
git push
```

---

### STEP 11: Write a summary

Print a clear summary for Chris:
- What was built
- Key backtest results (headline numbers: Brier score vs baseline, ROI, hit rate)
- Whether the model shows any positive signal
- What Phase 3 will build on top of this
- Any issues found and fixed along the way

Interpret the results in plain English. For example: "The model has a Brier score of 0.247 vs a naive baseline of 0.249 — this is slightly better than guessing, which is what we'd expect at this stage before any tuning."

## PROMPT END — STOP COPYING HERE

---

## What to expect

This session will take 20-40 minutes. The main work is:
1. Verifying and patching the three modules from local LLMs (they may have minor bugs)
2. Building the backtest engine and metrics module
3. Running the full backtest on 2 seasons of test data

**If something fails:** Claude Code should fix it automatically. If it gets stuck, copy the error and bring it back to this Cowork session.

**When it's done:** You'll have a backtest result showing whether the model has calibration signal on 2 seasons of held-out data. Come back to this Cowork session with the headline numbers (Brier score, ROI, hit rate) and we'll decide what to tune next.
