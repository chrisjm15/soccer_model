"""Pure closing-line value (CLV) calculation and AH line conversion module.

Pure functions only: no I/O, no pandas.
"""
import math
from typing import Optional

from model.markets import compute_ah_probs
from model.poisson import poisson_pmf


def _is_bad_number(x) -> bool:
    if x is None or isinstance(x, bool):
        return True
    try:
        f = float(x)
    except (TypeError, ValueError):
        return True
    return math.isnan(f) or math.isinf(f)


def novig_home(home_odds: float, away_odds: float) -> float:
    """Two-way no-vig home probability: (1/h) / (1/h + 1/a).

    Raises ValueError on any price <= 1.0, None, or NaN.
    """
    if _is_bad_number(home_odds) or _is_bad_number(away_odds):
        raise ValueError(f"Invalid odds: ({home_odds}, {away_odds})")
    h = float(home_odds)
    a = float(away_odds)
    if h <= 1.0 or a <= 1.0:
        raise ValueError(f"Odds must be > 1.0, got ({h}, {a})")
    inv_h = 1.0 / h
    inv_a = 1.0 / a
    return inv_h / (inv_h + inv_a)


def ah_q_home(lam_h: float, lam_a: float, line: float, max_goals: int = 10) -> float:
    """Price-implied no-vig HOME probability on an AH line under independent Poisson.

    Builds a (max_goals+1)x(max_goals+1) Poisson grid with poisson_pmf, calls
    compute_ah_probs, and returns p_home / (p_home + p_away).
    """
    grid = [
        [poisson_pmf(h, lam_h) * poisson_pmf(a, lam_a) for a in range(max_goals + 1)]
        for h in range(max_goals + 1)
    ]
    probs = compute_ah_probs(grid, float(line))
    denom = probs['p_home'] + probs['p_away']
    if denom <= 0.0:
        return 0.5
    return probs['p_home'] / denom


def convert_q_home(
    q_close_home: float,
    close_line: float,
    bet_line: float,
    mu: float = 2.8,
) -> Optional[float]:
    """Convert closing no-vig home probability from close_line onto bet_line.

    Identity when the lines are equal (no solve). Otherwise bisects goal supremacy
    s in (-mu, mu) with lam_h=(mu+s)/2, lam_a=(mu-s)/2 until ah_q_home(..., close_line)
    matches q_close_home (tolerance 1e-9), then returns ah_q_home(..., bet_line).
    Returns None for q <= 0, q >= 1, NaN, or no solution.
    """
    if (
        _is_bad_number(q_close_home)
        or _is_bad_number(close_line)
        or _is_bad_number(bet_line)
        or _is_bad_number(mu)
    ):
        return None

    q = float(q_close_home)
    c_line = float(close_line)
    b_line = float(bet_line)
    total_mu = float(mu)

    if q <= 0.0 or q >= 1.0 or total_mu <= 0.0:
        return None

    if abs(c_line - b_line) < 1e-9:
        return q

    eps = 1e-9
    lo = -total_mu + eps
    hi = total_mu - eps
    if lo >= hi:
        return None

    f_lo = ah_q_home((total_mu + lo) / 2.0, (total_mu - lo) / 2.0, c_line)
    f_hi = ah_q_home((total_mu + hi) / 2.0, (total_mu - hi) / 2.0, c_line)

    if q < f_lo or q > f_hi:
        return None

    for _ in range(100):
        mid = 0.5 * (lo + hi)
        val = ah_q_home((total_mu + mid) / 2.0, (total_mu - mid) / 2.0, c_line)
        if abs(val - q) <= 1e-9:
            lo = hi = mid
            break
        if val < q:
            lo = mid
        else:
            hi = mid

    s = 0.5 * (lo + hi)
    val_check = ah_q_home((total_mu + s) / 2.0, (total_mu - s) / 2.0, c_line)
    if abs(val_check - q) > 1e-5:
        return None

    return ah_q_home((total_mu + s) / 2.0, (total_mu - s) / 2.0, b_line)


def clv_for_row(
    bet_side: str,
    bet_line: float,
    bet_odds: float,
    bet_market_prob: Optional[float],
    close_line: float,
    close_home_odds: float,
    close_away_odds: float,
    mu: float = 2.8,
) -> dict:
    """Compute CLV metrics for a single paper-trading log row.

    Returns dict with keys:
      closing_prob_bet_side, clv_move, clv_price, line_converted
    Never raises; returns all-None dict on any invalid closing/bet input.
    """
    empty = {
        'closing_prob_bet_side': None,
        'clv_move': None,
        'clv_price': None,
        'line_converted': None,
    }
    try:
        if not isinstance(bet_side, str):
            return empty
        side = bet_side.strip().lower()
        if side not in ('home', 'away'):
            return empty

        if (
            _is_bad_number(bet_line)
            or _is_bad_number(bet_odds)
            or _is_bad_number(close_line)
            or _is_bad_number(close_home_odds)
            or _is_bad_number(close_away_odds)
        ):
            return empty

        b_line = float(bet_line)
        b_odds = float(bet_odds)
        c_line = float(close_line)
        if b_odds <= 1.0:
            return empty

        q_close_home = novig_home(close_home_odds, close_away_odds)
        q_bet_home = convert_q_home(q_close_home, c_line, b_line, mu=mu)
        if q_bet_home is None:
            return empty

        line_converted = bool(abs(c_line - b_line) >= 1e-9)
        closing_prob_bet_side = q_bet_home if side == 'home' else (1.0 - q_bet_home)
        clv_price = b_odds * closing_prob_bet_side - 1.0

        clv_move = None
        if bet_market_prob is not None and str(bet_market_prob).strip() != '':
            if not _is_bad_number(bet_market_prob):
                bmp = float(bet_market_prob)
                if 0.0 < bmp < 1.0:
                    clv_move = closing_prob_bet_side - bmp

        return {
            'closing_prob_bet_side': closing_prob_bet_side,
            'clv_move': clv_move,
            'clv_price': clv_price,
            'line_converted': line_converted,
        }
    except Exception:
        return empty
