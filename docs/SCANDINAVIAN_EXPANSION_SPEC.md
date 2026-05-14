# Scandinavian Expansion — Experiment Specification

*Produced 2026-05-09. Opus strategy session with Chris.*

---

## Strategic Context

### Problem Statement
The current xG-based Poisson model shows +7.1% ROI on Asian Handicaps in the EPL but is negative in all other Big 5 leagues (La Liga -2.1%, Bundesliga -6.1%, Ligue 1 -6.8%, Serie A -9.6%). The Big 5 European seasons end in 2-3 weeks. Scandinavian leagues (summer calendar, currently underway) are the next target.

### Why This Experiment Exists
Two critical constraints make a direct port of the current model impossible:

1. **FBref lost all xG data in January 2026** (Opta terminated their agreement). There is no free xG source for leagues outside the Big 5. Understat covers Big 5 + Russia only.
2. **football-data.co.uk has no match stats for Scandinavian leagues** — only scorelines and odds. They're classified as "extra leagues" with stripped-down CSVs.

Therefore, the model for Scandinavian leagues cannot rely on xG from Understat or match stats from football-data.co.uk. We need to find which alternative metrics (shots, SoT, corners, fouls, etc.) can replace xG as the input to the Poisson model, and we need to source that data from elsewhere.

### The Hypothesis
The original build plan hypothesised that Scandinavian leagues have "softer pricing" — less efficient bookmaker lines that a model can exploit even with cruder inputs. This experiment tests that hypothesis by running 25 metric variants across 6 proxy leagues and identifying which metrics (if any) produce positive ROI.

---

## Data Sources

### For Proxy Leagues (Championship, Eredivisie, Belgian, Portuguese, Scottish, Turkish)

| Data | Source | Notes |
|---|---|---|
| Goals, odds (1X2, AH, O/U) | football-data.co.uk | Rock solid. Full column coverage for all 6. |
| Shots, SoT, corners, fouls, cards, xG | FotMob unofficial API | No auth. Covers all leagues. One-time historical scrape, cache to disk. |

### For Target Scandinavian Leagues (Finland, Sweden, Norway, Denmark)

| Data | Source | Notes |
|---|---|---|
| Goals, odds | football-data.co.uk | Extra league format. Codes: FIN, SWE, NOR, DNK. ~14 seasons from 2012. |
| Shots, SoT, corners, fouls, cards, xG | FotMob unofficial API | Same source as proxy leagues — data parity maintained. |

### Why FBref Was Abandoned (Session 9)
FBref was the original plan for basic stats. Abandoned after confirming that FBref requires
a human to solve a Cloudflare CAPTCHA on every session — automated scraping is not possible.
FotMob provides the same stats (shots, SoT, corners, fouls, cards) plus xG for all target
leagues, with no auth and no CAPTCHA. Modules 2 and 3 are merged into a single FotMob loader.

### Proxy League Codes (football-data.co.uk)

| League | Code | Match Stats From | Seasons of Stats |
|---|---|---|---|
| English Championship | E1 | ~2000 | ~25 |
| Dutch Eredivisie | N1 | ~2000 | ~25 |
| Belgian Pro League | B1 | ~2000 | ~25 |
| Portuguese Primeira Liga | P1 | ~2000 | ~25 |
| Scottish Premiership | SC0 | ~2000 | ~25 |
| Turkish Super Lig | T1 | 2017 | ~8 |

### Data Parity Note
FotMob is the stats source for both proxy and Scandinavian leagues. This maintains full
data parity — the same pipeline works for both league sets. football-data.co.uk stats
(available for proxy leagues from Module 1) can be used for cross-validation.

---

## The 25 Metric Variants

### How Each Variant Works
Every variant follows the same pipeline:

```
Raw stat → EMA smoothing → Attack/Defence ratings → Lambda (home/away) → Poisson grid → Market probabilities → Compare to odds → ROI
```

The ONLY thing that changes between variants is what raw stat enters at step 1 and how it's converted to goal-equivalent units for the Poisson model.

### Conversion to Goal Units
Most metrics aren't in "goals" units. To feed the Poisson model, each metric must be scaled:
- **SoT → goals:** multiply by league-average goals-per-SoT (historical conversion rate)
- **Shots → goals:** multiply by league-average goals-per-shot
- **Corners → goals:** these don't convert directly to goals. Use as a modifier on base lambda, not a direct input. Scale relative to league average (e.g., team with 1.2× league-avg corners gets a multiplier on attack lambda).
- **Fouls → goals:** same modifier approach as corners.

### Group A — Volume Metrics (4 variants)
*Question: does raw chance creation predict outcomes?*

| # | Variant | Attack Input | Defence Input | Scaling |
|---|---|---|---|---|
| 1 | SoT raw | EMA of SoT for | EMA of SoT against | × league goals/SoT |
| 2 | SoT opponent-adjusted | SoT for, adjusted for opponent avg SoT conceded | SoT against, adjusted for opponent avg SoT created | × league goals/SoT |
| 3 | Shots raw | EMA of shots for | EMA of shots against | × league goals/shot |
| 4 | Shots opponent-adjusted | Shots for, adjusted for opponent | Shots against, adjusted for opponent | × league goals/shot |

**Opponent adjustment formula:** `adjusted_stat = (raw_stat / opponent_league_avg_stat_conceded) × league_avg_stat`

### Group B — Efficiency Metrics (4 variants)
*Question: does shot quality/conversion matter more than volume?*

| # | Variant | What It Captures |
|---|---|---|
| 5 | SoT × team rolling conversion rate | Volume × how clinical the team is. SoT_for × (team's rolling goals/SoT). Closest to "constructed xG". |
| 6 | SoT × conversion, opponent-adjusted | Same as 5, but SoT is opponent-adjusted first. |
| 7 | Shots × team rolling conversion rate | Cruder version of 5 using total shots. |
| 8 | Shots × conversion, opponent-adjusted | Same as 7, opponent-adjusted. |

**Rolling conversion rate:** EMA of (goals / SoT) or (goals / shots) per team. Use same EMA decay factor as main ratings.

### Group C — Alternative Signals (6 variants)
*Question: what non-shot metrics carry predictive signal?*

| # | Variant | What It Captures |
|---|---|---|
| 9 | Actual goals with regression to mean | Simplest possible model. EMA of goals for/against, regressed to league mean. Baseline everything must beat. |
| 10 | SoT accuracy (SoT/Shots ratio) | Shot selectivity. Teams putting 60% on target vs 30% — creating better chances or better finishers? Used as a modifier on base lambda. |
| 11 | Corners for/against | Territorial dominance proxy. Teams winning lots of corners are spending time in the attacking third. |
| 12 | Fouls committed/drawn | Pressing/aggression proxy. Crude PPDA substitute. Teams drawing many fouls are pressing or playing direct. |
| 13 | Half-time lead conversion | Fitness/depth signal. Uses HT goals vs FT goals to identify teams that fade (or surge) in second halves. |
| 14 | Cards drawn/committed ratio | Controlled aggression. Teams that draw cards from opponents without getting carded themselves are playing on the front foot. |

### Group D — xG Benchmark (3 variants)
*Question: how much do we lose by not having xG?*

| # | Variant | What It Tests |
|---|---|---|
| 15 | xG raw (FotMob) | Direct benchmark. Equivalent to current Understat-based model but with FotMob's xG. Answers: does FotMob xG work as well as Understat xG? |
| 16 | SoT_adj + conversion_adj vs xG | DIY xG (variant 6) compared directly against real xG (variant 15). The gap between these two is the "cost of not having xG". |
| 17 | 0.7 × xG + 0.3 × SoT_adj | Does SoT add information on top of xG? If this beats variant 15, blending is worth the complexity. |

**Note:** Variant 16 is not a separate model — it's a comparison metric. The backtest runner should output the correlation and ROI difference between variants 6 and 15.

### Group E — Combinations (8 variants)
*Question: does combining signals beat any single metric?*

| # | Variant | Components | Rationale |
|---|---|---|---|
| 18 | SoT_adj + conversion_adj | Volume × efficiency | The "DIY xG" model. Best single-source substitute for xG. |
| 19 | SoT_adj + corners_adj | Chance creation + territorial dominance | Tests if corners add signal beyond shots. |
| 20 | SoT_adj + fouls_adj | Chance creation + pressing proxy | Tests if pressing intensity adds signal. |
| 21 | SoT_adj + goals_regressed | Underlying metric + actual results | Blend of process and outcome. |
| 22 | Corners_adj + fouls_adj | Style only, no shot data | Deliberately provocative. Can you predict outcomes with zero shot information? |
| 23 | SoT_adj + conversion_adj + corners_adj | Three-factor | Does adding territorial info improve DIY xG? |
| 24 | SoT_adj + conversion_adj + fouls_adj | Three-factor with pressing | Does adding pressing info improve DIY xG? |
| 25 | SoT_accuracy + SoT_adj | Shot selectivity + volume | Tests the "shot-shy teams" hypothesis. High accuracy + low volume = different signal than low accuracy + high volume. |

### Combination Weighting
For multi-metric variants, start with equal weighting (0.5/0.5 for two-factor, 0.33/0.33/0.33 for three-factor). The experiment runner should also test optimised weights via grid search on a training set (first 60% of seasons) and evaluate on a holdout (last 40%).

---

## Market Selection

**Do not pre-commit to a single market.** The Poisson grid produces probabilities for all markets simultaneously. The experiment should evaluate each variant across ALL of:

- Asian Handicap (AH)
- Over/Under 2.5 goals (O/U)
- Both Teams to Score (BTTS)
- 1X2 (match result)

This means each variant × league combination produces 4 ROI figures. The summary table will be 25 variants × 6 leagues × 4 markets = 600 cells. Let the data decide which market has edge in which league.

### Edge Threshold
Run each variant at multiple edge thresholds: 0% (all flagged bets), 3%, 5%, 7%, 10%. Report ROI, number of bets, and Brier score at each threshold.

---

## Module Architecture

The experiment is a **standalone research project**, completely separate from the production model code. No imports from the existing `model/` or `scrapers/` directories. Self-contained scripts that communicate via CSV files.

All code lives in a new `experiment/` directory at the project root.

### Module Breakdown

| # | Module | Script | LLM Assignment | Dependencies |
|---|---|---|---|---|
| 1 | Data Loader (football-data.co.uk) | `experiment/load_footballdata.py` | Qwen3-Coder | None |
| 2 | Data Loader (FotMob — stats + xG) | `experiment/load_fotmob.py` | Qwen3-Coder | None |
| 3 | ~~Data Loader (FBref)~~ | ~~`experiment/load_fbref.py`~~ | ~~Abandoned~~ | FBref blocked by Cloudflare CAPTCHA |
| 4 | Data Merge | `experiment/merge_data.py` | Qwen3-Coder | Modules 1-2 |
| 5 | Metric Calculator | `experiment/metrics.py` | Qwen3-Coder | Module 4 |
| 6 | Ratings Engine | `experiment/ratings.py` | Gemma (correctness-critical) | Module 5 |
| 7 | Poisson + Markets | `experiment/poisson.py` | Gemma (correctness-critical) | Module 6 |
| 8 | Experiment Runner | `experiment/run_experiment.py` | Qwen3-Coder | Modules 5-7 |
| 9 | Results Analysis | Colab notebook | Manual | Module 8 output |

### Module Interfaces

**Module 1 output** (`data/proxy/{league}_{season}_footballdata.csv`):
```
date, home_team, away_team, home_goals, away_goals, ht_home_goals, ht_away_goals,
home_shots, away_shots, home_sot, away_sot, home_corners, away_corners,
home_fouls, away_fouls, home_yellow, away_yellow, home_red, away_red,
odds_home, odds_draw, odds_away, odds_btts_yes, odds_btts_no,
odds_over25, odds_under25, odds_ah_line, odds_ah_home, odds_ah_away
```

**Module 2 output** (`data/proxy/{league}_{season}_fbref.csv`):
```
date, home_team, away_team, home_shots, away_shots, home_sot, away_sot,
home_corners, away_corners, home_fouls, away_fouls, home_yellow, away_yellow
```

**Module 3 output** (`data/proxy/{league}_{season}_fotmob.csv`):
```
date, home_team, away_team, home_xg, away_xg
```

**Module 4 output** (`data/proxy/{league}_{season}_merged.csv`):
Unified schema combining all three sources, joined on date + home/away teams. Team name normalisation handled here.

**Module 5 output** (`data/proxy/{league}_{season}_metrics.csv`):
One row per match. All 25 variant values computed per match for both home and away teams. Columns: `date, home_team, away_team, v1_home_attack, v1_home_defence, v1_away_attack, v1_away_defence, v2_home_attack, ...` through v25.

**Module 6 output** (`data/proxy/{league}_{season}_ratings.csv`):
EMA-smoothed ratings per team per matchday. Same column structure as module 5 but with rolling EMA applied. Includes opponent-adjusted values where applicable.

**Module 7 output** (`data/proxy/{league}_{season}_predictions.csv`):
Per match: lambda_home, lambda_away, P(BTTS), P(O2.5), P(home/draw/away), AH probabilities, edges vs market odds, should_bet flags. One set of columns per variant.

**Module 8 output** (`output/experiment_results.csv`):
Summary table: variant × league × market × threshold → ROI, n_bets, brier_score, hit_rate.

### Build Order
Modules 1-3 can be built in parallel (no dependencies).
Module 4 depends on 1-3.
Module 5 depends on 4.
Modules 6-7 depend on 5.
Module 8 depends on 7.
Module 9 (Colab analysis) depends on 8.

### Prompt Sequence for Local LLMs
Write one self-contained prompt per module. Each prompt must include:
- Exact input file path(s) and schema
- Exact output file path(s) and schema
- All logic to implement (no references to other files)
- Test cases / expected output for validation
- Colab QC instructions where applicable

---

## Path B — Goals-Only Tier

After Path A completes, run a separate stripped-down experiment using ONLY football-data.co.uk data (goals + odds) for Scandinavian leagues directly. This tests variant 9 (actual goals with regression) as a standalone model on the actual target leagues.

This is the floor — the minimum viable model that works with guaranteed-available data. If Path A shows that e.g. variant 18 (SoT_adj + conversion_adj) is the best performer, but Path B shows variant 9 (goals only) also produces positive ROI in Scandinavian leagues, then we have two deployment options with different data requirements.

---

## Success Criteria

1. **At least one variant shows positive ROI (>3%) across at least 3 of 6 proxy leagues in at least one market.** This would validate that a non-xG model can find edge.
2. **The "DIY xG" variants (18, 6) come within 3 percentage points of real xG (variant 15) ROI.** This would confirm that SoT-based approaches are viable substitutes.
3. **Different leagues favour different variants.** This would confirm per-league tuning is needed and inform the Scandinavian deployment strategy.
4. **The goals-only model (variant 9) is not the best performer.** If it is, the added complexity of sourcing match stats isn't justified.

---

## What Sonnet Does With This Document

1. Read this spec at session start.
2. Write one local LLM prompt per module (9 prompts total), following the CLAUDE.md tool allocation rules.
3. The prompts should be saved to `prompts/experiment/` with clear naming.
4. Do NOT implement the code in the Sonnet CLI session — write the prompts for local LLMs to execute.
5. Exception: if integration issues arise between modules that require cross-file debugging, Sonnet handles that directly.

---

## Open Questions for Sonnet Session

1. **EMA decay factor:** Use α = 0.1 as default (same as production model). Consider testing α = 0.05 and α = 0.15 as part of the experiment — this could be a variant axis on top of the 25 metric variants, but may be too many combinations. Use judgment.
2. **FBref scraping rate limits:** The FBref loader needs respectful scraping with delays. Consider caching aggressively. The `soccerdata` Python library may help.
3. **FotMob API stability:** The unofficial API could change endpoints. Build the FotMob loader defensively with error handling and fallback to "no xG available" for matches where it fails.
4. **Team name normalisation across sources:** This is always painful. Module 4 (merge) needs a manual alias table per league. Start with one league (Championship) to debug the approach, then extend.
5. **Train/test split:** For combination weight optimisation, use first 60% of seasons as training, last 40% as holdout. Do NOT tune weights on the same data used for ROI evaluation.
