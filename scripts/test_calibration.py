"""
FIXED GOLD TESTS for model/calibration.py — written and hand-verified in Cowork 2026-10-24.
DO NOT MODIFY THIS FILE. Implement model/calibration.py so every assertion passes.
Run:  python scripts/test_calibration.py
Coefficients below are the 2026-07-12 EPL M3 TRAIN fit (recalibration_report.txt), used here only
as fixed test inputs — deployment uses the refit values from config/calibration.yaml.
"""
import math, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from model.calibration import consensus_novig, calibrate_prob, calibrated_ah_decision

COEFS = {'intercept': -0.1416, 'b_market': 0.2850, 'b_model': 0.2858}
TOL = 1e-4
def close(a, b): return abs(a - b) < TOL

# ---------- consensus_novig ----------
# book1 1.90/1.90 -> (1/1.9)/(2/1.9) = 0.5
# book2 2.00/1.80 -> 0.5/(0.5+0.555556) = 0.473684
# mean = (0.5 + 0.473684)/2 = 0.486842
assert close(consensus_novig([(1.90, 1.90), (2.00, 1.80)]), 0.486842)
assert close(consensus_novig([(1.90, 1.90)]), 0.5)
for bad in ([], [(1.0, 1.9)], [(1.9, 0.0)]):
    try:
        consensus_novig(bad); raise AssertionError(f"expected ValueError for {bad}")
    except ValueError:
        pass

# ---------- calibrate_prob ----------
# z = -0.1416 + 0.2850*logit(m) + 0.2858*logit(x); calib = 1/(1+e^-z)
# m=0.50 x=0.60: logit(m)=0, logit(x)=0.405465 -> z=-0.1416+0.115882=-0.025718 -> 0.493571
assert close(calibrate_prob(0.50, 0.60, COEFS), 0.493571)
# m=0.40 x=0.65: -0.1416 + 0.2850*(-0.405465) + 0.2858*0.619039 = -0.080236 -> 0.479952
assert close(calibrate_prob(0.40, 0.65, COEFS), 0.479952)
# clipping: m=0.005 -> 0.01, x=0.995 -> 0.99; logit = -/+4.595120
# z = -0.1416 - 1.309609 + 1.313285 = -0.137924 -> 0.465574
assert close(calibrate_prob(0.005, 0.995, COEFS), 0.465574)

# ---------- calibrated_ah_decision ----------
# Side chosen by RAW edge (p_side - novig_side), ties -> home. model_prob = p_side + 0.5*p_push.
# D1: home raw edge 0.55-0.50=+0.05 > away -0.05 -> home; model 0.55, mkt 0.50
#     z = -0.1416 + 0.2858*0.200671 = -0.084248 -> calib 0.478950, edge -0.021050 -> no bet
d = calibrated_ah_decision(0.55, 0.0, 0.45, 0.50, COEFS, 0.01)
assert d['bet_side'] == 'home' and close(d['model_prob'], 0.55) and close(d['market_prob'], 0.50)
assert close(d['calib_prob'], 0.478950) and close(d['calib_edge'], -0.021050) and d['should_bet'] is False

# D2: novig_home 0.60 -> novig_away 0.40; raw edges home 0.30-0.60=-0.30, away 0.50-0.40=+0.10 -> away
#     model_prob = 0.50 + 0.5*0.20 = 0.60; mkt 0.40
#     z = -0.1416 + 0.2850*(-0.405465) + 0.2858*0.405465 = -0.141276 -> 0.464740, edge +0.064740 -> bet
d = calibrated_ah_decision(0.30, 0.20, 0.50, 0.60, COEFS, 0.01)
assert d['bet_side'] == 'away' and close(d['model_prob'], 0.60) and close(d['market_prob'], 0.40)
assert close(d['calib_prob'], 0.464740) and close(d['calib_edge'], 0.064740) and d['should_bet'] is True

# D3 tie: raw edges both 0 -> home
d = calibrated_ah_decision(0.50, 0.0, 0.50, 0.50, COEFS, 0.01)
assert d['bet_side'] == 'home'

# D4 threshold boundary (inclusive, compare edge rounded to 6dp):
# intercept=logit(0.51), slopes 0 -> calib exactly 0.51 vs mkt 0.50 -> edge 0.01 -> bet
lg = lambda p: math.log(p / (1 - p))
d = calibrated_ah_decision(0.55, 0.0, 0.45, 0.50, {'intercept': lg(0.51), 'b_market': 0.0, 'b_model': 0.0}, 0.01)
assert close(d['calib_edge'], 0.01) and d['should_bet'] is True
d = calibrated_ah_decision(0.55, 0.0, 0.45, 0.50, {'intercept': lg(0.5099), 'b_market': 0.0, 'b_model': 0.0}, 0.01)
assert d['should_bet'] is False

print("ALL CALIBRATION GOLD TESTS PASSED")
