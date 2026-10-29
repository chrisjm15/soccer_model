"""STOP-DATE ANALYSIS for the live EPL AH rule (Cowork session 18, 2026-10-29). READ-ONLY.
Question: Chris bets real money on the live 1% rule. Session 17 found the model's information is early-season.
Where, by gameweek, does it stop? Gives a pre-committed stop rule for the rest of 2026-27.

DECISION RULE (written before the results were run):
  Stop GW = the first gameweek bucket G such that, for all EPL matches from G to season end (6 seasons, fit-free):
    (1) the move ~ signal slope has t < 2, AND
    (2) the live rule's OOS (2024-26) CLV at best-of-3 prices on bets from G onward has mean < 0.
  If the current gameweek (GW10, 2026-10-30) is already past the stop GW -> recommend stopping real-money stakes now
  and continuing paper logging only (the automation and checkpoint are unchanged either way).

  python scripts/stop_date_analysis.py      -> output/backtest_results/stop_date_report.txt
"""
import math, os, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
import advanced_research as ar

OUT = 'output/backtest_results/stop_date_report.txt'
BUCKETS = [(1, 4), (5, 7), (8, 10), (11, 13), (14, 16), (17, 19), (20, 25), (26, 31), (32, 38)]


def add_gw(m):
    """Gameweek proxy: 1 + max(games already played by home, by away) in that league-season, by date order."""
    m = m.sort_values(['league', 'season', 'date'], kind='stable').copy()
    gw = np.zeros(len(m), int)
    for (lg, s), idx in m.groupby(['league', 'season']).groups.items():
        cnt = {}
        for j, i in enumerate(idx):
            r = m.loc[i]
            g = max(cnt.get(r.home_team, 0), cnt.get(r.away_team, 0)) + 1
            gw[m.index.get_loc(i)] = g
            cnt[r.home_team] = cnt.get(r.home_team, 0) + 1
            cnt[r.away_team] = cnt.get(r.away_team, 0) + 1
    m['gw'] = gw
    return m


def clean_prices(d, ratio=1.3):
    """football-data 'Avg' AH prices > 1.3x Bet365 on the same side are data errors (e.g. 4.43 v 1.98, Man City v
    Leeds 2025-11-29). Found session 18: 2 such rows in the live-rule OOS set inflated CLV@best-of-3 by ~1.2pp.
    Drop that price (NaN) and recompute best-of-3. Same check for Pinnacle."""
    d = d.copy()
    for k in ('pin', 'avg'):
        bad = (d['p_' + k] / d.p_b365) > ratio
        d.loc[bad, 'p_' + k] = np.nan
        d['clv_' + k] = d['p_' + k] * d.close_prob_side - 1
    d['p_best3'] = d[['p_b365', 'p_pin', 'p_avg']].max(axis=1)
    d['clv_best3'] = d.p_best3 * d.close_prob_side - 1
    return d


def slope_line(name, x):
    x = x.dropna(subset=['move', 'signal'])
    if len(x) < 20:
        return f"  {name:<16}{len(x):>6}   too few", None
    r = ar.ols(x.move, x.signal)
    return f"  {name:<16}{len(x):>6}{r.params[1]:>+12.4f}{r.bse[1]:>9.4f}{r.tvalues[1]:>+7.2f}", r.tvalues[1]


def main():
    L = [f'  STOP-DATE ANALYSIS, LIVE EPL AH RULE  --  {date.today().isoformat()}',
         '  Decision rule in the script docstring (written before results). +/- = 1 SE. gw = gameweek proxy.']
    m = pd.read_csv(f'{ar.OUTDIR}/clv_edge_matches.csv',
                    usecols=['date', 'league', 'season', 'home_team', 'away_team', 'move', 'move_avg', 'signal'])
    m = add_gw(m)
    e = m[m.league == 'EPL']

    L += ['', '  S1. FIT-FREE move ~ signal, EPL 2020-26, by gameweek bucket (signal = logit(model) - logit(B365 pre))',
          f"  {'bucket':<16}{'n':>6}{'slope':>12}{'SE':>9}{'t':>7}"]
    for a, b in BUCKETS:
        L.append(slope_line(f'GW {a}-{b}', e[e.gw.between(a, b)])[0])
    L += ['', '  S1b. Same, cumulative from GW k to season end (the "rest of season" if you start at GW k)',
          f"  {'from':<16}{'n':>6}{'slope':>12}{'SE':>9}{'t':>7}"]
    t_from = {}
    for k in range(6, 21):
        s, t = slope_line(f'GW {k}+', e[e.gw >= k])
        L.append(s); t_from[k] = t
    L += ['', '  S1c. By calendar month (EPL, fit-free)', f"  {'month':<16}{'n':>6}{'slope':>12}{'SE':>9}{'t':>7}"]
    e2 = e.assign(month=pd.to_datetime(e.date).dt.month)
    for mo in (8, 9, 10, 11, 12, 1, 2, 3, 4, 5):
        L.append(slope_line(f'month {mo}', e2[e2.month == mo])[0])
    L.append('  EPL by season, GW 8-13 (the weeks we are in now):')
    L.append('   ' + '  '.join(f"{s_} {slope_line('', g)[0].split()[2] if len(g) > 20 else 'n/a'} (t {slope_line('', g)[1]:+.1f})"
                                for s_, g in e[e.gw.between(8, 13)].groupby('season')))

    # S2: live rule OOS (same construction as advanced_research A3)
    raw = ar.ah_frame()
    d = clean_prices(raw)
    nbad = int(((raw.p_avg / raw.p_b365) > 1.3).sum() + ((raw.p_pin / raw.p_b365) > 1.3).sum())
    ep = d[d.league == 'EPL'].copy()
    te = ep[ep.season.isin(ar.TEST)].copy()
    lo, hi = np.percentile(ep[ep.season.isin(ar.TRAIN)].market_prob_novig, [1, 99])
    te = te[te.market_prob_novig.between(lo, hi)].copy()
    te['edge'] = ar.edge_of(ar.fit_epl(ep[ep.season.isin(ar.TRAIN)]), te)
    te = te.merge(m[['date', 'league', 'home_team', 'away_team', 'gw']], on=['date', 'league', 'home_team', 'away_team'], how='left')
    f = te[te.edge.round(6) >= 0.01]
    L += ['', '  PRICE CLEANING: Pinnacle/Avg prices > 1.3x Bet365 dropped as data errors (17 prices, all leagues, 2020-26).',
          f'  Live rule OOS, all GWs: CLV@best3 {f.clv_best3.mean():+.2%} +/- {f.clv_best3.std()/math.sqrt(len(f)):.2%} '
          f'after cleaning (session 17 reported -0.29% +/- 1.03% before cleaning).',
          f'  Edge >= 2% subset: CLV@best3 {te[te.edge.round(6) >= 0.02].clv_best3.mean():+.2%} after cleaning (session 17: +0.94%).']
    L += ['', f'  S2. LIVE RULE OOS 2024-26 (EPL-only fit 2020-24, edge >= 1%, range guard). n = {len(f)} '
              f'(gw missing {f.gw.isna().sum()})', ar.HDR]
    for a, b in BUCKETS:
        L.append(ar.row(f'GW {a}-{b}', f[f.gw.between(a, b)]))
    L += ['', '  S2b. Live rule, cumulative from GW k (what is left if you keep betting from GW k)', ar.HDR]
    best_from = {}
    for k in range(6, 21):
        g = f[f.gw >= k]
        L.append(ar.row(f'GW {k}+', g)); best_from[k] = g.clv_best3.mean()
    L += ['', '  S2c. Live rule, edge >= 2% shadow subset, by phase', ar.HDR]
    f2 = te[te.edge.round(6) >= 0.02]
    for lab, (a, b) in (('GW 1-10', (1, 10)), ('GW 11-19', (11, 19)), ('GW 20-38', (20, 38))):
        L.append(ar.row(lab, f2[f2.gw.between(a, b)]))

    stop = next((k for k in range(6, 21) if t_from[k] is not None and t_from[k] < 2 and best_from[k] < 0), None)
    L += ['', '  VERDICT (pre-set rule)']
    if stop is None:
        L.append('  No stop GW in 6..20 satisfies both conditions.')
    else:
        L.append(f'  Stop GW = {stop}: from GW {stop} on, fit-free slope t {t_from[stop]:+.2f} (< 2) and live-rule '
                 f'CLV@best3 {best_from[stop]:+.2%} (< 0).')
        L.append('  Current gameweek: GW10 (Fri 2026-10-30 run).  ' +
                 ('Past the stop GW -> stop real-money stakes, keep paper logging.' if stop <= 10 else
                  f'Stop real-money stakes from GW {stop}; keep paper logging after that.'))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
