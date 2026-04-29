# Session 2 — 2026-04-29

## Key outcomes
- All Phase 2 module prompts written and saved to `prompts/`
- Three local LLM modules generated, reviewed, and corrected
- Phase 2 CLI session executed successfully — backtest ran and produced results
- Threshold sensitivity test run — identified 8-10% as the right operating zone
- Historical BTTS odds research completed — see findings below

## Phase 2 backtest results (assumed odds 1.90)
| Threshold | Bets | % matches | Hit rate | ROI | Brier (bets) |
|---|---|---|---|---|---|
| 5% | 1,954 | 55.9% | 58.6% | +11.4% | 0.2431 |
| 8% | 1,255 | 35.9% | 60.6% | +15.1% | 0.2401 |
| 10% | 815 | 23.3% | 62.6% | +18.9% | 0.2358 |

Calibration is strong: 60-70% probability bin landed at 60.2% actual BTTS rate.
Operating threshold set at 8% for Phase 3 (good selectivity, manageable volume ~12 bets/week).

## Historical BTTS odds research findings
**Verdict: free historical BTTS odds covering 2020-2025 do not exist from legitimate sources.**

- **The Odds API**: BTTS historical data only available from May 2023 onwards. Historical endpoint is paid-only. Cannot backfill 2020-23.
- **OddAlerts**: Historical downloads limited to 6 months at a time. Covers recent data only.
- **Kaggle datasets**: No confirmed Big 5 + BTTS + 2020-2025 dataset found.
- **OddsPortal scraping**: OddsHarvester tool exists and supports BTTS, but against ToS (educational use disclaimer).
- **football-data.co.uk**: Standard CSVs confirmed no BTTS odds. New data format (all_new_data.php) unverified.

## Strategic pivot for Phase 3
Stop trying to enrich the historical backtest. The calibration signal is sufficient.
Move directly to live prediction pipeline using real odds going forward:

1. **The Odds API free tier** (500 credits/month) — covers upcoming BTTS odds for all Big 5 leagues at ~20 credits/month. Free tier sufficient.
2. Build `python run.py predict` — fetches real pre-match BTTS odds via API, runs model, outputs bets above 8% edge.
3. Paper trade through remainder of 2025-26 season.
4. After ~3 months of real predictions vs real odds, validate true edge.

## Decisions made this session
- Operating threshold: 8%
- Phase 3 priority: live pipeline, not historical odds enrichment
- Data source for live odds: The Odds API (free tier)
- Paper trading period: remainder of 2025-26 season before real money

## Files created/modified this session
- `model/ratings.py` — generated (Qwen3), corrected (Cowork)
- `model/poisson.py` — generated (Gemma), test block added (Cowork)
- `model/btts.py` — generated (Qwen3), 2 fixes (Cowork)
- `prompts/RATINGS_PROMPT_QWEN3.md`
- `prompts/POISSON_PROMPT_GEMMA.md`
- `prompts/BTTS_PROMPT_QWEN3.md`
- `prompts/CLI_PROMPT_PHASE2.md`
- `prompts/CLI_PROMPT_THRESHOLD_TEST.md`
- `backtest/engine.py`, `backtest/metrics.py`, `scripts/threshold_test.py` (via CLI)
- `SESSION_LOG_COWORK.md` (this file)

## Next session priorities
1. Build The Odds API integration — fetch real BTTS odds for upcoming matches
2. Build `run.py predict` command — full live prediction output
3. Set up paper trading log (simple CSV: date, match, model_prob, real_odds, edge, bet_flag)
4. First live predictions for next gameweek
