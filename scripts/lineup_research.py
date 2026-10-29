"""LINEUP RESEARCH (Cowork session 18, 2026-10-29). READ-ONLY. Needs data/raw/understat_lineups/EPL_lineups.csv
(scrapers/understat_lineups.py fetch). Backlog item 4: does team news explain the closing line, and does the close
price it correctly?

METRIC (fixed before any data was fetched):
  regulars(team, match) = players who STARTED >= 4 of the team's previous 5 league matches that season
                          (needs 5 prior matches, so GW 6+ only).
  missing(team, match)  = number of regulars NOT in today's starting XI.   gk_change = regular GK not starting.
  diff (home view)      = missing_away - missing_home   (> 0 = home side has the stronger XI relative to normal)
PRE-SET TESTS (EPL 2020-26, all matches with the metric; HC1 t-stats):
  L1 sanity  move (pre -> close, home no-vig prob, on the pre line) ~ diff:  PASS if slope > 0 and t >= 3.
             (Lineups come out ~1 h before kick-off; a market that reacts must show this.)
  L2 edge    home AH score on the pre line ~ logit(close_home) + diff (fractional logit):  PASS if |t(diff)| >= 2.
             Only L2 is an edge, and only for bets placed AFTER lineups at close-like prices.
  L3, L4 are exploratory (no pass rule): does the model signal survive controlling for lineups; live-rule OOS CLV
             for bets whose side has >= 2 more missing regulars than the opponent.
  python scripts/lineup_research.py [path_to_lineups.csv]   -> output/backtest_results/lineup_report.txt
"""
import math, os, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import glob
import numpy as np
import pandas as pd
import advanced_research as ar
from stop_date_analysis import clean_prices

LINEUPS = 'data/raw/understat_lineups/EPL_lineups.csv'
OUT = 'output/backtest_results/lineup_report.txt'


def ah_score_home(margin, line):
    """Home AH result as a score in [0, 1] (refund = 0.5, quarter lines split)."""
    def one(l):
        x = margin + l
        return 1.0 if x > 1e-9 else (0.5 if abs(x) <= 1e-9 else 0.0)
    if abs((abs(line) % 0.5) - 0.25) < 1e-9:
        return (one(line - 0.25) + one(line + 0.25)) / 2
    return one(line)


def team_metric(lu, matches):
    """lu: lineup rows. matches: match_id, date, season, home_team, away_team. Returns per (match_id, side)."""
    st = lu[lu.starter == 1]
    xi = st.groupby(['match_id', 'side']).player_id.apply(frozenset).to_dict()
    gk = st[st.position == 'GK'].groupby(['match_id', 'side']).player_id.first().to_dict()
    long = pd.concat([matches.assign(side='h', team=matches.home_team), matches.assign(side='a', team=matches.away_team)])
    long = long.sort_values(['season', 'team', 'date'], kind='stable')
    out = []
    for (season, team), g in long.groupby(['season', 'team'], sort=False):
        hist = []   # list of (xi, gk) for previous matches with lineups
        for r in g.itertuples(index=False):
            key = (r.match_id, r.side)
            today = xi.get(key)
            miss = gkc = np.nan
            if today is not None and len(hist) >= 5:
                last5 = hist[-5:]
                counts = {}
                for s_, _ in last5:
                    for p in s_:
                        counts[p] = counts.get(p, 0) + 1
                regs = {p for p, c in counts.items() if c >= 4}
                miss = len(regs - today)
                gks = [g_ for _, g_ in last5 if g_ is not None]
                reg_gk = max(set(gks), key=gks.count) if gks and gks.count(max(set(gks), key=gks.count)) >= 4 else None
                gkc = float(reg_gk is not None and gk.get(key) != reg_gk)
            out.append({'match_id': r.match_id, 'side': r.side, 'missing': miss, 'gk_change': gkc})
            if today is not None:
                hist.append((today, gk.get(key)))
    return pd.DataFrame(out)


def friday_known(lu, matches):
    """L5 (added AFTER L1-L4 were seen - exploratory): Friday-knowable absences. regulars = started >= 4 of the 5
    matches BEFORE the previous one; prevmiss = regulars not in the PREVIOUS match's XI (known before Friday)."""
    xi = lu[lu.starter == 1].groupby(['match_id', 'side']).player_id.apply(frozenset).to_dict()
    long = pd.concat([matches.assign(side='h', team=matches.home_team), matches.assign(side='a', team=matches.away_team)])
    long = long.sort_values(['season', 'team', 'date'], kind='stable')
    out = []
    for _, g in long.groupby(['season', 'team'], sort=False):
        hist = []
        for r in g.itertuples(index=False):
            today, pm = xi.get((r.match_id, r.side)), np.nan
            if today is not None and len(hist) >= 6:
                c = {}
                for x in hist[-6:-1]:
                    for p in x:
                        c[p] = c.get(p, 0) + 1
                pm = len({p for p, k in c.items() if k >= 4} - hist[-1])
            out.append({'match_id': r.match_id, 'side': r.side, 'prevmiss': pm})
            if today is not None:
                hist.append(today)
    w = pd.DataFrame(out).pivot(index='match_id', columns='side', values='prevmiss')
    return (w['a'] - w['h']).rename('pdiff').reset_index()


def main(path=LINEUPS):
    L = [f'  LINEUP RESEARCH (EPL)  --  {date.today().isoformat()}', '  Metric and pass rules: script docstring '
         '(fixed before the data was fetched). +/- = 1 SE.']
    lu = pd.read_csv(path)
    u = pd.concat([pd.read_csv(f) for f in sorted(glob.glob('data/raw/understat/EPL_20*.csv'))])
    u = u[u.match_id.isin(lu.match_id)]
    tm = team_metric(lu, u[['match_id', 'date', 'season', 'home_team', 'away_team']])
    w = tm.pivot(index='match_id', columns='side', values=['missing', 'gk_change'])
    w.columns = [f'{a}_{b}' for a, b in w.columns]
    u = u.merge(w.reset_index(), on='match_id', how='left')
    u['diff'] = u.missing_a - u.missing_h
    c = pd.read_csv(f'{ar.OUTDIR}/clv_edge_matches.csv')
    c = c[c.league == 'EPL'].merge(u[['date', 'home_team', 'away_team', 'match_id', 'missing_h', 'missing_a', 'gk_change_h',
                                      'gk_change_a', 'diff']], on=['date', 'home_team', 'away_team'], how='left')
    L.append(f'  Lineups for {lu.match_id.nunique()} matches; EPL rows {len(c)}; with metric (GW 6+) {c["diff"].notna().sum()}')
    x = c.dropna(subset=['diff', 'move', 'close_home']).copy()
    L += ['', '  Distribution of missing regulars per team-match: ' +
          ', '.join(f'{k}: {v:.0%}' for k, v in pd.concat([x.missing_h, x.missing_a]).clip(upper=4).value_counts(normalize=True).sort_index().items())
          + '  (4 = 4+)']

    r1 = ar.ols(x.move, x['diff'])
    p1 = r1.params[1] > 0 and r1.tvalues[1] >= 3
    L += ['', '  L1  move ~ diff (market reacts to lineups?)',
          f'      slope {r1.params[1]:+.4f} per missing regular (SE {r1.bse[1]:.4f}, t {r1.tvalues[1]:+.2f}), n {len(x)}  '
          f'-> {"PASS" if p1 else "FAIL"}']
    gkd = x.gk_change_a.fillna(0) - x.gk_change_h.fillna(0)
    rg = ar.ols(x.move, [x['diff'], gkd])
    L.append(f'      with GK change: diff {rg.params[1]:+.4f} (t {rg.tvalues[1]:+.2f}), gk {rg.params[2]:+.4f} (t {rg.tvalues[2]:+.2f})')

    x['score'] = [ah_score_home(h - a, l) for h, a, l in zip(x.home_goals, x.away_goals, x.ah_line)]
    r2 = ar.glm(x.score, {'lc': ar.logit(x.close_home), 'diff': x['diff']})
    p2 = abs(r2.tvalues.iloc[2]) >= 2
    L += ['', '  L2  home AH score ~ logit(close) + diff (does the close price lineups correctly?)',
          f'      diff {r2.params.iloc[2]:+.4f} (SE {r2.bse.iloc[2]:.4f}, t {r2.tvalues.iloc[2]:+.2f}); logit(close) '
          f'{r2.params.iloc[1]:+.3f} (t {r2.tvalues.iloc[1]:+.2f})  -> {"PASS" if p2 else "FAIL"}']
    big = x[x['diff'].abs() >= 2]
    L.append(f'      matches with |diff| >= 2: {len(big)} ({len(big)/len(x):.0%}); mean score of the side with the stronger '
             f'XI minus its closing prob: {np.mean(np.where(big["diff"] > 0, big.score - big.close_home, (1 - big.score) - (1 - big.close_home))):+.2%}')

    y = x.dropna(subset=['signal'])
    r3a, r3b = ar.ols(y.move, y.signal), ar.ols(y.move, [y.signal, y['diff']])
    L += ['', '  L3  (exploratory) move ~ model signal, without / with diff',
          f'      signal alone {r3a.params[1]:+.4f} (t {r3a.tvalues[1]:+.2f});  with diff: signal {r3b.params[1]:+.4f} '
          f'(t {r3b.tvalues[1]:+.2f}), diff {r3b.params[2]:+.4f} (t {r3b.tvalues[2]:+.2f})',
          f'      corr(signal, diff) {np.corrcoef(y.signal, y["diff"])[0, 1]:+.3f}']

    d = clean_prices(ar.ah_frame())
    ep = d[d.league == 'EPL'].copy()
    te = ep[ep.season.isin(ar.TEST)].copy()
    lo, hi = np.percentile(ep[ep.season.isin(ar.TRAIN)].market_prob_novig, [1, 99])
    te = te[te.market_prob_novig.between(lo, hi)].copy()
    te['edge'] = ar.edge_of(ar.fit_epl(ep[ep.season.isin(ar.TRAIN)]), te)
    f = te[te.edge.round(6) >= 0.01].merge(c[['date', 'home_team', 'away_team', 'diff']], on=['date', 'home_team', 'away_team'], how='left')
    f['adv'] = np.where(f.bet_side == 'home', -f['diff'], f['diff'])   # > 0 = bet side weaker than normal vs opponent
    L += ['', '  L4  (exploratory) live rule OOS 2024-26 by lineup on the bet side (adv = bet side missing - opp missing)', ar.HDR]
    L.append(ar.row('all with metric', f.dropna(subset=['adv'])))
    L.append(ar.row('adv >= 2 (bet side weakened)', f[f.adv >= 2]))
    L.append(ar.row('adv in -1..1', f[f.adv.between(-1, 1)]))
    L.append(ar.row('adv <= -2 (opponent weakened)', f[f.adv <= -2]))

    pk = friday_known(lu, u[['match_id', 'date', 'season', 'home_team', 'away_team']])
    pk = pk.merge(u[['match_id', 'date', 'home_team', 'away_team']], on='match_id')
    z = c.merge(pk[['date', 'home_team', 'away_team', 'pdiff']], on=['date', 'home_team', 'away_team']).dropna(subset=['pdiff', 'move', 'signal'])
    r5, r5b = ar.ols(z.move, z.pdiff), ar.ols(z.signal, z.pdiff)
    L += ['', '  L5  (EXPLORATORY, added after seeing L1-L4) Friday-knowable absences: regulars missing from the PREVIOUS XI',
          f'      move ~ pdiff {r5.params[1]:+.4f} (t {r5.tvalues[1]:+.2f}), n {len(z)}   [vs actual-XI diff +0.0072 above]',
          f'      model signal ~ pdiff {r5b.params[1]:+.4f} (t {r5b.tvalues[1]:+.2f})  (the model does not adjust for absences)']
    g5 = te[te.edge.round(6) >= 0.01].merge(z[['date', 'home_team', 'away_team', 'pdiff']], on=['date', 'home_team', 'away_team'])
    g5 = g5.assign(adv=np.where(g5.bet_side == 'home', -g5.pdiff, g5.pdiff))
    L.append(ar.HDR)
    for lab, m in (('live rule, Friday-known adv >= 2', g5.adv >= 2), ('live rule, adv in -1..1', g5.adv.between(-1, 1)),
                   ('live rule, adv <= -2', g5.adv <= -2)):
        L.append(ar.row(lab, g5[m]))

    L += ['', '  VERDICT', f'  L1 {"PASS" if p1 else "FAIL"}, L2 {"PASS" if p2 else "FAIL"}.  ' +
          ('Close mis-prices lineups -> an edge exists for bets placed after lineups (~1 h before kick-off).' if p2 else
           'Close prices lineups correctly -> no lineup edge at the close. ' +
           ('The market reacts to lineups (L1), so part of our Friday-to-close CLV loss is team news.' if p1 else ''))]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else LINEUPS)
