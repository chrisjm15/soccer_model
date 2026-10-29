# Research findings — session 17 (2026-10-28)

Cowork, unattended. All read-only research; live model and automation unchanged. Reproduce with the scripts named.
Reports in `output/backtest_results/`. "t" = robust (HC1) t-statistic. Segment tables are exploratory.

> **Session 18 correction (2026-10-29):** two football-data Avg AH prices in the EPL OOS set are data errors
> (4.43 / 4.24 vs Bet365 1.98 / 2.03). All CLV@best-of-3 numbers below that include Avg prices are too high.
> Live rule: −1.5% ± 0.6 (not −0.3%); edge ≥ 2%: −0.2% (not +0.9%). CLV@Pinnacle figures are unaffected.
> **Luck AH rule at Average prices also corrected** (13 bad Avg rows among its bets): Big 5 +2.3% ± 1.4 (was +3.1%),
> EPL +6.0% ± 3.0 (was +7.9%), ex-EPL +1.3% ± 1.6 (was +1.7%). Pinnacle figures unchanged (ex-EPL +2.6%). Item 16
> now passes only on EPL at exactly t 2.0. Re-run reports: `live_rule_oos_report.txt`, `advanced_A.txt`, `advanced_J.txt`.
> Stop-date by gameweek: `output/backtest_results/stop_date_report.txt` (information gone by GW 8).

## Verdicts by hypothesis

| # | Hypothesis | Verdict | Key number | Report |
|---|---|---|---|---|
| 1 | Live EPL AH rule (1%) beats the close | **No** (OOS 2024-26) | CLV@Pinnacle −1.6% ± 0.7, n 179 | `live_rule_oos_report.txt` |
| 2 | EPL model information is spread across the season | **No — it is early-season** | move~signal Aug–Oct slope 0.0173 (t 6.9), +ve all 6 seasons; Nov–Jan t 1.7; Feb–May 0. Interaction t 4.9 (independently re-computed) | `advanced_A.txt` A4 |
| 3 | Early-season, strong-signal EPL bets beat the close | **Yes, small, sharp prices only** | Aug–Oct \|signal\| ≥ 0.6: ~33/season, move +1.9pp, CLV@Pinnacle +1.0% ± 0.5, best-of-3 +1.5% ± 0.5, CLV@avg ≈ 0 | `advanced_A.txt` A5 |
| 4 | The calibration's model term is robust | **No** — rests on 2020-21 (no crowds) | b_model 2021-26 +0.16 (t 1.3) vs 2020-21 alone +0.58 | `advanced_A.txt` A1 |
| 5 | Market (even at close) overrates teams whose goals ran ahead of xG ("luck") | **Yes** | Big 5 half lines, push-free, controlled: t −4.1 (independently re-computed); replicates on soft leagues with Sofascore xG (t −2.6/−2.7) | `advanced_C.txt` C6/C8 |
| 6 | Luck rule is profitable after margin | **EPL yes (historical), elsewhere no** | EPL back less-lucky side \|luck\| ≥ 0.4: ROI +8.0% ± 3.1 at avg AH prices (n 859, 5/6 seasons +ve); ex-EPL +1.6% ± 1.6; soft 1X2 −6% | `advanced_C.txt` C7/C8b |
| 7 | O/U 2.5 | **Fail** (incl. CLV test) | EPL b_model t 1.35; move~signal negative; OOS CLV@Avg −6.1% | `ou_1x2_calibration_report.txt`, `ou_1x2_clv_report.txt` |
| 8 | 1X2 | **Fail** (pre-set rule, 2026-10-28) | EPL home/away move~signal t 3.0 / 2.7 (same info as AH, half size) but OOS CLV@Avg −4.6%, @Pinnacle −3.3%. Draw signal anti-predicts movement (ex-EPL t −9) | `ou_1x2_clv_report.txt` |
| 9 | BTTS | **Fail** | b_model n.s. in every league; no edge ≥ 4pp exists. (Market-implied Poisson under-predicts BTTS by 2.6pp) | `advanced_D.txt` |
| 10 | Model-free "book beats Pinnacle fair" | **Not visible in this data** | Bet365 AH rarely above Pinnacle fair (6/season EPL); "Max" 1X2 prices that beat Pinnacle lose −3% to −8% (stale quotes) | `advanced_B.txt` |
| 11 | Betfair AU rescues execution | **No** | 6% commission ≈ 3pp EV at evens; luck rule on the same rows: Betfair net 6% +7.1% vs average bookmaker +8.2% | FUTURE_DEVELOPMENT item 3; `advanced_J.txt` |

### Part 2 (evening, full football-data files) — pass rule pre-set in `scripts/advanced_research2.py` docstring
Pass = closing price biased (|t| ≥ 2 pooled, controlled for logit(close)) AND fixed-threshold rule ROI at average prices > 0 with t ≥ 2.

| # | Hypothesis | Close biased? | Rule ROI @ Avg | Verdict | Report |
|---|---|---|---|---|---|
| 12 | Luck → O/U 2.5 (lucky runs inflate totals) | Yes, t −2.3 | −2.1% ± 1.6 (Big 5) | **Fail** | `advanced_E.txt` |
| 13 | Luck → 1X2 win / Draw No Bet | Yes, home t −3.2 | WIN −2.4% ± 2.8, DNB −2.3% ± 2.1 (Big 5); EPL DNB +2.4% ± 4.9 | **Fail** (margin) | `advanced_F.txt` |
| 14 | Promoted teams overrated early | No, t −0.97 | −0.5% ± 3.5 | **Fail** | `advanced_G.txt` |
| 15 | 'Nothing to play for' teams underperform | No, wrong sign t +1.4 | −9.2% ± 4.5 | **Fail** | `advanced_H.txt` |
| 16 | Luck → AH (the survivor), by venue | Yes, t −4.1 (part 1) | Big 5 +3.1% ± 1.4 (t 2.2); EPL +7.9% ± 3.1; best realistic quote (≤1.08× avg) Big 5 +5.0%, EPL +8.7% | **Passes** both parts — shadow-tested from GW10 (EPL); ex-EPL not yet live | `advanced_C.txt`, `advanced_J.txt` |

Data notes: football-data "Max" includes ~0.4% extreme quotes that inflate any Max-price ROI (cap them). Betfair
Exchange AH prices exist only for 2024-25/2025-26.

## What this means
- The model's real information is **early-season** (Aug–Oct) — plausibly the market anchoring on last season while
  xG updates faster. The live season is now leaving that window: the Feb checkpoint will mostly measure the part of
  the season where history shows no signal. Expect it to fail; that would not refute the early-season edge.
- **Luck (goals − xG) is the single strongest, simplest variable found.** It is not what the live model bets on
  (corr with model signal only −0.25). Pre-registered shadow test: `scripts/luck_shadow.py` (STATUS section 6),
  counting from GW10 (2026-10-30).
- **Price access still decides everything:** every positive result here is +1% to +2% CLV at Pinnacle-like prices;
  at average prices most go to ≈ 0 (the luck rule is the exception historically). The live log's "best price" comes
  from offshore books and may be flattered by stale quotes (finding 10).

- **The luck effect is real across markets (AH, 1X2, O/U closes all biased) but only the low-margin AH market
  converts it into profit.** Everything else tried tonight is priced correctly by the market.

## Off-season candidates (2027), in order
1. Read the luck shadow verdict; if it passes, add luck_diff to the model (or as its own rule).
2. Early-season-only EPL rule: |signal| threshold fixed in advance, sharp prices only; refit excluding or flagging 2020-21.
3. Ratings season-transition fix + push-consistent calibration baseline (handoff tech debt), then re-run
   `live_rule_oos_check.py` and `advanced_research.py A`.

Not explored (no data): lineups/team news, player availability, corners/cards markets, Asian totals.
