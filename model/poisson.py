import math
from typing import Optional


def poisson_pmf(k: int, lam: float) -> float:
    """
    Poisson probability mass function: P(X = k) given rate lam.
    Uses log-space computation for numerical stability.
    """
    if k < 0:
        return 0.0
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    # ln(P(k)) = k * ln(lam) - lam - ln(k!)
    # ln(k!) = lgamma(k + 1)
    log_pmf = k * math.log(lam) - lam - math.lgamma(k + 1)
    return math.exp(log_pmf)


def compute_match_probs(
    home_attack: float,
    home_defence: float,
    away_attack: float,
    away_defence: float,
    home_advantage: float = 0.0,
    max_goals: int = 8
) -> dict:
    """
    Compute match outcome probabilities using independent Poisson model.
    Returns dict with lambda_home, lambda_away, prob_btts_yes, prob_btts_no,
    prob_home_win, prob_draw, prob_away_win, prob_over_25, prob_under_25, goal_grid.
    """
    # 1. Compute lambdas
    lambda_home = (home_attack + away_defence) / 2.0 + home_advantage
    lambda_away = (away_attack + home_defence) / 2.0
    # Clamp to minimum 0.1 to avoid degenerate distributions
    lambda_home = max(0.1, lambda_home)
    lambda_away = max(0.1, lambda_away)

    # 2. Build goal probability grid
    # grid[h][a] = P(home scores h, away scores a)
    grid = []
    for h in range(max_goals + 1):
        row = []
        for a in range(max_goals + 1):
            prob = poisson_pmf(h, lambda_home) * poisson_pmf(a, lambda_away)
            row.append(prob)
        grid.append(row)

    # 3. Normalise (corrects for truncation at max_goals)
    total_sum = sum(sum(row) for row in grid)
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            grid[h][a] /= total_sum

    # 4. Compute market probabilities from normalised grid
    prob_btts_yes = 0.0
    prob_home_win = 0.0
    prob_draw = 0.0
    prob_away_win = 0.0
    prob_over_25 = 0.0
    prob_under_25 = 0.0

    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            cell_prob = grid[h][a]
            if h >= 1 and a >= 1:
                prob_btts_yes += cell_prob
            if h > a:
                prob_home_win += cell_prob
            elif h == a:
                prob_draw += cell_prob
            else:
                prob_away_win += cell_prob
            if h + a > 2:
                prob_over_25 += cell_prob
            else:
                prob_under_25 += cell_prob

    return {
        'lambda_home': lambda_home,
        'lambda_away': lambda_away,
        'prob_btts_yes': prob_btts_yes,
        'prob_btts_no': 1.0 - prob_btts_yes,
        'prob_home_win': prob_home_win,
        'prob_draw': prob_draw,
        'prob_away_win': prob_away_win,
        'prob_over_25': prob_over_25,
        'prob_under_25': prob_under_25,
        'goal_grid': grid
    }


if __name__ == '__main__':
    # --- Test 1: Symmetric-ish match ---
    result = compute_match_probs(
        home_attack=1.6, home_defence=1.3,
        away_attack=1.3, away_defence=1.6,
        home_advantage=0.0
    )
    print("Test 1 — Symmetric-ish match:")
    print(f"  lambda_home={result['lambda_home']:.4f}, lambda_away={result['lambda_away']:.4f}")
    print(f"  P(BTTS Yes)={result['prob_btts_yes']:.4f}  (expected ~0.48-0.56)")
    print(f"  P(Home Win)={result['prob_home_win']:.4f}, P(Draw)={result['prob_draw']:.4f}, P(Away Win)={result['prob_away_win']:.4f}")
    print(f"  WDL sum    ={result['prob_home_win'] + result['prob_draw'] + result['prob_away_win']:.6f}  (must be 1.0)")
    print(f"  P(Over 2.5)={result['prob_over_25']:.4f}")

    # --- Test 2: High-scoring match ---
    result2 = compute_match_probs(
        home_attack=2.0, home_defence=2.0,
        away_attack=2.0, away_defence=2.0,
    )
    print("\nTest 2 — High-scoring match (lambda ~2.0 each):")
    print(f"  P(BTTS Yes)={result2['prob_btts_yes']:.4f}  (expected ~0.73-0.75)")

    # --- Test 3: Defensive match ---
    result3 = compute_match_probs(
        home_attack=1.0, home_defence=0.8,
        away_attack=0.8, away_defence=1.0,
    )
    print("\nTest 3 — Defensive match (lambda ~0.9 each):")
    print(f"  P(BTTS Yes)={result3['prob_btts_yes']:.4f}  (expected ~0.33-0.36)")

    # --- Test 4: Verify all probabilities sum correctly ---
    all_passed = True
    for test_name, res in [('T1', result), ('T2', result2), ('T3', result3)]:
        btts_sum = res['prob_btts_yes'] + res['prob_btts_no']
        wdl_sum = res['prob_home_win'] + res['prob_draw'] + res['prob_away_win']
        ou_sum = res['prob_over_25'] + res['prob_under_25']
        if abs(btts_sum - 1.0) > 1e-6:
            print(f"FAIL {test_name}: BTTS sums to {btts_sum}")
            all_passed = False
        if abs(wdl_sum - 1.0) > 1e-6:
            print(f"FAIL {test_name}: WDL sums to {wdl_sum}")
            all_passed = False
        if abs(ou_sum - 1.0) > 1e-6:
            print(f"FAIL {test_name}: O/U sums to {ou_sum}")
            all_passed = False
    if all_passed:
        print("\nAll sum checks passed.")
