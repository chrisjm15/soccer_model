# Index

## Root
| File | Purpose |
|---|---|
| `CLAUDE.md` | Session constitution — roles, constraints, tool allocation |
| `COWORK_HANDOFF_PROMPT.md` | Next actions for incoming session |
| `SESSION_LOG_COWORK.md` | Current session log (replaced each session) |
| `README.md` | GitHub-facing project overview |
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
| `FUTURE_DEVELOPMENT.md` | Durable edge backlog (session 14) — ranked by edge-per-effort, incl. deprioritised items. Handoff carries only current top items; this is the full list. |
| `football_model_briefing.md` | Research briefing — xG, PPDA, markets, data sources |
| `SOCCER_COWORK_SESSION.md` | Original session planning doc (read-only reference) |
| `Football Pythag v0.5.xlsx` | Chris's existing Excel model (reference only, not being evolved) |

## prompts/
Active (session 16) — run in this order:
| File | Purpose |
|---|---|
| `ANTIGRAVITY_CLOSING_LINE_CLV.md` | Money-critical. Real closing odds (AHCh/PCAHH), line conversion, CLV on all log rows, display bug |
| `ANTIGRAVITY_CLV_EDGE_ANALYSIS.md` | After CLV brief. Historical EPL/Big5 test: does model signal predict line movement? + live log |
| `ANTIGRAVITY_SOFT_LEAGUE_MERGE.md` | Independent. Module 4 merge: Sofascore xG + football-data for B1 N1 P1 T1 E1 DNK SWE NOR |
| `ANTIGRAVITY_MERGE_SORT_KEY.md` | Low priority, after CLV brief. Replace ratings_backup row-order hack in merge.py |
| `rescrape_plan_2026-07-18.md` | Reference: soft-league inclusion table (Step 3) |

## prompts/completed/
25 executed or abandoned prompts (reference only) — all Phase 1-3 build prompts, experiment module prompts, bug-fix prompts, and session 14's `CLI_PROMPT_CALIBRATION_CLV.md` + `CLI_PROMPT_RECALIBRATION_TEST.md`. Scan the folder if you need one.

## archive/
| File | Purpose |
|---|---|
| `session_logs/SESSION_LOG_SESSIONS_3_to_6.md` | Sessions 3–6 logs (archived session 7) |
| `session_logs/SESSION_LOG_SESSIONS_9_to_13.md` | Sessions 9–13 logs (archived session 14) |
| `session_logs/SESSION_LOG_SESSION_14.md` | Session 14 log (strategy verdict) |
| `session_logs/SESSION_LOG_SESSION_15.md` | Session 15 log (calibrated deploy, main-line fix, automation) |
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
| `scripts/run_update.ps1` | Scheduled automation: `-Mode settle` (Tue: update+results) / `-Mode predict` (Fri: update+predict) |
| `output/predict_latest.txt`, `output/predictions/` | Console output of the scheduled predict runs |
| `prompts/completed/ANTIGRAVITY_*.md` | Session 15 executor briefs (executed) |
| `config/leagues.yaml` | League definitions + Odds API sport keys |
| `config/calibration.yaml` | EPL AH calibration config (M3/M1 coefficients, market_prob_range, 1% threshold, promoted_min_matches) |
| `data/aliases/team_aliases.json` | Team name mapping |
| `data/processed/all_merged.csv` | 10,714 merged match records (2020-21 to 2025-26) |
| `data/processed/ratings.csv` | Pre-match EMA ratings for all matches |
| `output/backtest_results/predictions.csv` | Full backtest predictions + outcomes |
| `output/backtest_results/calibration_matches.csv` | Per-match calibration data (10,702 rows) — model_prob, market_prob_novig, actual_score, pnl_flat10 |
| `output/backtest_results/calibration_report.txt` | Calibration report — prob zone × line-size tables, disagreement test, by-season drift |
| `output/backtest_results/recalibration_report.txt` | Market-blend test report — regression tables, OOS metrics, threshold sweep, bootstrap CIs |
| `output/backtest_results/recalibrated_test_matches.csv` | Test-season rows (2024-26) with M3/M4 calibrated probs, calibrated edge, P&L |
| `output/paper_trading/log_ah.csv` | EPL AH paper trading tracker (closing columns before the CLV brief are vs PRE-closing odds — invalid; recomputed by ANTIGRAVITY_CLOSING_LINE_CLV) |
| `run.py` | Entry point: `python run.py update / predict / backtest` |
