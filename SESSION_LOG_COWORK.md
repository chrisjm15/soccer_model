# Session 16 — 2026-10-25

## Status at session end (2026-10-25 19:00)
Six briefs executed and QC'd in one day. Outcomes: (1) live CLV fixed — it had never measured closing value;
(2) EPL edge confirmed real but ≈ one bookmaker margin → price access decides profitability; checkpoint moved to
live price CLV at ~40 bets (≈ Feb 2027); (3) soft leagues tested and closed for v1; (4) a ratings season-transition
bug found, deferred to the off-season. Automation unchanged and running. No briefs outstanding.

## Done (Cowork)
1. **Session 15 commit made locally — `85b9efe`** (13 files). Cowork shell has no GitHub credentials;
   Chris pushed from PowerShell — origin/main = `06346f2`.
   - Cross-project files (`AFL/`, `SPORTS_PROJECT_SETUP.md`, `skillcreator_sports_project_starter.md`)
     added to `.gitignore` instead of committed. `scripts/run_update.ps1.bak` deleted.
   - First attempt stored 4 files with CRLF (Cowork's Linux git has no autocrlf); amended with
     `--renormalize` before any push. Repo is LF; working tree is CRLF on Windows. If Cowork shell
     `git status` shows hundreds of "modified" files, they are line-ending phantoms — check with
     `git -c core.autocrlf=true status`.
2. **CLV defect found (money-critical).** `run.py results` uses football-data `AHh/B365AHH/B365AHA`.
   football-data notes.txt: those are pre-closing odds "collected Friday afternoons"; closing columns
   carry a `C` (`AHCh`, `PCAHH`, `AvgCAHH`). Our bet is logged Friday 12:00 AEDT, so the "CLV" compared
   two prices roughly 15 hours apart and, when the line differed, was left blank. All existing CLV values
   are invalid. Also found: `odds_ah_home/away_at_bet` are best prices from different books, so their
   no-vig is not a market probability — the fix uses `market_prob_consensus` instead.
   → `prompts/ANTIGRAVITY_CLOSING_LINE_CLV.md` + gold tests `scripts/test_clv.py` (line conversion via
   Poisson supremacy solve; gold values from an independent Cowork reference implementation; file
   verified passing against that reference).
3. **Checkpoint re-plan.** ROI on 40 bets has a 95% CI of about ±30pp (per-bet SD ≈ 0.95 units at ~1.9
   odds) — it cannot decide anything. Replaced with a line-movement test: does the model signal predict
   pre-closing → closing movement? Answerable now on EPL 2020-26 (~2,279 matches) with football-data
   closing columns. → `prompts/ANTIGRAVITY_CLV_EDGE_ANALYSIS.md`. Decision rule in the handoff.
4. **Soft-league AH check.** Proxy leagues B1/E1/N1/P1/SC0/T1: AH odds ~100% present.
   Scandinavian DNK/SWE/NOR/FIN: **zero** AH odds in every season → their test market is 1X2.
   Scandinavian 1X2 odds are **closing** (B365CH/AvgCH); proxy odds are pre-closing.
   xG seasons: proxy 2023-24→2025-26 (DNK from 2022-23); Scandinavian 2023→2025 + partial 2026.
   Team names differ heavily between Sofascore and football-data (needs an alias table).
   → `prompts/ANTIGRAVITY_SOFT_LEAGUE_MERGE.md`.
5. **Tech debt.** Display bug folded into the CLV brief. merge.py row-order hack →
   `prompts/ANTIGRAVITY_MERGE_SORT_KEY.md` (pass/fail gate: ratings diff < 1e-6, else restore).
   Also found: merge.py rewrites `data/aliases/team_aliases.json` on every run (cause of its
   line-ending churn) — harmless, noted.
6. **`scripts/run_update.ps1` fix (Cowork):** `Tee-Object` in PowerShell 5.1 wrote the dated predict file
   as UTF-16 (git saw it as binary). Now captures output once and writes both copies with
   `Out-File -Encoding utf8`. Exit code captured into `$predictCode`. Not yet run on Windows — the CLV
   brief's Task 6 runs it once. `output/predictions/predict_2026-10-24.txt` converted to UTF-8.
7. Scheduled a check-in for Tue 2026-10-27 14:00 AEDT to verify the first automatic settle.

8. **Brief 1 executed by Antigravity (`4115d4b`) — QC PASSED.** Gold tests unchanged and passing (re-run by
   Cowork); 7 converted rows re-computed with Cowork's independent reference — all within 1e-5; log diff vs
   backup clean; unrequested predict change (append keeps all columns) reviewed — harmless, consistent with
   the never-drop-columns rule. Findings: football-data has no Pinnacle columns after ~210 EPL matches of
   2025-26 → live closing source is market-average (`avg`). May-2026 bets: mean clv_price −3.66% (n=11; old ±1.5
   lines, pre-calibration model — not evidence about the current model).
9. **Defect caused by Cowork's brief:** Task 6 step 6 (hand-run predict on Sunday) logged 7 GW10 rows on
   ratings missing GW9 (2 flagged: Spurs v Palace away −1.00, Man City v Brighton away −0.75). First-sighting
   would have locked them. Cowork deleted exactly those 7 rows (verified 7-line diff). Lesson: never ask an
   executor to run `predict` outside the Friday slot.
10. Brief 2 amended: add avg-to-avg movement (`move_avg`), note Pinnacle gap.

11. **Brief 2 executed (`5db7ca2`) — QC PASSED, verdict reached.** 100% joins; Cowork reproduced H1 slope
    (0.0069, t=4.69) and ran an artefact control (move ~ logit(model) + logit(pre price)): EPL model term
    t=3.2–4.4; Big 5 ex-EPL ≈ 0. Conclusion: real but small EPL information edge (flagged OOS bets: +2.0pp
    move, price CLV ≈ 0 at B365/avg prices). Checkpoint changed to live mean clv_price at ~40 flagged bets.
    Side note, unexplained: OOS flagged bets here are 44 over 2 seasons (−4.2% realised ROI) vs the July
    figure of ~92/season at +8.9%. Likely different coefficients (train-only vs refit) — check before quoting
    either number again.

12. **Brief 3 executed (`f06852c`) — QC: alias table and joins correct, but data incomplete.** Cowork found
    `experiment/load_footballdata.py` had a frozen season list ending 2024-25 (same bug as session 15's scrapers)
    → 2025-26 missing for all 5 proxy leagues (1 of 3 xG seasons). Scandinavian football-data stops 2026-05-04.
    Cowork added 2025-26/2026-27 to SEASON_CODES; `prompts/ANTIGRAVITY_SOFT_LEAGUE_REFRESH.md` re-downloads and
    re-merges. Lesson: every scraper/loader with a hard-coded season list needs checking at each season rollover.

13. **Refresh brief executed (`5388a3b`) — QC PASSED.** 2025-26 now merged for all 5 proxy leagues (100% match),
    DNK 2025 complete; 7 new promoted-club aliases all exact/normalised. Pre-existing seasons unchanged. Cowork
    re-checked soft_merged.csv: 7,841 matched xG rows, 0 duplicates.

14. Wrote `prompts/ANTIGRAVITY_SOFT_LEAGUE_CALIBRATION.md`: proxy closing odds via loader (Part A), soft ratings
    via unmodified `build_ratings` on xG rows only (B), warm-up season + 10-match guard (C), M1/M3 AH and 1X2,
    stacked robustness, OOS sweep, movement test with EPL benchmark (D). Decision rule pre-set in handoff §4.

15. **Soft-league calibration executed (`c758b04`) — QC PASSED, result: FAIL.** Ratings fingerprint unchanged;
    filters lost ≤ 11.7% at the experience guard; hand-checks correct. Cowork reproduced D2 pooled AH b_model
    (−0.0974, SE 0.0965) and D5 controlled movement term (t=3.10). Pre-set rule required both → fail. 1X2 fails
    in every group. Soft-league route closed for v1; focus returns to EPL execution.

16. **Merge sort-key brief: stop gate triggered (correct behaviour).** Deterministic sort changed ratings by up to
    0.018 (8,280/11,060 rows > 1e-6); Antigravity restored merge.py/ratings.csv/all_merged.csv, tree clean. Cowork
    confirmed its root cause in `model/ratings.py` (league means for season regression read live, partly
    new-season-updated ratings → order-dependent). Deferred to the off-season with a calibration refit.

17. Real-money data point (Chris): Sunderland +0.00 at **Bet365 AU 2.025** (best offshore 2.15, break-even 2.08 →
    ≈ −2.6% EV). Bet365 AU is the only AU book where Chris reliably gets Asian handicaps. Recorded in handoff §4.
18. Defect (Cowork): end-of-session commit `770acd6` contained a stale early-session handoff (staged-copy path).
    Rewritten directly on disk and verified; process note added to handoff tech debt.

19. AU price spread, same bet: Sportsbet DNB 2.10, Bet365 AH 2.025, Ladbrokes DNB 1.95 (break-even 2.08). Recorded.

## Decisions
- Primary verdict metric = line movement vs model signal (historical + live, all logged matches).
  ROI is reported but not used to decide before season end.
- CLV is computed on every logged match, not just flagged bets.
- Closing source: Pinnacle closing, fallback market-average closing. Line conversion mu = 2.8.
- Cross-project files stay out of the soccer repo (.gitignore).
- Ratings season-transition fix deferred to 2027 off-season (would change the live model mid-test).
- Soft leagues: closed for v1 per the rule set before the results (handoff §4).

## Files changed this session
All committed and pushed. Key new files: `model/clv.py`, `scripts/test_clv.py` (gold), `scripts/clv_edge_analysis.py`,
`scripts/soft_league_calibration.py`, `experiment/build_soft_aliases.py`, `experiment/merge_data.py`,
`data/aliases/soft_league_aliases.json`, two verdict reports in `output/backtest_results/`. Briefs moved to
`prompts/completed/`. Docs refreshed: CLAUDE.md (focus line), handoff (full rewrite), INDEX, FUTURE_DEVELOPMENT.
