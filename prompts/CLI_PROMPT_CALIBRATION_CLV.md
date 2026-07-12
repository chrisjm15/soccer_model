# Sonnet CLI Prompt — Calibration Backtest + CLV Tracking

Copy everything below the line into the Sonnet CLI session (after `/effort max`).

---

## Context

The EPL AH paper trading season is complete: 11 settled bets, +20.4% ROI — far too small a sample to mean anything. We have 10,617 historical matches in `data/processed/all_merged.csv` with AH lines and odds (`ah_line`, `odds_ah_home`, `odds_ah_away`), plus Pinnacle 1X2 closing odds on 9,867 of them. Design notes are in `docs/LARGE_LINE_CALIBRATION.md` — read it before starting.

Two goals this session:

1. **Measure model calibration historically** — is the model overconfident at 65%+ probability and on large lines (±1.5+), as paper trading hinted? And when the model disagrees with the market, does reality follow the model or the market?
2. **Add CLV (closing line value) tracking to the live paper trading loop** — so next season we get a statistically fast verdict on whether the model beats the closing line, instead of waiting years for ROI significance.

**Hard rules:**
- Do NOT modify anything in `model/` or the settlement/probability logic in `backtest/multi_market_engine.py`. Reuse those functions read-only. If the engine's logic is wrong, report it — don't fix it silently.
- Lookahead safety: all model probabilities must use pre-match ratings only (`data/processed/ratings.csv` is already pre-match — same approach as the existing backtest engine).
- This is money-critical measurement code. Prefer boring, explicit code over clever code.

---

## Task 1 — `scripts/calibration_backtest.py`

New script. For every match in `all_merged.csv` that has `ah_line`, `odds_ah_home`, and `odds_ah_away` present:

1. Generate the model's AH probability using the exact same pipeline as `backtest/multi_market_engine.py` (import and reuse its functions — do not reimplement Poisson maths or AH settlement).
2. Select the bet side the same way the engine does (best-edge side). Record the match even if edge is below threshold — we want the full probability spectrum for calibration, not just flagged bets.
3. Compute the market's no-vig probability for that side: `implied = (1/odds_side) / (1/odds_ah_home + 1/odds_ah_away)`.
4. Settle against the actual score using the engine's existing AH settlement function (must handle quarter lines: half win / half loss / push).

**Scoring convention — critical, get this consistent:** define `actual_score` as Win=1.0, HalfWin=0.75, Push=0.5, HalfLoss=0.25, Loss=0.0. The model probability compared against it must be the model's *expected value of that same score* under its Poisson grid (for quarter lines, the average of the two half-line win probabilities gives this). If the engine's `model_prob` already uses a different convention, convert explicitly and document which convention each column uses in a comment. Calibration comparisons are meaningless if the two sides of the comparison use different conventions.

### Output 1 — per-match CSV: `output/backtest_results/calibration_matches.csv`

One row per match, columns:
`date, league, season, home_team, away_team, home_goals, away_goals, home_xg, away_xg, ah_line, bet_side, model_prob, market_odds, market_prob_novig, edge, pinnacle_home_novig, pinnacle_draw_novig, pinnacle_away_novig, ah_result, actual_score, pnl_flat10`

(Pinnacle no-vig columns blank where Pinnacle odds missing. This CSV feeds the factor analysis next session — make it complete.)

### Output 2 — report: `output/backtest_results/calibration_report.txt`

All tables produced twice: **all leagues** and **EPL only**. Each cell shows: n, mean model_prob, mean actual_score, gap in percentage points (model − actual), and flat-stake ROI.

1. **By model probability zone:** 50–55%, 55–60%, 60–65%, 65–70%, 70–75%, 75–80%, 80%+.
2. **By absolute line size:** |line| ≤ 0.5, 0.75–1.25, 1.5–2.0, ≥ 2.25.
3. **Zone × line-size cross-tab** (n and gap only — this is the money table: it shows exactly where the model breaks).
4. **Disagreement test** — bucket by (model_prob − market_prob_novig): <2%, 2–5%, 5–10%, >10%. For each bucket report n, mean model_prob, mean market_prob, mean actual_score, ROI. *The question this answers: when model and market disagree, does the actual outcome track the model (edge is real) or the market (model is just miscalibrated)? This is the single most important table in the report.*
5. **By season** (2020-21 through 2025-26): n, gap, ROI — checks whether calibration drifts over time.

### Sanity checks (print to console, fail loudly if violated)

- Row count ≈ 10,617 (report exact count and how many were dropped and why).
- All `actual_score` values in {0, 0.25, 0.5, 0.75, 1.0}; all probabilities in (0, 1).
- Cross-check: filter to EPL, seasons 2023-24 to 2025-26, edge ≥ 5%, and confirm ROI is in the same ballpark as the existing `multi_market_report.txt` EPL AH figure (+6.5%). If it's wildly different, something is inconsistent between this script and the engine — stop and investigate, do not proceed.
- No prediction uses ratings dated on/after its match date.

---

## Task 2 — CLV tracking in `run.py results`

When settling each bet, look up the match's closing AH line and odds from the freshly updated `all_merged.csv` (football-data closing odds — same row used to settle the score).

- **If the closing line equals the bet's line:** compute `clv = closing_novig_prob(bet_side) − bet_novig_prob(bet_side)` (both no-vig, same formula as Task 1). Positive CLV = we beat the close.
- **If the lines differ:** record the closing line and odds but leave `clv` blank — comparing probabilities across different lines is invalid.

Changes:
- Add columns to `output/paper_trading/log_ah.csv`: `closing_line, closing_odds, clv`. Preserve all existing rows and columns; existing rows get back-filled where the data allows (attempt back-fill for all 11 settled bets).
- `results` output gains a CLV summary block: count with valid CLV, mean CLV, count positive vs negative.
- Do not change any settlement or P&L logic.

---

## Task 3 — Verify, document, commit

1. Run `python scripts/calibration_backtest.py` end to end. Show me the full report.
2. Run `python run.py results` — must report 0 unsettled, print the CLV summary, and leave the 11 settled bets' P&L unchanged (diff the log before/after to prove no regression).
3. Update `docs/INDEX.md`: add `scripts/calibration_backtest.py` and the two new output files.
4. Commit everything with message: `Calibration backtest + CLV tracking in paper trading loop`. Push.

Plain-English summary at the end: what the calibration tables show, whether the 65%+ / large-line overconfidence is confirmed historically, and what the disagreement test says about whether the edge is real.
