"""
model/markets.py — Market prediction output layers.

Uses output from model.poisson.compute_match_probs().
Provides prediction functions for 1X2, Over/Under 2.5, and Asian Handicap.
"""

from model.poisson import compute_match_probs

DEFAULT_EDGE_THRESHOLD = 0.05


def compute_ah_probs(goal_grid: list, ah_line: float) -> dict:
    """
    Returns P(AH home wins), P(push), P(AH away wins) for a given handicap line.

    ah_line is from the home team's perspective:
      -1.0 = home gives 1 goal (needs to win by 2+ to win AH)
      +0.5 = home receives 0.5 goal (wins AH if match result is home win or draw)

    Handles three line types:
      - Half lines (-0.5, -1.5, 2.5 etc): no push possible
      - Whole lines (-1.0, -2.0, 1.0 etc): push when margin == |line|
      - Quarter lines (-0.25, -0.75, -1.25, -1.75 etc): split stake
        A quarter line is the average of two adjacent half/whole lines.
        e.g. -1.75 = average of -1.5 and -2.0
        Return weighted average of those two lines' outcomes.

    Returns:
        {
            'p_home': float,   # P(AH home wins)
            'p_push': float,   # P(push / stake returned) — 0.0 for half lines
            'p_away': float,   # P(AH away wins)
        }
    """
    # Determine if it's a quarter line
    is_quarter = (ah_line * 4) % 2 == 1

    if is_quarter:
        # Split into two adjacent lines
        lower_line = ah_line - 0.25
        upper_line = ah_line + 0.25
        p1 = compute_ah_probs(goal_grid, lower_line)
        p2 = compute_ah_probs(goal_grid, upper_line)
        # Average the probabilities
        return {
            'p_home': (p1['p_home'] + p2['p_home']) / 2,
            'p_push': (p1['p_push'] + p2['p_push']) / 2,
            'p_away': (p1['p_away'] + p2['p_away']) / 2,
        }

    p_home = 0.0
    p_push = 0.0
    p_away = 0.0

    # Iterate through all possible goal combinations
    for h in range(len(goal_grid)):
        for a in range(len(goal_grid[h])):
            prob = goal_grid[h][a]
            margin = h - a

            if margin > -ah_line:
                p_home += prob
            elif margin < -ah_line:
                p_away += prob
            else:  # margin == -ah_line (only for whole lines)
                p_push += prob

    return {
        'p_home': p_home,
        'p_push': p_push,
        'p_away': p_away,
    }


def predict_1x2(
    probs: dict,
    odds_home: float,
    odds_draw: float,
    odds_away: float,
    edge_threshold: float = DEFAULT_EDGE_THRESHOLD
) -> dict:
    """
    Predicts 1X2 market edge.

    For each outcome, edge = model_prob - implied_prob (where implied = 1/odds).
    Flag the single best-edge outcome if it exceeds edge_threshold.
    If multiple outcomes exceed threshold, flag only the highest-edge one.

    Returns:
        {
            'edge_home': float,
            'edge_draw': float,
            'edge_away': float,
            'best_outcome': str,       # 'home', 'draw', 'away', or None
            'best_edge': float,        # edge of best_outcome (or 0.0)
            'best_odds': float,        # odds of best_outcome (or None)
            'best_model_prob': float,  # model prob of best_outcome (or None)
            'should_bet': bool,
            'ev': float,               # EV of best_outcome per unit staked (or
0.0)
        }
    """
    # No-vig implied probabilities (normalise out the bookmaker overround)
    overround = 1/odds_home + 1/odds_draw + 1/odds_away
    implied_home = (1/odds_home) / overround
    implied_draw = (1/odds_draw) / overround
    implied_away = (1/odds_away) / overround

    # Model probabilities
    model_home = probs['prob_home_win']
    model_draw = probs['prob_draw']
    model_away = probs['prob_away_win']

    # Edge calculation (model prob vs no-vig implied prob)
    edge_home = model_home - implied_home
    edge_draw = model_draw - implied_draw
    edge_away = model_away - implied_away

    # Find the best edge
    edges = {
        'home': edge_home,
        'draw': edge_draw,
        'away': edge_away
    }

    best_outcome = max(edges, key=edges.get)
    best_edge = edges[best_outcome]

    # EV for the best outcome
    if best_outcome == 'home':
        ev = model_home * (odds_home - 1) - (1 - model_home)
    elif best_outcome == 'draw':
        ev = model_draw * (odds_draw - 1) - (1 - model_draw)
    else:  # away
        ev = model_away * (odds_away - 1) - (1 - model_away)

    should_bet = best_edge >= edge_threshold

    return {
        'edge_home': edge_home,
        'edge_draw': edge_draw,
        'edge_away': edge_away,
        'best_outcome': best_outcome if should_bet else None,
        'best_edge': best_edge if should_bet else 0.0,
        'best_odds': odds_home if best_outcome == 'home' else
                     odds_draw if best_outcome == 'draw' else
                     odds_away if best_outcome == 'away' else None,
        'best_model_prob': model_home if best_outcome == 'home' else
                           model_draw if best_outcome == 'draw' else
                           model_away if best_outcome == 'away' else None,
        'should_bet': should_bet,
        'ev': ev,
    }


def predict_over_under(
    probs: dict,
    odds_over: float,
    odds_under: float,
    edge_threshold: float = DEFAULT_EDGE_THRESHOLD
) -> dict:
    """
    Predicts Over/Under 2.5 market edge.
    Only considers betting Over (consistent with current model approach).

    Returns:
        {
            'edge_over': float,
            'implied_over': float,
            'model_prob_over': float,
            'should_bet': bool,
            'ev': float,
            'odds_over': float,
        }
    """
    # No-vig implied probability for over
    overround = 1/odds_over + 1/odds_under
    implied_over = (1/odds_over) / overround
    model_prob_over = probs['prob_over_25']

    edge_over = model_prob_over - implied_over
    ev = model_prob_over * (odds_over - 1) - (1 - model_prob_over)
    should_bet = edge_over >= edge_threshold

    return {
        'edge_over': edge_over,
        'implied_over': implied_over,
        'model_prob_over': model_prob_over,
        'should_bet': should_bet,
        'ev': ev,
        'odds_over': odds_over,
    }


def predict_asian_handicap(
    probs: dict,
    ah_line: float,
    odds_ah_home: float,
    odds_ah_away: float,
    edge_threshold: float = DEFAULT_EDGE_THRESHOLD
) -> dict:
    """
    Predicts Asian Handicap market edge for home and away sides.

    Uses compute_ah_probs() internally.

    For edge calculation with push, use:
        ev_home = p_home * (odds_ah_home - 1) - p_away
        ev_away = p_away * (odds_ah_away - 1) - p_home
        (push contributes 0 EV — stake returned)

    For implied prob comparison, treat as two-outcome market:
        implied_home = 1 / odds_ah_home
        edge_home = p_home - implied_home   [approximation, ignoring push]

    Flag the best side if edge >= threshold.

    Returns:
        {
            'p_ah_home': float,
            'p_push': float,
            'p_ah_away': float,
            'edge_ah_home': float,
            'edge_ah_away': float,
            'best_side': str,        # 'home', 'away', or None
            'best_edge': float,
            'best_odds': float,
            'should_bet': bool,
            'ev': float,
            'ah_line': float,
        }
    """
    ah_probs = compute_ah_probs(probs['goal_grid'], ah_line)
    p_home = ah_probs['p_home']
    p_push = ah_probs['p_push']
    p_away = ah_probs['p_away']

    # No-vig implied probabilities for AH (two-outcome market)
    overround = 1/odds_ah_home + 1/odds_ah_away
    implied_home = (1/odds_ah_home) / overround
    implied_away = (1/odds_ah_away) / overround

    edge_ah_home = p_home - implied_home
    edge_ah_away = p_away - implied_away

    # EV calculations
    ev_home = p_home * (odds_ah_home - 1) - p_away
    ev_away = p_away * (odds_ah_away - 1) - p_home

    # Choose the best side
    edges = {
        'home': edge_ah_home,
        'away': edge_ah_away
    }

    best_side = max(edges, key=edges.get)
    best_edge = edges[best_side]

    # EV for the best side
    if best_side == 'home':
        ev = ev_home
    else:
        ev = ev_away

    should_bet = best_edge >= edge_threshold

    return {
        'p_ah_home': p_home,
        'p_push': p_push,
        'p_ah_away': p_away,
        'edge_ah_home': edge_ah_home,
        'edge_ah_away': edge_ah_away,
        'best_side': best_side if should_bet else None,
        'best_edge': best_edge if should_bet else 0.0,
        'best_odds': odds_ah_home if best_side == 'home' else odds_ah_away,
        'should_bet': should_bet,
        'ev': ev,
        'ah_line': ah_line,
    }


if __name__ == '__main__':
    # Self-test: one match, all three markets
    probs = compute_match_probs(
        home_attack=1.8, home_defence=1.2,
        away_attack=1.2, away_defence=1.6,
        home_advantage=0.15
    )

    r1x2 = predict_1x2(probs, odds_home=2.10, odds_draw=3.40, odds_away=3.60)
    rou = predict_over_under(probs, odds_over=1.85, odds_under=2.00)
    rah = predict_asian_handicap(probs, ah_line=-0.5, odds_ah_home=1.95, odds_ah_away=1.95)

    print("=== 1X2 ===")
    print(f"  edge home={r1x2['edge_home']:+.3f}, draw={r1x2['edge_draw']:+.3f}, away={r1x2['edge_away']:+.3f}")
    print(f"  best={r1x2['best_outcome']}, edge={r1x2['best_edge']:+.3f}, should_bet={r1x2['should_bet']}")

    print("=== O/U 2.5 ===")
    print(f"  model_prob_over={rou['model_prob_over']:.3f}, implied={rou['implied_over']:.3f}")
    print(f"  edge={rou['edge_over']:+.3f}, should_bet={rou['should_bet']}")

    print("=== Asian Handicap (-0.5) ===")
    print(f"  p_home={rah['p_ah_home']:.3f}, p_push={rah['p_push']:.3f}, p_away={rah['p_ah_away']:.3f}")
    print(f"  edge_home={rah['edge_ah_home']:+.3f}, best={rah['best_side']}, should_bet={rah['should_bet']}")

    # Sanity check: AH probs sum to 1
    assert abs(rah['p_ah_home'] + rah['p_push'] + rah['p_ah_away'] - 1.0) < 1e-6, "AH probs must sum to 1"
    print("\nAll checks passed.")