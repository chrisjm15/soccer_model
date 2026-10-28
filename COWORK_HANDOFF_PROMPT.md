# Handoff

CLAUDE.md is already loaded. Read `SESSION_LOG_COWORK.md` only. Use `docs/INDEX.md` to locate files — do not read files preemptively.
*Last updated: 2026-10-28 21:20 (end of session 17).*

## Where the project stands (end of session 17, 2026-10-28)
- **Live:** EPL Asian Handicap model, 1% calibrated-edge rule, unchanged. **Chris bets real money on it** (decided
  28 Oct against Cowork's advice — see below). Paper log `output/paper_trading/log_ah.csv`.
- **Research verdicts:** `docs/RESEARCH_SESSION_17.md` (one table, 16 hypotheses). In short: the live 1% rule does not
  beat the close OOS (CLV@Pinnacle −1.6%); the model's information is early-season only (Aug–Oct); the one new edge is
  **luck** (goals − xG): the market overrates lucky teams even at the close (t −4.1) and only the AH market converts it
  to profit (Big 5 +3.1% ± 1.4, EPL +7.9% at avg prices). O/U, 1X2, BTTS, promoted, dead rubbers, Betfair AU: all fail.
- **Two pre-registered paper tests running** (rule fixed in each script's docstring; verdict at season end):
  EPL luck shadow `scripts/luck_shadow.py` (from GW10, STATUS §6) and Big-5 ex-EPL luck log
  `scripts/luck_paper_big5.py` (Fri log / Tue settle inside `run_update.ps1`, STATUS §7).
- **No manual AU prices** (Chris, final): Telegram shows the Odds API best (offshore) price + exact worth-it price.
  The Odds API never carries Bet365 or AU books for EPL AH. AU-price evidence for the checkpoint will be missing.

## PC schedule (all automatic; `SETUP_SCHEDULE.bat` / `REMOVE_SCHEDULE.bat`; runs only while Chris is logged on)
| When | What |
|---|---|
| Tue 12:00 | `run_update.ps1` settle: update → results → Big-5 luck settle |
| Fri 12:00 | `run_update.ps1 -Mode predict`: update → predict → Big-5 luck log (~8 Odds API credits) |
| Tue + Fri 13:00 | `STATUS.bat` opens (also writes `output/status_latest.txt`) |
| Tue + Fri 13:15 | `scripts/push_quiet.bat` → `output/push_log.txt` |
| Fri 17:00 | `scripts/telegram_send.bat` → `telegram_post.py send`: EPL bets + separate EXPERIMENTAL "underrated picks" (Big-5 luck) message → `output/telegram_latest.txt` |
Telegram: token in `.env`; channel rules in gitignored `TELEGRAM_CHANNEL_HANDOFF.md` (contains the token — never commit);
one post per round (`output/paper_trading/telegram_sent.csv`); refuses stale rounds and Sat 11:25–11:40 (racing card).
Public wording says "underrated picks", never "luck" (Chris). Test message confirmed in channel 28 Oct.

## Decision record
- 28 Oct: **real-money bets continue** (Chris). Cowork recommended stopping: edge historically Aug–Oct only.
- 28 Oct: automatic prices only; Big-5 picks posted to Telegram as experimental.

## Next actions (in order)

### 1. TOP PRIORITY — QC the first full automated Friday (Fri 2026-10-30, check from ~17:15)
- `output/scheduler_log.txt`: predict exit 0 AND `luck_paper_big5 log complete (exit code: 0)`.
- `log_ah.csv`: 9–10 GW10 rows, prediction_date 2026-10-30. **Never run predict by hand outside the Friday slot.**
- `output/luck_big5_latest.txt`: no UNMAPPED / errors; `luck_big5_log.csv` ≈ 40 fixtures, ≈ 15 flagged.
- `output/telegram_latest.txt` says "Posted round 2026-10-30: 2 message(s)"; `output/push_log.txt` shows a clean push.
- First real Telegram post: check wording renders (KEY, no stray HTML).

### 2. Tue 2026-11-03 settle — first Big-5 settle (`luck_paper_big5 settle` in scheduler_log; CLV filled for weekend rows).

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
