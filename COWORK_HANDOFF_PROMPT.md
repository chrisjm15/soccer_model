# Handoff

CLAUDE.md is already loaded. Read `SESSION_LOG_COWORK.md` only. Use `docs/INDEX.md` to locate files if needed — do not read files preemptively.

## Next actions
1. Write Phase 2 module prompts — BTTS model. Three self-contained local LLM prompts (ratings.py, poisson.py, btts.py) plus one Sonnet CLI prompt to wire them together and build the backtest engine.
2. Design inputs locked: EMA α=0.1 start, league-specific home advantage, train 2020-23 / test 2023-25, calibration-only backtest (no BTTS odds in source data).
3. When ready to write a prompt, read the relevant spec from docs/ at that point — not before.
