# Research findings — session 17 (2026-10-28)

Cowork, unattended. All read-only research; live model and automation unchanged. Reproduce with the scripts named.
Reports in `output/backtest_results/`. "t" = robust (HC1) t-statistic. Segment tables are exploratory.

## Verdicts by hypothesis

| # | Hypothesis | Verdict | Key number | Report |
|---|---|---|---|---|
| 1 | Live EPL AH rule (1%) beats the close | **No** (OOS 2024-26) | CLV@Pinnacle −1.6% ± 0.7, n 179 | `live_rule_oos_report.txt` |
| 2 | EPL model information is spread across the season | **No — it is early-season** | move~signal Aug–Oct slope 0.0173 (t 6.9), +ve all 6 seasons; Nov–Jan t 1.7; Feb–May 0. Interaction t 4.9 (independently re-computed) | `advanced_A.txt` A4 |
| 3 | Early-season, strong-signal EPL bets beat the close | **Yes, small, sharp prices only** | Aug–Oct \|signal\| ≥ 0.6: ~33/season, move +1.9pp, CLV@Pinnacle +1.0% ± 0.5, best-of-3 +1.5% ± 0.5, CLV@avg ≈ 0 | `advanced_A.txt` A5 |
| 4 | The calibration's model term is robust | **No** — rests on 2020-21 (no crowds) | b_model 2021-26 +0.16 (t 1.3) vs 2020-21 alone +0.58 | `advanced_A.txt` A1 |
| 5 | Market (even at close) overrates teams whose goals ran ahead of xG ("luck") | **Yes** | Big 5 half lines, push-free, controlled: t −4.1 (independently re-computed); replicates on soft leagues with Sofascore xG (t −2.6/−2.7) | `advanced_C.txt` C6/C8 |
| 6 | Luck rule is profitable after margin | **EPL yes (historical), elsewhere no** | EPL back less-lucky side \|luck\| ≥ 0.4: ROI +8.0% ± 3.1 at avg AH prices (n 859, 5/6 seasons +ve); ex-EPL +1.6% ± 1.6; soft 1X2 −6% | `advanced_C.txt` C7/C8b |
| 7 | O/U 2.5 | **Fail** | EPL b_model t 1.35; OOS worse than market | `ou_1x2_calibration_report.txt` |
| 8 | 1X2 | **Pending CLV** (`DOWNLOAD_AND_TEST_1X2_OU.bat`) | EPL away b_model t 2.14; OOS ROI noise-level | same + `ou_1x2_clv_report.txt` |
| 9 | BTTS | **Fail** | b_model n.s. in every league; no edge ≥ 4pp exists. (Market-implied Poisson under-predicts BTTS by 2.6pp) | `advanced_D.txt` |
| 10 | Model-free "book beats Pinnacle fair" | **Not visible in this data** | Bet365 AH rarely above Pinnacle fair (6/season EPL); "Max" 1X2 prices that beat Pinnacle lose −3% to −8% (stale quotes) | `advanced_B.txt` |
| 11 | Betfair AU rescues execution | **No** | 6% commission ≈ 3pp EV at evens | FUTURE_DEVELOPMENT item 3 |

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

## Off-season candidates (2027), in order
1. Read the luck shadow verdict; if it passes, add luck_diff to the model (or as its own rule).
2. Early-season-only EPL rule: |signal| threshold fixed in advance, sharp prices only; refit excluding or flagging 2020-21.
3. Ratings season-transition fix + push-consistent calibration baseline (handoff tech debt), then re-run
   `live_rule_oos_check.py` and `advanced_research.py A`.
4. 1X2 only if the CLV test passes its pre-set rule.

Not explored (no data): lineups/team news, player availability, corners/cards markets, Asian totals.
