"""Advanced edge research, part 2 (Cowork, session 17, 2026-10-28). READ-ONLY.
Needs data/raw/footballdata_full/ (DOWNLOAD_AND_TEST_1X2_OU.bat).
  python scripts/advanced_research2.py E   luck -> totals (O/U 2.5) at the close
  python scripts/advanced_research2.py F   luck -> 1X2 at the close (AU-available market)
  python scripts/advanced_research2.py G   promoted teams, first matches of the season (AH close)
  python scripts/advanced_research2.py H   late-season 'nothing to play for' teams (AH close)
Each writes output/backtest_results/advanced_<X>.txt.

PRE-SET PASS RULE (written before any of these results were seen, 2026-10-28):
  (1) the closing price is biased: regression of (result - closing no-vig prob) on the variable, controlling for
      logit(close), coefficient in the hypothesised direction with |t| >= 2 on pooled Big 5, AND
  (2) the betting rule (threshold fixed below, not tuned) has ROI at AVERAGE pre-closing prices > 0 with t >= 2
      on pooled Big 5 or on EPL.
Both are needed. Anything else = fail. Segment tables are exploratory.
"""
import glob, math, os, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
from advanced_research import ols, logit, ms, OUTDIR

FULL = 'data/raw/footballdata_full'
LEAGUE_FILES = ['EPL', 'La_Liga', 'Bundesliga', 'Serie_A', 'Ligue_1']


def full_frame():
    rows = []
    for lg in LEAGUE_FILES:
        for f in sorted(glob.glob(f'{FULL}/{lg}_*.csv')):
            x = pd.read_csv(f, encoding='latin-1').dropna(subset=['Date', 'HomeTeam', 'FTHG'])
            x['league'] = lg
            x['season'] = os.path.basename(f)[len(lg) + 1:-4]
            x['date'] = pd.to_datetime(x['Date'], dayfirst=True).dt.strftime('%Y-%m-%d')
            rows.append(x)
    return pd.concat(rows, ignore_index=True)


def luck_components(alpha=0.1):
    """Pre-match EMA (alpha 0.1, from 0) of goals-xG for (att) and goals-xG against (def), per team, all Big 5."""
    a = pd.read_csv('data/processed/all_merged.csv').dropna(subset=['home_xg', 'away_xg', 'home_goals', 'away_goals'])
    a['date'] = pd.to_datetime(a.date)
    a = a.sort_values('date', kind='stable').reset_index(drop=True)
    st, out = {}, []
    for r in a.itertuples(index=False):
        h = st.setdefault(r.home_team, [0.0, 0.0]); w = st.setdefault(r.away_team, [0.0, 0.0])
        out.append((h[0], h[1], w[0], w[1]))
        h[0] = alpha * (r.home_goals - r.home_xg) + (1 - alpha) * h[0]
        h[1] = alpha * (r.away_goals - r.away_xg) + (1 - alpha) * h[1]
        w[0] = alpha * (r.away_goals - r.away_xg) + (1 - alpha) * w[0]
        w[1] = alpha * (r.home_goals - r.home_xg) + (1 - alpha) * w[1]
    c = pd.DataFrame(out, columns=['h_att', 'h_def', 'a_att', 'a_def'])
    a = pd.concat([a, c], axis=1)
    a['date'] = a.date.dt.strftime('%Y-%m-%d')
    a['luck_diff'] = (a.h_att - a.h_def) - (a.a_att - a.a_def)
    a['luck_total'] = a.h_att + a.h_def + a.a_att + a.a_def   # >0: recent games of both teams had more goals than xG
    return a


def merged():
    a = luck_components()
    f = full_frame()
    d = a.merge(f, left_on=['date', 'odds_home', 'odds_away', 'home_goals', 'away_goals'],
                right_on=['date', 'B365H', 'B365A', 'FTHG', 'FTAG'], how='inner', suffixes=('', '_f'))
    d['season'] = d['season']
    return d


def nv2(a, b):
    ia, ib = 1 / a, 1 / b
    return ia / (ia + ib)


def nv3(h, d_, a):
    s = 1 / h + 1 / d_ + 1 / a
    return (1 / h) / s, (1 / d_) / s, (1 / a) / s


def header(title):
    return [f'  {title}  --  {date.today().isoformat()}',
            '  Pass rule (pre-set): close biased |t| >= 2 pooled AND rule ROI@Avg > 0 with t >= 2 (pooled or EPL).', '']


def roi_line(name, pnl_avg, pnl_fair, pnl_best=None, extra=''):
    s = f"  {name:<34}{len(pnl_avg.dropna()):>6}{ms(pnl_fair)}{ms(pnl_avg)}"
    if pnl_best is not None:
        s += ms(pnl_best)
    return s + extra


# ------------------------------------------------------------------------------------------------ E
def section_e():
    d = merged().dropna(subset=['AvgC>2.5', 'AvgC<2.5', 'Avg>2.5', 'Avg<2.5'])
    d['over'] = ((d.home_goals + d.away_goals) > 2.5).astype(float)
    cpin = nv2(d['PC>2.5'], d['PC<2.5'])
    d['cq'] = np.where(cpin.notna(), cpin, nv2(d['AvgC>2.5'], d['AvgC<2.5']))
    d['pq'] = nv2(d['Avg>2.5'], d['Avg<2.5'])
    d['move'] = nv2(d['AvgC>2.5'], d['AvgC<2.5']) - d.pq
    L = header('E. LUCK -> TOTALS: are O/U 2.5 closes inflated after goal-lucky runs?')
    sd = d.luck_total.std()
    k = sd   # fixed a priori: 1 SD of luck_total
    L.append(f'  Rows {len(d)}; luck_total SD {sd:.3f}; rule threshold k = 1 SD = {k:.3f}.  Hypothesis: coef < 0 (lucky -> overs overpriced).')
    L.append(f"  {'test':<52}{'group':<14}{'n':>6}{'coef':>9}{'t':>7}")
    groups = [('Big 5', d.league.notna()), ('EPL', d.league == 'EPL'), ('ex-EPL', d.league != 'EPL')]
    for g, m in groups:
        x = d[m]
        r = ols(x.over - x.cq, [x.luck_total, logit(x.cq)])
        L.append(f"  {'over - close ~ luck_total + logit(close)':<52}{g:<14}{len(x):>6}{r.params[1]:>+9.4f}{r.tvalues[1]:>+7.2f}")
        r = ols(x.move, [x.luck_total])
        L.append(f"  {'move(avg) ~ luck_total':<52}{g:<14}{len(x):>6}{r.params[1]:>+9.4f}{r.tvalues[1]:>+7.2f}")
        r = ols(x.over - x.cq, [x.h_att + x.a_att, x.h_def + x.a_def, logit(x.cq)])
        L.append(f"  {'  split: attack-luck term':<52}{g:<14}{len(x):>6}{r.params[1]:>+9.4f}{r.tvalues[1]:>+7.2f}")
        L.append(f"  {'  split: defence-luck term':<52}{g:<14}{len(x):>6}{r.params[2]:>+9.4f}{r.tvalues[2]:>+7.2f}")
    # rule: bet UNDER when luck_total >= k, OVER when <= -k
    L += ['', f"  Rule: UNDER when luck_total >= {k:.2f}, OVER when <= -{k:.2f}.  ROI flat.",
          f"  {'subset':<34}{'n':>6}{'ROI@fair close':>15}{'ROI@Avg pre':>15}{'ROI@Max pre':>15}"]
    for side in ('under', 'over', 'both'):
        mask = (d.luck_total >= k) if side == 'under' else (d.luck_total <= -k) if side == 'over' else (d.luck_total.abs() >= k)
        for g, m in groups:
            x = d[m & mask]
            und = x.luck_total > 0
            won = np.where(und, 1 - x.over, x.over)
            pf = won / np.where(und, 1 - x.cq, x.cq) - 1
            pa = won * np.where(und, x['Avg<2.5'], x['Avg>2.5']) - 1
            pm = won * np.where(und, x['Max<2.5'], x['Max>2.5']) - 1
            L.append(roi_line(f'{side} {g}', pd.Series(pa), pd.Series(pf), pd.Series(pm)))
    x = d[d.luck_total.abs() >= k]
    L.append('  By season (both sides, Big 5):')
    for s_, g in x.groupby('season'):
        und = g.luck_total > 0
        won = np.where(und, 1 - g.over, g.over)
        L.append(f"    {s_:<10}{len(g):>5}{ms(won * np.where(und, g['Avg<2.5'], g['Avg>2.5']) - 1)}")
    return L


# ------------------------------------------------------------------------------------------------ F
def section_f():
    d = merged().dropna(subset=['AvgCH', 'AvgCD', 'AvgCA', 'AvgH', 'AvgD', 'AvgA'])
    pin_ok = d[['PSCH', 'PSCD', 'PSCA']].notna().all(axis=1)
    ph, pd_, pa = nv3(d.PSCH, d.PSCD, d.PSCA)
    ah, ad, aa = nv3(d.AvgCH, d.AvgCD, d.AvgCA)
    d['ch'] = np.where(pin_ok, ph, ah); d['ca'] = np.where(pin_ok, pa, aa); d['cd'] = np.where(pin_ok, pd_, ad)
    d['yh'] = (d.home_goals > d.away_goals).astype(float)
    d['ya'] = (d.home_goals < d.away_goals).astype(float)
    d['yd'] = (d.home_goals == d.away_goals).astype(float)
    L = header('F. LUCK -> 1X2 at the close (market every AU book offers)')
    L.append('  Hypothesis: coef < 0 (lucky home side -> home win overpriced at close). Rule threshold |luck_diff| >= 0.4 (as AH shadow).')
    L.append(f"  {'test':<52}{'group':<14}{'n':>6}{'coef':>9}{'t':>7}")
    groups = [('Big 5', d.league.notna()), ('EPL', d.league == 'EPL'), ('ex-EPL', d.league != 'EPL')]
    for g, m in groups:
        x = d[m]
        r = ols(x.yh - x.ch, [x.luck_diff, logit(x.ch)])
        L.append(f"  {'home win - close ~ luck_diff + logit(close)':<52}{g:<14}{len(x):>6}{r.params[1]:>+9.4f}{r.tvalues[1]:>+7.2f}")
        r = ols(x.ya - x.ca, [-x.luck_diff, logit(x.ca)])
        L.append(f"  {'away win - close ~ (-luck_diff) + logit(close)':<52}{g:<14}{len(x):>6}{r.params[1]:>+9.4f}{r.tvalues[1]:>+7.2f}")
        r = ols(x.yd - x.cd, [x.luck_diff.abs(), logit(x.cd)])
        L.append(f"  {'draw - close ~ |luck_diff| + logit(close)':<52}{g:<14}{len(x):>6}{r.params[1]:>+9.4f}{r.tvalues[1]:>+7.2f}")
    L += ['', '  Rules at |luck_diff| >= 0.4: back the less lucky side to WIN; and Draw No Bet built from 1X2',
          '  (DNB price = (1 - 1/draw price) x win price, the standard 1X2->DNB conversion; fair = close no-vig).',
          f"  {'subset':<34}{'n':>6}{'ROI@fair close':>15}{'ROI@Avg pre':>15}{'ROI@Max pre':>15}"]
    sel = d[d.luck_diff.abs() >= 0.4].copy()
    home = sel.luck_diff < 0
    won = np.where(home, sel.yh, sel.ya)
    cpw = np.where(home, sel.ch, sel.ca)
    sel['w_fair'] = won / cpw - 1
    sel['w_avg'] = won * np.where(home, sel.AvgH, sel.AvgA) - 1
    sel['w_max'] = won * np.where(home, sel.MaxH, sel.MaxA) - 1
    # DNB: stake returned on draw
    dnb = lambda w, dr: (1 - 1 / dr) * w
    fair_dnb = (sel.ch + sel.ca) / cpw
    sel['d_fair'] = np.where(sel.yd == 1, 0.0, won * fair_dnb - 1)
    sel['d_avg'] = np.where(sel.yd == 1, 0.0, won * dnb(np.where(home, sel.AvgH, sel.AvgA), sel.AvgD) - 1)
    sel['d_max'] = np.where(sel.yd == 1, 0.0, won * dnb(np.where(home, sel.MaxH, sel.MaxA), sel.MaxD) - 1)
    for g, m in [('Big 5', sel.league.notna()), ('EPL', sel.league == 'EPL'), ('ex-EPL', sel.league != 'EPL')]:
        x = sel[m]
        L.append(roi_line(f'WIN  {g}', x.w_avg, x.w_fair, x.w_max))
        L.append(roi_line(f'DNB  {g}', x.d_avg, x.d_fair, x.d_max))
    L.append('  DNB by season (EPL):')
    for s_, x in sel[sel.league == 'EPL'].groupby('season'):
        L.append(f"    {s_:<10}{len(x):>5}{ms(x.d_fair)}{ms(x.d_avg)}")
    return L


# ------------------------------------------------------------------------------------------------ G / H helpers
def ah_base():
    from run import _calculate_ah
    cols = ['date', 'league', 'season', 'home_team', 'away_team', 'ah_line', 'close_home', 'pre_home', 'odds_ah_home',
            'odds_ah_away', 'avg_ah_home', 'avg_ah_away', 'pin_ah_home', 'pin_ah_away', 'home_goals', 'away_goals']
    m = pd.read_csv(f'{OUTDIR}/clv_edge_matches.csv', usecols=cols).dropna(subset=['close_home', 'ah_line'])
    sc = {'Win': 1, 'Half Win': .75, 'Push': .5, 'Half Loss': .25, 'Loss': 0}
    m['h_score'] = [sc[_calculate_ah(int(h), int(a), l, 'home', 2.0, 1)[0]] for h, a, l in zip(m.home_goals, m.away_goals, m.ah_line)]
    return m.reset_index(drop=True)


def ah_rule(m, back_home, name):
    """ROI of backing home (back_home True) / away on the AH main line at fair close, avg, B365, Pinnacle."""
    from run import _calculate_ah
    out = {}
    cp = np.where(back_home, m.close_home, 1 - m.close_home)
    for k, (ph, pa) in {'fair': (None, None), 'avg': ('avg_ah_home', 'avg_ah_away'), 'b365': ('odds_ah_home', 'odds_ah_away'),
                        'pin': ('pin_ah_home', 'pin_ah_away')}.items():
        price = 1 / cp if k == 'fair' else np.where(back_home, m[ph], m[pa])
        out[k] = pd.Series([np.nan if not (o > 1) else _calculate_ah(int(h), int(a), l, 'home' if bh else 'away', o, 1)[1]
                            for h, a, l, bh, o in zip(m.home_goals, m.away_goals, m.ah_line, back_home, price)])
    return f"  {name:<40}{len(m):>6}{ms(out['fair'])}{ms(out['avg'])}{ms(out['b365'])}{ms(out['pin'])}"


RULE_HDR = f"  {'rule':<40}{'n':>6}{'ROI@fair close':>15}{'ROI@Avg':>15}{'ROI@B365':>15}{'ROI@Pinnacle':>15}"


# ------------------------------------------------------------------------------------------------ G
def section_g():
    m = ah_base()
    a = pd.read_csv('data/processed/all_merged.csv')
    teams = a.groupby(['league', 'season']).apply(lambda g: set(g.home_team) | set(g.away_team)).to_dict()
    seasons = sorted(a.season.unique())
    prev = {s: seasons[i - 1] for i, s in enumerate(seasons) if i > 0}
    def promoted(lg, s, t):
        p = prev.get(s)
        return None if p is None or (lg, p) not in teams else t not in teams[(lg, p)]
    m = m.sort_values('date', kind='stable')
    cnt = {}
    nh, na = [], []
    for r in m.itertuples(index=False):
        for t, lst in ((r.home_team, nh), (r.away_team, na)):
            k = (r.league, r.season, t); cnt[k] = cnt.get(k, 0) + 1; lst.append(cnt[k])
    m['n_home'], m['n_away'] = nh, na
    m['prom_h'] = [promoted(l, s, t) for l, s, t in zip(m.league, m.season, m.home_team)]
    m['prom_a'] = [promoted(l, s, t) for l, s, t in zip(m.league, m.season, m.away_team)]
    m = m[m.prom_h.notna() & m.prom_a.notna()].copy()
    L = header('G. PROMOTED TEAMS: does the market overrate them early in the season? (AH main line, close)')
    L.append('  Hypothesis (pre-set): promoted team underperforms the close in its first 10 matches -> bet AGAINST it.')
    L.append(f'  Rows {len(m)} (2021-22..2025-26; 2020-21 has no previous season in the data).')
    L.append(f"  {'test':<56}{'group':<10}{'n':>6}{'coef':>9}{'t':>7}")
    for N in (10, 19):
        m['ph'] = ((m.prom_h == True) & (m.n_home <= N)).astype(float)
        m['pa'] = ((m.prom_a == True) & (m.n_away <= N)).astype(float)
        for g, mk in (('Big 5', m.league.notna()), ('EPL', m.league == 'EPL'), ('ex-EPL', m.league != 'EPL')):
            x = m[mk]
            r = ols(x.h_score - x.close_home, [x.ph - x.pa, logit(x.close_home)])
            L.append(f"  {f'result - close ~ promoted(home - away), first {N}':<56}{g:<10}{len(x):>6}{r.params[1]:>+9.4f}{r.tvalues[1]:>+7.2f}")
    m['ph'] = ((m.prom_h == True) & (m.n_home <= 10)).astype(float)
    m['pa'] = ((m.prom_a == True) & (m.n_away <= 10)).astype(float)
    L += ['', RULE_HDR]
    for g, mk in (('Big 5', m.league.notna()), ('EPL', m.league == 'EPL'), ('ex-EPL', m.league != 'EPL')):
        x = m[mk & ((m.ph + m.pa) == 1)].reset_index(drop=True)
        L.append(ah_rule(x, (x.pa == 1).values, f'against promoted, first 10, {g}'))
    x = m[(m.prom_h == True) | (m.prom_a == True)]
    x = x[(x.prom_h != x.prom_a)].reset_index(drop=True)
    L.append(ah_rule(x, (x.prom_a == True).values, 'against promoted, whole season, Big 5'))
    return L


# ------------------------------------------------------------------------------------------------ H
def section_h():
    a = pd.read_csv('data/processed/all_merged.csv').dropna(subset=['home_goals', 'away_goals'])
    a['date'] = pd.to_datetime(a.date); a = a.sort_values('date', kind='stable')
    dead_h, dead_a = [], []
    for (lg, s), g in a.groupby(['league', 'season'], sort=False):
        teams = sorted(set(g.home_team) | set(g.away_team)); n = len(teams); total = 2 * (n - 1)
        pts = {t: 0 for t in teams}; pl = {t: 0 for t in teams}
        for r in g.itertuples():
            res = []
            for t in (r.home_team, r.away_team):
                rem = total - pl[t]
                table = sorted(pts.values(), reverse=True)
                europe = table[5]            # 6th place points
                releg = table[n - 3]         # points of the first relegation place (n-2 th)
                safe = pts[t] - releg > 3 * rem
                no_europe = europe - pts[t] > 3 * rem
                res.append(bool(rem <= 8 and safe and no_europe))
            dead_h.append((r.Index, res[0])); dead_a.append((r.Index, res[1]))
            hg, ag = r.home_goals, r.away_goals
            pts[r.home_team] += 3 if hg > ag else 1 if hg == ag else 0
            pts[r.away_team] += 3 if ag > hg else 1 if hg == ag else 0
            pl[r.home_team] += 1; pl[r.away_team] += 1
    a['dead_h'] = pd.Series(dict(dead_h)); a['dead_a'] = pd.Series(dict(dead_a))
    a['date'] = a.date.dt.strftime('%Y-%m-%d')
    m = ah_base().merge(a[['date', 'league', 'home_team', 'away_team', 'dead_h', 'dead_a']],
                        on=['date', 'league', 'home_team', 'away_team'], how='inner')
    m['dh'] = m.dead_h.astype(float); m['da'] = m.dead_a.astype(float)
    L = header("H. LATE SEASON: teams with nothing to play for (AH main line, close)")
    L.append("  'Dead' = last 8 matches, cannot drop to the relegation zone and cannot reach 6th (3 pts x matches left).")
    L.append("  Hypothesis (pre-set): dead team underperforms the close -> bet AGAINST it when the opponent is not dead.")
    L.append(f"  Rows {len(m)}; dead-team appearances {int(m.dh.sum() + m.da.sum())}")
    L.append(f"  {'test':<56}{'group':<10}{'n':>6}{'coef':>9}{'t':>7}")
    for g, mk in (('Big 5', m.league.notna()), ('EPL', m.league == 'EPL'), ('ex-EPL', m.league != 'EPL')):
        x = m[mk]
        r = ols(x.h_score - x.close_home, [x.dh - x.da, logit(x.close_home)])
        L.append(f"  {'result - close ~ dead(home - away)':<56}{g:<10}{len(x):>6}{r.params[1]:>+9.4f}{r.tvalues[1]:>+7.2f}")
    L += ['', RULE_HDR]
    for g, mk in (('Big 5', m.league.notna()), ('EPL', m.league == 'EPL'), ('ex-EPL', m.league != 'EPL')):
        x = m[mk & ((m.dh + m.da) == 1)].reset_index(drop=True)
        L.append(ah_rule(x, (x.da == 1).values, f'against dead team, {g}'))
    return L


# ------------------------------------------------------------------------------------------------ J
def section_j():
    """Execution venues for the luck AH rule (the only survivor): does it pay at Max / Betfair Exchange after AU commission?"""
    from run import _calculate_ah
    d = merged().dropna(subset=['AHh', 'AvgAHH', 'AvgAHA'])
    c = pd.read_csv(f'{OUTDIR}/clv_edge_matches.csv', usecols=['date', 'league', 'home_team', 'away_team', 'close_home'])
    d = d.merge(c, on=['date', 'league', 'home_team', 'away_team'], how='inner').dropna(subset=['close_home'])
    d = d[d.luck_diff.abs() >= 0.4].reset_index(drop=True)
    home = (d.luck_diff < 0).values
    L = header('J. LUCK AH RULE (|luck_diff| >= 0.4, back the less lucky side, AHh line) BY EXECUTION VENUE')
    L.append('  Betfair Exchange (BFE) = UK exchange back price at football-data collection time; AU commission 6% on net wins.')
    L.append(f"  {'venue':<26}" + ''.join(f"{g:>22}" for g in ('Big 5', 'EPL', 'ex-EPL')))
    avg_side = np.where(home, d.AvgAHH, d.AvgAHA)
    def pnl(ph, pa, comm=0.0, cap=None):
        price = np.where(home, d[ph], d[pa]).astype(float)
        if cap is not None:   # drop quotes implausibly far above the market average (stale / illiquid)
            price = np.where(price / avg_side > cap, np.nan, price)
        out = []
        for h, a, l, bh, o in zip(d.home_goals, d.away_goals, d.AHh, home, price):
            if not (o > 1):
                out.append(np.nan); continue
            v = _calculate_ah(int(h), int(a), l, 'home' if bh else 'away', o, 1)[1]
            out.append(v * (1 - comm) if v > 0 else v)
        return pd.Series(out)
    venues = [('Average', 'AvgAHH', 'AvgAHA', 0), ('Bet365 (intl)', 'B365AHH', 'B365AHA', 0),
              ('Pinnacle', 'PAHH', 'PAHA', 0), ('Max (best quoted)', 'MaxAHH', 'MaxAHA', 0),
              ('Betfair Ex gross', 'BFEAHH', 'BFEAHA', 0), ('Betfair Ex net 6% (AU)', 'BFEAHH', 'BFEAHA', 0.06)]
    for ph, pa, nm in (('MaxAHH', 'MaxAHA', 'Max'), ('BFEAHH', 'BFEAHA', 'Betfair Ex'), ('PAHH', 'PAHA', 'Pinnacle')):
        r = pd.Series(np.where(home, d[ph], d[pa]) / avg_side).dropna()
        L.append(f"  price / Avg ratio, {nm:<10}: median {r.median():.3f}  p95 {r.quantile(.95):.3f}  share > 1.10: {(r > 1.10).mean():.1%}")
    venues += [('Max, quotes <= 1.08 x Avg', 'MaxAHH', 'MaxAHA', 0, 1.08), ('Betfair net 6%, <= 1.08 x Avg', 'BFEAHH', 'BFEAHA', 0.06, 1.08)]
    for vv in venues:
        name, ph, pa, cm = vv[:4]
        cap = vv[4] if len(vv) > 4 else None
        if ph not in d.columns:
            continue
        v = pnl(ph, pa, cm, cap)
        if name.startswith('Betfair net 6%, <='):
            vavg = pnl('AvgAHH', 'AvgAHA')
            sub = v.notna().values
            L.append(f"  {'  same rows at Average':<26}" + ''.join(f"{ms(vavg[sub & mk.values]):>22}"
                     for mk in (d.league.notna(), d.league == 'EPL', d.league != 'EPL')))
            L.append(f"  {'  BFE seasons':<26}{str(sorted(d.season[sub].unique()))}")
        L.append(f"  {name:<26}" + ''.join(f"{ms(v[mk.values]) + ' n' + str(int(v[mk.values].notna().sum())):>22}"
                                         for mk in (d.league.notna(), d.league == 'EPL', d.league != 'EPL')))
    return L


SECTIONS = {'E': section_e, 'F': section_f, 'G': section_g, 'H': section_h, 'J': section_j}

if __name__ == '__main__':
    for key in (sys.argv[1:] or list(SECTIONS)):
        out = SECTIONS[key]()
        open(f'{OUTDIR}/advanced_{key}.txt', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
        print('\n'.join(out))
