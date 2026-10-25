# Session 16 — 2026-10-25

## Status
Model live and automated (unchanged). This session found that **the live CLV metric was never
measuring closing line value**, briefed the fix, and replaced the ROI checkpoint with a CLV-based
decision that can be answered on six seasons of history instead of ~40 live bets.
Four Antigravity briefs are queued in `prompts/`. Nothing executed by Antigravity yet.

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

## Decisions
- Primary verdict metric = line movement vs model signal (historical + live, all logged matches).
  ROI is reported but not used to decide before season end.
- CLV is computed on every logged match, not just flagged bets.
- Closing source: Pinnacle closing, fallback market-average closing. Line conversion mu = 2.8.
- Cross-project files stay out of the soccer repo (.gitignore).

## Files changed this session
Committed locally in `85b9efe` (session 15 work). Uncommitted Cowork changes: `.gitignore` (in 85b9efe),
`scripts/run_update.ps1`, `scripts/test_clv.py`, `output/predictions/predict_2026-10-24.txt`,
`prompts/ANTIGRAVITY_*.md` (4 new), `docs/INDEX.md`, `SESSION_LOG_COWORK.md`, `COWORK_HANDOFF_PROMPT.md`,
`archive/session_logs/SESSION_LOG_SESSION_15.md`.
