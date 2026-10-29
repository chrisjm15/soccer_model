# Future Development — Edge Backlog

*Created 2026-07-12 (session 14), after the recalibration verdict. Updated 2026-10-28 (session 17). This is the
durable list — the handoff doc carries only the current top items and points here.*

**Session 17 research — see `docs/RESEARCH_SESSION_17.md`.** New top items: luck (goals − xG) bias (shadow test
running), early-season-only EPL rule. O/U 2.5 and BTTS (item 8) tested and failed.

**Session 18 update (2026-10-29):** best-of-3 CLV figures corrected for two bad Avg prices (live rule −1.5%, edge
≥ 2% −0.2%); model information ends by GW 8 (`stop_date_report.txt`). Item 4 (lineups): scraper + pre-set test built,
awaiting Chris's fetch (`LINEUPS_FETCH_AND_TEST.bat`). Item 12: fix ready in `experiment/offseason_2027/`.

**Session 17 update (2026-10-28):** the session-16 flagged-bet CLV (+0.7%, n=43) was measured on the all-leagues
fit, not the live EPL-only rule. For the live rule (OOS 2024-26, n=179): market move +0.6pp, CLV −1.6% at Pinnacle
pre-close, −0.3% at best of B365/Pinnacle/avg. The 1–2% edge band carries no signal (move −0.2pp); edges ≥ 2% do
(move +1.2pp, t≈3; CLV −0.7% Pinnacle / +0.9% best-of-3). See `output/backtest_results/live_rule_oos_report.txt`.
Item 9 (Pinnacle-anchor) moves up: the AU price tracker already collects what it needs.

**Session 16 update:** EPL line-movement test confirmed real but small information (market moves +2.0pp toward
flagged bets ≈ one margin; price CLV ≈ 0 at average prices). Soft leagues failed. Execution items (Tier 1)
are now the highest-value work.

**Organising principle (from the 2026-07-12 analysis):** the model is at information parity with
the EPL market and behind everywhere else in the Big 5. Model-quality work improves calibration
but adds no information the market lacks — it gets us to parity faster, not past it. Edge comes
from (a) knowing something the price doesn't yet reflect, or (b) getting a better price for the
same knowledge. Items are ranked by realistic edge-per-effort.

---

## Tier 1 — Execution / mechanical (no modelling required)

### 1. Best-price execution ✅ partly done (session 15)
Predict now prices bets at the best available book (edge still measured vs consensus no-vig). Open: the best
prices mostly come from offshore/exchange books with no AU access — see item 3. On the measured edge (≈ one
margin) this item decides whether the EPL model makes money at all.

### 2. Bet timing
Currently betting Thursday; 6 of 11 paper bets had the line move before close — we bet before
the market's biggest information event (lineups, ~1h before kickoff). Two exploitation routes:
- Bet later, post-lineups (needs item 4 to be worth anything), or
- In soft leagues, bet **opening** lines before lazy books sharpen them — plausibly the single
  richest seam available to this project. Test once Scandinavian pipeline is live.

### 3. Line shopping / venue
- Widen the Odds API book set; always take best price (extends item 1).
- **Betfair exchange (AU):** lower effective margin than corporates, no limiting of winners, and
  the exchange close is a clean CLV benchmark. **Checked 2026-10-28:** Betfair AU Market Base Rate for sport is
  **6%** of net winnings (betfair.com.au help page; was 5% before March 2025; volume discounts exist, amounts not
  published). At evens that costs ≈ 3pp of EV (6% × (o−1)/o). Worked case, Sunderland +0.00 GW9: exact break-even
  2.111 → Betfair back price needed 1 + 1.111/0.94 = 2.18; fair no-vig price was 2.16 and back prices sit just below
  fair → not bettable. Rule of thumb: Betfair AU pays only for edges ≳ 3pp near evens. Not the rescue for the 1–2%
  band. Liquidity for EPL AH on the AU exchange still unchecked (needs Chris to look at a live market).

## Tier 2 — Information inputs (things the market knows and we don't)

### 4. Lineup-aware adjustment — tested 2026-10-29 (`lineup_report.txt`)
Market reacts strongly to lineups (t 13.6) and the close prices them correctly (no post-lineup edge). Lead: absences
known on Friday (regulars missing from the previous XI) move the price later (t 3.6, post-hoc) and the model ignores
them -> candidate 2027 input/veto, pre-register a prospective test first. Data: `scrapers/understat_lineups.py`.

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

### 7. Soft-league expansion ❌ closed for v1 (2026-10-25)
Tested B1 N1 P1 T1 E1 (AH + 1X2) and DNK SWE NOR (1X2 only — no AH odds exist). Pooled AH M3 b_model −0.097
(CI excludes EPL's +0.245); 1X2 ≤ 0 everywhere; OOS ROI ≈ 0 / negative. Curiosity: the model predicts soft-league
line *movement* (t=3.1) but not results — revisit only with a new information source. Report:
`output/backtest_results/soft_calibration_report.txt`. Pipeline kept (`experiment/merge_data.py`).

### 8. Derivative markets (EPL only — soft leagues failed)
BTTS+result combos, team totals: fewer punters model these rigorously, books price them lazier
(original BUILD_PLAN 3C thesis). Higher vig partially offsets. Only worth testing where the
underlying model has demonstrated information (i.e. not Big 5 ex-EPL).

### 9. Top-down Pinnacle-anchor betting (research session before dismissing)
Today's result proved the market's no-vig price ≈ truth. Use that: take Pinnacle no-vig as the
probability, bet AU soft books wherever their price deviates materially. No model required; the
most proven retail edge in existence. Caveat: AU corporates limit winners within weeks — sprint
economics, not a business. The model can tiebreak which discrepancies to hit.

## Measurement / infrastructure (supports everything above)

### 10. CLV decision framework ✅ live (fixed session 16)
CLV now uses football-data closing odds (market-average), converted onto the bet line, on every logged match.
Checkpoint ≈ Feb 2027 at ~40 flagged bets on mean `clv_price` (> +1% → plan stakes; ≤ 0 → edge doesn't survive our
prices). Historical test: `output/backtest_results/clv_edge_report.txt`.

### 11. Promoted-team rating initialisation ✅ done (session 15)
Promoted-team veto until 10 matches played (`promoted_min_matches` in `config/calibration.yaml`).

### 12. Calibration refit cadence + ratings season-transition fix — 2027 off-season
Refit each pre-season, never mid-season. Next refit must follow the `model/ratings.py` season-transition fix
(league means read live/partly-updated ratings → order-dependent ratings; see handoff tech debt), then re-run
`scripts/clv_edge_analysis.py` to confirm the EPL result survives.

---

## Deprioritised — calibration/quality, not information (do not build until the above is exhausted)
- Dixon-Coles correction; bivariate Poisson / goal correlation structure
- PPDA, goalkeeper xGOT, EMA decay tuning, dynamic home advantage
- **10-factor large-line correction layer — killed 2026-07-12** (M4 interaction insignificant;
  global M3 recalibration already handles the miscalibration). See `LARGE_LINE_CALIBRATION.md` header.
