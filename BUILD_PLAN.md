# Soccer Model — Build Plan

*Produced 2026-04-23. Decisions locked in this session.*

---

## Decisions Made

| Decision | Choice | Rationale |
|---|---|---|
| Architecture | Fresh xG-based build | xG models consistently outperform actual-goals models. v0.5 informs feature selection but code is new. |
| First market | BTTS | Forces attack/defence decomposition (hardest part). Less efficiently priced than WDL. WDL and Totals come cheaply once this works. |
| League scope (launch) | Big 5 (EPL, La Liga, Bundesliga, Serie A, Ligue 1) | Understat provides clean xG scraping. Deepest betting markets in Australia. |
| League scope (wave 2) | Nordic 4 (Finland, Sweden, Norway, Denmark) | Tests the "softer pricing" hypothesis. FBref scraping. Summer season calendar. |
| Build order | Big 5 first, Nordic second | Validate model on proven data before adding scraping complexity. |
| Data sources | Understat (xG, Big 5) + football-data.co.uk (results, odds, cards) + FBref (Nordic xG, wave 2) | Free only until positive ROI demonstrated. |

---

## Phase 1 — Data Pipeline (~1 CLI session)

**Goal:** Ingest and normalise match-level data for Big 5 leagues, merging xG from Understat with results/odds from football-data.co.uk.

### What gets built:
1. **Understat scraper** — Pull match-level xG, xGA for all Big 5 leagues. Store per-team, per-match. Use existing Python scraping libraries (understatAPI or soccerdata). Cover 2020-21 through current season (5+ seasons of data for stable estimates).
2. **football-data.co.uk loader** — Download CSVs for same leagues/seasons. Extract: result, shots, shots on target, corners, cards (yellow/red), referee, closing odds (B365, Pinnacle where available).
3. **Data merge and normalisation** — Join on match date + home/away teams. Standardise team names across sources (this is always painful — Understat says "Manchester United", football-data says "Man United"). Output: one clean Parquet/CSV per league-season with all fields aligned.
4. **Validation checks** — Row counts match between sources. No orphan matches. Spot-check xG values against Understat website.

### Data schema (per match row):
- `date`, `league`, `season`, `home_team`, `away_team`
- `home_goals`, `away_goals`, `result` (H/D/A)
- `home_xg`, `away_xg`, `home_xga`, `away_xga`
- `home_shots`, `away_shots`, `home_sot`, `away_sot`
- `home_corners`, `away_corners`
- `home_yellow`, `away_yellow`, `home_red`, `away_red`
- `home_fouls`, `away_fouls`
- `referee`
- `odds_home`, `odds_draw`, `odds_away`, `odds_btts_yes`, `odds_btts_no`, `odds_over25`, `odds_under25`

### Known risks:
- Team name mapping between sources. Mitigate: build a manual alias table, start with EPL only to debug it, then extend.
- Understat rate limiting. Mitigate: respectful scraping with delays, cache aggressively.
- football-data.co.uk may not have BTTS odds for all seasons. Mitigate: check availability early, calculate implied BTTS from scoreline if needed for backtesting.

---

## Phase 2 — BTTS Model (~2 CLI sessions)

**Goal:** Given two teams and a match date, output P(BTTS Yes) and compare to market odds to identify +EV bets.

### 2A: Attack/Defence Rating Engine
- For each team, compute rolling xG (attack) and xGA (defence) using **EMA smoothing** (not hard window). EMA decay factor to be tuned — start with α = 0.1 (roughly equivalent to weighting last 10 matches heavily).
- Separate home and away ratings. A team's home attack strength ≠ away attack strength.
- **Regression to league mean:** Early-season ratings should be pulled toward prior season's final ratings. Weight shifts to current-season data as sample grows. Bayesian shrinkage or simple weighted blend.
- Output per team per matchday: `attack_home`, `attack_away`, `defence_home`, `defence_away` (all in xG units).

### 2B: Scoring Probability Model
- Given home team's home attack rating vs away team's away defence rating → expected home goals (λ_home).
- Given away team's away attack rating vs home team's home defence rating → expected away goals (λ_away).
- Apply home advantage adjustment (league-specific, ~0.2-0.4 xG historically).
- Model each team's goal count as **independent Poisson** with rate λ.
- P(BTTS Yes) = 1 - P(home=0) - P(away=0) + P(home=0 AND away=0)
  = 1 - e^(-λ_home) - e^(-λ_away) + e^(-(λ_home + λ_away))

### 2C: BTTS Output
- For each upcoming match: P(BTTS Yes), P(BTTS No).
- Compare to market implied probability (from odds).
- **Edge = model probability - implied probability.**
- Flag matches where edge exceeds threshold (start with 5%, tune later).
- Output includes: confidence level, key drivers (which team's attack/defence is driving the edge), regression flags.

### 2D: Backtest Engine
- Run the model historically (2020-21 through 2024-25 seasons).
- For each match where the model would have bet: record whether the bet won, at what odds.
- Calculate: ROI, hit rate, Brier score, calibration curve, P&L by league, by season, by edge threshold.
- **Critical:** Avoid lookahead bias. At each prediction point, only use data available before that match.
- Compare to: flat staking, proportional staking (Kelly), and half-Kelly.

### Known risks:
- Independent Poisson assumption is wrong — goals in a match are correlated (game state effects: team losing opens up, trailing team presses). Accept this as v1 limitation, note for future improvement (bivariate Poisson or copula).
- BTTS odds may not be in football-data.co.uk for all leagues/seasons. May need to derive implied BTTS from scoreline distribution for backtesting.

---

## Phase 3 — Market Expansion (~1-2 CLI sessions per market)

**Build order** (each builds on Phase 2 infrastructure):

### 3A: Over/Under Totals
- Near-free: λ_home + λ_away from Phase 2 already gives expected total goals.
- P(Over 2.5) = 1 - P(total ≤ 2) = 1 - Σ P(H=h, A=a) for all h+a ≤ 2.
- Same backtest framework, different odds column.

### 3B: Win/Draw/Loss
- P(H wins) = Σ P(H=h, A=a) for all h > a.
- P(Draw) = Σ P(H=h, A=a) for all h = a.
- P(A wins) = 1 - P(H) - P(Draw).
- Three-outcome calibration is harder. Likely needs a Dixon-Coles adjustment (inflates probabilities of 0-0, 1-0, 0-1, 1-1 draws beyond what independent Poisson predicts).

### 3C: BTTS + Result (Combo)
- Joint probability from the Poisson grid: P(BTTS Yes AND Home Win) = Σ P(H=h, A=a) for h > a, h ≥ 1, a ≥ 1.
- This is where the model's value really shows — bookmakers price these combos less efficiently because fewer punters model them rigorously.

### 3D: Cards
- Separate model stream. Inputs: referee card rate, team foul rate, PPDA (if available from FBref), fixture context.
- Likely a regression model (Poisson on card counts) rather than the match-outcome Poisson.
- **Deferred until Phase 2 is validated.** Can be built in parallel if desired since it's architecturally independent.

### 3E: Corners
- Lowest priority. Corner data exists in football-data.co.uk. Model as Poisson on team corner rates adjusted for opponent.
- Build only if the other markets show positive ROI and justify the time investment.

---

## Phase 4 — Nordic Expansion (~1 CLI session)

**Goal:** Add Finnish Veikkausliiga, Swedish Allsvenskan, Norwegian Eliteserien, Danish Superliga to test the softer-pricing hypothesis.

### What gets built:
1. **FBref scraper** — Different site structure from Understat. Use worldfootballR patterns or build custom. Pull xG, xGA per match.
2. **Summer season calendar handling** — These leagues run April–November (roughly). The model's season-start regression logic needs to handle this different calendar.
3. **Team name normalisation** — Another round of alias mapping for Nordic teams.
4. **Edge comparison** — Key question: is the edge (model probability minus implied probability) systematically larger in Nordic leagues? If yes, the hypothesis holds and scaling to more small leagues is justified.

### When to do this:
- After Phase 2 backtest shows the model is calibrated and not delusional on Big 5.
- Nordic 2026 seasons will be mid-season by then (started April). Can backtest on 2024 and 2025 seasons, then go live for remainder of 2026.

---

## Repo Structure (Proposed)

```
soccer_model/
├── CLAUDE.md
├── README.md
├── data/
│   ├── raw/              # Downloaded CSVs, scraped JSON
│   ├── processed/        # Cleaned, merged Parquet files
│   └── aliases/          # Team name mapping tables
├── scrapers/
│   ├── understat.py      # Big 5 xG scraper
│   ├── footballdata.py   # football-data.co.uk CSV loader
│   └── fbref.py          # Nordic xG scraper (Phase 4)
├── model/
│   ├── ratings.py        # EMA attack/defence rating engine
│   ├── poisson.py        # Scoring probability model
│   ├── btts.py           # BTTS market predictions
│   ├── wdl.py            # Win/Draw/Loss predictions
│   ├── totals.py         # Over/Under predictions
│   ├── cards.py          # Cards model (Phase 3D)
│   └── regression.py     # Regression-to-mean logic
├── backtest/
│   ├── engine.py         # Historical simulation engine
│   ├── metrics.py        # ROI, Brier score, calibration
│   └── reports.py        # Output formatting
├── output/
│   └── predictions/      # Match-day prediction files
├── config/
│   └── leagues.yaml      # League definitions, season dates, home advantage
├── requirements.txt
└── run.py                # Main entry point
```

---

## First CLI Session Prompt

When you're ready to start building, open Claude Code and use the prompt in `CLI_PROMPT_PHASE1.md` (to be written next).

---

## Open Questions (to resolve during build)

1. **EMA decay factor (α):** Start with 0.1, but should be tuned via backtest optimisation. Risk of overfitting if tuned on same data used for ROI evaluation — need train/test split by season.
2. **Home advantage magnitude:** League-specific? Season-specific? Start with a fixed per-league value from historical data, consider making it dynamic later.
3. **Dixon-Coles correction:** Needed for WDL market. Research whether it also improves BTTS calibration or only affects low-scoring outcomes.
4. **PPDA data:** Understat provides it for Big 5. Should it be included in Phase 2 or deferred? It's a BTTS-relevant signal per the briefing doc, but adds scraping complexity.
5. **Goalkeeper quality (xGOT-based goals prevented):** High-signal for BTTS per briefing, but player-level data is harder to get from free sources. Investigate FBref's player-level pages.
