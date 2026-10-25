# Antigravity Task: fix the log-wipe bug and price the model on the main Asian line

Workspace: `C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer`
Risk tier: **MONEY-CRITICAL.** Follow-up to `prompts/ANTIGRAVITY_EPL_CALIBRATED_DEPLOY.md`
(commit 9efe4f2). Cowork's review of that deployment found two defects.

## Defect A: `run.py results` deletes the calibration columns
`cmd_results` writes back only its own `desired_cols` list. The 6 calibration columns that
`predict` writes (`market_prob_consensus, calib_prob, calib_edge, calib_prob_m1_only, n_books,
coef_fit_date`) are dropped on every results run. They are missing from the committed log now.
The same run also overwrote the old `clv` values with `nan` (e.g. Liverpool v Chelsea was -0.081507
at cb2a344).

## Defect B: the live feed prices the wrong market
Every one of this week's 9 matches used a ±1.50 line, with market probs of 0.23–0.82. The model
was trained on football-data's `AHh` / `B365AHH/B365AHA`: the **main Asian line**, where the market
is close to 50/50 (1st–99th pct 0.457–0.541). UK/AU books mostly post ±1.5 under `spreads`, and the
modal-line rule picks it. The out-of-range guard correctly vetoed everything, but as built the model
can never bet. Pinnacle (`pinnacle`) and Betfair Exchange (`betfair_ex_eu`) are in the Odds API `eu`
region and should carry main Asian lines. Also: the bet365 check looked for key `bet365`, but the AU
key is `bet365_au`.

## Hard rules
- Do NOT edit `scripts/test_calibration.py` or `scripts/test_line_selection.py`. Their expected
  values are hand-verified. If you think one is wrong, stop and explain why.
- Do not change settlement/P&L logic, `config/calibration.yaml` coefficients, or anything in `backtest/`.
- API calls cost credits. Budget for this task: at most 2 `predict`-equivalent calls plus the diagnostic.

## Task 0: Diagnostic first (STOP point)
Make one call: `soccer_epl` odds, `regions=uk,au,eu`, `markets=spreads`. For each match print
every bookmaker key with its home line and both prices. Report:
- Does `pinnacle` and/or `betfair_ex_eu` return spreads for EPL?
- For each match, the line whose consensus no-vig is closest to 0.5. Is it within 0.44–0.56?
- Which AU books (if any) offer that same line?

**STOP condition:** if no book returns a line with consensus no-vig inside 0.44–0.56 for most
matches, do Task 1 only, then stop and report. Do not build Task 2 on a feed that can't supply it.

## Task 1: Fix the log
1. In `cmd_results`, never drop columns. Keep every column already in the log, in their existing
   order, and append any missing `desired_cols` at the end.
2. Restore the `clv` values for the old rows (prediction_date before 2026-10-23) from commit
   `cb2a344`'s `output/paper_trading/log_ah.csv`. Match rows on (match_date, home_team, away_team).
   Do not change any other value in those rows (the `3.0` vs `3` goal formatting can stay).
3. Delete the 9 rows with `prediction_date == 2026-10-23`. None were flagged, and they were logged
   without calibration columns; Task 3 re-logs them.
4. Test: run `python run.py results` twice in a row and confirm the calibration columns and the old
   `clv` values survive both runs.

## Task 2: Price on the main Asian line
1. Add `select_main_line(ah_data: dict[float, list[tuple[float, float]]]) -> tuple[float, float]`
   to `model/calibration.py`. Rule: choose the line whose `consensus_novig` is closest to 0.5
   (distance rounded to 6dp). Ties go to the line with more books, then to the smaller |line|.
   Return `(line, consensus_novig_home)`. Raise `ValueError` if `ah_data` is empty.
   `python scripts/test_line_selection.py` must pass.
2. In `fetch_epl_ah_odds`: use `regions='uk,au,eu'`. Collect prices per line (as now). Replace the
   modal-line choice with `select_main_line`. At the chosen line, return `book_prices`,
   `bookmakers`, best home/away price, and `best_home_book` / `best_away_book`. Also return
   `best_au_home` / `best_au_away`: the best price at that line among AU-region books, or blank if
   no AU book offers it. Fix the bet365 check to match any key starting with `bet365`.
3. In `run.py predict`, add log columns `best_book` (the book giving the logged bet price) and
   `best_au_price` (the bet side's best AU price, or blank). Bet price and CLV columns stay on the
   overall best price. Chris needs `best_au_price` to know whether a bet is placeable from Australia.
4. Keep the out-of-range and promoted-team guards unchanged.

## Task 3: Verify (show full output)
1. Both gold test files pass.
2. `python run.py predict`: match count, chosen line per match, market prob per match (most should
   now be inside `market_prob_range`), flagged bets, vetoes, `best_book` and `best_au_price` for
   any flagged bet.
3. Open `output/paper_trading/log_ah.csv` and confirm the 6 calibration columns plus `best_book` and
   `best_au_price` are populated for the new rows. Then run `python run.py results` and confirm they
   are still there.
4. Hand-check one new row's `calib_prob` from its logged inputs and the config coefficients. Show
   the arithmetic.

## Task 4: Commit
`Fix results column-drop and restore CLV; price on main Asian line (uk,au,eu)`. Push.

## Report back in plain English
1. Task 0 findings: which books gave main lines, and did AU books offer them?
2. Did both defects get fixed? Show the evidence from two consecutive results runs.
3. This week: how many matches are now in range, how many flagged, and for each flagged bet, can it
   be placed at an AU book, at what price?
