# CLI Prompt — Task 1: Switch Odds to AU Region

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

Make the following targeted change to `scrapers/odds_api.py`. **Chris has no coding background. Fix all errors automatically. Commit and push when done.**

---

### What to change

In `scrapers/odds_api.py`, find the function `fetch_epl_ah_odds()` (or equivalent — search for `regions=` if unsure of the exact function name).

Change:
```python
regions='uk'
```
To:
```python
regions='au'
```

---

### Additional changes in the same file

1. Wherever the output or any print statement refers to "UK bookmakers", update it to say "AU bookmakers".

2. After making the change, add a temporary debug print inside the function that prints the bookmaker names returned by the AU region. Something like:
   ```python
   print("AU bookmakers returned:", [b['key'] for b in response_data])
   ```
   This can be removed after we confirm the right bookmakers are appearing.

---

### Verification

Run the predict command to confirm:
```
python run.py predict
```

Check the output:
- The debug line should print the AU bookmaker names (e.g., `bet365`, `tab`, `sportsbet`, `unibet_au` etc.)
- AH odds should still be present
- No crashes or missing-field errors

If AU bookmakers return no AH lines or different field names than UK, print a clear description of exactly what the AU response contains and stop — do not silently fall back to UK region.

---

### After verifying

Remove the debug print line, then commit and push:
```
git add -A
git commit -m "Switch odds fetch to AU region"
git push
```

---

### Summary for Chris when done

Print:
- Which AU bookmakers were returned by the API
- Whether AH lines and odds were present in the AU response
- Any field name differences vs the UK response (if any)
- Confirmation that the predict output still looks correct
