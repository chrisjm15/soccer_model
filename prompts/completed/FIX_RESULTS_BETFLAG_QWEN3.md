/no_think

# Fix: results command must filter on bet_flag=True

## File to edit
`C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer\run.py`

## Problem
The `cmd_results()` function (starts around line 367) settles and counts ALL rows
in the paper trading log, including rows where `bet_flag` is `False`. These are
predictions that were below the betting threshold and were never actually placed.
This inflates the bet count and dilutes the ROI figure.

`bet_flag` is read from CSV with `dtype=str`, so its values are the strings
`'True'` and `'False'`.

## Two fixes required — both in `cmd_results()`

### Fix 1 — only settle bet_flag=True rows (line ~393)

FIND this line:
```python
    for i in log_df[unsettled_mask].index:
```

REPLACE with:
```python
    bet_mask = log_df['bet_flag'].str.strip().str.lower() == 'true'
    for i in log_df[unsettled_mask & bet_mask].index:
```

### Fix 2 — only count bet_flag=True rows in running totals (line ~461)

FIND this block:
```python
    settled_all = log_df[
        log_df['actual_ah_result'].notna() & (log_df['actual_ah_result'].str.strip() != '')
    ].copy()
```

REPLACE with:
```python
    bet_mask = log_df['bet_flag'].str.strip().str.lower() == 'true'
    settled_all = log_df[
        bet_mask &
        log_df['actual_ah_result'].notna() &
        (log_df['actual_ah_result'].str.strip() != '')
    ].copy()
```

## Do NOT change anything else
- Do not touch the CSV save logic — False rows stay in the log file untouched
- Do not change any other function
- Do not rewrite or stub out any code
- Return only the two modified code blocks with enough surrounding context
  (3–4 lines before and after each change) to locate them precisely
