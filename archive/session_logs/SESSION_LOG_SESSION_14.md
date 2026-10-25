# Session 14 — 2026-07-12

## Status at session end
Strategy verdict reached. Big 5 ex-EPL retired — model has no edge vs the market. EPL carries a weak, unconfirmed signal forward as a live hypothesis for 2026-27 using calibrated probabilities. Raw-probability edge thresholds (the old 7%) are retired. Scandinavian scraping resumed via desktop bat file (N1 mid-run at session end).

## What was done this session

### Full project review (first Fable session)
Identified: paper ROI statistically meaningless at n=5; +6.5% EPL AH backtest number carries a 15-cell selection problem; CLV tracking missing; calibration backtest designed but unbuilt for 2 months.

### Final EPL paper trading settled
`run.py results` settled the last 6 bets. **Final season: 11 bets, 8W 3L, +$22.40, +20.4% ROI.**
Caveat: includes 2 bets Chris had vetoed (Arsenal/Burnley +2.50, Bournemouth +1.50 — both won, +$13.30). Excluding vetoes: 9 bets, +$9.10, ~+10%. **Convention decided: log stays pure model output; vetoes recorded in `notes`, never removed.**

### Calibration backtest built and run (Sonnet CLI, prompt now in prompts/completed/)
`scripts/calibration_backtest.py` over 10,702 matches → `calibration_report.txt` + `calibration_matches.csv`.
Findings:
- **Overconfidence is universal**, not just 65%+: +3.1pp at 50-55% rising to +31.5pp at 80%+. Actual coverage ~48-54% regardless of model probability.
- **Disagreement test (all leagues): reality tracks the MARKET, not the model** (>10% disagreement, n=4,337: actual 50.6% vs market 49.9%). Raw model edges were almost entirely calibration error; the season's +20.4% was luck.
- **EPL exception:** >10% bucket n=1,071, actual 53.7% vs market 50.0% (~2.4σ, but effective p≈0.10 after 5-league selection).
- CLV added to `run.py results` (was biased gross-vs-novig on old rows; fixed properly for future via both-sides logging below).

### Recalibration / market-blend test built and run (Sonnet CLI)
`scripts/recalibration_test.py` — fractional logit, train 2020-24, OOS test 2024-26 → `recalibration_report.txt`.
- **All leagues: model coefficient p=0.13, OOS worse than market-only. Dead.**
- **EPL: model coefficient +0.286, p=0.02 — model and market get near-equal weight.** OOS sweep positive at every threshold 1-4% (1%: 92 bets/season, +8.9% ROI, CI [-3.1, +20.9]). Real but unconfirmed; only true test is 2026-27.
- **M4: large-line interaction insignificant (p≈0.8) → the model's signal is NOT concentrated in big lines. The 10-factor large-line correction layer (docs/LARGE_LINE_CALIBRATION.md) is superseded — do not build it.** Global recalibration handles the miscalibration.
- `run.py predict` now logs both AH sides' odds → clean no-vig CLV from next season.

### Scandinavian scraping resumed
- `scrape_next_league.bat` (project root — copy to desktop): one league per click, state in `experiment/sofascore_done.txt`, only marks a league done on clean exit. Queue: N1→B1→P1→SC0→T1→SWE→NOR→DNK→FIN. `--seasons-back 6` (26/27 is listed but empty — counting it as a season was costing the oldest real season).
- N1 mid-run at session end (3 season files saved). "9/10 completed" round counts = Sofascore duplicate/postponed fixture entries; dedup guard handles it. QC check: Eredivisie full season = 306 rows.

### Edge-improvement priorities discussed (ranked, recorded in handoff)
Best-price execution → soft-league opening lines / lineup-aware timing → non-penalty + game-state + set-piece xG → player-availability veto → top-down Pinnacle-anchor research. Model-quality work (Dixon-Coles, PPDA etc.) explicitly deprioritised: adds calibration, not information.

### Housekeeping
All 25 executed prompts moved to `prompts/completed/`. Stale session-10 `load_sofascore.py` copy moved to `archive/`. Sessions 9-13 log archived. INDEX, handoff, CLAUDE.md updated. Old headline numbers (+18.2% ROI, 7% threshold, +6.5% raw EPL AH) superseded in all active docs.

## Files touched (uncommitted — see handoff for commit block)
New: `scrape_next_league.bat`, `prompts/completed/CLI_PROMPT_CALIBRATION_CLV.md`, `prompts/completed/CLI_PROMPT_RECALIBRATION_TEST.md`, `archive/session_logs/SESSION_LOG_SESSIONS_9_to_13.md`, N1 sofascore CSVs (in progress).
Moved: 25 prompts → `prompts/completed/`, stale script → `archive/`.
Updated: `COWORK_HANDOFF_PROMPT.md`, `SESSION_LOG_COWORK.md`, `docs/INDEX.md`, `docs/LARGE_LINE_CALIBRATION.md` (supersession note), `CLAUDE.md` (project description).
Already committed by CLI sessions: calibration + recalibration scripts, reports, run.py changes.
