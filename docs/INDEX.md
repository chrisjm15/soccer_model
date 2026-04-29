# Index

## Root
| File | Purpose |
|---|---|
| `CLAUDE.md` | Session constitution — roles, constraints, tool allocation (~65 lines) |
| `COWORK_HANDOFF_PROMPT.md` | Next actions for incoming session |
| `SESSION_LOG_COWORK.md` | What happened last session (replaced each session) |
| `README.md` | GitHub-facing project overview |

## docs/
| File | Purpose |
|---|---|
| `INDEX.md` | This file — find anything without scanning |
| `BUILD_PLAN.md` | Full 4-phase build plan with architecture and design decisions |
| `LOCAL_LLM_SETUP.md` | Hardware specs, model benchmarks, prompt settings (merged from MODEL_FINDINGS) |
| `SESSION_MANAGEMENT_GUIDE.md` | Guide for Chris on managing multi-session projects (not for Claude) |
| `football_model_briefing.md` | Research briefing — xG, PPDA, markets, data sources |
| `SOCCER_COWORK_SESSION.md` | Original session planning doc (read-only reference) |
| `Football Pythag v0.5.xlsx` | Chris's existing Excel model (reference only, not being evolved) |

## prompts/
| File | Purpose |
|---|---|
| `RATINGS_PROMPT_QWEN3.md` | Phase 2 prompt → Qwen3-Coder 30B → produces `model/ratings.py` |
| `POISSON_PROMPT_GEMMA.md` | Phase 2 prompt → Gemma 4 26B → produces `model/poisson.py` |
| `BTTS_PROMPT_QWEN3.md` | Phase 2 prompt → Qwen3-Coder 30B → produces `model/btts.py` |
| `CLI_PROMPT_PHASE2.md` | Phase 2 Sonnet CLI prompt — wires modules, builds backtest engine, runs results |

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
| `data/aliases/team_aliases.json` | Team name mapping |
| `data/processed/all_merged.csv` | 8,972 merged match records |
| `config/leagues.yaml` | League definitions |
