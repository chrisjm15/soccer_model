# Session 2 — 2026-04-29

## Status at session end
Phase 2 complete. Phase 3 prompt and odds_api.py module ready. CLI_PROMPT_PHASE3.md is the next thing to run.

## What was built this session

### Phase 2 (completed)
- `model/ratings.py` — EMA attack/defence rating engine (generated Qwen3, corrected Cowork)
- `model/poisson.py` — Poisson probability model (generated Gemma, test block added Cowork)
- `model/btts.py` — BTTS prediction + edge calculation (generated Qwen3, 2 fixes Cowork)
- `backtest/engine.py` — lookahead-safe backtest runner (Sonnet CLI)
- `backtest/metrics.py` — Brier score, ROI, calibration, league/season breakdown (Sonnet CLI)
- `scripts/threshold_test.py` — edge threshold sensitivity test (Sonnet CLI)
- `run.py` — updated with `backtest` command

### Phase 3 (ready to run)
- `scrapers/odds_api.py` — The Odds API integration, fetches live BTTS odds (generated Qwen3, 2 fixes + dotenv added Cowork)
- `config/leagues.yaml` — updated with `odds_api_sport_key` for all 5 leagues
- `prompts/ODDS_API_PROMPT_QWEN3.md` — prompt that produced odds_api.py
- `prompts/CLI_PROMPT_PHASE3.md` — next CLI session to run

## Phase 2 backtest results (assumed odds 1.90)
| Threshold | Bets | % matches | Hit rate | ROI | Brier (bets) |
|---|---|---|---|---|---|
| 5% | 1,954 | 55.9% | 58.6% | +11.4% | 0.2431 |
| 8% | 1,255 | 35.9% | 60.6% | +15.1% | 0.2401 |
| 10% | 815 | 23.3% | 62.6% | +18.9% | 0.2358 |

**Operating threshold: 8%** (best balance of selectivity and volume ~12 bets/week)
Calibration is strong: 60-70% probability bin landed at 60.2% actual BTTS rate.

## Key design decisions locked
- EMA α = 0.1
- Season regression: SHRINK_WEIGHT = 0.3 (30% pull toward league mean at season start)
- λ formula: λ_home = (home_attack + away_defence) / 2, λ_away = (away_attack + home_defence) / 2
- Edge threshold: 8% for live operations
- Home advantage: 0.0 (baked into home/away split; tune later)
- Independent Poisson accepted as v1 limitation

## Historical BTTS odds research finding
Free historical BTTS odds covering 2020-2025 do not exist from legitimate sources.
- The Odds API: BTTS history only from May 2023, historical endpoint is paid-only
- OddAlerts: 6 months max, recent data only
- Kaggle: no confirmed Big 5 + BTTS + full period dataset
**Strategic decision:** Skip historical enrichment. Move to live pipeline with real odds going forward.

## Phase 3 next session — what CLI_PROMPT_PHASE3.md does
1. Refreshes data pipeline with 2025-26 season matches (re-run scrapers)
2. Builds `model/live_ratings.py` — latest team ratings lookup
3. Builds `scrapers/team_name_mapper.py` — maps Odds API names to canonical names
4. Builds `run.py predict` — fetches real odds, runs model, outputs bets ≥8% edge
5. Sets up `output/paper_trading/log.csv` — paper trading tracker
6. Builds `run.py update` — weekly data refresh command
7. Runs first live prediction for remaining 2025-26 gameweeks

## Weekly workflow (once Phase 3 is built)
```
python run.py update    # run once a week to refresh data
python run.py predict   # outputs this week's flagged bets
```
After each gameweek: manually fill `actual_btts` and `profit_loss` columns in `output/paper_trading/log.csv`.

## API and environment setup
- The Odds API: free tier, 500 credits/month, ~20 credits/month needed
- API key stored in `.env` file (project root) — loaded automatically via python-dotenv
- `.env` is in `.gitignore` — key will not be pushed to GitHub
- No PowerShell env var setup needed

## Local LLM findings this session
| Model | Task | Quality | Notes |
|---|---|---|---|
| Qwen3-Coder 30B | ratings.py | Poor | Logic bugs, missing imports, needed full rewrite |
| Gemma 4 26B | poisson.py | Good | Just truncated at test block |
| Qwen3-Coder 30B | btts.py | Good | 2 markdown link corruptions only |
| Qwen3-Coder 30B | odds_api.py | Good | 2 markdown link corruptions only |

**Known Qwen3 paste issue:** `x.y_z()` dot notation sometimes renders as `[x.y](url)_z()` in Cowork chat. Always scan `__main__` blocks for this pattern before saving.
**num_predict:** Use 8192 (not 4096) to avoid truncation on longer modules.

## Files created/modified this session
**Local project folder (C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer):**
- `model/ratings.py` (new)
- `model/poisson.py` (new)
- `model/btts.py` (new)
- `scrapers/odds_api.py` (new)
- `config/leagues.yaml` (updated — odds_api_sport_key added)
- `prompts/RATINGS_PROMPT_QWEN3.md` (new)
- `prompts/POISSON_PROMPT_GEMMA.md` (new)
- `prompts/BTTS_PROMPT_QWEN3.md` (new)
- `prompts/CLI_PROMPT_PHASE2.md` (new, executed)
- `prompts/CLI_PROMPT_THRESHOLD_TEST.md` (new, executed)
- `prompts/ODDS_API_PROMPT_QWEN3.md` (new, executed)
- `prompts/CLI_PROMPT_PHASE3.md` (new — run next session)
- `SESSION_LOG_COWORK.md` (this file)
- `docs/INDEX.md` (updated)

**GitHub repo (via CLI sessions):**
- `model/ratings.py`, `model/poisson.py`, `model/btts.py`
- `backtest/engine.py`, `backtest/metrics.py`
- `scripts/threshold_test.py`
- `run.py` (updated)
- `output/backtest_results/predictions.csv`
- Pending commit: `scrapers/odds_api.py`, `config/leagues.yaml`, prompt files
