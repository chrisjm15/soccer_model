# Handoff

CLAUDE.md is already loaded. Read `SESSION_LOG_COWORK.md` only. Use `docs/INDEX.md` to locate files — do not read files preemptively.
*Last updated: 2026-10-28 (session 17, Chris away — Cowork worked unattended).*

## Where the project stands
- **EPL Asian Handicap is the only live hypothesis.** The model carries real information (market moves toward it,
  H1 t=4.7), but **session 17 re-measured the LIVE rule out of sample** (EPL-only fit, 1% threshold, range guard,
  2024-26, n=179; `output/backtest_results/live_rule_oos_report.txt`):
  move +0.6pp; price CLV **−1.6% at Pinnacle pre-close**, −2.1% at B365, **−0.3% at best of B365/Pinnacle/avg**.
  The **1–2% edge band carries no signal** (move −0.2pp, CLV@Pinnacle −3.0%, n=78). **Edges ≥ 2%** do: move +1.2pp
  (t≈3), CLV −0.7% Pinnacle / +0.9% best-of-3 (n=101, ~50/season).
  Session 16's "+0.7% on 44 flagged" used the **all-leagues** fit's edge — a stricter subset, not the live rule.
  The July "92/season, +8.9%" = EPL fit without the range guard (ROI is noise: SE 6.7pp).
- **Big 5 ex-EPL: retired** (July). **Soft leagues: closed for v1** (session 16).
- Live and automated: Tue 12:00 settle, Fri 12:00 predict (`scripts/run_update.ps1`). Edge = calibrated prob
  (M3) − consensus no-vig; flag at ≥ 1%. Paper log `output/paper_trading/log_ah.csv`. Model unchanged in session 17.
- New (session 17): `STATUS.bat` (read-only status, checkpoint split by edge band), `AU_PRICES.bat` + 
  `output/paper_trading/au_prices.csv` (AU price capture, exact break-even), `PUSH_TO_GITHUB.bat`.
- No briefs outstanding.

## Session 17 research (read `docs/RESEARCH_SESSION_17.md` — one table of verdicts)
- EPL model information is **early-season only** (Aug–Oct move~signal t 6.9, +ve every season; Feb–May 0).
- **Luck (goals − xG) bias survives to the close** (t −4.1, replicated on soft leagues). EPL rule historical +8% at avg
  prices. Pre-registered shadow test from GW10: `scripts/luck_shadow.py`, STATUS section 6.
- O/U 2.5 fail, BTTS fail, **1X2 fail** (CLV test run by Chris 28 Oct, QC'd: 100% joins; CLV@Avg −4.6%), model-free
  Bet365-vs-Pinnacle not visible, Betfair AU no.
- Calibration model term rests on the 2020-21 no-crowd season (b_model t 1.3 without it).

## Decision for Chris (open)
Given the live-rule OOS result, choose before ~10 more flagged bets accumulate:
- Added later in session 17: the live season is leaving the Aug–Oct window where the edge lives. Real-money bets
  from here on have no historical support; paper trading costs nothing.
- **(a) Recommended:** stop real-money bets for this season; keep the 1% rule paper-trading unchanged to the Feb checkpoint (it is the pre-registered test), and read
  the ≥ 2% shadow subset in `STATUS.bat` alongside it. No model change. Decide at the checkpoint on BOTH, and on
  CLV at the price actually obtainable in AU (from `au_prices.csv`), not only the logged offshore best price.
- (b) Raise the threshold to 2% now: ~half the volume (≈ 20 bets by Feb), changes the test mid-season.
- (c) Accept now that the 1% rule does not survive AU prices; keep paper trading for data, put effort into
  backlog item 9 (Pinnacle-anchor price discrepancies at AU books — model-free; the AU tracker collects the data).

## Next actions (in order)

### 1. Fri 2026-10-30 — GW10 predict run, then AU prices (Chris)
- Check 9–10 GW10 rows logged with prediction_date 2026-10-30 (`STATUS.bat` section 1–2).
  **Never run predict by hand outside the Friday slot** — first sighting locks the row.
- After the run: double-click `AU_PRICES.bat`, type Bet365 AU / Sportsbet / Ladbrokes / TAB / Betfair back prices for
  each flagged bet (market named in the sheet), save, close Excel, run `STATUS.bat`.
- `STATUS.bat` verified on Windows 28 Oct; session 17 pushed (`eb507e4`).

### 2. Tue 2026-11-03 settle — automated. `STATUS.bat` shows exit codes and CLV.

### 3. Checkpoint ≈ Feb 2027 (~40 flagged bets) — decided on price CLV, not ROI
Mean `clv_price` on flagged bets (per-bet SD ≈ 0.063 → SE ≈ 1pp at n=40):
- > +1% → plan real stakes (needs AU-price evidence, item 4).  ≤ 0 → edge doesn't survive.  Between → continue.
Historical expectation for this rule at best-of-3 prices: −0.3% ± 1.0% → most likely outcome is "≤ 0 / between".
Also watch `clv_move ~ calib_edge` (STATUS section 4; historical OOS slope +0.67).

### 4. Execution — now the binding constraint (Chris, manual)
- **AU books — partly answered 2026-10-25:** Chris: **Bet365 AU is the only AU book where he can reliably get
  Asian handicaps.** First real data point: Sunderland +0.00 v Leeds (GW9) at Bet365 AU **2.025**, vs best offshore
  2.15 at the Friday run → ≈ 6% worse than best. If that gap is typical, the EPL edge is not bettable at AU corporates.
  Measuring it: `AU_PRICES.bat` each Friday (sheet + exact break-even), `STATUS.bat` section 5 (aim for 10+ bets).
  Same match, Chris's checks ~19:50 Sun: **Sportsbet Draw No Bet 2.10**, **Ladbrokes DNB 1.95**.
  **Corrected session 17 (push-aware EV):** exact break-even 2.111, not 2.08 → Sportsbet 2.10 ≈ −0.4% EV,
  Bet365 2.025 ≈ −3.1%, Ladbrokes ≈ −5.7%, best offshore 2.15 ≈ +1.4%. Now recorded in `au_prices.csv`.
  AU spread 1.95–2.10 (7.7%) ≫ the model's edge → shopping across AU books matters as much as the
  model. AU books often don't label AH: DNB = AH 0.00, Double Chance = +0.5, H2H win = −0.5, ±0.25 = split stake
  (DNB + win / DNB + double chance); ±0.75 / ±1.0 need a genuine 2-way handicap market ("3-way/European
  handicap" is NOT Asian). This mapping is coded in `scripts/au_prices.py` (gold-tested).
  Caveat: football-data's B365 columns are Bet365 international prices, not Bet365 AU.
- **Betfair AU exchange — checked 2026-10-28:** 6% commission on sport → ≈ 3pp of EV at evens. Sunderland case
  needed a back price of 2.18 vs fair 2.16. Pays only for edges ≳ 3pp. Not the rescue (backlog item 3).
- **Rotate the Odds API key** (exposed in a Cowork tool error 2026-10-24) → new key into `.env`.

### 5. 2027 off-season (do not start mid-season — it would change the model under test)
1. Fix the ratings season-transition bug (below), 2. refit `config/calibration.yaml` with the push-consistent market
baseline (tech debt), 3. re-run `scripts/live_rule_oos_check.py` + `clv_edge_analysis.py` on the refit, 4. set the
threshold from the OOS CLV table (not ROI), 5. fix predict's break-even display.

## Verdict detail (for reference)
**EPL (`output/backtest_results/clv_edge_report.txt`):** move~signal slope +0.0069, t=4.7 (Pinnacle t=3.9, avg t=3.3),
positive all 6 seasons; artefact-controlled model term t=3.2–4.4; Big 5 ex-EPL ≈ 0 (control). Its H2 "OOS flagged"
block (n=43, +2.0pp move, +0.7% CLV) used the all-leagues fit — **superseded for the live rule by
`live_rule_oos_report.txt`** (resolved session 17: 44 = all-leagues fit; 92/season = EPL fit, no range guard).

**Soft leagues (`output/backtest_results/soft_calibration_report.txt`):** proxy AH movement passes (t=3.10) but
results don't — pooled M3 b_model −0.097 (SE 0.097), CI excludes EPL's +0.245; 1X2 b_model ≤ 0 everywhere; OOS ROI
≈ 0 (AH) and −8% to −23% (1X2). Model predicts price moves but not results beyond the price. Pipeline kept
(`experiment/merge_data.py`, `data/processed/soft_*`); Scandinavian Sofascore stops 2026-07-18.

## Known issues / tech debt
- **Ratings season-transition bug** (`model/ratings.py`): regression-to-mean target computed lazily from live
  ratings, some already updated by same-matchday new-season games → order-dependent ratings. This is why the
  `scrapers/merge.py` ratings_backup row-order hack exists; a clean sort moves ratings by up to 0.018.
  Off-season fix (item 5). Until then never touch merge.py row ordering or `ratings_backup.csv`.
- **Push mismatch (found session 17, display + small edge bias):** calib_prob is an expected SCORE (push = 0.5)
  but is compared with the two-way no-vig q, which excludes pushes. (1) Predict's "Break-Even Odds" = 1/calib_prob is
  exact only on half lines; on 0/whole lines it is ≈1.4% low for underdogs, high for favourites (exact:
  (1−p_push)/(calib − p_push/2); `AU_PRICES.bat` prints the exact figure). (2) The edge baseline should be
  q + p_push·(0.5 − q): shifts individual 0/whole-line edges by up to ±1pp; refit b_model unchanged (0.2456 vs
  0.2450); OOS flags 179 → 172 (162 shared), CLV the same. Off-season fix with the refit; not worth a mid-season change.
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
None — Cowork commits locally (needs file-deletion permission in the session for git's lock files). If
`git -c core.autocrlf=true status -sb` shows `ahead`, Chris double-clicks `PUSH_TO_GITHUB.bat`.
