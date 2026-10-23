# Handoff

CLAUDE.md is already loaded. Read `SESSION_LOG_COWORK.md` only. Use `docs/INDEX.md` to locate files — do not read files preemptively.

## Strategy verdict (2026-07-12 — constrains everything below)
- **Big 5 ex-EPL: retired.** Recalibration test proved the model adds no information beyond the market (coef p=0.13, OOS worse than market-only). No bets in these leagues under the current model.
- **EPL: live hypothesis, not proven edge.** Model coefficient +0.286 (p=0.02 train; ~0.10 after selection correction). OOS sweep: 1% calibrated-edge threshold → ~92 bets/season, +8.9% ROI, CI straddles zero. 2026-27 season is the true out-of-sample test.
- **Raw model probabilities and the old 7% edge threshold are retired.** All future edges = calibrated probability (market-blend M3) − market no-vig.
- **10-factor large-line layer (docs/LARGE_LINE_CALIBRATION.md): superseded, do not build** — M4 showed no large-line interaction.
- Paper trading final 2025-26: 11 bets, +$22.40, +20.4% ROI (luck riding calibration error — see session log). Log convention: pure model output; vetoes go in `notes` column only.

## Priorities (in order)

### 1. TOP — Deploy calibrated EPL model before GW1 (~mid-August)
Cowork writes one Sonnet CLI prompt covering:
- Refit EPL M3 (market-blend fractional logit) on ALL six seasons (the test fit deliberately excluded 2024-26; deployment uses everything). Store coefficients in config, not hard-coded.
- `run.py predict`: replace raw edge/7% threshold with calibrated edge at **1% threshold** (maximises sample for the CLV verdict; stricter thresholds can gate any future real stakes).
- **Best-price execution:** check whether predict evaluates edge vs average or best available odds from the Odds API — switch to best price (worth ~1-2% ROI mechanically).
- Verify promoted-team rating initialisation (3 promoted clubs, no EPL xG history) — how do their ratings seed? If league-mean, flag early-season EPL bets involving them.

### 2. Scandinavian scraping → merge → the same disagreement test
- Chris clicks `scrape_next_league.bat` (desktop copy) whenever the PC is on. N1 was mid-run at session end — check `experiment/sofascore_done.txt`. Queue: N1, B1, P1, SC0, T1, SWE, NOR, DNK, FIN. ~60-110 min per league. Failures (403) are safe — league re-runs next click.
- When queue done: write Module 4 merge prompt (Sofascore xG + football-data results/odds). Check during merge whether the Scandinavian football-data files carry AH odds or only 1X2 closing — determines which market the soft-league test uses.
- Then replicate calibration_backtest + recalibration_test on soft leagues. **This is where the project's remaining upside is concentrated** — the Big-5 result showed the machinery works and the market there is simply too sharp.

### 3. In-season decision framework (2026-27 EPL)
Paper trade calibrated model at 1% threshold with clean CLV (both-sides odds now logged). By ~Christmas (~40-50 bets): positive mean CLV → edge likely real, consider small stakes; negative CLV → close the Big-5 chapter entirely.

### 4. Edge research backlog — full ranked list in `docs/FUTURE_DEVELOPMENT.md`
Top of the list: best-price execution (in priority 1 above), soft-league opening lines /
bet-timing near lineups, xG input upgrades (non-penalty, game-state, set-piece split),
player-availability veto, top-down Pinnacle-anchor research, Betfair exchange, derivative
markets. Deprioritised (calibration, not information): Dixon-Coles, bivariate Poisson, PPDA,
GK xGOT. Read the doc before starting any edge work — it carries the rationale and status flags.

## Commit block — paste to Sonnet CLI (or run before other CLI work)
```
Stage and commit in two groups:
1. "Session 14 wrap: strategy verdict docs, prompt archive, session log"
   — COWORK_HANDOFF_PROMPT.md, SESSION_LOG_COWORK.md, docs/INDEX.md, CLAUDE.md,
     docs/LARGE_LINE_CALIBRATION.md, docs/FUTURE_DEVELOPMENT.md, archive/session_logs/SESSION_LOG_SESSIONS_9_to_13.md,
     scrape_next_league.bat, all moves into prompts/completed/,
     archive/load_sofascore_STALE_SESSION10_COPY.py, experiment/sofascore_done.txt (if present)
   — also: remove the now-empty prompts/experiment/ folder
2. "Scandinavian scrape data: N1 (+ any later leagues)"
   — data/proxy/*_sofascore.csv, data/scandinavian/*_sofascore.csv
Push. Do NOT commit .env.
```

## CLI launch
```
cd "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
claude --model claude-sonnet-4-6
/effort max
```
Run python scripts in plain Windows Terminal only — never inside the CLI.
