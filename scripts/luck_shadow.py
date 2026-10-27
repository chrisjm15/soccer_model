"""LUCK SHADOW TEST - pre-registered 2026-10-28 (Cowork session 17). Does NOT change the live model or log.

Hypothesis (from scripts/advanced_research.py section C, 2020-26 history): the market, even at the close, overrates
teams whose recent goals ran ahead of their xG ("lucky") and underrates the unlucky. Historical EPL: rule below
returned +8.0% +/- 3.1% at average AH prices (n 859, 6 seasons); the close's bias replicated on soft leagues
with a different xG source. The rule's threshold was chosen in-session, so it needs a prospective test.

FIXED RULE (do not tune mid-season):
  luck(team)  = EMA, alpha 0.10, of (goals for - xG for) minus EMA of (goals against - xG against), pre-match,
                over every Big-5 match in data/processed/all_merged.csv (state carries across seasons)
  luck_diff   = luck(home) - luck(away)
  shadow bet  = back the LESS lucky side on the logged EPL AH main line when |luck_diff| >= 0.40,
                at the logged best price at the Friday run (odds_ah_home_at_bet / odds_ah_away_at_bet)
COUNTS ONLY from prediction_date >= 2026-10-30 (GW10): GW9 rows were visible when the rule was written.
VERDICT at season end (~100+ shadow bets): mean clv_price > 0 AND ROI > 0 -> build it into the model for 2027-28
  (off-season); mean clv_price <= -1% -> drop. ROI SE will be ~ +/-10pp: CLV carries the decision.

Output: output/paper_trading/luck_shadow.csv (rebuilt every run; deterministic - luck only uses matches dated before
the fixture, so re-running never leaks results).  Run:  python scripts/luck_shadow.py
"""
import math, os, sys
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from model.clv import clv_for_row  # noqa: E402

ALPHA = 0.10
THRESH = 0.40
SEASON_START = '2026-08-01'
REGISTERED_FROM = '2026-10-30'
LOG = PROJECT / 'output' / 'paper_trading' / 'log_ah.csv'
MERGED = PROJECT / 'data' / 'processed' / 'all_merged.csv'
OUT = PROJECT / 'output' / 'paper_trading' / 'luck_shadow.csv'


def luck_before(history: pd.DataFrame, team_a: str, team_b: str, date: str, alpha: float = ALPHA):
    """Pre-match net luck of two teams using only matches dated strictly before `date`."""
    st = {}
    h = history[history['date'] < date]
    for r in h.itertuples(index=False):
        x = st.setdefault(r.home_team, [0.0, 0.0])
        y = st.setdefault(r.away_team, [0.0, 0.0])
        x[0] = alpha * (r.home_goals - r.home_xg) + (1 - alpha) * x[0]
        x[1] = alpha * (r.away_goals - r.away_xg) + (1 - alpha) * x[1]
        y[0] = alpha * (r.away_goals - r.away_xg) + (1 - alpha) * y[0]
        y[1] = alpha * (r.home_goals - r.home_xg) + (1 - alpha) * y[1]
    net = lambda t: (st[t][0] - st[t][1]) if t in st else 0.0
    return net(team_a), net(team_b)


def _f(x):
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def settle(hg, ag, ah_line, side, odds):
    from run import _calculate_ah
    return _calculate_ah(int(hg), int(ag), ah_line, side, odds, stake=1.0)


def build():
    hist = pd.read_csv(MERGED).dropna(subset=['home_xg', 'away_xg', 'home_goals', 'away_goals'])
    hist['date'] = pd.to_datetime(hist['date']).dt.strftime('%Y-%m-%d')
    hist = hist.sort_values('date', kind='stable')
    log = pd.read_csv(LOG)
    log = log[(log['prediction_date'].astype(str) >= SEASON_START) & (log['league'] == 'EPL')]
    rows = []
    for _, r in log.iterrows():
        lh, la = luck_before(hist, r.home_team, r.away_team, str(r.match_date))
        diff = lh - la
        side = 'home' if diff < 0 else 'away'
        odds = _f(r.odds_ah_home_at_bet) if side == 'home' else _f(r.odds_ah_away_at_bet)
        q = _f(r.market_prob_consensus)
        if q is not None and side != r.bet_side:
            q = 1 - q
        out = {'prediction_date': r.prediction_date, 'match_date': r.match_date, 'home_team': r.home_team,
               'away_team': r.away_team, 'ah_line': r.ah_line, 'luck_home': round(lh, 4), 'luck_away': round(la, 4),
               'luck_diff': round(diff, 4), 'shadow_side': side, 'shadow_flag': abs(diff) >= THRESH,
               'shadow_odds': odds, 'market_prob_side': q, 'model_bet_side': r.bet_side,
               'model_flag': str(r.bet_flag) == 'True', 'result': '', 'pnl_unit': '', 'clv_move': '', 'clv_price': ''}
        hg, ag = _f(r.actual_home_goals), _f(r.actual_away_goals)
        if hg is not None and ag is not None and odds:
            res, pnl = settle(hg, ag, r.ah_line, side, odds)
            out['result'], out['pnl_unit'] = res, pnl
        cl, ch, ca = _f(r.closing_line), _f(r.closing_home_odds), _f(r.closing_away_odds)
        if None not in (cl, ch, ca) and odds:
            c = clv_for_row(bet_side=side, bet_line=float(r.ah_line), bet_odds=odds, bet_market_prob=q,
                            close_line=cl, close_home_odds=ch, close_away_odds=ca)
            out['clv_move'] = '' if c['clv_move'] is None else round(c['clv_move'], 6)
            out['clv_price'] = '' if c['clv_price'] is None else round(c['clv_price'], 6)
        rows.append(out)
    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    return df


def report_lines(df):
    L = [f'  Rule: back the less lucky side when |luck_diff| >= {THRESH} (pre-registered 2026-10-28; verdict at season end).']
    if df.empty:
        return L + ['  No current-season EPL rows yet.']
    pre = df[df.shadow_flag & (df.prediction_date.astype(str) < REGISTERED_FROM)]
    if len(pre):
        L.append(f'  (GW9 and earlier, seen before registration - NOT counted: {len(pre)} bets, '
                 f"P/L {pd.to_numeric(pre.pnl_unit, errors='coerce').sum():+.2f} units)")
    f = df[df.shadow_flag & (df.prediction_date.astype(str) >= REGISTERED_FROM)]
    L.append(f'  Logged matches: {len(df)}   shadow bets: {len(f)}   overlap with model flags: {int((f.model_flag & (f.shadow_side == f.model_bet_side)).sum())}')
    num = lambda s: pd.to_numeric(s, errors='coerce').dropna()
    for name, col in (('clv_price', 'clv_price'), ('clv_move', 'clv_move'), ('P/L per unit', 'pnl_unit')):
        v = num(f[col])
        if len(v):
            se = v.std() / math.sqrt(len(v)) if len(v) > 1 else float('nan')
            L.append(f'  {name:<13} n={len(v):<3} mean {v.mean():+.2%}' + ('' if math.isnan(se) else f' (SE {se:.2%})'))
    for _, r in f.iterrows():
        team = r.home_team if r.shadow_side == 'home' else r.away_team
        line = float(r.ah_line) if r.shadow_side == 'home' else -float(r.ah_line)
        L.append(f"    {r.match_date}  {team} {line + 0.0:+.2f} @ {r.shadow_odds}  luck {r.luck_diff:+.2f}  "
                 f"{r.result or 'pending'}  CLV {r.clv_price if r.clv_price != '' else 'n/a'}")
    return L


if __name__ == '__main__':
    print('\n'.join(report_lines(build())))
