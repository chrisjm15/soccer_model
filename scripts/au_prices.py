"""AU price tracker for flagged EPL Asian Handicap bets.

Why: the EPL edge is about one bookmaker margin, so whether the model makes money depends on the
prices Chris can actually get in Australia. This tool records the AU prices for each flagged bet
and compares them with the logged best (mostly offshore) price and the model break-even.

It never changes the paper-trading log. It only reads output/paper_trading/log_ah.csv and
reads/writes output/paper_trading/au_prices.csv.

Usage (from the project folder):
    python scripts/au_prices.py prepare   # add new flagged bets to the sheet (keeps what is there)
    python scripts/au_prices.py report    # print the comparison

Conventions (same as run.py predict):
    bet line   = ah_line for a home bet, -ah_line for an away bet (ah_line is home-perspective)
    calib_prob = calibrated expected SCORE of the bet (win 1, half-win 0.75, push 0.5, ...), not a win prob
    p_push     = push weight on the line (compute_ah_probs p_push), implied by the market no-vig prob
    EV         = calib_prob * price - 1 + (1 - price/2) * p_push     (exact money EV per unit staked)
    break-even = (1 - p_push) / (calib_prob - p_push/2)
    The predict printout uses 1/calib_prob, which is exact only on half lines (p_push = 0). On a 0.00
    line it is about 1.4% too low for an underdog (Sunderland GW9: 2.082 shown, 2.111 exact).
    Betfair    = back price after commission: 1 + (price - 1) * (1 - BETFAIR_COMMISSION)
"""
import math
import sys
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from model.markets import compute_ah_probs  # noqa: E402
from model.poisson import poisson_pmf  # noqa: E402

MU = 2.8  # total-goals assumption for the push solve, same as model/clv.py
LOG_PATH = PROJECT / 'output' / 'paper_trading' / 'log_ah.csv'
SHEET_PATH = PROJECT / 'output' / 'paper_trading' / 'au_prices.csv'

# Only bets from the current (calibrated) model. May-2026 rows are the old raw-edge model.
FIRST_PREDICTION_DATE = '2026-08-01'

# Betfair Australia Market Base Rate for sport (betfair.com.au help page, checked 2026-10-28).
# Change this if your account has a commission discount.
BETFAIR_COMMISSION = 0.06

# Columns Chris fills in. Prices are decimal odds for the market named in 'au_market'.
BOOK_COLUMNS = ['bet365_price', 'sportsbet_price', 'ladbrokes_price', 'tab_price',
                'betfair_back_price', 'other_price']
BOOK_LABELS = {
    'bet365_price': 'Bet365 AU', 'sportsbet_price': 'Sportsbet', 'ladbrokes_price': 'Ladbrokes',
    'tab_price': 'TAB', 'betfair_back_price': 'Betfair (after comm.)', 'other_price': 'Other',
}
SHEET_COLUMNS = (['key', 'match', 'bet', 'au_market', 'exact_at_corporates',
                  'logged_best_price', 'logged_best_book', 'break_even', 'calib_prob', 'p_push']
                 + BOOK_COLUMNS + ['other_book', 'notes'])


# ----------------------------------------------------------------------------------------------
# Pure functions (tested in scripts/test_au_prices.py)
# ----------------------------------------------------------------------------------------------

def bet_line(ah_line: float, bet_side: str) -> float:
    """Line from the bet team's point of view. ah_line is home-perspective."""
    line = float(ah_line)
    out = line if str(bet_side).lower() == 'home' else -line
    return out + 0.0  # turn -0.0 into 0.0


def au_market(line: float):
    """Which AU market gives exactly this Asian Handicap bet.

    Returns (description, exact) where exact=True means any AU corporate market of that name pays
    exactly the same as the AH bet, and exact=False means only a genuine 2-way Asian handicap
    (Bet365 AU or Betfair) matches it.
    """
    q = round(float(line) * 4) / 4
    if abs(q - float(line)) > 1e-9:
        raise ValueError(f'Not an Asian handicap line: {line}')
    if q == 0.0:
        return 'Draw No Bet', True
    if q == 0.5:
        return 'Double Chance (team or draw)', True
    if q == -0.5:
        return 'Head to Head: team to win', True
    frac = abs(q) % 1
    if frac == 0.5:
        return f'2-way handicap/line {q:+.1f} (same as AH)', True
    if q == 0.25:
        return 'AH +0.25 at Bet365. Split = half DNB + half Double Chance', False
    if q == -0.25:
        return 'AH -0.25 at Bet365. Split = half DNB + half H2H win', False
    return f'Asian handicap {q:+.2f} only (Bet365 AU / Betfair). NOT 3-way/European handicap', False


def betfair_effective(price: float, commission: float = BETFAIR_COMMISSION) -> float:
    """Back price after commission on net winnings."""
    p = float(price)
    if p <= 1.0:
        raise ValueError(f'Price must be > 1.0, got {p}')
    return 1.0 + (p - 1.0) * (1.0 - commission)


def ev(calib_prob: float, price: float, p_push: float = 0.0) -> float:
    """Exact money EV per unit staked, from the expected score and the push weight.

    Payoff = score * price - 1 for win/loss; a push (score 0.5) pays 0 instead of 0.5*price - 1, and
    half-win/half-loss differ by half that, so EV = s*o - 1 + (1 - o/2) * p_push.
    """
    o = float(price)
    return float(calib_prob) * o - 1.0 + (1.0 - o / 2.0) * float(p_push)


def break_even(calib_prob: float, p_push: float = 0.0) -> float:
    """Price where ev() = 0: (1 - p_push) / (calib_prob - p_push/2)."""
    return (1.0 - float(p_push)) / (float(calib_prob) - float(p_push) / 2.0)


def market_push_prob(q_side: float, ah_line: float, bet_side: str, mu: float = MU) -> float:
    """p_push on this line implied by the market's two-way no-vig prob of the bet side.

    Solves goal supremacy s (lam_h=(mu+s)/2, lam_a=(mu-s)/2) so the Poisson grid reproduces the no-vig
    home prob on ah_line (home perspective), then returns compute_ah_probs(...)['p_push'].
    """
    line = float(ah_line)
    if abs(line * 2 - round(line * 2)) > 1e-9 and abs(line * 4 - round(line * 4)) > 1e-9:
        raise ValueError(f'Not an AH line: {line}')
    if (abs(line) % 1) == 0.5:
        return 0.0
    q_home = float(q_side) if str(bet_side).lower() == 'home' else 1.0 - float(q_side)

    def probs(sup):
        lh, la = (mu + sup) / 2, (mu - sup) / 2
        g = [[poisson_pmf(h, lh) * poisson_pmf(a, la) for a in range(11)] for h in range(11)]
        return compute_ah_probs(g, line)

    lo, hi = -mu + 1e-6, mu - 1e-6
    for _ in range(60):
        mid = (lo + hi) / 2
        p = probs(mid)
        if p['p_home'] / (p['p_home'] + p['p_away']) < q_home:
            lo = mid
        else:
            hi = mid
    return probs((lo + hi) / 2)['p_push']


def gap_vs_best(price: float, best: float) -> float:
    """Relative price gap: price / best - 1 (negative = worse than the logged best)."""
    return float(price) / float(best) - 1.0


def _num(x):
    """Read a filled-in cell. Blank, text or <= 1.0 -> None."""
    if x is None:
        return None
    try:
        f = float(str(x).strip())
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or f <= 1.0:
        return None
    return f


def effective_prices(row: dict) -> dict:
    """{column: effective decimal price} for every book filled in on one sheet row."""
    out = {}
    for col in BOOK_COLUMNS:
        v = _num(row.get(col))
        if v is None:
            continue
        out[col] = betfair_effective(v) if col == 'betfair_back_price' else v
    return out


# ----------------------------------------------------------------------------------------------
# I/O
# ----------------------------------------------------------------------------------------------

def make_key(r) -> str:
    return f"{r['prediction_date']}|{r['home_team']}|{r['away_team']}"


def flagged_bets(log: pd.DataFrame) -> pd.DataFrame:
    flag = log['bet_flag'].astype(str).str.lower() == 'true'
    cur = log['prediction_date'].astype(str) >= FIRST_PREDICTION_DATE
    return log[flag & cur].copy()


def new_sheet_rows(log: pd.DataFrame, existing_keys: set) -> list:
    rows = []
    for _, r in flagged_bets(log).iterrows():
        key = make_key(r)
        if key in existing_keys:
            continue
        line = bet_line(r['ah_line'], r['bet_side'])
        team = r['home_team'] if str(r['bet_side']).lower() == 'home' else r['away_team']
        desc, exact = au_market(line)
        p = float(r['calib_prob'])
        pp = market_push_prob(float(r['market_prob_consensus']), r['ah_line'], r['bet_side'])
        row = {c: '' for c in SHEET_COLUMNS}
        row.update({
            'key': key,
            'match': f"{r['match_date']} {r['home_team']} v {r['away_team']}",
            'bet': f"{team} {line:+.2f}",
            'au_market': desc,
            'exact_at_corporates': 'yes' if exact else 'no',
            'logged_best_price': float(r['odds_ah']),
            'logged_best_book': r.get('best_book', ''),
            'break_even': round(break_even(p, pp), 3),
            'calib_prob': p,
            'p_push': round(pp, 4),
        })
        rows.append(row)
    return rows


def read_sheet() -> pd.DataFrame:
    if not SHEET_PATH.exists():
        return pd.DataFrame(columns=SHEET_COLUMNS)
    try:
        df = pd.read_csv(SHEET_PATH, dtype=str, keep_default_na=False, encoding='utf-8-sig')
    except UnicodeDecodeError:  # Excel 'CSV (Comma delimited)' saves as Windows-1252
        df = pd.read_csv(SHEET_PATH, dtype=str, keep_default_na=False, encoding='cp1252')
    for c in SHEET_COLUMNS:
        if c not in df.columns:
            df[c] = ''
    return df


def cmd_prepare() -> int:
    log = pd.read_csv(LOG_PATH, dtype={'bet_flag': str})
    sheet = read_sheet()
    rows = new_sheet_rows(log, set(sheet['key']))
    if rows:
        sheet = pd.concat([sheet, pd.DataFrame(rows, columns=SHEET_COLUMNS).astype(str)],
                          ignore_index=True)
    try:
        sheet.to_csv(SHEET_PATH, index=False, encoding='utf-8-sig')
    except PermissionError:
        print('ERROR: au_prices.csv is open in Excel. Close it, then run this again.')
        return 1
    print(f'{len(rows)} new flagged bet(s) added. Sheet has {len(sheet)} row(s): {SHEET_PATH}')
    if len(sheet):
        latest = max(k.split('|')[0] for k in sheet['key'])
        print()
        print(f'  THIS WEEK (predict run {latest}) - a price must beat the exact break-even to be +EV on the model numbers:')
        for _, r in sheet[sheet['key'].str.startswith(latest + '|')].iterrows():
            print(f"  {r['match']}: {r['bet']}")
            print(f"      look for: {r['au_market']}")
            print(f"      exact break-even {float(r['break_even']):.3f}   logged best {float(r['logged_best_price']):.2f}"
                  f" ({r['logged_best_book']})")
        print('  (The predict printout break-even is 1/calib_prob; on 0 / whole / quarter lines the')
        print('   exact figure above can differ by about 1-2%. Use this one.)')
    return 0


def report_lines(sheet: pd.DataFrame) -> list:
    lines = []
    filled = []
    for _, r in sheet.iterrows():
        prices = effective_prices(r.to_dict())
        if not prices:
            continue
        p = float(r['calib_prob'])
        try:
            pp = float(str(r.get('p_push', '')).strip() or 0.0)
        except ValueError:
            pp = 0.0
        best_logged = float(r['logged_best_price'])
        col, best_au = max(prices.items(), key=lambda kv: kv[1])
        filled.append({'gap': gap_vs_best(best_au, best_logged), 'ev_au': ev(p, best_au, pp),
                       'ev_logged': ev(p, best_logged, pp), 'b365': prices.get('bet365_price'),
                       'p': p, 'pp': pp, 'best_logged': best_logged})
        lines.append(f"  {r['match']}  |  {r['bet']}  |  break-even {float(r['break_even']):.3f}")
        lines.append(f"    logged best {best_logged:.3f} ({r['logged_best_book']}): EV {ev(p, best_logged, pp):+.1%}")
        for c, v in sorted(prices.items(), key=lambda kv: -kv[1]):
            tag = '  <- best AU' if c == col else ''
            lines.append(f"    {BOOK_LABELS[c]:<22} {v:.3f}  gap {gap_vs_best(v, best_logged):+.1%}  "
                         f"EV {ev(p, v, pp):+.1%}{tag}")
        if str(r.get('exact_at_corporates', '')).lower() == 'no':
            lines.append('    note: quarter/whole line - only a genuine Asian handicap price is comparable')
    if not filled:
        return ['  No AU prices entered yet. Run AU_PRICES.bat after the Friday predict run.']
    n = len(filled)
    mean = lambda k: sum(f[k] for f in filled) / n
    b365 = [f for f in filled if f['b365']]
    head = [f'  Bets with AU prices: {n}',
            f'  Mean gap, best AU vs logged best: {mean("gap"):+.1%}',
            f'  Mean EV at logged best price:     {mean("ev_logged"):+.1%}',
            f'  Mean EV at best AU price:         {mean("ev_au"):+.1%}',
            f'  Best AU price >= break-even:      {sum(f["ev_au"] >= 0 for f in filled)}/{n}']
    if b365:
        g = sum(gap_vs_best(f['b365'], f['best_logged']) for f in b365) / len(b365)
        e = sum(ev(f['p'], f['b365'], f['pp']) for f in b365) / len(b365)
        head.append(f'  Bet365 AU only ({len(b365)}): mean gap {g:+.1%}, mean EV {e:+.1%}')
    if n < 10:
        head.append(f'  (n={n}: too few to judge. Aim for 10+ bets before drawing a conclusion.)')
    return head + [''] + lines


def cmd_report() -> int:
    print('AU PRICE CHECK (flagged bets)')
    print(f'  Betfair commission assumed: {BETFAIR_COMMISSION:.0%}')
    for line in report_lines(read_sheet()):
        print(line)
    return 0


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'report'
    sys.exit({'prepare': cmd_prepare, 'report': cmd_report}.get(cmd, cmd_report)())
