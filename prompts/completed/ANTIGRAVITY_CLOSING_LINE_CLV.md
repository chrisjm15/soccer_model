# Antigravity brief — Closing-line CLV (money-critical: this is the season's verdict metric)

Written by Cowork 2026-10-25 (session 16). Carry out every task in order. Report after each task.
Repo root: `C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer`

## Why
`run.py results` claims to measure closing line value, but it compares our bet against
football-data `AHh` / `B365AHH` / `B365AHA`. Per football-data's own notes
(https://www.football-data.co.uk/notes.txt) those are **pre-closing** odds, "collected Friday
afternoons" — i.e. about the same time as our Friday bet. Closing odds carry an extra `C`
(`AHCh`, `PCAHH`, `AvgCAHH` …). Every CLV number in the log so far is therefore not CLV.

Second problem: CLV is left blank whenever the closing line differs from our bet line, which is
most of the time for quarter-line moves. We now convert the closing price onto our bet line.

## Read first (context, do not change unless a task says so)
`run.py` (`cmd_results`, and the predict print block near line 316), `scrapers/footballdata.py`,
`scrapers/merge.py`, `model/markets.py` (`compute_ah_probs`), `model/poisson.py` (`poisson_pmf`),
`model/calibration.py`, `scripts/test_calibration.py` (style of a gold test file).

## Hard rules
- `scripts/test_clv.py`, `scripts/test_calibration.py`, `scripts/test_line_selection.py` are fixed
  gold tests written by Cowork. **Do not edit them.** Make the code pass them.
- `data/processed/ratings.csv` must be **bit-identical** before and after this brief.
- Never rewrite the log with a fixed column list — keep every existing column (a previous brief
  broke this).
- Do not change the betting rule, calibration, or line selection.

---

## Task 0 — Back up and fingerprint
1. Copy `output/paper_trading/log_ah.csv` → `output/paper_trading/log_ah_backup_2026-10-25.csv`.
2. Record SHA-256 of `data/processed/ratings.csv` and the row count + column list of
   `data/processed/all_merged.csv`. Put them in your report.

## Task 1 — Confirm the closing columns exist (STOP if not)
Download `https://www.football-data.co.uk/mmz4281/2627/E0.csv` and `.../2021/E0.csv`.
For each, report presence and non-null count of:
`AHCh, PCAHH, PCAHA, AvgCAHH, AvgCAHA, B365CAHH, B365CAHA, PAHH, PAHA, AvgAHH, AvgAHA`.
If `AHCh` is missing, or both `PCAHH` and `AvgCAHH` are missing, **stop and report** — do not
improvise another closing source.

## Task 2 — Carry the closing columns through the data pipeline
1. `scrapers/footballdata.py`: add to `ODDS_COLUMNS`:
   `"AHCh", "PCAHH", "PCAHA", "AvgCAHH", "AvgCAHA", "B365CAHH", "B365CAHA", "PAHH", "PAHA", "AvgAHH", "AvgAHA"`.
2. `scrapers/merge.py`: add the same to `odds_cols` and to `rename_map`:
   | source | new column |
   |---|---|
   | AHCh | close_ah_line |
   | PCAHH / PCAHA | close_pin_ah_home / close_pin_ah_away |
   | AvgCAHH / AvgCAHA | close_avg_ah_home / close_avg_ah_away |
   | B365CAHH / B365CAHA | close_b365_ah_home / close_b365_ah_away |
   | PAHH / PAHA | pin_ah_home / pin_ah_away (Pinnacle **pre-closing**) |
   | AvgAHH / AvgAHA | avg_ah_home / avg_ah_away (market average **pre-closing**) |
   Add columns only. Do not touch row ordering, the ratings-backup ordering logic, or anything
   that feeds ratings.
3. Run `python run.py update`.
4. Verify and report: ratings.csv SHA-256 unchanged; all_merged.csv row count unchanged; every
   pre-existing all_merged column identical to before (compare values, not just names); new
   columns present with non-null counts per season for EPL.

## Task 3 — New pure module `model/clv.py`
Pure functions, no pandas, no I/O. Must make `python scripts/test_clv.py` print
`ALL CLV GOLD TESTS PASSED`. The definitions are in the docstring of `scripts/test_clv.py`; read it.
Functions and signatures (exactly):
- `novig_home(home_odds, away_odds) -> float` — ValueError on any price ≤ 1.0, None or NaN.
- `ah_q_home(lam_h, lam_a, line, max_goals=10) -> float` — build an independent Poisson grid with
  `poisson_pmf`, call `compute_ah_probs`, return `p_home / (p_home + p_away)`.
- `convert_q_home(q_close_home, close_line, bet_line, mu=2.8) -> float | None` — identity when the
  lines are equal (no solve). Otherwise bisect goal supremacy `s` in (−mu, mu) with
  `lam_h=(mu+s)/2, lam_a=(mu-s)/2` until `ah_q_home(.., close_line)` matches `q_close_home`
  (tolerance 1e-9), then return `ah_q_home(.., bet_line)`. Return None for q ≤ 0, q ≥ 1, NaN, or
  no solution.
- `clv_for_row(bet_side, bet_line, bet_odds, bet_market_prob, close_line, close_home_odds,
  close_away_odds, mu=2.8) -> dict` with keys `closing_prob_bet_side, clv_move, clv_price,
  line_converted`. Away side = 1 − converted home value. `clv_move` is None when
  `bet_market_prob` is None/NaN. Any bad closing input → all values None; never raise.

## Task 4 — Rewrite the CLV block in `run.py results`
Replace the existing "CLV back-fill" loop.
1. Loop over **all** log rows (bets and non-bets), not just bets. Recompute every run
   (idempotent) — overwrite earlier CLV values; they were measured against pre-closing odds.
2. Match to `all_merged.csv` as now (home, away, date ±1 day).
3. Closing source: Pinnacle closing (`close_pin_ah_home/away`, both > 1.0) → `closing_source='pinnacle'`;
   else market-average closing → `'avg'`; else leave blank and skip the row.
   Closing line = `close_ah_line`.
4. Call `clv_for_row(bet_side, ah_line, odds_ah, market_prob_consensus or None, ...)`.
5. Write these columns (add if missing): `closing_line`, `closing_home_odds`, `closing_away_odds`,
   `closing_source`, `closing_prob_bet_side`, `clv_move`, `clv_price`, `clv_line_converted`.
   Keep the old `closing_odds` column = closing price of the bet side, and old `clv` = `clv_price`
   (back-compat for anything reading it).
6. Non-bet rows: also fill `actual_home_goals` / `actual_away_goals` when the score is known.
   Leave their `actual_ah_result` and `profit_loss` blank (only bets are settled).
7. Column handling: start from the log's existing columns, append any new ones at the end. Do not
   drop or reorder existing columns.
8. Replace the CLV summary print with: rows with CLV (bets / all), rows where the line was
   converted, mean `clv_price` (bets), mean `clv_move` (bets, and all rows), each with n.

## Task 5 — Display bug (routine)
In the predict print block (`run.py` ~line 316), a 0.00 line prints
"win or draw (or lose by up to 0.00)". For a 0.00 line print "win (draw = stake returned)".
Check the other line types still print as before.

## Task 6 — Verify (report every item with the actual output)
1. `python scripts/test_clv.py`, `python scripts/test_calibration.py`,
   `python scripts/test_line_selection.py` — all pass. Paste the last line of each.
2. `python run.py results`. Paste the full CLV summary.
3. Compare the new log with the backup: every column that existed before, **except**
   `closing_line, closing_odds, clv, actual_home_goals, actual_away_goals` (and, for rows that were
   unsettled bets, `actual_ah_result, profit_loss`), must be identical row for row. Report the diff
   (expected: none).
4. Print a table of every row that now has CLV: home, away, ah_line, bet_side, odds_ah,
   market_prob_consensus, closing_line, closing_source, closing_home_odds, closing_away_odds,
   closing_prob_bet_side, clv_move, clv_price, clv_line_converted.
5. Hand-check ONE row with a converted line: show novig of the closing odds, the converted
   probability from `convert_q_home`, and the clv_price arithmetic.
6. Run the Friday script once by hand to confirm `scripts/run_update.ps1` (edited by Cowork today:
   it now writes UTF-8 instead of UTF-16) still works:
   `powershell -ExecutionPolicy Bypass -File scripts\run_update.ps1 -Mode predict`
   Report the last 3 lines of `output/scheduler_log.txt` and confirm
   `output/predictions/predict_<today>.txt` opens as normal text. Confirm the paper log gained no
   duplicate rows (first sighting is kept).
   GW9 rows will only get CLV once football-data publishes the weekend's results (usually by
   Monday/Tuesday) — blanks for them today are expected.

## Task 7 — Commit and push
Delete `output/paper_trading/log_ah_backup_2026-10-25.csv` only after Task 6 passes.
```
git add -A scrapers/ model/clv.py run.py scripts/test_clv.py scripts/run_update.ps1 output/paper_trading/log_ah.csv output/predictions/ output/predict_latest.txt output/scheduler_log.txt prompts/
git commit -m "Closing-line CLV: football-data closing AH columns, line conversion, CLV on all rows"
git push
```
Do not commit `data/processed/` or `data/raw/` (gitignored).
