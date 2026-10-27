"""
GOLD TESTS for scripts/au_prices.py - written in Cowork 2026-10-28. Expected values are hand arithmetic,
shown beside each assertion. Do not edit to make a change pass.
Run:  python scripts/test_au_prices.py
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import pandas as pd
from au_prices import (bet_line, au_market, betfair_effective, ev, break_even, market_push_prob,
                       gap_vs_best, effective_prices, new_sheet_rows)

def close(a, b, tol=1e-6):
    return abs(a - b) < tol

# --- bet line: ah_line is home-perspective; away bet flips the sign; no negative zero
assert bet_line(-1.0, 'away') == 1.0
assert bet_line(1.0, 'home') == 1.0
assert bet_line(0.25, 'home') == 0.25
z = bet_line(0.0, 'away'); assert z == 0.0 and math.copysign(1, z) == 1.0

# --- AU market mapping (exact = an AU corporate market pays identically)
assert au_market(0.0) == ('Draw No Bet', True)                         # 0: draw -> stake back
assert au_market(0.5) == ('Double Chance (team or draw)', True)        # +0.5: win or draw
assert au_market(-0.5) == ('Head to Head: team to win', True)          # -0.5: must win
assert au_market(1.5)[1] is True and au_market(-1.5)[1] is True       # half lines: any 2-way line
for q in (0.25, -0.25, 0.75, -0.75, 1.0, -1.0, 1.25):
    assert au_market(q)[1] is False, q                                 # need a genuine AH
try:
    au_market(0.3); raise AssertionError('0.3 must be rejected')
except ValueError:
    pass

# --- Betfair commission on net winnings: 1 + (2.15 - 1) * 0.94 = 2.081
assert close(betfair_effective(2.15, 0.06), 2.081)
assert close(betfair_effective(2.00, 0.06), 1.94)                      # 1 + 1.00 * 0.94
try:
    betfair_effective(1.0); raise AssertionError('price 1.0 must be rejected')
except ValueError:
    pass

# --- EV from expected score s and push weight p: s*o - 1 + (1 - o/2)*p
assert close(ev(0.4803, 2.025), -0.0273925)              # no push: 0.9606 + 0.0120075 - 1
assert close(ev(0.4803, 2.10), 0.00863)                  # no push: 1.00863 - 1
assert close(ev(0.5, 2.0, 0.3), 0.0)                     # at o = 2 the push term vanishes
assert close(ev(0.4803, 2.10, 0.252), -0.00397)          # 0.00863 + (1 - 1.05)*0.252 = 0.00863 - 0.0126
# Cross-check by outcomes on a 0.00 line: P(push)=0.252, W = s - p/2 = 0.3543, L = 1 - 0.252 - 0.3543 = 0.3937
#   EV = W*(o-1) - L = 0.3543*1.10 - 0.3937 = 0.38973 - 0.3937 = -0.00397
assert close(ev(0.4803, 2.10, 0.252), 0.3543 * 1.10 - 0.3937)
# Quarter line (-0.25 = half on 0.00, half on -0.5), draw prob 0.26 -> p_push (averaged) = 0.13.
#   Outcomes for the bet: win 0.40 (score 1), draw 0.26 (half loss, score 0.25), loss 0.34 (score 0)
#   s = 0.40 + 0.25*0.26 = 0.465; payoff at o=2.2: 0.40*1.2 - 0.26*0.5 - 0.34 = 0.48 - 0.13 - 0.34 = 0.01
assert close(ev(0.465, 2.2, 0.13), 0.01)
# --- break-even: (1 - p) / (s - p/2)
assert close(break_even(0.5), 2.0)
assert close(break_even(0.4803, 0.252), 0.748 / 0.3543)  # 2.111205
assert close(ev(0.4803, break_even(0.4803, 0.252), 0.252), 0.0)
# --- market-implied push weight: half line 0; 0.00 line at q = 0.5 -> P(draw) with lam 1.4 v 1.4
#   e^-2.8 * sum 1.96^k / (k!)^2 = 0.0608101 * 4.1572945 = 0.252801
assert market_push_prob(0.5, 0.5, 'home') == 0.0
assert close(market_push_prob(0.5, 0.0, 'home'), 0.252801, 1e-5)
assert close(market_push_prob(0.5, 0.0, 'away'), 0.252801, 1e-5)
# quarter line averages two sub-lines: -0.25 at q=0.5 -> half the draw weight of the 0.00 sub-line, but the
# solve now puts supremacy > 0, so only check the bounds 0 < p < 0.2528/2 + 0.01
pq = market_push_prob(0.5, -0.25, 'home'); assert 0.10 < pq < 0.1364, pq
# --- gap vs logged best: 2.025 / 2.15 - 1 = -0.0581395
assert close(gap_vs_best(2.025, 2.15), -0.05813953, 1e-7)

# --- reading filled-in cells: blanks, text and <= 1.0 ignored; Betfair net of 6%
row = {'bet365_price': '2.025', 'sportsbet_price': ' 2.10 ', 'ladbrokes_price': '',
       'tab_price': 'n/a', 'betfair_back_price': '2.15', 'other_price': '1.0'}
eff = effective_prices(row)
assert set(eff) == {'bet365_price', 'sportsbet_price', 'betfair_back_price'}
assert close(eff['sportsbet_price'], 2.10) and close(eff['betfair_back_price'], 2.081)

# --- sheet rows from a log: only flagged, current-model bets; existing keys skipped
log = pd.DataFrame([
    dict(prediction_date='2026-10-24', match_date='2026-10-25', home_team='Sunderland', away_team='Leeds',
         ah_line=0.0, bet_side='home', odds_ah=2.15, calib_prob=0.4803, bet_flag='True', best_book='onexbet',
         market_prob_consensus=0.5),
    dict(prediction_date='2026-10-24', match_date='2026-10-24', home_team='Arsenal', away_team='Everton',
         ah_line=-1.5, bet_side='away', odds_ah=2.16, calib_prob=0.4863, bet_flag='True', best_book='matchbook',
         market_prob_consensus=0.4565),
    dict(prediction_date='2026-10-24', match_date='2026-10-24', home_team='Chelsea', away_team='Tottenham',
         ah_line=-0.75, bet_side='away', odds_ah=1.85, calib_prob=0.5161, bet_flag='False', best_book='x',
         market_prob_consensus=0.5),
    dict(prediction_date='2026-05-05', match_date='2026-05-09', home_team='Fulham', away_team='Bournemouth',
         ah_line=0.0, bet_side='home', odds_ah=2.08, calib_prob=0.5, bet_flag='True', best_book='x',
         market_prob_consensus=0.5),
])
rows = new_sheet_rows(log, set())
assert [r['key'] for r in rows] == ['2026-10-24|Sunderland|Leeds', '2026-10-24|Arsenal|Everton']
s, a = rows
assert s['bet'] == 'Sunderland +0.00' and s['au_market'] == 'Draw No Bet' and s['exact_at_corporates'] == 'yes'
assert s['p_push'] == 0.2528                     # q = 0.5 on 0.00 (test value, not the real GW9 q)
assert s['break_even'] == round((1 - 0.252801) / (0.4803 - 0.252801 / 2), 3)   # 0.747199/0.3539 = 2.111
assert a['bet'] == 'Everton +1.50' and a['exact_at_corporates'] == 'yes' and a['p_push'] == 0.0
assert a['break_even'] == 2.056                  # half line: 1 / 0.4863 = 2.05634 -> 2.056
assert new_sheet_rows(log, {'2026-10-24|Sunderland|Leeds', '2026-10-24|Arsenal|Everton'}) == []

print('ALL AU PRICE GOLD TESTS PASSED')
