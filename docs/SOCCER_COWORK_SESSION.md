# Soccer Cowork Session — Planning & Architecture

*Hand this to a Cowork session dedicated to soccer model work. This session plans and reviews — it does not execute code. Code execution happens in Claude Code CLI sessions.*

---

## Role of This Session

- Review existing v0.5 Excel model and briefing research
- Design the Python model architecture (markets, signals, data sources)
- Decide league selection strategy (including data availability)
- Write prompts for Claude Code build sessions
- Track progress and review outputs

**This session does NOT:** run scripts, call APIs, push to git, or execute Python.

---

## Setup — Do This First

**Create a `CLAUDE.md` file in this folder** that establishes this session's governance. It must contain:

- This is a **planning and architecture session**, not an execution session
- It does NOT run scripts, execute Python, push to git, or build code
- It plans, researches, designs, reviews, and writes prompts for Claude Code CLI sessions to execute
- Code execution happens in Claude Code CLI (`claude --model claude-opus-4-6` from the Soccer folder)
- Chris has no coding background — Claude Code prompts must include step-by-step terminal instructions
- Style: precise, not polite. Don't guess — search. Challenge reasoning. No sycophancy.
- Local path: `C:\Users\Chris\Documents\Claude\Projects\Sports Betting - Architecture\Soccer`
- Parent architecture session: `Sports Betting - Architecture` folder (contains master plan, action plan, cross-sport specs)
- Update CLAUDE.md if decisions are made that future sessions need to know

---

## First Task

**Plan the soccer model build.** This is a planning session — explore the research, the existing v0.5 model, and the briefing doc, then produce a build plan. Key questions to resolve:

1. **League selection:** Which leagues, and why? Consider the thesis that less popular leagues (Nordic, Eastern European) may offer more edge due to softer bookmaker pricing in Australia. Balance against data availability from free APIs. What's stopping us doing 10 leagues? More data = more signal, but also more maintenance and more APIs to manage. Research what free data sources exist for which leagues.

2. **Market prioritisation:** Five candidate markets identified:
   - Result (Win/Draw/Loss)
   - Both Teams To Score (BTTS)
   - Cards (Yellow/Red)
   - BTTS & Result (combination)
   - Corners
   
   Which markets should be built first? Which have the most exploitable edge? Which share the most underlying signals?

3. **Model architecture:** The briefing doc recommends xG-based Poisson with attack/defence decomposition. The v0.5 Excel model uses Pythagorean expectation with SOT (Shots on Target) as a proxy. Decide: start from the v0.5 approach and evolve, or build fresh from the briefing doc's recommendations?

4. **Data source audit:** What free APIs and data sources exist? The briefing doc lists Understat, FBref, football-data.co.uk, StatsBomb Open Data. Which cover which leagues? What are the rate limits and reliability?

---

## What Exists

### Briefing Document
`Soccer/football_model_briefing.md` — Comprehensive research covering:
- Structural differences from AFL (three outcomes, low scoring, attack/defence asymmetry)
- Core metrics: xG, xGOT, PPDA
- Form measurement (EMA on xG, not raw results)
- Referee effects (cards, penalties, game tempo)
- Player availability (goalkeeper absences most impactful)
- Market-specific requirements (WDL, BTTS, totals, cards)
- Data sources and costs
- Input priority matrix by market

### v0.5 Excel Model
`Soccer/Football Pythag v0.5.xlsx` — Chris's existing spreadsheet model:
- **29 sheets** including 10 league data sheets and 10 season summary sheets
- **Leagues covered:** EPL, EFC (Championship), EFL1, EFL2, SPL, Bundesliga, Serie A, La Liga, Ligue 1, Eredivisie
- **88 columns per league** covering:
  - Raw match data (scores, shots, shots on target, fouls, corners, cards, referee)
  - Pythagorean performance (result-based and SOT-based)
  - Goal performance vs opponent averages
  - SOT Pythagorean by location (home/away) and opponent strength
  - Form adjustments (rolling window, goals scored/conceded form)
  - Corner analysis (opponent corner averages, win/concede adjustments)
  - Card averages (home/away)
  - BTTS tracking (binary per match)
- **Data period:** 2016-17 to 2018-19 (3 seasons for EPL, 1 season for most others)
- **Data source:** football-data.co.uk (column structure matches their CSV format)
- **Key tabs:** Drivers (Pythagorean exponents), Calc of exponent, Predictor, Output Pivots
- **Note:** BunL, SeriA, LaLiga, LigUn, Erediv sheets have 87 columns (no Referee column — referee data not available for those leagues from football-data.co.uk)

### Architecture Context
- **Shared prediction JSON schema** exists (defined in `NEXT_SESSION_PROMPT.md`) — don't build to it yet, just be aware it exists for later integration
- **Output format:** For now, match the AFL model's approach — model-specific output that works, adapt to shared schema later
- **Repo:** Will be a separate repo (e.g., `chrisjm15/soccer_model`), same pattern as AFL

---

## Chris's Hypotheses to Test

1. **Less popular leagues = more edge.** Aussie bookmakers may have weaker models for Nordic/Eastern European leagues. Investigate: Finnish Veikkausliiga, Swedish Allsvenskan, Norwegian Eliteserien, Danish Superliga, Belgian Pro League. What data is available?

2. **Volume matters.** More leagues = more matches = more bets = better statistical validation. If the model works, scaling to 10+ leagues is pure upside (assuming data quality holds).

3. **More data = better signal.** Cross-league training could reveal universal patterns (e.g., PPDA matchup effects on BTTS) that single-league models miss.

---

## Critical Constraints

1. **Three-outcome problem.** Soccer has draws. The model MUST treat draw as a first-class prediction, not a fallback. This is the fundamental structural difference from AFL.
2. **xG > actual goals for prediction.** The briefing doc is clear: across ~12,000 matches, xG-based models consistently outperform actual-goals models. Don't build on raw scorelines alone.
3. **Attack and defence are separate.** Unlike AFL where margins reflect overall quality, soccer requires decomposed attack/defence ratings. A 0-0 team and a 3-3 team are very different for BTTS.
4. **Referee data matters for cards market.** But individual referee sample sizes are small (~25-30 matches/season). Multiple seasons needed for stable estimates.
5. **Free data only to start.** No paid APIs until a model is validated and generating positive ROI.

---

## CLI Quick Reference (for Chris)

When it's time to build:
```
cd "C:\Users\Chris\Documents\Claude\Projects\Sports Betting - Architecture\Soccer"
claude --model claude-opus-4-6
```
Then inside Claude Code:
```
/effort max
```

---

## Related Documents (in Architecture folder)

- `sports-model-specs.md` — Comparative spec (soccer section covers target leagues, inputs, outputs, what "working" looks like)
- `MASTER_ARCHITECTURE_PLAN.docx` — Full platform architecture
- `ACTION_PLAN.md` — Prioritised action plan (soccer is Phase 2)
- `AFL_COWORK_SESSION.md` — AFL session doc (for reference on how that model was built)

---

*Created 2026-04-23 from the master architecture session.*
