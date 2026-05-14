# Large Line Calibration — Research Notes

*Documented 2026-05-12. Design only — no implementation yet.*

## The Problem

The Poisson model is well-calibrated in the 55-65% confidence zone but overconfident at 65%+.
Paper trading data: 65%+ zone hitting ~50%, 55-65% zone hitting ~60-70%.

**Root cause:** xG measures relative team quality well, but large AH lines (±2.0, ±2.5) require
predicting extreme scoreline outcomes. Scoreline distribution is highly volatile even in mismatches.
The Poisson model assumes season-average xG rates hold through 90 minutes — they don't.

Mechanisms that compress scorelines in large mismatches:
- Favourites ease off once 2-0 up (scoreline management)
- Underdogs defend deep specifically against elite opposition (tactical compression)
- Motivation asymmetry at end of season (nothing to play for)
- Fixture congestion causes rotation by the favourite
- Finishing variance regresses to mean regardless of quality gap

## Proposed Signal Factors

All factors below are derivable from existing data (all_merged.csv + standings calculations).
No new scrapers required.

---

### A. Motivation / Context

**1. Motivation proxy (league position)**
- Calculate points gap to nearest meaningful threshold for each team:
  - Favourite: distance from title / top-4 / Europa cutoff
  - Underdog: distance from relegation / promotion playoff
- A "done" favourite (gap too large to close) is less likely to push for a 3rd goal
- A fighting underdog (relegation scrap) defends harder than a mid-table team
- Signal: combined motivation score for both teams → dampens edge on large lines

**2. Rest days / fixture congestion**
- Days since last match for each team, computed from match dates in existing data
- Favourite playing 3 days after a cup game will rotate squad
- Signal: if favourite has <5 days rest, shade probability down on large lines

---

### B. Favourite's Offensive Profile

**3. Goals vs xG delta (finishing variance)**
- Actual goals scored vs xG over last 10 games
- Overperforming favourite (scoring well above xG) is likely to regress
- Underperforming favourite may be about to convert more
- Signal: regression-to-mean adjustment on expected goal output

**4. Score variance (std dev of goal margins)**
- Standard deviation of the favourite's goal margin over last 20 home/away games
- High-variance team: regularly wins 4-0 or loses 2-1 → better large-line bet
- Low-variance team: consistently grinds 1-0 or 2-1 → worse large-line bet
- Signal: variance multiplier on AH coverage probability

**5. Attack style — shots/corners volume**
- Teams that generate high shot and corner volume (15+ shots, 8+ corners/game) pile on
  goals late more than clinical low-volume attacks
- High-volume attacking style is more correlated with large margins than xG efficiency
- Signal: volume score for the favourite → modifies expected goal ceiling

---

### C. Underdog's Defensive Profile

**6. Defensive compression vs strong opponents**
- Split each team's xG conceded by opponent quality (top-half vs bottom-half)
- Some teams specifically defend deep against elite opposition, conceding far less xG
  than their season average suggests
- Signal: use opponent-quality-adjusted xG against (not season average) for the underdog

**7. Clean sheet rate**
- Distinct from xG conceded average — measures the tail of the defensive distribution
- A team keeping clean sheets 25% of the time has a different scoreline ceiling to
  one at 5%, even at the same average xG conceded
- Signal: clean sheet rate adjusts the model's probability of the favourite scoring 3+

**8. Recent large-loss frequency**
- Has the underdog been getting hammered (3-0, 4-1) or keeping it competitive in defeats?
- A team that loses 5 in a row but keeps them to 1-0 and 2-1 is a different
  proposition to one leaking 3+ regularly
- Signal: recent large-loss rate as a secondary defensive ceiling measure

---

### D. Market Signal

**9. Model line vs market line discrepancy**
- Currently: compare model probability vs market implied probability → edge
- Additional: compare the implied AH line itself (what line does the model think is fair
  vs what line the market is offering?)
- If model implies -1.5 is fair but market offers -2.5, the market has priced in something
  the model hasn't (injury, team selection, motivation, variance)
- A large discrepancy should dampen confidence even if edge looks positive
- Signal: line discrepancy flag on any bet where market line > model line by 0.75+

---

### E. Historical / Head-to-Head

**10. H2H AH history (this specific matchup)**
- What has the actual scoreline distribution been in the last 6-8 meetings?
- Some matchups have a consistent pattern the season-average model misses
- Small sample (use with low weight) but directly relevant signal
- Signal: H2H AH coverage rate as a weak prior

---

## Implementation Approach

These factors would NOT replace the Poisson model. They act as a second layer that
only activates when the primary model is in the overconfident zone (≥65%).

Conceptual flow:
1. Poisson model generates base probability and edge
2. If model probability ≥ 65% AND AH line ≥ ±1.5:
   - Compute confidence adjustment score from factors above
   - Shade probability down (or up) accordingly
   - Recalculate edge at adjusted probability
   - If edge falls below threshold → no bet

**Priority order for implementation** (highest value, simplest first):
1. Motivation proxy — not captured by xG at all, end-of-season critical
2. Score variance — directly measures scoreline distribution, not quality
3. Goals vs xG delta — regression signal, easy to calculate
4. Underdog defensive compression vs top-half — opponent-quality adjusted
5. Underdog clean sheet rate — defensive ceiling
6. Rest days — fixture congestion proxy
7. Recent large-loss frequency — current defensive form signal
8. Model line vs market line discrepancy — market intelligence signal
9. Shots/corners volume — attack style signal
10. H2H AH history — weak prior, small sample

## Data Available

`data/processed/all_merged.csv` — 10,624 matches, 2020-21 to 2025-26, 42 columns.

Key columns confirmed present:
| Column | Coverage | Use |
|---|---|---|
| `ah_line` | 10,617/10,624 | Historical market AH line |
| `odds_ah_home` / `odds_ah_away` | 10,617/10,624 | Historical AH odds — can calculate historical coverage |
| `pinnacle_home/draw/away` | 9,867/10,624 | Pinnacle closing odds — sharpest market reference for true probability |
| `home_xg` / `away_xg` | 10,624/10,624 | Full xG history |
| `home_goals` / `away_goals` | 10,624/10,624 | Full scoreline history |
| `home_shots` / `away_shots` / `home_corners` / `away_corners` | 10,623/10,624 | Attack style |
| `date` | 10,624/10,624 | Rest days calculation |

Standings (motivation proxy) can be reconstructed from match results by date — no new data needed.

## When to Implement

**Sooner than originally thought.** Historical data is sufficient to backtest all 10 factors
without waiting for paper trading volume. 5 seasons × ~380 EPL matches = ~1,900 EPL matches
alone, all with AH lines and odds.

Recommended approach:
1. Run the model retrospectively over historical matches to generate model probabilities
2. Segment by confidence zone (55-65%, 65-75%, 75%+) and AH line size
3. Measure actual AH coverage rate vs model probability in each segment
4. Identify which of the 10 factors best explains the calibration error
5. Build correction layer from that analysis

**Pinnacle line as benchmark:** where Pinnacle odds are available (93% of matches),
use Pinnacle implied probability as the "true" reference. If the model says 80% and
Pinnacle says 65%, the model is overconfident by ~15pp on that match type.
This is more reliable than waiting for paper trading results.

Timeline: next session (2026-05-13). One Sonnet CLI session for the backtest script,
then analysis and correction layer design in Cowork.
