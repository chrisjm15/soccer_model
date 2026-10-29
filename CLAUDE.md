# Soccer Model — Session Constitution

## What This Is
xG-based Poisson prediction model for soccer betting markets. GitHub: `chrisjm15/soccer_model`.
Current focus: EPL Asian Handicap only, using market-blend **calibrated** probabilities (raw edges and the old 7% threshold are retired). Big 5 ex-EPL has no edge (2026-07-12). Soft leagues failed their calibration test and are closed for v1 (2026-10-25). The EPL model carries real information, but under the live 1% rule it does not beat the close out of sample (CLV −1.6% at Pinnacle, −1.5% at best-of-3 after the session 18 price-error fix). Its information is early-season only — gone by GW 8 (session 18 stop-date analysis). Upside depends on price access in AU and the edge threshold. Season verdict metric: live price CLV on flagged bets, read alongside AU-obtainable prices.

## Session Continuity — MANDATORY (Cowork)
Chris should never have to ask for a handoff. Sessions run long and can end at any time.
- **Update `COWORK_HANDOFF_PROMPT.md` and `SESSION_LOG_COWORK.md` at every milestone, not at session end.**
  A milestone is any of: a brief handed to Antigravity; Antigravity's report QC'd (pass or fail); a
  decision made; a defect found; a config/schedule/automation change; a finding that changes priorities.
- Do it in the same turn as the milestone, before replying to Chris. Keep both docs current-state (rewrite
  stale sections; don't just append).
- At the start of a new session, archive the previous session log to `archive/session_logs/` before
  writing the new one.
- Each handoff ends with a ready-to-paste commit block for everything Cowork changed but couldn't commit.

## Roles
| Context | Role |
|---|---|
| **Cowork session** | Strategic planner and QC. Design, research, write briefs, verify executor output against the repo. Does not push to git. |
| **Antigravity (Gemini)** | Default executor. Multi-file work, running scripts, git. Briefed via the `antigravity-handoff` skill; briefs live in `prompts/`. |
| **Sonnet CLI** | Fallback executor if Antigravity fails a task twice. |
| **Local LLMs** | Parked (see `docs/LOCAL_LLM_SETUP.md`). |

Chris has no coding background. All prompts must be copy-paste ready with exact paths and plain English explanations.

## Cowork Default Behaviour
1. **Coding task** → `antigravity-handoff` skill → brief in `prompts/` sized to the cost of being wrong →
   Chris pastes one line into Antigravity.
2. **Money-critical code** (edges, calibration, staking, settlement, line selection) → Cowork writes a
   hand-verified gold test file that the executor may not edit.
3. **Always QC the executor's report against the repo** (git log/diff, run the tests, inspect outputs).
   Never accept its claims unverified.
4. **Architecture, design, research** → handle in Cowork.

## Sonnet CLI Launch (fallback only) — Full Steps

1. Press **Windows key**, type `PowerShell`, press **Enter**
2. Paste this and press Enter:
   ```
   cd "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
   ```
3. Paste this and press Enter:
   ```
   claude --model claude-sonnet-4-6
   ```
4. Once the CLI is running, type:
   ```
   /effort max
   ```
5. Now paste the prompt.

## Hard Constraints
- Free data sources only until positive ROI demonstrated
- xG-based models only — never fall back to actual-goals approaches
- Attack and defence modelled separately (not combined margins)
- Independent Poisson for v1 — correlation limitation accepted
- No PPDA or goalkeeper xGOT in base model — keep v1 clean

## Key Concepts
| Term | Meaning |
|---|---|
| xG | Shot quality probability. Better predictor than actual goals. |
| Poisson | Goal distribution model. Grid of outcomes → any market probability. |
| BTTS | Both Teams To Score. First target market. |
| EMA | Exponential Moving Average. Recent-form weighting without cliff effects. |

## Folder Structure
```
docs/                 Build plan, LLM setup, briefing, index — read on demand only
prompts/              Active CLI/local prompts
prompts/completed/    Executed prompts (reference only)
archive/session_logs/ One file per past session
```

## Finding Files
Check `docs/INDEX.md` before scanning. Do not read it on startup — only when you need to locate something.
