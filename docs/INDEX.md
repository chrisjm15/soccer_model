# Index

## Root
| File | Purpose |
|---|---|
| `CLAUDE.md` | Session constitution — roles, constraints, tool allocation |
| `COWORK_HANDOFF_PROMPT.md` | Next actions for incoming session |
| `SESSION_LOG_COWORK.md` | Current session log (replaced each session) |
| `README.md` | GitHub-facing project overview |
| `STATUS.bat` | Double-click: read-only live status (automation, flagged bets, CLV checkpoint split by edge band, live signal, AU prices). Saves `output/status_latest.txt` (gitignored) |
| `AU_PRICES.bat` | Double-click after the Friday predict run: adds flagged bets to `output/paper_trading/au_prices.csv`, prints the AU market + exact break-even, opens the sheet in Excel |
| `DOWNLOAD_AND_TEST_1X2_OU.bat` | Double-click: downloads unfiltered football-data CSVs to `data/raw/footballdata_full/` and runs the 1X2 / O/U CLV test |
| `LUCK_BIG5_DRYRUN.bat` | One-off: runs luck paper gold tests + a dry-run fetch of Big-5 (ex-EPL) AH odds to check team-name mapping (~8 credits) |
| `PUSH_TO_GITHUB.bat` | Double-click: `git push` of Cowork's local commits |
| `scrape_next_league.bat` | Desktop-clickable Sofascore scraper — one league per click, resumable, state in `experiment/sofascore_done.txt` |
| `.env` | API keys — NOT in git, loaded via python-dotenv |

## docs/
| File | Purpose |
|---|---|
| `INDEX.md` | This file — find anything without scanning |
| `BUILD_PLAN.md` | Full 4-phase build plan with architecture and design decisions |
| `LOCAL_LLM_SETUP.md` | Hardware specs and model benchmarks only — workflow is in `local-llm` Cowork skill |
| `local-llm.skill` | Packaged `local-llm` Cowork skill (reference copy — already installed globally) |
| `SESSION_MANAGEMENT_GUIDE.md` | Guide for Chris on managing multi-session projects (not for Claude) |
| `SCANDINAVIAN_EXPANSION_SPEC.md` | Full experiment spec — 25 metric variants, 6 proxy leagues, module architecture, data sources. Handoff doc for Sonnet execution. |
| `LARGE_LINE_CALIBRATION.md` | SUPERSEDED 2026-07-12 — 10-factor layer killed by recalibration test (M4: no large-line interaction). Kept for the factor research notes only. |
| `RESEARCH_SESSION_17.md` | Session 17 verdict table: 11 hypotheses (early-season edge, luck bias, O/U, 1X2, BTTS, model-free, Betfair) with numbers and report pointers |
| `FUTURE_DEVELOPMENT.md` | Durable edge backlog (session 14) — ranked by edge-per-effort, incl. deprioritised items. Handoff carries only current top items; this is the full list. |
| `football_model_briefing.md` | Research briefing — xG, PPDA, markets, data sources |
| `SOCCER_COWORK_SESSION.md` | Original session planning doc (read-only reference) |
| `Football Pythag v0.5.xlsx` | Chris's existing Excel model (reference only, not being evolved) |

## prompts/
No active prompts (session 17). Everything executed lives in `prompts/completed/`.

## prompts/completed/
Session 16 briefs (all executed): `ANTIGRAVITY_CLOSING_LINE_CLV`, `_CLV_EDGE_ANALYSIS`, `_SOFT_LEAGUE_MERGE`,
`_SOFT_LEAGUE_REFRESH`, `_SOFT_LEAGUE_CALIBRATION`, `_MERGE_SORT_KEY` (stopped at its gate, restored), plus
`rescrape_plan_2026-07-18.md`. Older: 25 executed or abandoned prompts (reference only) — all Phase 1-3 build prompts, experiment module prompts, bug-fix prompts, and session 14's `CLI_PROMPT_CALIBRATION_CLV.md` + `CLI_PROMPT_RECALIBRATION_TEST.md`. Scan the folder if you need one.

## archive/
| File | Purpose |
|---|---|
| `session_logs/SESSION_LOG_SESSIONS_3_to_6.md` | Sessions 3–6 logs (archived session 7) |
| `session_logs/SESSION_LOG_SESSIONS_9_to_13.md` | Sessions 9–13 logs (archived session 14) |
| `session_logs/SESSION_LOG_SESSION_14.md` | Session 14 log (strategy verdict) |
| `session_logs/SESSION_LOG_SESSION_15.md` | Session 15 log (calibrated deploy, main-line fix, automation) |
| `session_logs/SESSION_LOG_SESSION_16.md` | Session 16 log (live CLV fix, EPL edge verdict, soft leagues closed) |
| `local-llm-eval-review.html` | Skill eval viewer output (session 7, reference only) |
| `load_sofascore_STALE_SESSION10_COPY.py` | Old buggy copy that caused the session-10 caching incident — do NOT run. Live script: `experiment/load_sofascore.py` |

## GitHub repo (chrisjm15/soccer_model)
| File/Folder | Purpose |
|---|---|
| `scrapers/understat.py` | Big 5 xG scraper |
| `scrapers/footballdata.py` | football-data.co.uk CSV loader |
| `scrapers/merge.py` | Data merge engine |
| `scrapers/odds_api.py` | The Odds API — live AH odds fetcher |
| `scrapers/team_name_mapper.py` | Maps Odds API team names to canonical names |
| `model/ratings.py` | EMA attack/defence rating engine |
| `model/clv.py` | Pure CLV functions: no-vig, AH line conversion (Poisson supremacy solve), clv_move / clv_price |
| `model/calibration.py` | Pure calibration functions (consensus no-vig, calibrate_prob, calibrated_ah_decision, calibrate_m1) |
| `model/poisson.py` | Poisson probability model (BTTS, WDL, O/U) |
| `model/btts.py` | BTTS prediction, edge calculation, bet flagging |
| `model/markets.py` | 1X2, O/U, AH output layers with no-vig edge calculation |
| `model/live_ratings.py` | Latest team ratings lookup for live predictions |
| `backtest/engine.py` | Historical simulation engine (lookahead-safe) |
| `backtest/metrics.py` | Brier score, ROI, calibration, league/season breakdown |
| `backtest/multi_market_engine.py` | Multi-market backtest (1X2, O/U, AH) |
| `scripts/threshold_test.py` | Edge threshold sensitivity explorer |
| `scripts/threshold_sweep.py` | Threshold optimisation sweep |
| `scripts/calibration_backtest.py` | AH model calibration over all 10,702 historical matches — probability zone × line-size cross-tab, disagreement test |
| `scripts/recalibration_test.py` | Market-blend logistic regression test (M1-M4) — trains on 2020-24, evaluates OOS on 2024-26. Tests if model adds info beyond market. Threshold sweep with bootstrap CI. |
| `scripts/fit_epl_calibration.py` | Refit M3 & M1 on 6 historical EPL seasons (2020-26), generates config/calibration.yaml |
| `scripts/test_calibration.py` | Fixed gold tests for model/calibration.py |
| `scripts/test_line_selection.py` | Fixed gold tests for select_main_line (main Asian line choice) |
| `scripts/test_clv.py` | Fixed gold tests for model/clv.py (closing-line conversion, clv_move, clv_price) — session 16 |
| `scripts/clv_edge_analysis.py` | Historical EPL/Big 5 line-movement vs model signal test + live log → `clv_edge_report.txt` (session 16 verdict) |
| `scripts/soft_league_calibration.py` | Soft-league M1/M3 (AH + 1X2), OOS sweep, movement test → `soft_calibration_report.txt` (failed) |
| `experiment/load_footballdata.py` | football-data loader for proxy + Scandinavian leagues (season list to 2026-27) |
| `experiment/build_soft_aliases.py`, `experiment/merge_data.py` | Soft-league alias table + Sofascore/football-data merge → `data/processed/soft_merged.csv` |
| `data/aliases/soft_league_aliases.json` | Sofascore → football-data team names, 8 soft leagues (Cowork-reviewed) |
| `scripts/live_rule_oos_check.py` | Session 17: OOS CLV of the LIVE rule (EPL-only fit, 1% + range guard) by threshold and price source; push-consistency check of the calibration → `live_rule_oos_report.txt` |
| `scripts/ou_1x2_calibration_check.py` | Session 17: M1/M3 calibration + OOS ROI for O/U 2.5 and 1X2 (Big 5) → `ou_1x2_calibration_report.txt` (O/U fails; 1X2 inconclusive) |
| `scripts/download_full_footballdata.py`, `scripts/ou_1x2_clv_check.py` | Full football-data download; 1X2 / O/U line-movement + CLV test → `ou_1x2_clv_report.txt` |
| `scripts/advanced_research.py` | Session 17 sections A (live-rule robustness, early-season), B (model-free value), C (luck bias), D (BTTS) → `advanced_<X>.txt` |
| `scripts/advanced_research2.py` | Session 17 part 2 (needs `data/raw/footballdata_full/`): E luck→O/U, F luck→1X2/DNB, G promoted, H dead rubbers, J luck AH by venue → `advanced_<X>.txt` |
| `scripts/luck_paper_big5.py`, `scripts/test_luck_paper.py` | Luck rule paper log for La Liga/Bundesliga/Serie A/Ligue 1 (Fri log, Tue settle via run_update.ps1) → `output/paper_trading/luck_big5_log.csv`; gold tests |
| `scripts/luck_shadow.py` | Pre-registered luck shadow test on the live log → `output/paper_trading/luck_shadow.csv` (STATUS section 6) |
| `scripts/au_prices.py` | AU price tracker: AH line → AU market mapping, exact push-aware EV / break-even, Betfair 6% commission. `prepare` / `report` |
| `scripts/test_au_prices.py` | Gold tests for `scripts/au_prices.py` (hand arithmetic) |
| `scripts/live_status.py` | Read-only live status report (run by `STATUS.bat`) |
| `scripts/run_update.ps1` | Scheduled automation: `-Mode settle` (Tue: update+results) / `-Mode predict` (Fri: update+predict) |
| `output/predict_latest.txt`, `output/predictions/` | Console output of the scheduled predict runs |
| `prompts/completed/ANTIGRAVITY_*.md` | Session 15 executor briefs (executed) |
| `config/leagues.yaml` | League definitions + Odds API sport keys |
| `config/calibration.yaml` | EPL AH calibration config (M3/M1 coefficients, market_prob_range, 1% threshold, promoted_min_matches) |
| `data/aliases/team_aliases.json` | Team name mapping |
| `data/processed/all_merged.csv` | ~11,060 merged Big 5 records 2020-21→2026-27, incl. football-data closing AH columns (close_*) |
| `data/processed/soft_merged.csv`, `soft_ratings.csv` | Soft-league merged data (12,869 rows) and xG ratings — gitignored, regenerate with merge_data.py |
| `data/processed/ratings.csv` | Pre-match EMA ratings for all matches |
| `output/backtest_results/predictions.csv` | Full backtest predictions + outcomes |
| `output/backtest_results/calibration_matches.csv` | Per-match calibration data (10,702 rows) — model_prob, market_prob_novig, actual_score, pnl_flat10 |
| `output/backtest_results/calibration_report.txt` | Calibration report — prob zone × line-size tables, disagreement test, by-season drift |
| `output/backtest_results/recalibration_report.txt` | Market-blend test report — regression tables, OOS metrics, threshold sweep, bootstrap CIs |
| `output/backtest_results/recalibrated_test_matches.csv` | Test-season rows (2024-26) with M3/M4 calibrated probs, calibrated edge, P&L |
| `output/paper_trading/log_ah.csv` | EPL AH paper trading tracker — real closing CLV (closing_source, clv_move, clv_price) on every row |
| `output/backtest_results/clv_edge_report.txt`, `soft_calibration_report.txt` | Session 16 verdict reports (EPL edge real but small; soft leagues fail). NOTE: clv_edge H2 "44 flagged" used the all-leagues fit — superseded for the live rule by `live_rule_oos_report.txt` |
| `output/backtest_results/live_rule_oos_report.txt` | Session 17: live rule OOS — 179 bets/2 seasons, CLV@Pinnacle −1.6%, edge ≥2% subset carries the signal |
| `output/paper_trading/au_prices.csv` | AU prices per flagged bet (Chris fills in; Excel-safe text key) |
| `run.py` | Entry point: `python run.py update / predict / backtest` |
