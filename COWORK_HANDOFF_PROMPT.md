# Handoff

CLAUDE.md is already loaded. Read `SESSION_LOG_COWORK.md` only. Use `docs/INDEX.md` to locate files — do not read files preemptively.
*Last updated: 2026-10-25 (session 16).*

## Strategy verdict (2026-07-12, unchanged — constrains everything below)
- **Big 5 ex-EPL: retired.** No bets there.
- **EPL: live hypothesis, being tested now (2026-27).** M3 b_model +0.245 (p=0.022). Edge = calibrated prob − consensus no-vig; flag at ≥ 1%.
- 10-factor large-line layer: superseded, do not build.

## Current state
- Live and automated: Tue 12:00 settle, Fri 12:00 predict (`scripts/run_update.ps1`). Check `output/scheduler_log.txt`.
- Paper log `output/paper_trading/log_ah.csv`: 2 flagged GW9 bets (Villa +1.00 @1.83, Sunderland 0.00 @2.15).
- CLV now uses real closing odds (brief 1 done, `4115d4b`, QC passed). Closing source is market-average: football-data dropped Pinnacle columns mid-2025-26.
- Sessions 15–16 pushed to GitHub (head `06346f2`, 2026-10-25).

## Priorities (in order)

### 1. Run the briefs (Chris)
1. Pushed — done.
2. Antigravity, one brief per fresh session, in this order — paste:
   `Read prompts/<FILE>.md and carry out every task in it, in order.`
   1. ~~`ANTIGRAVITY_CLOSING_LINE_CLV.md`~~ — DONE + QC'd 2026-10-25
   2. `ANTIGRAVITY_CLV_EDGE_ANALYSIS.md` — needs brief 1 committed
   3. `ANTIGRAVITY_SOFT_LEAGUE_MERGE.md` — independent, any time
   4. `ANTIGRAVITY_MERGE_SORT_KEY.md` — low priority, after brief 1
3. Cowork QCs each report against the repo before the next one (run the gold tests, diff the log, spot-check rows).

### 2. Watch Friday's GW10 predict run (Fri 2026-10-30 12:00)
The brief-1 test run on Sunday logged 7 GW10 rows on ratings missing all of GW9 (2 flagged). Cowork deleted
them (still in git at `4115d4b`) so the Friday run logs GW10 normally. Confirm 9–10 GW10 rows appear with
prediction_date 2026-10-30. **Never run predict by hand before Friday** — first sighting locks the row.

### 2b. Verify the first automated settle (Tue 2026-10-27; check-in scheduled 14:00 AEDT)
Villa/Sunderland settled correctly by hand; calibration columns still present. After brief 1: how many
GW9 rows got CLV and how many needed line conversion.

### 3. Checkpoint — decide on line movement, not ROI
ROI at 40 bets has a 95% CI of about ±30pp, so it is reported but not decided on before season end.
Decision rule, applied to `clv_edge_report.txt` (H1 EPL; Pinnacle-to-Pinnacle movement preferred, avg-to-avg must agree in sign):
- slope > 0 with t ≥ 2, **and** H2 flagged bets have mean price-CLV > 0 → edge credible: keep going and plan real execution (see 5).
- t < 1 or slope ≤ 0 → the model does not anticipate the market: keep the paper log running untouched, move effort to soft leagues.
- 1 ≤ t < 2 → inconclusive: re-run with live rows at ~150 logged matches (≈ late Jan 2027).
- Control: H3 (Big 5) should show ~no slope. A strong Big-5 slope means the test is picking up something other than model skill — investigate before trusting H1.

### 4. Soft-league expansion
After the merge brief is QC'd (alias table reviewed by Cowork), the next brief replicates
calibration_backtest + recalibration_test per league. Test market: **AH for B1/N1/P1/T1/E1, 1X2 for
DNK/SWE/NOR** (no AH odds exist there). Scandinavian odds are closing prices — a harder benchmark and
not prices we could bet at. Only ~3 xG seasons per league → ~2 usable test seasons after warm-up.
SC0 and FIN stay parked.

### 5. Manual actions for Chris (no code)
- **Rotate the Odds API key** (exposed in a Cowork tool error on 2026-10-24): new key from your The Odds API
  account → replace the value in `.env`.
- **AU execution check** before any real stakes: in Bet365 AU, Sportsbet, TAB and Betfair AU, open any EPL
  match and note whether a main Asian line (e.g. −0.25 / −0.75 / 0.00) is offered or only ±1.5 / ±0.5.
  The API shows only PlayUp (±1.5) for AU. Couldn't confirm from the web — needs a logged-in look.

### 6. Known issues / tech debt (not urgent)
- Matchbook prices exclude commission → its "best price" is slightly overstated.
- 1% rule ignores margin (some flagged bets ≈ 0 EV at best price). Deliberately unchanged for the season.
- `scrapers/merge.py` rewrites `data/aliases/team_aliases.json` every run (line-ending churn only).
- Cowork shell git: no autocrlf and no GitHub credentials. Use `git -c core.autocrlf=true status`; stage text
  with `git -c core.autocrlf=true add --renormalize`; Chris pushes.

### 7. Edge research backlog — `docs/FUTURE_DEVELOPMENT.md` (unchanged; read before any edge work)

## How work gets executed
Cowork scopes and QCs; Antigravity codes via the `antigravity-handoff` skill. Money-critical code gets
Cowork-written gold tests Antigravity may not edit. **Always QC Antigravity's report against the repo** —
in session 15 it claimed a check that hadn't happened.

## Commit block (Cowork changes not yet committed)
Cowork committed these locally in session 16 (see `git log`); Chris only needs `git push`. If that commit is
missing:
```
git add .gitignore scripts/run_update.ps1 scripts/test_clv.py output/predictions/predict_2026-10-24.txt prompts/ docs/INDEX.md SESSION_LOG_COWORK.md COWORK_HANDOFF_PROMPT.md archive/session_logs/SESSION_LOG_SESSION_15.md
git commit -m "Session 16: CLV defect briefs + gold tests, soft-league merge brief, UTF-8 predict output"
git push
```
