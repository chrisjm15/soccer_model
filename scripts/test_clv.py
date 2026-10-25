"""
FIXED GOLD TESTS for model/clv.py — written in Cowork 2026-10-25.
DO NOT MODIFY THIS FILE. Implement model/clv.py so every assertion passes.
Run:  python scripts/test_clv.py

How the expected values were produced:
  - no-vig and price-CLV values: hand arithmetic, shown beside each assertion.
  - line-conversion values: an independent reference implementation written in Cowork
    (independent Poisson grid, 16 goals, bisection on goal supremacy), cross-checked against
    the closed-form symmetric case below. model/clv.py must use max_goals >= 10 (truncation
    error at 10 goals is < 1e-5; at the model's default 8 goals it can exceed 1e-4).

Definitions (home perspective; AH line as football-data AHh, e.g. -0.5 = home gives 0.5):
  q_home(line)  = price-implied no-vig HOME probability on that line
                = p_home / (p_home + p_away), with p_home / p_away from
                  model.markets.compute_ah_probs (quarter lines already split there).
                  Pushes drop out, which is exactly what a two-way no-vig price measures.
  convert       = find goal supremacy s with lam_h=(mu+s)/2, lam_a=(mu-s)/2 such that
                  q_home(close_line) == q_close_home, then return q_home(bet_line).
                  Identity (no solve) when the lines are equal.
  clv_move      = closing no-vig prob of the bet side, on the BET line − market prob of the bet
                  side at bet time (log column market_prob_consensus).
  clv_price     = bet_odds × closing no-vig prob of the bet side on the bet line − 1
                  (expected return per unit staked, priced at the close).
"""
import math, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from model.clv import novig_home, ah_q_home, convert_q_home, clv_for_row

TOL = 1e-4
def close(a, b): return a is not None and b is not None and abs(a - b) < TOL

# ---------- novig_home ----------
# 1.95/1.95 -> 0.5
assert close(novig_home(1.95, 1.95), 0.5)
# 2.10/1.80: 1/2.1=0.476190, 1/1.8=0.555556, sum=1.031746 -> 0.476190/1.031746 = 0.461538
assert close(novig_home(2.10, 1.80), 0.461538)
# 2.00/1.90: 0.5 / (0.5+0.526316) = 0.487179
assert close(novig_home(2.00, 1.90), 0.487179)
for bad in [(1.0, 1.9), (1.9, 0.0), (float('nan'), 1.9)]:
    try:
        novig_home(*bad); raise AssertionError(f"expected ValueError for {bad}")
    except ValueError:
        pass

# ---------- ah_q_home ----------
# Symmetric teams, level line: exactly 0.5 by symmetry
assert close(ah_q_home(1.4, 1.4, 0.0), 0.5)
# Symmetric, home +0.5: home wins bet on H>=A, no pushes -> 1 - P(A>H) = 0.626403 (closed form)
assert close(ah_q_home(1.4, 1.4, 0.5), 0.626403)
# Asymmetric reference values (lam_h=1.6, lam_a=1.2)
assert close(ah_q_home(1.6, 1.2, 0.0), 0.619700)    # level: pushes on draws drop out
assert close(ah_q_home(1.6, 1.2, -0.25), 0.532337)  # quarter line
assert close(ah_q_home(1.6, 1.2, -0.5), 0.466563)   # home must win

# ---------- convert_q_home ----------
# Equal lines -> identity, exactly, independent of mu
assert close(convert_q_home(0.47, 0.25, 0.25), 0.47)
assert close(convert_q_home(0.47, 0.25, 0.25, mu=3.1), 0.47)
# Level close at 0.50 -> symmetric teams; moving home to +0.5 reproduces the closed form above
assert close(convert_q_home(0.50, 0.0, 0.5), 0.626403)
# Quarter steps either side of level are mirror images: 0.572346 and 1-0.572346 = 0.427654
assert close(convert_q_home(0.50, 0.0, 0.25), 0.572346)
assert close(convert_q_home(0.50, 0.0, -0.25), 0.427654)
# General reference cases (mu = 2.8 default)
assert close(convert_q_home(0.52, -0.5, -0.25), 0.590594)
assert close(convert_q_home(0.48, -0.75, -1.0), 0.397970)
assert close(convert_q_home(0.55, 1.0, 0.75), 0.473249)
assert close(convert_q_home(0.50, -1.5, -1.25), 0.569328)
# mu is a real parameter (sensitivity is small but non-zero)
assert close(convert_q_home(0.50, 0.0, 0.25, mu=2.5), 0.578050)
assert close(convert_q_home(0.50, 0.0, 0.25, mu=3.1), 0.567702)
# Invalid probability -> None (never raise inside the results loop)
assert convert_q_home(0.0, 0.0, 0.5) is None
assert convert_q_home(1.0, 0.0, 0.5) is None
assert convert_q_home(float('nan'), 0.0, 0.5) is None

# ---------- clv_for_row ----------
# R1  HOME bet, line moved. Bet: Villa +1.00 @ 1.83, market_prob 0.5321.
#     Close: AHCh +1.25, Pinnacle 2.00/1.90 -> q_close_home(+1.25) = 0.487179
#     converted to +1.00 = 0.402756
#     clv_move  = 0.402756 - 0.5321 = -0.129344
#     clv_price = 1.83 * 0.402756 - 1 = -0.262957
r = clv_for_row(bet_side='home', bet_line=1.0, bet_odds=1.83, bet_market_prob=0.5321,
                close_line=1.25, close_home_odds=2.00, close_away_odds=1.90)
assert close(r['closing_prob_bet_side'], 0.402756)
assert close(r['clv_move'], -0.129344)
assert close(r['clv_price'], -0.262957)
assert r['line_converted'] is True

# R2  AWAY bet, same line. Bet: Spurs (away) at -0.75 @ 1.85, market_prob 0.5264.
#     Close: AHCh -0.75, Pinnacle 2.02/1.88: 1/2.02=0.495050, 1/1.88=0.531915
#     q_home = 0.495050/1.026965 = 0.482051 -> away = 0.517949
#     clv_move  = 0.517949 - 0.5264 = -0.008451
#     clv_price = 1.85 * 0.517949 - 1 = -0.041795
r = clv_for_row(bet_side='away', bet_line=-0.75, bet_odds=1.85, bet_market_prob=0.5264,
                close_line=-0.75, close_home_odds=2.02, close_away_odds=1.88)
assert close(r['closing_prob_bet_side'], 0.517949)
assert close(r['clv_move'], -0.008451)
assert close(r['clv_price'], -0.041795)
assert r['line_converted'] is False

# R3  AWAY bet, line moved. Bet line -0.25 (home gives 0.25), away @ 2.00, market_prob 0.50.
#     Close: AHCh -0.5, Pinnacle 2.10/1.80 -> q_close_home(-0.5) = 0.461538
#     converted home q at -0.25 = 0.526780 -> away = 0.473220
#     clv_move  = 0.473220 - 0.50 = -0.026780
#     clv_price = 2.00 * 0.473220 - 1 = -0.053560
r = clv_for_row(bet_side='away', bet_line=-0.25, bet_odds=2.00, bet_market_prob=0.50,
                close_line=-0.5, close_home_odds=2.10, close_away_odds=1.80)
assert close(r['closing_prob_bet_side'], 0.473220)
assert close(r['clv_move'], -0.026780)
assert close(r['clv_price'], -0.053560)

# R4  Old row with no bet-time market prob -> clv_move None, clv_price still computed.
#     Same close as R2, home bet @ 2.06 at -0.75: home q = 0.482051
#     clv_price = 2.06 * 0.482051 - 1 = -0.006975
r = clv_for_row(bet_side='home', bet_line=-0.75, bet_odds=2.06, bet_market_prob=None,
                close_line=-0.75, close_home_odds=2.02, close_away_odds=1.88)
assert r['clv_move'] is None
assert close(r['clv_price'], -0.006975)

# R5  Missing / bad closing data -> every output None, no exception
for bad_close in [(None, 2.0, 1.9), (0.0, None, 1.9), (0.0, 1.0, 1.9), (float('nan'), 2.0, 1.9)]:
    r = clv_for_row(bet_side='home', bet_line=0.0, bet_odds=2.0, bet_market_prob=0.5,
                    close_line=bad_close[0], close_home_odds=bad_close[1], close_away_odds=bad_close[2])
    assert r['closing_prob_bet_side'] is None and r['clv_move'] is None and r['clv_price'] is None

print("ALL CLV GOLD TESTS PASSED")
