"""GOLD TESTS for scripts/luck_paper_big5.py (Cowork 2026-10-28). Hand arithmetic beside each assertion.
Run: python scripts/test_luck_paper.py"""
import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import luck_paper_big5 as lp

close = lambda a, b, t=1e-6: abs(a - b) < t

# --- name mapping (Odds API style -> understat canonical)
canon = {'Inter', 'Juventus', 'Atletico Madrid', 'RasenBallsport Leipzig', 'Borussia M.Gladbach', 'FC Cologne',
         'Paris Saint Germain', 'Athletic Club', 'Bayern Munich', 'Parma Calcio 1913'}
for api, want, lg in (('Inter Milan', 'Inter', 'Serie_A'), ('Juventus', 'Juventus', 'Serie_A'),
                      ('Atlético Madrid', 'Atletico Madrid', 'La_Liga'), ('RB Leipzig', 'RasenBallsport Leipzig', 'Bundesliga'),
                      ('Borussia Monchengladbach', 'Borussia M.Gladbach', 'Bundesliga'), ('1. FC Köln', 'FC Cologne', 'Bundesliga'),
                      ('Paris Saint-Germain', 'Paris Saint Germain', 'Ligue_1'), ('Athletic Bilbao', 'Athletic Club', 'La_Liga'),
                      ('Bayern Munich', 'Bayern Munich', 'Bundesliga'), ('Parma', 'Parma Calcio 1913', 'Serie_A')):
    got = lp.map_name(api, lg, canon)
    assert got == want, (api, got)
assert lp.map_name('Totally Unknown FC', 'Serie_A', canon) is None

# --- side pick: diff = -0.3 - 0.2 = -0.5 -> back home, flagged, home odds, home prob
assert lp.shadow_pick(-0.3, 0.2, 1.9, 2.0, 0.48) == (-0.5, 'home', True, 1.9, 0.48)
d, s, f, o, q = lp.shadow_pick(0.1, 0.0, 1.9, 2.0, 0.48)
assert close(d, 0.1) and s == 'away' and f is False and o == 2.0 and close(q, 0.52)

# --- luck state: A 2-0 B, xG 1.0-0.5. A att .1*(2-1)=.1, A def .1*(0-.5)=-.05 -> net .15; B net -.15
h = pd.DataFrame([dict(date='2026-01-01', home_team='A', away_team='B', home_goals=2, away_goals=0, home_xg=1.0, away_xg=0.5)])
assert lp.luck_state(h, '2026-01-01') == {}
st = lp.luck_state(h, '2026-01-02')
assert close(st['A'], 0.15) and close(st['B'], -0.15)

# --- settlement + CLV
row = {'ah_line': '-0.5', 'shadow_side': 'home', 'shadow_odds': '2.0', 'market_prob_side': '0.5'}
r = lp.settle_row(row, {'home_goals': 1, 'away_goals': 0, 'close_ah_line': -0.5,
                        'close_pin_ah_home': 1.9, 'close_pin_ah_away': 1.9})
assert r['result'] == 'Win' and close(r['pnl_unit'], 1.0) and r['closing_source'] == 'pinnacle'
assert close(r['clv_price'], 0.0) and close(r['clv_move'], 0.0)          # close prob .5: 2.0*.5-1 = 0
r = lp.settle_row(row, {'home_goals': 0, 'away_goals': 0, 'close_ah_line': -0.5, 'close_pin_ah_home': None,
                        'close_pin_ah_away': None, 'close_avg_ah_home': 1.8, 'close_avg_ah_away': 2.0})
# avg close: (1/1.8)/(1/1.8+1/2) = .555556/1.055556 = .526316 ; clv_price = 2*.526316-1 = .052632
assert r['result'] == 'Loss' and r['closing_source'] == 'avg' and close(r['clv_price'], 0.052632, 1e-5)
assert close(r['clv_move'], 0.026316, 1e-5)
assert lp.settle_row(row, {'home_goals': None, 'away_goals': None}) == {}

# --- log run with a mocked fetch: writes once, never duplicates (first sighting locks)
tmp = Path(tempfile.mkdtemp()) / 'log.csv'
lp.LOG = tmp
fake = lambda sport, lg: ([dict(date='2099-01-01', home_team='Inter Milan', away_team='Juventus', ah_line=-0.5,
                                odds_ah_home_best=1.9, odds_ah_away_best=2.0, best_home_book='x', best_away_book='y',
                                book_prices=[(1.9, 2.0)], n_bookmakers=1)] if lg == 'Serie_A' else [])
assert lp.cmd_log(fetch=fake) == 0 and lp.cmd_log(fetch=fake) == 0
log = pd.read_csv(tmp)
assert len(log) == 1 and log.home_team[0] == 'Inter' and log.away_team[0] == 'Juventus'
assert close(log.market_prob_home[0], (1 / 1.9) / (1 / 1.9 + 1 / 2.0), 1e-6)   # .512821
assert lp.cmd_log(fetch=fake, dry_run=True) == 0 and len(pd.read_csv(tmp)) == 1
print('ALL LUCK PAPER GOLD TESTS PASSED')
