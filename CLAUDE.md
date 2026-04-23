# Soccer Model — Session Governance

## Session Continuity
**This project spans multiple Cowork chat sessions.** Chats compact or expire. When a new session starts:
1. Read this file first
2. Read `SESSION_STATE.md` for current progress and next actions
3. Read `BUILD_PLAN.md` for the full phased plan
4. Do NOT re-derive decisions already made — they're logged below

If `SESSION_STATE.md` says a phase or task is complete, trust it and move forward.

## Session Role
This is a **planning and architecture session**. It does NOT run scripts, execute Python, push to git, or build code. It plans, researches, designs, reviews, and writes prompts for Claude Code CLI sessions to execute.

## Chris's Experience Level
Chris has **no coding background**. All Claude Code CLI prompts must:
- Include the exact folder path to `cd` into
- Include the `/effort max` command
- Be copy-paste ready — no "adapt this to your setup" instructions
- Explain what each step does in plain English
- Never assume familiarity with git, Python, pip, or terminal concepts

## Execution — Claude Code CLI
When it's time to build, Chris opens a terminal and pastes:
```
cd "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
claude --model claude-opus-4-6
```
Then inside Claude Code, paste:
```
/effort max
```
Then paste the session prompt (provided by this Cowork session).

## Version Control — GitHub
- Repo: `chrisjm15/soccer_model` (to be created in Phase 1)
- All code is committed and pushed to GitHub
- CLI prompts must include git instructions (init, add, commit, push)
- Chris will need a GitHub repo created — the Phase 1 CLI prompt must walk through this step-by-step
- Branch strategy: `main` branch for stable code. Feature branches for each phase if needed, but keep it simple — Chris is not a developer.

## Style
- Precise, not polite. Don't guess — search. Challenge reasoning. No sycophancy.
- Failure is acceptable if the request is impossible.

## Paths
- Local: `C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer`
- Parent architecture session: `Sports Betting - Architecture` folder (if applicable)

## Key Documents
- `football_model_briefing.md` — Research briefing (xG, PPDA, markets, data sources)
- `Football Pythag v0.5.xlsx` — Existing Excel model (10 leagues, 88 cols, Pythagorean + SOT)
- `SOCCER_COWORK_SESSION.md` — Session planning doc
- `BUILD_PLAN.md` — Phased build plan (4 phases)
- `SESSION_STATE.md` — Current progress, handover notes, next actions

## Key Concepts (for context)
- **xG (Expected Goals):** Probability-weighted measure of chance quality. Better than actual goals for prediction.
- **Poisson distribution:** Statistical model for "how many times does a rare event happen." Used here to model goal counts — given a team's expected goals (e.g., 1.5 xG), Poisson tells you the probability of 0, 1, 2, 3... goals. Build a grid for both teams → derive any market probability.
- **BTTS:** Both Teams To Score. First market target because it forces attack/defence decomposition.
- **EMA:** Exponential Moving Average. Smooth way to weight recent form more heavily without cliff effects.

## Decisions Log

- **2026-04-23:** Session created. Planning phase begun.
- **2026-04-23:** Architecture → Fresh xG-based build (not evolving v0.5)
- **2026-04-23:** First market → BTTS (forces attack/defence decomposition)
- **2026-04-23:** Leagues (launch) → Big 5 via Understat
- **2026-04-23:** Leagues (wave 2) → Nordic 4 via FBref
- **2026-04-23:** Build order → Big 5 first, Nordic second
- **2026-04-23:** Build plan written → see BUILD_PLAN.md
- **2026-04-23:** Version control → GitHub repo `chrisjm15/soccer_model`
- **2026-04-23:** Session handover protocol established → see SESSION_STATE.md
