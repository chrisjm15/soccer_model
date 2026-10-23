"""Pure calibration module for EPL Asian Handicap model.

Pure functions only: no I/O, no pandas.
"""
import math


def consensus_novig(book_prices: list[tuple[float, float]]) -> float:
    """Mean across bookmakers of each book's no-vig HOME probability.

    Formula per book: (1/h) / (1/h + 1/a).
    Raises ValueError on an empty list or any price <= 1.0.
    """
    if not book_prices:
        raise ValueError("book_prices must not be empty")

    probs = []
    for h, a in book_prices:
        if h <= 1.0 or a <= 1.0:
            raise ValueError(f"Prices must be > 1.0, got ({h}, {a})")
        inv_h = 1.0 / h
        inv_a = 1.0 / a
        novig_h = inv_h / (inv_h + inv_a)
        probs.append(novig_h)

    return sum(probs) / len(probs)


def calibrate_prob(market_prob: float, model_prob: float, coefs: dict) -> float:
    """Clip both probs to [0.01, 0.99] and return sigmoid(intercept + b_market*logit(m) + b_model*logit(x))."""
    m = max(0.01, min(0.99, market_prob))
    x = max(0.01, min(0.99, model_prob))

    logit_m = math.log(m / (1.0 - m))
    logit_x = math.log(x / (1.0 - x))

    z = coefs['intercept'] + coefs['b_market'] * logit_m + coefs['b_model'] * logit_x
    return 1.0 / (1.0 + math.exp(-z))


def calibrate_m1(market_prob: float, m1_coefs: dict) -> float:
    """Diagnostic M1 calibration: sigmoid(intercept + b_market*logit(m))."""
    m = max(0.01, min(0.99, market_prob))
    logit_m = math.log(m / (1.0 - m))
    z = m1_coefs['intercept'] + m1_coefs['b_market'] * logit_m
    return 1.0 / (1.0 + math.exp(-z))


def calibrated_ah_decision(
    p_home: float,
    p_push: float,
    p_away: float,
    novig_home: float,
    coefs: dict,
    threshold: float
) -> dict:
    """Compute calibrated AH decision matching the training definition.

    - novig_away = 1 - novig_home
    - side = larger raw edge (p_home - novig_home vs p_away - novig_away), ties -> home
    - model_prob = p_side + 0.5 * p_push
    - market_prob = novig_side
    - calib_edge = calib_prob - market_prob
    - should_bet = round(calib_edge, 6) >= threshold
    """
    novig_away = 1.0 - novig_home

    raw_edge_home = p_home - novig_home
    raw_edge_away = p_away - novig_away

    if raw_edge_home >= raw_edge_away:
        bet_side = 'home'
        model_prob = p_home + 0.5 * p_push
        market_prob = novig_home
    else:
        bet_side = 'away'
        model_prob = p_away + 0.5 * p_push
        market_prob = novig_away

    calib_prob = calibrate_prob(market_prob, model_prob, coefs)
    calib_edge = calib_prob - market_prob
    should_bet = round(calib_edge, 6) >= threshold

    return {
        'bet_side': bet_side,
        'model_prob': model_prob,
        'market_prob': market_prob,
        'calib_prob': calib_prob,
        'calib_edge': calib_edge,
        'should_bet': bool(should_bet),
    }
