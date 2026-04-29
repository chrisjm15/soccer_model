# Session 2 — 2026-04-29

## Key outcomes
- All Phase 2 module prompts written and saved to `prompts/`
- Four prompts produced: three local LLM prompts + one Sonnet CLI integration prompt
- Ready to execute Phase 2: paste local LLM prompts first, then run CLI prompt

## Execution order
1. Run `prompts/RATINGS_PROMPT_QWEN3.md` → Qwen3-Coder 30B → produces `model/ratings.py`
2. Run `prompts/POISSON_PROMPT_GEMMA.md` → Gemma 4 26B → produces `model/poisson.py`
3. Run `prompts/BTTS_PROMPT_QWEN3.md` → Qwen3-Coder 30B → produces `model/btts.py`
4. Add the three files to the GitHub repo (`soccer_model/model/`)
5. Run `prompts/CLI_PROMPT_PHASE2.md` → Sonnet CLI → wires modules, builds backtest, runs it

## Design decisions locked in this session
- EMA α = 0.1
- Season regression: 30% pull toward league mean at season start
- Default priors: attack_home=1.60, defence_home=1.30, attack_away=1.10, defence_away=1.50
- λ_home = (home_attack + away_defence) / 2 + home_advantage (home_advantage defaults to 0.0)
- λ_away = (away_attack + home_defence) / 2
- BTTS formula: P(BTTS Yes) = sum of grid[h][a] for h≥1, a≥1
- No scipy in poisson.py (pure math module, no external deps beyond stdlib)
- Home advantage set to 0.0 by default (embedded in home/away split; tune later)
- Train: 2020-21 through 2022-23 | Test: 2023-24 through 2024-25
- No BTTS odds → use assumed 1.90, calibration via Brier score
- EV computation: prob * (odds - 1) - (1 - prob) * 1

## Pending
- Execute the four prompts (Chris runs these outside Cowork)
- Return with backtest results (Brier score, ROI, hit rate)
- Next session: interpret results, decide whether to tune α, add home advantage, or proceed to Phase 3

## Files created/modified this session
- `prompts/RATINGS_PROMPT_QWEN3.md` (new)
- `prompts/POISSON_PROMPT_GEMMA.md` (new)
- `prompts/BTTS_PROMPT_QWEN3.md` (new)
- `prompts/CLI_PROMPT_PHASE2.md` (new)
- `SESSION_LOG_COWORK.md` (this file, updated)
- `docs/INDEX.md` (updated with new prompts)
