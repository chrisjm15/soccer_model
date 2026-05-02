# Index

## Root
| File | Purpose |
|---|---|
| `CLAUDE.md` | Session constitution — roles, constraints, tool allocation (~65 lines) |
| `COWORK_HANDOFF_PROMPT.md` | Next actions for incoming session |
| `SESSION_LOG_COWORK.md` | What happened last session (replaced each session) |
| `README.md` | GitHub-facing project overview |
| `.env` | API keys — NOT in git, loaded via python-dotenv |

## docs/
| File | Purpose |
|---|---|
| `INDEX.md` | This file — find anything without scanning |
| `BUILD_PLAN.md` | Full 4-phase build plan with architecture and design decisions |
| `LOCAL_LLM_SETUP.md` | Hardware specs, model benchmarks, prompt settings |
| `SESSION_MANAGEMENT_GUIDE.md` | Guide for Chris on managing multi-session projects (not for Claude) |
| `football_model_briefing.md` | Research briefing — xG, PPDA, markets, data sources |
| `SOCCER_COWORK_SESSION.md` | Original session planning doc (read-only reference) |
| `Football Pythag v0.5.xlsx` | Chris's existing Excel model (reference only, not being evolved) |

## prompts/
| File | Purpose | Status |
|---|---|---|
| `RATINGS_PROMPT_QWEN3.md` | Phase 2 → Qwen3 → `model/ratings.py` | Executed |
| `POISSON_PROMPT_GEMMA.md` | Phase 2 → Gemma → `model/poisson.py` | Executed |
| `BTTS_PROMPT_QWEN3.md` | Phase 2 → Qwen3 → `model/btts.py` | Executed |
| `CLI_PROMPT_PHASE2.md` | Phase 2 Sonnet CLI — backtest engine + results | Executed |
| `CLI_PROMPT_THRESHOLD_TEST.md` | Threshold sensitivity test (5% / 8% / 10%) | Executed |
| `ODDS_API_PROMPT_QWEN3.md` | Phase 3 → Qwen3 → `scrapers/odds_api.py` | Executed |
| `CLI_PROMPT_PHASE3.md` | Phase 3 Sonnet CLI — live pipeline, predict command, paper trading | **Run next** |

## prompts/completed/
| File | Purpose |
|---|---|
| `CLI_PROMPT_PHASE1.md` | Phase 1 data pipeline prompt (executed, complete) |

## archive/session_logs/
| File | Purpose |
|---|---|
| *(empty — past session logs archived here)* | |

## GitHub repo (chrisjm15/soccer_model)
| File/Folder | Purpose |
|---|---|
| `scrapers/understat.py` | Big 5 xG scraper |
| `scrapers/footballdata.py` | football-data.co.uk CSV loader |
| `scrapers/merge.py` | Data merge engine |
| `scrapers/odds_api.py` | The Odds API — live BTTS odds fetcher |
| `model/ratings.py` | EMA attack/defence rating engine |
| `model/poisson.py` | Poisson probability model (BTTS, WDL, O/U) |
| `model/btts.py` | BTTS prediction, edge calculation, bet flagging |
| `backtest/engine.py` | Historical simulation engine (lookahead-safe) |
| `backtest/metrics.py` | Brier score, ROI, calibration, league/season breakdown |
| `scripts/threshold_test.py` | Edge threshold sensitivity explorer |
| `config/leagues.yaml` | League definitions + Odds API sport keys |
| `data/aliases/team_aliases.json` | Team name mapping |
| `data/processed/all_merged.csv` | 8,972 merged match records (Phase 1) |
| `data/processed/ratings.csv` | Pre-match EMA ratings for all matches (Phase 2) |
| `output/backtest_results/predictions.csv` | Full backtest predictions + outcomes |
| `run.py` | Entry point: `python run.py backtest` / `predict` / `update` |
