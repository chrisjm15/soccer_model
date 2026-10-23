# Future Development — Edge Backlog

*Created 2026-07-12 (session 14), after the recalibration verdict. This is the durable list —
the handoff doc carries only the current top items and points here.*

**Organising principle (from the 2026-07-12 analysis):** the model is at information parity with
the EPL market and behind everywhere else in the Big 5. Model-quality work improves calibration
but adds no information the market lacks — it gets us to parity faster, not past it. Edge comes
from (a) knowing something the price doesn't yet reflect, or (b) getting a better price for the
same knowledge. Items are ranked by realistic edge-per-effort.

---

## Tier 1 — Execution / mechanical (no modelling required)

### 1. Best-price execution ⚠️ scheduled — part of the pre-GW1 deployment prompt
Check whether `run.py predict` evaluates edge against average or best-available odds from the
Odds API. Switch to best price. Worth ~1–2% ROI mechanically — on a hypothesised 1–3% edge this
can roughly double it. Zero modelling work.

### 2. Bet timing
Currently betting Thursday; 6 of 11 paper bets had the line move before close — we bet before
the market's biggest information event (lineups, ~1h before kickoff). Two exploitation routes:
- Bet later, post-lineups (needs item 4 to be worth anything), or
- In soft leagues, bet **opening** lines before lazy books sharpen them — plausibly the single
  richest seam available to this project. Test once Scandinavian pipeline is live.

### 3. Line shopping / venue
- Widen the Odds API book set; always take best price (extends item 1).
- **Betfair exchange (AU):** lower effective margin than corporates, no limiting of winners, and
  the exchange close is a clean CLV benchmark. Investigate commission impact on a 1–3% edge.

## Tier 2 — Information inputs (things the market knows and we don't)

### 4. Lineup-aware adjustment
Sofascore (already scraped) publishes lineups. Even a crude flag — "favourite resting 3+
starters" — beats nothing. Full version: adjust λ by xG-share of absent players.

### 5. Player-availability veto
The market's biggest edge over us is team news. Cheapest version first: manual pre-bet check
against a team-news source; veto bets where key attackers are out. Automation later.

### 6. xG input upgrades (Understat shot-level data, already accessible)
- **Strip penalties** — penalty xG is noise for team-strength estimation.
- **Game-state adjustment** — raw xG overrates teams padding stats while ahead and underrates
  game-managers; directly attacks the scoreline-management failure mode identified in calibration.
- **Set-piece / open-play split** — set-piece strength is persistent and systematically
  underweighted by aggregate models.
These are information upgrades, not quality polish — but note they mostly move us toward sharp
parity, not past it. Higher value in soft leagues than EPL.

## Tier 3 — Market / structural

### 7. Soft-league expansion ⚠️ in motion — data collection via scrape_next_league.bat
Where the remaining upside is concentrated. Sequence: finish Sofascore queue → Module 4 merge →
replicate calibration_backtest + recalibration disagreement test per league. Check during merge
whether Scandinavian football-data files carry AH odds or only 1X2 — determines target market.

### 8. Derivative markets (revisit after soft-league test)
BTTS+result combos, team totals: fewer punters model these rigorously, books price them lazier
(original BUILD_PLAN 3C thesis). Higher vig partially offsets. Only worth testing where the
underlying model has demonstrated information (i.e. not Big 5 ex-EPL).

### 9. Top-down Pinnacle-anchor betting (research session before dismissing)
Today's result proved the market's no-vig price ≈ truth. Use that: take Pinnacle no-vig as the
probability, bet AU soft books wherever their price deviates materially. No model required; the
most proven retail edge in existence. Caveat: AU corporates limit winners within weeks — sprint
economics, not a business. The model can tiebreak which discrepancies to hit.

## Measurement / infrastructure (supports everything above)

### 10. CLV decision framework ⚠️ live from next season
Both-sides odds now logged; CLV computed at settle. Checkpoint ~Christmas 2026 (~40–50 bets):
positive mean CLV → edge likely real, consider small stakes; negative → close the Big-5 chapter.

### 11. Promoted-team rating initialisation ⚠️ scheduled — part of the pre-GW1 deployment prompt
Three promoted clubs have no EPL xG history. Verify how their ratings seed; if league-mean, flag
or veto early-season bets involving them.

### 12. Calibration refit cadence
Deployment refits the EPL M3 blend on all six seasons. Decide refit schedule (e.g. each
pre-season, or mid-season if CLV drifts). Never refit on data that will also judge the model.

---

## Deprioritised — calibration/quality, not information (do not build until the above is exhausted)
- Dixon-Coles correction; bivariate Poisson / goal correlation structure
- PPDA, goalkeeper xGOT, EMA decay tuning, dynamic home advantage
- **10-factor large-line correction layer — killed 2026-07-12** (M4 interaction insignificant;
  global M3 recalibration already handles the miscalibration). See `LARGE_LINE_CALIBRATION.md` header.
