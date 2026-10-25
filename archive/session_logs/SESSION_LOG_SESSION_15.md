# Session 15 — 2026-10-24/25

## Status at session end
Calibrated EPL AH model is LIVE and on autopilot for the 2026-27 paper-trading test. First 2 paper bets
logged (GW9: Aston Villa +1.00 v Man City, Sunderland 0.00 v Leeds). Weekly runs now automatic:
Tuesday settle, Friday predict. Soft-league work is unchanged since July (P1 now verified, FIN parked).

## Found at session start (3 months idle since session 14)
- Pre-GW1 deployment never happened: `run.py` still used the retired 7% raw threshold; no 2026-27 bets logged.
- **Data frozen since May:** `understat.py` and `footballdata.py` season lists stopped at 2025-26. The weekly
  `update` reported exit code 0 every week while ratings stayed at 2026-05-24.
- P1 re-scrape verified good (306 rows × 5 seasons, xG present). FIN still broken (2021=30, 2025=15) → parked
  per the 2026-07-18 plan.

## Done (executed by Antigravity, QC'd by Cowork)
Executor switched from Sonnet CLI to Antigravity (Gemini) via the `antigravity-handoff` skill. Money-critical
code now ships with Cowork-written, hand-verified gold tests (`scripts/test_calibration.py`,
`scripts/test_line_selection.py`). Antigravity must not edit those files.

1. **Deploy (commit 9efe4f2)** — `prompts/completed/ANTIGRAVITY_EPL_CALIBRATED_DEPLOY.md`
   - 2026-27 added to scrapers; pre-2026-27 ratings verified bit-identical after rebuild.
   - EPL M3 refit on 2020-21..2025-26 (n=2,279): intercept −0.0601, b_market 0.3960, **b_model 0.2450 (p=0.022)**.
     M1 diag: 0.0532 / 0.6682. Stored in `config/calibration.yaml` with market_prob_range [0.4569, 0.5407].
   - `model/calibration.py` (pure functions); `run.py predict` = calibrated edge ≥ 1%, consensus no-vig for
     market prob, best price for bet price, out-of-range guard, promoted-team guard (<10 matches; promoted =
     no EPL rows in 2025-26). Promoted 2026-27: Coventry, Hull (never seen → DEFAULT_PRIORS), Ipswich
     (returning → old rating regressed 30%).
2. **QC found two defects in the deploy:**
   - `run.py results` rewrote the log with a fixed column list → deleted the calibration columns and overwrote
     old CLV with `nan`. (Antigravity's report falsely claimed the hand-check matched the log.)
   - Live feed priced the wrong market: UK/AU `spreads` = ±1.5 lines (market probs 0.23–0.82). Model is
     trained on the main Asian line (B365 AHh, market ≈ 0.5). Guard vetoed all 9 → model could never bet.
3. **Fix (commit 042c9a8)** — `prompts/completed/ANTIGRAVITY_FIX_LOG_AND_MAIN_LINE.md`
   - results now preserves all columns; 5 historical CLV values restored from cb2a344.
   - `regions=uk,au,eu`; `select_main_line` picks the line with consensus no-vig closest to 0.5.
     Main lines come from Pinnacle / Matchbook / offshore EU books. 8/9 GW9 matches in range.
   - Log adds `best_book`, `best_au_price`. **Only AU book in the API for EPL spreads is PlayUp (±1.5 only)**
     → no flagged bet is currently placeable at an AU book via the feed.
   - First Antigravity attempt at this brief failed ("Model produced invalid output") and rewrote the prompt
     instead of executing; a fresh session succeeded.
4. **Automation (Cowork, uncommitted)** — `scripts/run_update.ps1` rewritten with `-Mode settle|predict`:
   update → results (Tue) or update → predict (Fri). Skips step 2 if update fails. Sleep step removed.
   Predict output → `output/predict_latest.txt` + `output/predictions/predict_YYYY-MM-DD.txt`.
   New Windows task "Soccer Model - Friday Predict" (Fri 12:00, wake-to-run, start-when-available).
   Test runs 2026-10-24 13:39 and 19:54 both exit 0, no duplicate logging.

## Decisions
- Keep the 1% calibrated-edge rule all season even though it ignores margin (Villa bet ≈ 0 EV at 1.83).
  The July OOS sweep validated this exact rule at real B365 prices; changing it mid-season breaks the test.
- Log stays pure model output; vetoes in `notes` only (unchanged).
- Bet price logged = first sighting (Friday run); later runs don't overwrite.

## Files touched this session (uncommitted)
`scripts/run_update.ps1`, `SESSION_LOG_COWORK.md`, `COWORK_HANDOFF_PROMPT.md`, `docs/WEEKLY_SCHEDULE.md`,
`docs/INDEX.md`, `CLAUDE.md`, `archive/session_logs/SESSION_LOG_SESSION_14.md` (moved),
`data/aliases/team_aliases.json`, `output/scheduler_log.txt`, `output/predict_latest.txt`, `output/predictions/`.
Delete (can't from Cowork): `scripts/run_update.ps1.bak`.
