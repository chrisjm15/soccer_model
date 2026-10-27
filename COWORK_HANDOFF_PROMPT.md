# Handoff

CLAUDE.md is already loaded. Read `SESSION_LOG_COWORK.md` only. Use `docs/INDEX.md` to locate files — do not read files preemptively.
*Last updated: 2026-10-25 19:45 (end of session 16).*

## Where the project stands
- **EPL Asian Handicap is the only live hypothesis.** Session 16 showed the EPL model carries real information
  (the market moves toward it before kick-off, t=4.7, controlled for artefacts), but the edge is about one
  bookmaker margin: price CLV ≈ 0 at average prices. It only pays at better-than-average prices.
- **Big 5 ex-EPL: retired** (July). **Soft leagues: closed for v1** (session 16, failed the pre-set rule).
- Live and automated: Tue 12:00 settle, Fri 12:00 predict (`scripts/run_update.ps1`). Edge = calibrated prob
  (M3) − consensus no-vig; flag at ≥ 1%. Paper log `output/paper_trading/log_ah.csv`.
- CLV in the log is now real (football-data closing odds, line-converted, every logged match). Closing source is
  market-average — football-data dropped Pinnacle mid-2025-26.
- No briefs outstanding (all in `prompts/completed/`).

## Next actions (in order)

### 1. ~~Tue 2026-10-27 — first automated settle~~ ✅ PASSED (Cowork check 14:00)
- Settle ran 12:00, exit 0 (an extra settle also ran Mon 19:42 — idempotent, harmless).
- Villa 2-1 City, +1.00 @1.83 → Win +8.30 ✓ (by hand). Sunderland 0-0 Leeds, +0.00 @2.15 → Push 0.00 ✓.
- CLV on 9/9 GW9 rows, source avg, 6/9 needed line conversion. Flagged: Villa clv_price −2.9% (move −0.1pp),
  Sunderland +10.7% (move +5.3pp). n=2 — meaningless yet. Chris's real Bet365 AU bet at 2.025 also beat the close
  (≈ +4.2%) and pushed. Calibration columns present; three gold tests pass.

### 2. Fri 2026-10-30 — GW10 predict run
Confirm 9–10 GW10 rows logged with prediction_date 2026-10-30. (A Sunday test run had logged GW10 on stale ratings;
Cowork deleted those 7 rows — still in git at `4115d4b`.) **Never run predict by hand outside the Friday slot** —
first sighting locks the row.

### 3. Checkpoint ≈ Feb 2027 (~40 flagged bets) — decided on price CLV, not ROI
Mean `clv_price` on flagged bets (per-bet SD ≈ 0.063 → SE ≈ 1pp at n=40; ROI SE would be ≈ 15pp):
- > +1% → plan real stakes (needs item 4 resolved).
- ≤ 0 → the edge doesn't survive the prices we actually get.
- In between → continue to season end.
Also watch `clv_move ~ calib_edge` across all logged matches (9–10/round) as a live replica of the historical test.

### 4. Execution — now the binding constraint (Chris, manual)
- **AU books — partly answered 2026-10-25:** Chris: **Bet365 AU is the only AU book where he can reliably get
  Asian handicaps.** First real data point: Sunderland +0.00 v Leeds (GW9) at Bet365 AU **2.025**, vs best offshore
  2.15 at the Friday run and model break-even 2.08 → ≈ 6% worse than best, ≈ −2.6% EV on the model's numbers.
  If that gap is typical, the EPL edge is not bettable at AU corporates. To measure: note the Bet365 AU price
  for each flagged bet for a few rounds and compare with the logged best price and break-even.
  Same match, Chris's checks ~19:50 Sun: **Sportsbet Draw No Bet 2.10** (≈ +0.9% EV), **Ladbrokes DNB 1.95**
  (≈ −6.3%). AU spread 1.95–2.10 (7.7%) ≫ the model's edge → shopping across AU books matters as much as the
  model. AU books often don't label AH: DNB = AH 0.00, Double Chance = +0.5, H2H win = −0.5, ±0.25 = split stake
  (DNB + win / DNB + double chance); ±0.75 / ±1.0 need a genuine 2-way handicap market ("3-way/European
  handicap" is NOT Asian). Proposed habit: for each flagged bet record Bet365 / Sportsbet / Ladbrokes prices.
  Caveat: football-data's B365 columns are Bet365 international prices — the historical +0.7% price CLV
  "at B365 pre-closing" may not transfer to Bet365 AU.
- **Betfair AU exchange** still unchecked — most promising execution route (backlog item 3).
- **Rotate the Odds API key** (exposed in a Cowork tool error 2026-10-24) → new key into `.env`.

### 5. 2027 off-season (do not start mid-season — it would change the model under test)
1. Fix the ratings season-transition bug (below), 2. refit `config/calibration.yaml`, 3. re-run
`clv_edge_analysis.py` on the refit to confirm the EPL result survives.

## Verdict detail (for reference)
**EPL (`output/backtest_results/clv_edge_report.txt`):** move~signal slope +0.0069, t=4.7 (Pinnacle t=3.9, avg t=3.3),
positive all 6 seasons; artefact-controlled model term t=3.2–4.4; Big 5 ex-EPL ≈ 0 (control). OOS flagged bets
(n=43): market moved +2.0pp toward us (t=3.9); price CLV +0.7% at B365 pre-closing, −1.1% at average prices.
Unresolved: this file shows 44 OOS flagged bets / −4.2% ROI vs the July report's ~92/season / +8.9% — likely
different coefficients (train-only vs refit). Check before quoting either.

**Soft leagues (`output/backtest_results/soft_calibration_report.txt`):** proxy AH movement passes (t=3.10) but
results don't — pooled M3 b_model −0.097 (SE 0.097), CI excludes EPL's +0.245; 1X2 b_model ≤ 0 everywhere; OOS ROI
≈ 0 (AH) and −8% to −23% (1X2). Model predicts price moves but not results beyond the price. Pipeline kept
(`experiment/merge_data.py`, `data/processed/soft_*`); Scandinavian Sofascore stops 2026-07-18.

## Known issues / tech debt
- **Ratings season-transition bug** (`model/ratings.py`): regression-to-mean target computed lazily from live
  ratings, some already updated by same-matchday new-season games → order-dependent ratings. This is why the
  `scrapers/merge.py` ratings_backup row-order hack exists; a clean sort moves ratings by up to 0.018.
  Off-season fix (item 5). Until then never touch merge.py row ordering or `ratings_backup.csv`.
- Matchbook prices exclude commission → "best price" slightly overstated.
- 1% rule ignores margin (some flagged bets ≈ 0 EV). Deliberately unchanged for the season.
- `scrapers/merge.py` rewrites `data/aliases/team_aliases.json` every run (line-ending churn only).
- Any loader with a hard-coded season list needs checking at each season rollover (bit us twice).
- Cowork shell git: no autocrlf, no GitHub credentials. Use `git -c core.autocrlf=true status` (plain `git status`
  shows hundreds of line-ending phantoms), stage with `git -c core.autocrlf=true add --renormalize`; Chris pushes.
- Cowork: write repo docs directly with device_bash, not via a staged copy + device_commit_files — on 2026-10-25
  that path committed a stale handoff (`770acd6`), fixed in the next commit. Always check the file on disk.

## How work gets executed
Cowork scopes and QCs; Antigravity codes via the `antigravity-handoff` skill; briefs in `prompts/`, Chris pastes
`Read prompts/<FILE>.md and carry out every task in it, in order.` Money-critical code gets Cowork-written gold
tests Antigravity may not edit. **Always QC Antigravity's report against the repo.** Never brief an executor to run
`predict` outside the Friday slot. Instructions for Chris: PowerShell, one command per block.

## Commit block
None — Cowork commits locally; if `git -c core.autocrlf=true status -sb` shows `ahead`, Chris runs `git push` in PowerShell.
