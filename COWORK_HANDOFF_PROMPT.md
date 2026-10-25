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
   2. ~~`ANTIGRAVITY_CLV_EDGE_ANALYSIS.md`~~ — DONE + QC'd 2026-10-25 (`5db7ca2`). Verdict in §3.
   3. ~~`ANTIGRAVITY_SOFT_LEAGUE_MERGE.md`~~ — DONE + QC'd (`f06852c`). Alias table reviewed: correct.
   3b. ~~`ANTIGRAVITY_SOFT_LEAGUE_REFRESH.md`~~ — DONE + QC'd (`5388a3b`). soft_merged: 7,841 matched xG rows; proxy xG 2023-24..2025-26, DNK 2022-25, SWE/NOR 2023-26.
   4. `ANTIGRAVITY_MERGE_SORT_KEY.md` — low priority, after brief 1
3. Cowork QCs each report against the repo before the next one (run the gold tests, diff the log, spot-check rows).

### 2. Watch Friday's GW10 predict run (Fri 2026-10-30 12:00)
The brief-1 test run on Sunday logged 7 GW10 rows on ratings missing all of GW9 (2 flagged). Cowork deleted
them (still in git at `4115d4b`) so the Friday run logs GW10 normally. Confirm 9–10 GW10 rows appear with
prediction_date 2026-10-30. **Never run predict by hand before Friday** — first sighting locks the row.

### 2b. Verify the first automated settle (Tue 2026-10-27; check-in scheduled 14:00 AEDT)
Villa/Sunderland settled correctly by hand; calibration columns still present. After brief 1: how many
GW9 rows got CLV and how many needed line conversion.

### 3. Checkpoint — VERDICT 2026-10-25: EPL information edge is real; profitability depends on price
From `output/backtest_results/clv_edge_report.txt`, QC'd by Cowork:
- EPL: market moves toward the model between pre-closing and close. move~signal slope +0.0069, t=4.7
  (Pinnacle-to-Pinnacle t=3.9, avg-to-avg t=3.3); positive in all 6 seasons.
- Not an artefact: Cowork re-ran with the pre-closing price as a separate control — model term t=3.2–4.4 in EPL,
  ~0 in Big 5 ex-EPL (t −0.3 to 1.3). Big 5 control pooled slope ≈ 0, matching the July "no edge" verdict.
- Size is small. OOS flagged bets (n=43): mean move toward us +2.0pp (t=3.9), ≈ the bookmaker margin.
  Price CLV ≈ 0: +0.7% at B365 pre-closing prices (t=0.7), −1.1% at market-average prices.
  → The edge only pays if we beat the average price. Best-price shopping is the whole game.
- **New live checkpoint: mean `clv_price` on flagged bets at ~40 bets (≈ Feb 2027).** Per-bet SD of price CLV
  ≈ 0.063 → SE ≈ 1pp at n=40 (ROI SE would be ≈ 15pp). Rule: mean clv_price > +1% → plan real stakes;
  ≤ 0 → the edge doesn't survive the prices we actually get; in between → continue to season end.
- AU execution (§5) is now the binding constraint: the model edge is only usable at sharp/best prices.

### 4. Soft-league expansion
Data ready. Next brief (Cowork to write) replicates
calibration_backtest + recalibration_test per league. Test market: **AH for B1/N1/P1/T1/E1, 1X2 for
DNK/SWE/NOR** (no AH odds exist there). Scandinavian odds are closing prices — a harder benchmark and
not prices we could bet at. Only ~3 xG seasons per league → ~2 usable test seasons after warm-up.
SC0 and FIN stay parked. For that brief: exclude `matched=False` rows (play-offs, walkovers) from rating
updates; Scandinavian Sofascore stops 2026-07-18 while football-data runs to 2026-10-19 (SWE 2026 52%, NOR 2026 57% matched)
— re-scrape via scrape_next_league.bat before live use; for backtests, 2026 is partial.

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
