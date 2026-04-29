# Football (Soccer) Prediction Model — Research Briefing

## Context

This project extends the AFL Pythagorean prediction model framework into football (soccer). The AFL model uses Pythagorean expectation to estimate team quality from scoring margins, with innovations around home ground advantage, strength-of-schedule correction, and regression to mean. The football model adapts these principles but must handle structural differences in the sport.

The goal is to build a model that predicts not just match outcomes (win/draw/loss) but a range of betting markets: **Both Teams to Score (BTTS)**, **BTTS & Win**, **Over/Under totals**, **cards**, and **win/draw/loss**. This multi-market focus shapes which inputs matter and how they are used.

---

## Structural Differences vs. AFL

### The Draw Problem
Football has three outcomes, not two. This fundamentally complicates the Pythagorean approach:
- The optimal Pythagorean exponent for football is **k ≈ 1.70** (vs. k = 3.65 for AFL), meaning goal ratio is a much weaker predictor of standings than scoring margin is in AFL
- A draw distributes only 2 points total vs. 3 for a win — not all outcomes are worth the same, so win% alone is a poor target variable
- The standard approach is to predict **points per game** (0, 1, or 3) rather than win percentage
- A Weibull distribution (not Gaussian) better fits football goal distributions

### Low Scoring = High Variance
Football's low-scoring nature means single-game results are noisier than AFL. A team can lose 1-0 from 3.0 xG against 0.3 xG and that outcome tells you almost nothing about quality. This makes underlying metrics (xG, xGA) substantially more predictive than actual results, especially early in a season.

### Attack vs. Defence Decomposition
Unlike AFL where margins tend to reflect overall team quality, football is tactically asymmetric — some teams are set up to suppress goals even at the cost of attacking output. The model must treat attacking and defensive performance as **separate components** and model how they interact in specific matchups. A high-defensive team vs. a low-output attack is a fundamentally different game than two open, pressing sides.

---

## Core Metrics

### xG (Expected Goals)
- Assigns a probability (0–1) to each shot based on location, angle, assist type, body part, defensive pressure, and other factors
- Summed across a match gives "expected goals" — how many goals a team *should* have scored given the chances created
- **Superior to actual goals for prediction**: across ~12,000 Big 5 European league matches, xG-based Poisson models consistently outperform actual-goals models in Brier score; the top 10 predictive models in published research are all xG-based
- **xGA** (expected goals against) is the defensive equivalent
- Both bookmakers and professional clubs use xG as standard — it is table stakes, not an edge in itself
- The edge comes from *how* you use it: attack/defence decomposition, regression identification, matchup modelling

**Data sources:** FBref (free), Understat (free for major leagues)

### xGOT (Expected Goals on Target) — Post-Shot Metric
- xGOT extends xG to shots *on target only*, incorporating where the ball actually ended up in the goal frame and goalkeeper positioning
- It is a **post-shot** metric: you cannot know it before the match, so it cannot be used as a direct prediction input
- **How it is used in the model:**
  - **Goalkeeper quality assessment**: xGOT conceded vs. goals conceded reveals "goals prevented" — a keeper consistently preventing more goals than expected is running above their true level and is a regression candidate
  - **BTTS and totals**: a team with an elite goalkeeper (large positive goals prevented) structurally suppresses both BTTS-Yes probability and over totals, independent of their outfield defensive quality
  - **Regression flagging**: if a team's keeper has prevented 5+ goals above expectation over the season, bet BTTS-Yes against them — the luck will normalise

### PPDA (Passes Per Defensive Action) — Pressing Intensity
- Measures how many passes a team allows the opponent to make in their own defensive 60% of the pitch before a defensive action (tackle, interception, foul, won duel) is made
- **Lower PPDA = more intense pressing**; typical top-division range is 7–16
- Introduced by Colin Trainor (2014); widely used in professional analytics

**How it is used in the model:**

| Matchup | Implication |
|---|---|
| High press vs. high press (both low PPDA) | Open, transitional game → BTTS-Yes, Over |
| High press vs. low block | Favourites create through sustained pressure, concede on counter → BTTS-Yes even in wins |
| Low block vs. low block (both high PPDA) | Cagey, few chances → BTTS-No, Under |
| High press team with leaky defence | Structurally BTTS-Yes regardless of opponent |

**Known limitation:** Teams that dominate territory show artificially low PPDA simply because they spend most of the game in the opponent's half — not because they press intensely. PSG is a recurring example. PPDA should be used alongside field tilt and possession data to avoid misclassifying dominant possession teams as high pressers.

**Card market connection:** High-pressing teams generate more fouls, particularly when the press breaks down late and players commit tactical fouls to stop counters. A high-card referee officiating a low-PPDA (high press) team is a multiplier on card probability.

---

## Form and Timing

Form is a genuine signal but must be measured in underlying metrics, not raw results:

- A team on a 5-game winning streak that generated 4.0 xG vs. 3.5 xGA is showing genuine form
- A team on a 5-game winning streak from 2.0 xG vs. 3.0 xGA is carrying variance
- **EMA (exponential moving average) smoothing** is preferred over hard windows (e.g., "last 5 games") to avoid cliff effects where one old result dropping out shifts ratings sharply

Timing within the season matters:
- Teams often start slow while a manager's system beds in
- Late-season fatigue affects high-pressing sides more than low-block sides (pressing is physically demanding)
- Squads with thin depth show more degradation in xG metrics during fixture congestion

When during the season a team plays another team matters because of hot/cold streaks — but the signal is in xG-based form, not the scoreboard results.

---

## Referee Effects

Referee assignment is typically known before the market fully prices it in. Referee tendencies are stable over time and measurable.

**Key referee dimensions:**
- Card frequency (yellow and red cards per game)
- Foul tolerance (fouls allowed per game)
- Penalty award rate
- Game tempo management (how quickly they stop play)

**Markets where referee effects are most significant:**
- **Cards market**: most direct impact; high-card referees in physical or feisty matchups dramatically shift probability
- **Over/Under totals**: high penalty-award referees add expected goals to both sides; penalties have xG of ~0.78
- **BTTS**: a red card changes game state dramatically — the reduced team often parks the bus, suppressing BTTS-Yes; but it can also open up space for the other team
- **Win/draw/loss**: referee effects tend to be somewhat symmetric and have less impact here than on the above markets

**Practical limitation:** Individual referee sample sizes are small (~25–30 matches per season). Multiple seasons of data are needed for stable estimates. Must also control for the fact that elite referees are assigned to elite fixtures, which are systematically different games.

---

## Player Availability

High signal in theory; operationally difficult:

- **Goalkeeper absences** have the most measurable impact: clean sheet rates and goals conceded per game shift materially when a first-choice keeper is out
- **First-choice centre back absences** are the next most significant defensive impact
- Key striker absences affect xG generation but the squad depth factor varies enormously by club
- Research generally finds that outfield player absences matter less than intuition suggests — tactical shape often compensates
- **Suspensions from card accumulation** are deterministic, public, and knowable before betting — these are the most tractable availability inputs

**Practical approach:** Flag matches where goalkeeper or key defender is suspended (known) rather than trying to model injury probability systematically.

---

## Betting Markets — What Each Requires

### Win / Draw / Loss
- Core signal: xG-based Pythagorean (points per game), form, home advantage, strength of schedule
- Three-outcome problem means this is harder to model cleanly than AFL's two-outcome structure
- Bookmakers are strongest here — this is the most efficiently priced market

### Both Teams to Score (BTTS Yes/No)
- Requires modelling each team's **independent** scoring probability, then combining as a joint probability
- Key inputs: team xG (for), team xGA (for), goalkeeper quality (xGOT-based goals prevented), PPDA matchup, clean sheet rate, form
- BTTS Yes implied probability at standard 1.90 odds is ~52.6% — need to find games where true probability exceeds this
- Structural BTTS-Yes indicators: high-pressing teams with leaky defences, both teams with poor clean sheet rates, high-card referees who disrupt defensive shape
- Structural BTTS-No indicators: elite goalkeeper on one side, low-block vs. low-block matchup, high-stakes/derby matches where teams play conservatively

### BTTS & Win
- Combination market: even harder to price, more room for model edge
- Requires both the BTTS assessment and a directional view on winner
- High-pressing teams that concede on the counter are natural BTTS-Win candidates when favoured

### Over / Under Totals (e.g., Over 2.5 goals)
- Combined xG of both teams is the primary input
- PPDA matchup, referee penalty rate, and xGOT-based goalkeeper quality all adjust the base expected total
- Regression candidates (teams over/under-converting vs xG) create recency bias in bookmaker lines that can be exploited

### Cards Market
- Referee tendency is the dominant input
- Team PPDA and foul rate are secondary inputs
- Fixture context (derby, relegation battle, top-of-table clash) modifies base rates

---

## Data Sources

| Data | Source | Cost |
|---|---|---|
| Match results, xG, xGA | Understat.com | Free (Big 5 leagues) |
| xG, advanced stats, PPDA proxy | FBref.com | Free |
| Historical odds | football-data.co.uk | Free |
| xGOT, detailed shot data | StatsBomb Open Data | Free (limited); paid API for full access |
| Referee stats | football-data.co.uk, RefStats | Free |
| Lineups/injuries | Various; FlashScore, SofaScore | Free (manual); paid APIs available |

---

## Summary: Input Priority by Market

| Input | Win/Draw/Loss | BTTS | Totals | Cards |
|---|---|---|---|---|
| xG / xGA (rolling) | ★★★ | ★★★ | ★★★ | — |
| Form (xG-based EMA) | ★★★ | ★★ | ★★ | — |
| Home advantage | ★★ | ★ | ★ | — |
| PPDA matchup | ★ | ★★★ | ★★ | ★★ |
| Goalkeeper xGOT (goals prevented) | ★ | ★★★ | ★★ | — |
| Referee tendencies | ★ | ★★ | ★★ | ★★★ |
| Player availability (GK/CB) | ★★ | ★★★ | ★★ | — |
| Season timing / fixture congestion | ★ | ★ | ★ | ★ |

---

## Relationship to AFL Model

The AFL model's core innovations — Pythagorean expectation, regression to mean, overperformance as a fade signal — all apply in principle. The implementation differs:

- Exponent: k ≈ 1.70 for football (vs. 3.65 for AFL)
- Target variable: points per game rather than win%
- Three outcomes require explicit draw probability modelling
- Attack and defence must be separated (not just total margin)
- Market selection is broader — not just spread/line but BTTS, totals, cards

The most directly transferable insight from the AFL model: **overperformance vs. Pythagorean expectation is a regression signal**. A team with more actual points than xG-based expected points is carrying luck. Fade them, particularly in BTTS-Yes and totals.
