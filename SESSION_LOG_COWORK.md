# Session 17 — 2026-10-28 (Chris away; Cowork worked unattended)

## Status
Chris asked to analyse "data scraped overnight" and progress the project. **No overnight scrape exists** — the last
data pull was the Tue 27 Oct 12:00 settle (already QC'd in session 16). Its log output had not been committed.
Cowork built AU price tooling and status/push bat files, resolved the 44-vs-92 discrepancy, and in doing so found
that the live rule's OOS CLV is negative. Model and automation unchanged. Decision (a)/(b)/(c) open in the handoff.

## Done (Cowork)
1. Archived session 16 log → `archive/session_logs/SESSION_LOG_SESSION_16.md`. Committed the Tue settle output
   (`log_ah.csv` GW9 results + CLV, `scheduler_log.txt`) — `4deea6c`.
2. **44 vs 92 resolved.** `recalibrated_test_matches.csv` `calibrated_edge` = all-leagues M3 fit; the EPL-only edge
   was never saved. Session 16 H2 (44 flagged, +0.7% CLV) used it. July's 92/season = EPL-only fit, no range guard.
3. **Live rule OOS (new, money-relevant).** `scripts/live_rule_oos_check.py` → `live_rule_oos_report.txt`. Replicates
   the July train coefs exactly (−0.1416 / 0.2850 / 0.2858) and session 16's 43-bet subset (+0.65% vs +0.69%).
   Live rule 2024-26: 179 bets, move +0.60pp ± 0.30, CLV@Pinnacle −1.63% ± 0.65, best-of-3 −0.29% ± 1.03.
   1–2% band: move −0.17pp, CLV@Pinnacle −3.0%. ≥ 2%: move +1.21pp ± 0.40, CLV@Pinnacle −0.69%, best-of-3 +0.94%.
   Slope price_clv ~ edge (EPL fit) +0.32, t 3.0. Signal is real; the 1% threshold is too low to beat the close.
4. **Push mismatch found** (calib_prob is an expected score; q excludes pushes). Sized: |gap| mean 0.5pp on 0/whole
   lines, 0.24pp quarter; refit b_model unchanged; OOS flags 179→172; CLV unchanged. Main practical effect: predict's
   break-even display (1/calib) is ≈1.4% wrong on 0/whole lines → AU EV numbers corrected (Sportsbet 2.10 was
   −0.4% EV, not +0.9%). Deferred to off-season refit.
5. **Betfair AU:** 6% Market Base Rate on sport (betfair.com.au help page). ≈ 3pp of EV at evens → only edges ≳ 3pp.
6. Built `scripts/au_prices.py` + gold tests `scripts/test_au_prices.py` (all pass; hand arithmetic incl. an
   outcome-by-outcome EV cross-check and the closed-form P(draw) at λ=1.4/1.4 = 0.252801), sheet
   `output/paper_trading/au_prices.csv` pre-filled with GW9 (Sunderland prices from Chris's 25 Oct checks).
7. Built `scripts/live_status.py` (read-only). Bat files: `STATUS.bat`, `AU_PRICES.bat`, `PUSH_TO_GITHUB.bat` (CRLF;
   absolute paths; Python312 path with fallback to `python`). Not run on Windows yet — first click is the test.
8. Docs: handoff rewritten (decision block, corrected AU EVs, push tech debt, off-season list), CLAUDE.md focus line,
   INDEX, FUTURE_DEVELOPMENT (session 17 note, Betfair item).

9. **New hypotheses (Chris asked for more models).** Markets every AU book offers:
   - O/U 2.5 (`scripts/ou_1x2_calibration_check.py`): fail — b_model n.s., OOS M3 worse than market, ROI negative.
   - 1X2: inconclusive on ROI (EPL away b_model t 2.14). Cowork bug caught: per-outcome fits must be renormalised
     to sum to 1 (fixed; sums were ≈ 1.000 so results barely moved).
   - CLV test written (`scripts/ou_1x2_clv_check.py`) + `DOWNLOAD_AND_TEST_1X2_OU.bat` (football-data unreachable from
     Cowork). Validated on mock closing data: caught a book-mix artefact (Pinnacle close − Avg pre gave t −11 on pure
     noise) → movement is now like-for-like; null mock then gives slopes ≈ 0. Decision rule pre-set in the script.

10. **Advanced research (Chris: "go through all the outstanding stuff... BTTS... advanced analysis").**
    `scripts/advanced_research.py` A–D + `docs/RESEARCH_SESSION_17.md` (verdict table). Headlines: EPL information is
    early-season (interaction t 4.9); calibration model term rests on 2020-21; luck bias at close t −4.1, replicated on
    soft leagues; BTTS fail; model-free Bet365/Max vs Pinnacle not visible. Two headline results re-computed with
    independent code (exact match). A late-season ROI anomaly (t 2.6 post-hoc) checked for look-ahead (none) and
    recorded as noise / prospective only.
11. Pre-registered `scripts/luck_shadow.py` (rule fixed in docstring; counts from GW10); STATUS section 6.

12. Chris home 28 Oct: STATUS.bat ran on Windows (identical to Linux output); pushed to `eb507e4`; luck_shadow.csv
    untracked (line-ending churn). Chris ran DOWNLOAD_AND_TEST_1X2_OU.bat — QC: 30 files, 100% join, Pinnacle close 92%.
    **1X2 and O/U fail the pre-set rule** (EPL home/away move t 3.0/2.7 but CLV@Avg −4.6%).

13. Part 2 research (Chris: "keep exploring"): `scripts/advanced_research2.py` E–H, J with a pass rule written
    before results. E luck→O/U fail; F luck→1X2/DNB fail; G promoted fail; H dead rubbers fail; J luck AH by venue:
    Big 5 +3.1% ± 1.4 at avg (passes), Max inflated by ~0.4% extreme quotes (capped), Betfair net 6% ≈ avg − 1pp
    on the same rows. Real-money decision still unanswered by Chris.

14. **Chris decided: continue real-money bets.** Built Big-5 luck paper log (`scripts/luck_paper_big5.py` + gold tests
    `scripts/test_luck_paper.py`), wired into `scripts/run_update.ps1` (Fri log / Tue settle, try/catch, after main
    steps; CRLF kept), STATUS section 7, `LUCK_BIG5_DRYRUN.bat`. Not yet run against the live Odds API.

## Decisions
- Real-money bets continue (Chris, 2026-10-28), against Cowork's recommendation.
- None taken on the model. Recommendation to Chris: (a) keep the 1% rule to the Feb checkpoint, read the ≥ 2% shadow
  subset and AU-price CLV alongside it.
- Push mismatch: off-season fix with the refit, not mid-season.

## Not verified
- Bat files on Windows (Linux VM only). Tests and scripts ran under Linux Python 3.10 / pandas 2.3.
- Betfair AU EPL AH liquidity (needs a live market look).
