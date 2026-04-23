# Soccer Model — Session State & Handover

*Last updated: 2026-04-23, Session 1*

---

## Current Status

**Phase:** Phase 1 — CLI prompt written, ready for Chris to execute

**What's done:**
- Research briefing reviewed (`football_model_briefing.md`)
- v0.5 Excel model reviewed (`Football Pythag v0.5.xlsx` — 10 leagues, 88 cols, SOT-based Pythagorean)
- Free data source audit completed (Understat = Big 5 xG; FBref = 40+ leagues xG; football-data.co.uk = results/odds/cards)
- All architectural decisions made and logged in `CLAUDE.md`
- 4-phase build plan written (`BUILD_PLAN.md`)
- Session governance and handover protocol established
- Phase 1 CLI prompt written (`CLI_PROMPT_PHASE1.md`)

**What's NOT done yet:**
- Phase 1 not yet executed (Chris needs to run it in Claude Code CLI)
- No code exists yet
- No GitHub repo created yet
- No data downloaded yet

---

## Next Action

**Chris executes Phase 1.** Open terminal, follow the 3 steps in `CLI_PROMPT_PHASE1.md`:
1. `cd` to the Soccer folder
2. Launch Claude Code with `/effort max`
3. Paste the prompt

**After Phase 1 completes:** Come back to this Cowork session with the summary output. We'll review the data quality, check merge rates, note any issues, and then write the Phase 2 CLI prompt (BTTS model).

---

## Decisions Made (Summary)

| # | Decision | Choice | Date |
|---|---|---|---|
| 1 | Architecture | Fresh xG-based build (not evolving v0.5) | 2026-04-23 |
| 2 | First market | BTTS (Both Teams To Score) | 2026-04-23 |
| 3 | Launch leagues | Big 5 (EPL, La Liga, Bundesliga, Serie A, Ligue 1) via Understat | 2026-04-23 |
| 4 | Wave 2 leagues | Nordic 4 (Finland, Sweden, Norway, Denmark) via FBref | 2026-04-23 |
| 5 | Build order | Big 5 first, Nordic second | 2026-04-23 |
| 6 | Data sources | Understat (xG) + football-data.co.uk (results/odds) + FBref (Nordic, later) | 2026-04-23 |
| 7 | Version control | GitHub repo `chrisjm15/soccer_model` | 2026-04-23 |

---

## Open Questions (to resolve during build)

1. **EMA decay factor (α):** Starting at 0.1, tune via backtest. Need train/test split to avoid overfitting.
2. **Home advantage magnitude:** League-specific fixed value to start.
3. **Dixon-Coles correction:** Needed for WDL. Research whether it helps BTTS too.
4. **PPDA inclusion:** Deferred from Phase 2 base model. Add as enhancement if base model calibrates well.
5. **Goalkeeper xGOT data:** High signal for BTTS but hard to get from free sources at player level.
6. **BTTS odds availability:** football-data.co.uk may not have BTTS odds columns for all leagues/seasons. Check in Phase 1.

---

## File Inventory

| File | Purpose |
|---|---|
| `CLAUDE.md` | Session governance, decisions log, CLI instructions |
| `SESSION_STATE.md` | This file — progress tracking, handover |
| `BUILD_PLAN.md` | Full 4-phase build plan with architecture details |
| `SOCCER_COWORK_SESSION.md` | Original session planning doc (read-only reference) |
| `football_model_briefing.md` | Research briefing on xG, PPDA, markets, data sources |
| `Football Pythag v0.5.xlsx` | Chris's existing Excel model (reference, not being evolved) |

---

## Session Log

### Session 1 (2026-04-23)
- Reviewed briefing doc and session planning doc
- Created CLAUDE.md governance file
- Researched free data sources (Understat, FBref, football-data.co.uk, StatsBomb, API-Football)
- Key finding: only Understat and FBref provide free xG. Understat = Big 5 only. FBref = 40+ leagues.
- Made all 7 architectural decisions
- Wrote BUILD_PLAN.md (4 phases: Data Pipeline → BTTS Model → Market Expansion → Nordic Expansion)
- Established session handover protocol
- **Stopped at:** Ready to write Phase 1 CLI prompt
- Phase 1 CLI prompt written (`CLI_PROMPT_PHASE1.md`)
- Confirmed: Chris has GitHub account `chrisjm15`, Git installed on Windows
- **Stopped at:** Phase 1 prompt ready, Chris needs to execute it in Claude Code CLI
