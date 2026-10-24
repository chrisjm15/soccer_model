"""
FIXED GOLD TESTS for select_main_line() in model/calibration.py — hand-verified in Cowork 2026-10-24.
DO NOT MODIFY THIS FILE. Run: python scripts/test_line_selection.py

Rule: the main Asian line is the line whose consensus no-vig HOME probability is closest to 0.5
(distance rounded to 6dp). Ties -> line with more books -> smaller |line|.
Returns (line, consensus_novig_home). Empty input -> ValueError.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from model.calibration import select_main_line

TOL = 1e-4
def close(a, b): return abs(a - b) < TOL

# T1: the modal line (-1.5, 3 books) must NOT win.
#  -1.5: (1/3)/(1/3+1/1.4) = 0.318182 -> dist 0.181818
#  -0.75: mean(0.435897, 0.427481) = 0.431689 -> dist 0.068311
#  -0.5: (1/1.90)/(1/1.90+1/1.92) = 0.502618 -> dist 0.002618  <- winner
line, p = select_main_line({-1.5: [(3.0, 1.40)] * 3,
                            -0.75: [(2.20, 1.70), (2.25, 1.68)],
                            -0.5: [(1.90, 1.92)]})
assert line == -0.5 and close(p, 0.502618), (line, p)

# T2: near-tie decided by distance, not book count.
#  -0.5 dist 0.002618 ; -0.25 mean(0.494737, 0.5) = 0.497368 -> dist 0.002632 -> -0.5 wins
line, p = select_main_line({-0.5: [(1.90, 1.92)], -0.25: [(1.92, 1.88), (1.90, 1.90)]})
assert line == -0.5 and close(p, 0.502618), (line, p)

# T3: exact tie on distance (0.479381 vs 0.520619, both 0.020619) -> more books wins -> -0.25
line, p = select_main_line({0.25: [(2.02, 1.86)], -0.25: [(1.86, 2.02), (1.86, 2.02)]})
assert line == -0.25 and close(p, 0.520619), (line, p)

# T4: empty -> ValueError
try:
    select_main_line({}); raise AssertionError("expected ValueError")
except ValueError:
    pass

print("ALL LINE SELECTION GOLD TESTS PASSED")
