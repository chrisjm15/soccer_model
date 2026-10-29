"""Advanced edge research, session 17 (Cowork, 2026-10-28). READ-ONLY. Sections run independently:
  python scripts/advanced_research.py A     robustness of the live EPL AH rule
  python scripts/advanced_research.py B     model-free value rules (book price vs Pinnacle no-vig fair), AH, Big 5
  python scripts/advanced_research.py C     luck signal: goals-minus-xG divergence vs market movement
  python scripts/advanced_research.py D     BTTS via market-implied Poisson
Each section writes output/backtest_results/advanced_<X>.txt
Conventions as scripts/live_rule_oos_check.py: move = closing no-vig prob of the bet side (Pinnacle close, fallback
avg, converted onto the pre line) - pre no-vig prob; CLV@X = price X * closing prob - 1. +/- = 1 SE.
Segment tables are exploratory: with many cuts, expect ~1 in 20 to look 'significant' by chance.
"""
import math, os, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
import statsmodels.api as sm

TRAIN = ['2020-21', '2021-22', '2022-23', '2023-24']
TEST = ['2024-25', '2025-26']
CLIP = (0.01, 0.99)
OUTDIR = 'output/backtest_results'


def logit(p):
    p = np.clip(np.asarray(p, float), *CLIP)
    return np.log(p / (1 - p))


def sig(z):
    return 1 / (1 + np.exp(-z))


def glm(y, cols):
    X = sm.add_constant(pd.DataFrame(cols).reset_index(drop=True), has_constant='add')
    return sm.GLM(np.asarray(y, float), X, family=sm.families.Binomial()).fit(cov_type='HC1')


def ols(y, x):
    X = sm.add_constant(np.column_stack([np.asarray(v, float) for v in x]) if isinstance(x, list) else np.asarray(x, float))
    return sm.OLS(np.asarray(y, float), X).fit(cov_type='HC1')


def ms(v):
    v = pd.Series(np.asarray(v, float)).dropna()
    if len(v) < 2:
        return f"{'n/a':>15}"
    return f"{v.mean():+.2%}+/-{v.std()/math.sqrt(len(v)):.2%}".rjust(15)


def ah_frame():
    """EPL+Big5 AH rows: calibration_matches (model side, actual score) + clv_edge_matches (prices, closes)."""
    cal = pd.read_csv(f'{OUTDIR}/calibration_matches.csv')
    keep = ['date', 'home_team', 'away_team', 'close_prob_side', 'move_side', 'pin_ah_home', 'pin_ah_away',
            'avg_ah_home', 'avg_ah_away', 'odds_ah_home', 'odds_ah_away', 'close_home', 'pre_home',
            'pre_home_pin', 'pre_home_avg', 'close_home_pin', 'close_home_avg', 'close_ah_line']
    clv = pd.read_csv(f'{OUTDIR}/clv_edge_matches.csv', usecols=keep + ['league'])
    d = cal.merge(clv, on=['date', 'league', 'home_team', 'away_team'], how='left')
    home = d.bet_side == 'home'
    d['p_b365'] = d.market_odds
    d['p_pin'] = np.where(home, d.pin_ah_home, d.pin_ah_away)
    d['p_avg'] = np.where(home, d.avg_ah_home, d.avg_ah_away)
    for k in ('pin', 'avg'):   # session 18: drop football-data price errors (> 1.3x Bet365)
        d.loc[d['p_' + k] / d.p_b365 > 1.3, 'p_' + k] = np.nan
    d['p_best3'] = d[['p_b365', 'p_pin', 'p_avg']].max(axis=1)
    for k in ('b365', 'pin', 'avg', 'best3'):
        d['clv_' + k] = d['p_' + k] * d.close_prob_side - 1
    frac = (d.ah_line.abs() % 1).round(2)
    d['ltype'] = np.where(frac == 0.5, 'half', np.where(frac == 0.0, 'whole/zero', 'quarter'))
    d['month'] = pd.to_datetime(d.date).dt.month
    return d


def fit_epl(tr):
    return glm(tr.actual_score, {'a': logit(tr.market_prob_novig), 'b': logit(tr.model_prob)})


def edge_of(r, x):
    X = sm.add_constant(pd.DataFrame({'a': logit(x.market_prob_novig), 'b': logit(x.model_prob)}), has_constant='add')
    return np.asarray(r.predict(X)) - x.market_prob_novig.values


def row(name, f):
    return (f"  {name:<34}{len(f):>5}{ms(f.move_side)}{ms(f.clv_pin)}{ms(f.clv_best3)}"
            f"{f.pnl_flat10.sum()/10/max(len(f),1):>+8.1%}")


HDR = f"  {'subset':<34}{'n':>5}{'move':>15}{'CLV@Pinnacle':>15}{'CLV@best of 3':>15}{'ROI':>8}"


# ------------------------------------------------------------------------------------------------ A
def section_a():
    L = [f'  A. ROBUSTNESS OF THE LIVE EPL AH RULE  --  {date.today().isoformat()}']
    d = ah_frame()
    e = d[d.league == 'EPL'].copy()
    L += ['', '  A1. Is the model term driven by the 2020-21 no-crowd season?']
    for name, seasons in (('2020-26 (live config)', TRAIN + TEST), ('2021-26 (drop 2020-21)', TRAIN[1:] + TEST),
                          ('2020-21 only', ['2020-21']), ('train 2020-24', TRAIN), ('train 2021-24', TRAIN[1:])):
        x = e[e.season.isin(seasons)]
        r = fit_epl(x)
        L.append(f"  {name:<26} n {len(x):>5}  b_market {r.params.iloc[1]:+.3f}  b_model {r.params.iloc[2]:+.3f} "
                 f"(SE {r.bse.iloc[2]:.3f}, t {r.tvalues.iloc[2]:+.2f})  intercept {r.params.iloc[0]:+.3f}")
    # home win share by season (AH model side home share & actual home AH score)
    L.append('  Home-side AH score by season (mean actual score when betting home on the main line):')
    hs = e.assign(hscore=np.where(e.bet_side == 'home', e.actual_score, 1 - e.actual_score)).groupby('season').hscore.mean()
    L.append('   ' + '  '.join(f'{k} {v:.3f}' for k, v in hs.items()))

    te = e[e.season.isin(TEST)].copy()
    lo, hi = np.percentile(e[e.season.isin(TRAIN)].market_prob_novig, [1, 99])
    te = te[te.market_prob_novig.between(lo, hi)].copy()
    for name, seasons in (('train 2020-24 (as live)', TRAIN), ('train 2021-24 (no 2020-21)', TRAIN[1:])):
        te['edge_' + name[:11]] = edge_of(fit_epl(e[e.season.isin(seasons)]), te)
    L += ['', '  A2. OOS live rule (edge >= 1%) with and without 2020-21 in training', HDR]
    for c in [c for c in te.columns if c.startswith('edge_')]:
        for th in (0.01, 0.02):
            L.append(row(f'{c[5:]} >= {th:.0%}', te[te[c].round(6) >= th]))

    te['edge'] = te['edge_train 2020-']
    f = te[te.edge.round(6) >= 0.01]
    L += ['', '  A3. Segments of the live rule (train 2020-24, edge >= 1%, OOS 2024-26). EXPLORATORY.', HDR]
    L.append(row('all', f))
    for col, lab in (('ltype', 'line'), ('bet_side', 'side')):
        for k, g in f.groupby(col):
            L.append(row(f'{lab}={k}', g))
    L.append(row('bet side underdog (q < 0.5)', f[f.market_prob_novig < 0.5]))
    L.append(row('bet side favourite (q >= 0.5)', f[f.market_prob_novig >= 0.5]))
    for lab, months in (('Aug-Oct', [8, 9, 10]), ('Nov-Jan', [11, 12, 1]), ('Feb-May', [2, 3, 4, 5])):
        L.append(row(f'months {lab}', f[f.month.isin(months)]))
    L.append(row('|line| <= 0.5', f[f.ah_line.abs() <= 0.5]))
    L.append(row('|line| >= 0.75', f[f.ah_line.abs() >= 0.75]))
    L.append(row('edge >= 2%, underdog', te[(te.edge >= 0.02) & (te.market_prob_novig < 0.5)]))
    L.append(row('edge >= 2%, favourite', te[(te.edge >= 0.02) & (te.market_prob_novig >= 0.5)]))

    # A4: fit-free check of the seasonal pattern on ALL matches, all seasons (much larger n)
    m = pd.read_csv(f'{OUTDIR}/clv_edge_matches.csv', usecols=['date', 'league', 'season', 'move', 'move_avg', 'move_pin', 'signal'])
    m['month'] = pd.to_datetime(m.date).dt.month
    m['phase'] = np.select([m.month.isin([8, 9, 10]), m.month.isin([11, 12, 1])], ['Aug-Oct', 'Nov-Jan'], 'Feb-May')
    L += ['', '  A4. FIT-FREE move ~ signal (home perspective, all matches, 2020-26) by phase of season',
          '      (session 16 H1 definition: signal = logit(model_home) - logit(B365 pre); move to Pinnacle/avg close).',
          f"  {'group':<14}{'phase':<9}{'n':>6}{'slope move':>12}{'t':>7}{'slope move_avg':>16}{'t':>7}"]
    for gname, mask in (('EPL', m.league == 'EPL'), ('Big 5 ex-EPL', m.league != 'EPL')):
        for ph in ('Aug-Oct', 'Nov-Jan', 'Feb-May'):
            x = m[mask & (m.phase == ph)].dropna(subset=['move', 'signal'])
            r = ols(x.move, x.signal)
            y = x.dropna(subset=['move_avg'])
            r2 = ols(y.move_avg, y.signal)
            L.append(f"  {gname:<14}{ph:<9}{len(x):>6}{r.params[1]:>+12.4f}{r.tvalues[1]:>+7.2f}{r2.params[1]:>+16.4f}{r2.tvalues[1]:>+7.2f}")
    L.append('  EPL Aug-Oct slope by season (move):')
    x = m[(m.league == 'EPL') & (m.phase == 'Aug-Oct')].dropna(subset=['move', 'signal'])
    L.append('   ' + '  '.join(f"{s_} {ols(g.move, g.signal).params[1]:+.4f} (t {ols(g.move, g.signal).tvalues[1]:+.1f})"
                                for s_, g in x.groupby('season')))
    # interaction test: is the Aug-Oct slope significantly bigger than the rest?
    e2 = m[m.league == 'EPL'].dropna(subset=['move', 'signal']).copy()
    e2['early'] = (e2.phase == 'Aug-Oct').astype(float)
    r = ols(e2.move, [e2.signal, e2.early, e2.signal * e2.early])
    L.append(f"  EPL interaction signal x Aug-Oct: {r.params[3]:+.4f} (SE {r.bse[3]:.4f}, t {r.tvalues[3]:+.2f})")
    L += section_a5()
    return L


def section_a5():
    """Calibration-free early-season rule: bet the side the raw signal favours when |signal| >= k, Aug-Oct only."""
    cols = ['date', 'league', 'season', 'signal', 'close_home', 'pre_home', 'odds_ah_home', 'odds_ah_away',
            'pin_ah_home', 'pin_ah_away', 'avg_ah_home', 'avg_ah_away', 'ah_line', 'home_goals', 'away_goals']
    m = pd.read_csv(f'{OUTDIR}/clv_edge_matches.csv', usecols=cols).dropna(subset=['signal', 'close_home'])
    m['month'] = pd.to_datetime(m.date).dt.month
    home = m.signal > 0
    cp = np.where(home, m.close_home, 1 - m.close_home)
    m['move'] = cp - np.where(home, m.pre_home, 1 - m.pre_home)
    pr = {'b365': np.where(home, m.odds_ah_home, m.odds_ah_away), 'pin': np.where(home, m.pin_ah_home, m.pin_ah_away),
          'avg': np.where(home, m.avg_ah_home, m.avg_ah_away)}
    for k in ('pin', 'avg'):   # session 18: drop football-data price errors (> 1.3x Bet365)
        pr[k] = np.where(pr[k] / pr['b365'] > 1.3, np.nan, pr[k])
    pr['best3'] = np.nanmax(np.column_stack(list(pr.values())), axis=1)
    for k, v in pr.items():
        m['clv_' + k] = v * cp - 1
    # realised AH result (flat 1 unit) at B365 price, bet side
    from run import _calculate_ah
    res = [_calculate_ah(int(h), int(a), l, 'home' if hm else 'away', o, stake=1.0)[1]
           for h, a, l, hm, o in zip(m.home_goals, m.away_goals, m.ah_line, home, pr['b365'])]
    m['pnl_b365'] = res
    m['abs_sig'] = m.signal.abs()
    L = ['', '  A5. CALIBRATION-FREE EARLY-SEASON RULE (all 6 seasons, in-sample threshold): bet the side the raw',
         '      signal favours. |signal| is in logit units (0.10 ~ 2.5pp of probability near 0.5).',
         f"  {'rule':<30}{'n':>5}{'move':>15}{'CLV@B365':>15}{'CLV@Pinnacle':>15}{'CLV@avg':>15}{'CLV@best3':>15}{'ROI@B365':>15}"]
    def r_(name, f):
        return (f"  {name:<30}{len(f):>5}{ms(f.move)}{ms(f.clv_b365)}{ms(f.clv_pin)}{ms(f.clv_avg)}{ms(f.clv_best3)}{ms(f.pnl_b365)}")
    for lg in ('EPL', 'ex-EPL'):
        g = m[m.league == 'EPL'] if lg == 'EPL' else m[m.league != 'EPL']
        for ph, months in (('Aug-Oct', [8, 9, 10]), ('Nov-May', [11, 12, 1, 2, 3, 4, 5])):
            for k in (0.0, 0.2, 0.4, 0.6):
                f = g[g.month.isin(months) & (g.abs_sig >= k)]
                L.append(r_(f'{lg} {ph} |sig|>={k:.1f}', f))
    L.append('  EPL Aug-Oct |signal| >= 0.4 by season:')
    g = m[(m.league == 'EPL') & m.month.isin([8, 9, 10]) & (m.abs_sig >= 0.4)]
    for s_, f in g.groupby('season'):
        L.append(r_(f'   {s_}', f))
    L.append('  Late-season anomaly (post-hoc, likely noise): EPL Nov-May |sig|>=0.4 excl. 2020-21: ROI@B365 +9.2% +/- 3.6%')
    L.append('  (n 630) with the outcome beating the close by 6-8pp of score in 2022-26, yet move ~ 0 and CLV < 0.')
    L.append('  Ratings checked for look-ahead (pre-match recorded; no duplicate rows). ~16 cuts tried -> t 2.6 is not')
    L.append('  significant after multiple testing. Prospective test only (live log, season end).')
    L.append('  EPL Aug-Oct |signal| >= 0.4 by month:')
    for mo, f in g.groupby('month'):
        L.append(r_(f'   month {mo}', f))
    return L


# ------------------------------------------------------------------------------------------------ B
def section_b():
    """Model-free: bet a side when a book's PRE price beats the Pinnacle PRE no-vig fair price by >= x%.
    Measures CLV against the close (Pinnacle close, fallback avg, converted to the pre line). Bet365 int'l is the
    nearest proxy we have for an AU corporate; Max is the best price across books (offshore incl.)."""
    cols = ['date', 'league', 'season', 'ah_line', 'close_home', 'pre_home_pin', 'odds_ah_home', 'odds_ah_away',
            'pin_ah_home', 'pin_ah_away', 'avg_ah_home', 'avg_ah_away', 'home_goals', 'away_goals']
    m = pd.read_csv(f'{OUTDIR}/clv_edge_matches.csv', usecols=cols).dropna(subset=['close_home', 'pin_ah_home', 'pin_ah_away'])
    fair_h = m.pre_home_pin
    from run import _calculate_ah
    L = [f'  B. MODEL-FREE VALUE RULES (AH main line, Big 5 2020-26)  --  {date.today().isoformat()}',
         '  value = book price x Pinnacle pre no-vig prob - 1 (bet that side if value >= x).  CLV = price x close prob - 1.',
         f"  {'book':<8}{'group':<14}{'x':>5}{'n':>6}{'per season':>11}{'mean value':>12}{'CLV':>15}{'ROI':>15}"]
    for book, ph, pa in (('B365', 'odds_ah_home', 'odds_ah_away'), ('Avg', 'avg_ah_home', 'avg_ah_away')):
        rows = []
        for side, price, fair, close in (('home', m[ph], fair_h, m.close_home), ('away', m[pa], 1 - fair_h, 1 - m.close_home)):
            v = price * fair - 1
            rows.append(pd.DataFrame({'league': m.league, 'season': m.season, 'value': v, 'clv': price * close - 1,
                                      'price': price, 'side': side, 'h': m.home_goals, 'a': m.away_goals, 'l': m.ah_line}))
        b = pd.concat(rows, ignore_index=True).dropna(subset=['value', 'clv'])
        bad = b.value.abs() > 0.15   # price inconsistent with Pinnacle on the same line = data error
        L.append(f"  {book}: dropped {int(bad.sum())} side-rows with |value| > 15% (data errors)")
        b = b[~bad]
        for gname, mask in (('EPL', b.league == 'EPL'), ('Big 5 ex-EPL', b.league != 'EPL')):
            for x in (0.0, 0.01, 0.02, 0.03):
                f = b[mask & (b.value >= x)]
                if len(f) < 10:
                    L.append(f"  {book:<8}{gname:<14}{x:>5.0%}{len(f):>6}")
                    continue
                pnl = [_calculate_ah(int(h), int(a), l, sd, o, 1.0)[1] for h, a, l, sd, o in zip(f.h, f.a, f.l, f.side, f.price)]
                L.append(f"  {book:<8}{gname:<14}{x:>5.0%}{len(f):>6}{len(f)/6:>11.0f}{f.value.mean():>+12.2%}{ms(f.clv)}{ms(pnl)}")
    L.append('  Reading: Bet365 (international) almost never prices an EPL AH side above Pinnacle fair. A model-free')
    L.append('  "beat Pinnacle" rule needs books that are slow/off-market; the AU sheet will show whether AU books are.')
    L.append('  Max (best price) is not in the AH data (football-data has no MaxAH after 2019).')

    # 1X2 version: best (Max) or B365 pre price vs Pinnacle pre no-vig. No local 1X2 close -> realised ROI only.
    a = pd.read_csv('data/processed/all_merged.csv')
    a = a[a.season.isin(TRAIN + TEST)].dropna(subset=['pinnacle_home', 'pinnacle_draw', 'pinnacle_away', 'home_goals'])
    inv = 1 / a[['pinnacle_home', 'pinnacle_draw', 'pinnacle_away']]
    fair = inv.div(inv.sum(axis=1), axis=0).values
    res = np.select([a.home_goals > a.away_goals, a.home_goals == a.away_goals], [0, 1], 2)
    L += ['', '  1X2: book pre price vs Pinnacle pre no-vig (Big 5 2020-26; Pinnacle missing after mid 2025-26). ROI only.',
          f"  {'book':<6}{'group':<14}{'x':>5}{'n':>6}{'per season':>11}{'mean value':>12}{'ROI':>16}{'mix H/D/A':>16}"]
    for book, cs in (('Max', ['max_odds_home', 'max_odds_draw', 'max_odds_away']), ('B365', ['odds_home', 'odds_draw', 'odds_away'])):
        P = a[cs].values
        V = P * fair - 1
        for gname, mask in (('EPL', (a.league == 'EPL').values), ('Big 5 ex-EPL', (a.league != 'EPL').values)):
            for x in (0.02, 0.04, 0.06):
                ii, kk = np.where((V >= x) & (V <= 0.3) & mask[:, None])
                if len(ii) < 10:
                    L.append(f"  {book:<6}{gname:<14}{x:>5.0%}{len(ii):>6}")
                    continue
                won = (res[ii] == kk)
                pnl = np.where(won, P[ii, kk] - 1, -1.0)
                mix = '/'.join(str(int((kk == j).sum())) for j in range(3))
                L.append(f"  {book:<6}{gname:<14}{x:>5.0%}{len(ii):>6}{len(ii)/6:>11.0f}{V[ii, kk].mean():>+12.2%}{ms(pnl):>16}{mix:>16}")
    return L


# ------------------------------------------------------------------------------------------------ C
def luck_frame(alpha=0.1, comp='net', path='data/processed/all_merged.csv'):
    """Pre-match EMA (same alpha as ratings) of each team's goals - xG for and against. luck > 0 = results ran
    ahead of chance quality. Home-perspective luck_diff = home team's net luck - away team's net luck."""
    a = pd.read_csv(path).dropna(subset=['home_xg', 'away_xg', 'home_goals', 'away_goals'])
    a['date'] = pd.to_datetime(a.date)
    a = a.sort_values('date', kind='stable').reset_index(drop=True)
    st = {}
    out = []
    for r in a.itertuples(index=False):
        h = st.setdefault(r.home_team, [0.0, 0.0])
        w = st.setdefault(r.away_team, [0.0, 0.0])
        if comp == 'attack':
            out.append(h[0] - w[0])
        elif comp == 'defence':
            out.append(-h[1] + w[1])
        else:
            out.append((h[0] - h[1]) - (w[0] - w[1]))
        h[0] = alpha * (r.home_goals - r.home_xg) + (1 - alpha) * h[0]
        h[1] = alpha * (r.away_goals - r.away_xg) + (1 - alpha) * h[1]
        w[0] = alpha * (r.away_goals - r.away_xg) + (1 - alpha) * w[0]
        w[1] = alpha * (r.home_goals - r.home_xg) + (1 - alpha) * w[1]
    a['luck_diff'] = out
    a['date'] = a.date.dt.strftime('%Y-%m-%d')
    a['n_prior'] = a.groupby('home_team').cumcount()  # rough experience counter (home games only)
    return a[['date', 'league', 'home_team', 'away_team', 'luck_diff']]


def section_c():
    from run import _calculate_ah
    cols = ['date', 'league', 'season', 'home_team', 'away_team', 'signal', 'move', 'close_home', 'pre_home',
            'odds_ah_home', 'odds_ah_away', 'pin_ah_home', 'pin_ah_away', 'ah_line', 'home_goals', 'away_goals']
    m = pd.read_csv(f'{OUTDIR}/clv_edge_matches.csv', usecols=cols).dropna(subset=['signal', 'move', 'close_home'])
    m = m.merge(luck_frame(), on=['date', 'league', 'home_team', 'away_team'], how='inner')
    m['month'] = pd.to_datetime(m.date).dt.month
    m['early'] = m.month.isin([8, 9, 10]).astype(float)
    m['h_score'] = [{'Win': 1, 'Half Win': .75, 'Push': .5, 'Half Loss': .25, 'Loss': 0}[_calculate_ah(int(h), int(a_), l, 'home', 2.0, 1)[0]]
                    for h, a_, l in zip(m.home_goals, m.away_goals, m.ah_line)]
    m['res_vs_close'] = m.h_score - m.close_home
    L = [f'  C. LUCK SIGNAL (goals - xG divergence) vs MARKET  --  {date.today().isoformat()}',
         '  luck_diff: home team net (goals-xG) EMA minus away team net, pre-match, alpha 0.1, home perspective.',
         '  If the market prices off goals, it overrates lucky teams: expect move < 0 and results < close when luck_diff > 0.',
         f"  Rows {len(m)}; corr(signal, luck_diff) EPL {np.corrcoef(m[m.league=='EPL'].signal, m[m.league=='EPL'].luck_diff)[0,1]:+.3f},"
         f" ex-EPL {np.corrcoef(m[m.league!='EPL'].signal, m[m.league!='EPL'].luck_diff)[0,1]:+.3f}",
         f"  {'test':<44}{'group':<14}{'n':>6}{'coef':>10}{'t':>8}"]
    def add(name, g, y, xs, k):
        r = ols(g[y], [g[c] for c in xs])
        L.append(f"  {name:<44}{gname:<14}{len(g):>6}{r.params[k]:>+10.4f}{r.tvalues[k]:>+8.2f}")
    for gname, mask in (('EPL', m.league == 'EPL'), ('Big 5 ex-EPL', m.league != 'EPL'), ('Big 5 all', m.league.notna())):
        g = m[mask]
        add('C1 move ~ luck_diff', g, 'move', ['luck_diff'], 1)
        add('C2 move ~ signal + luck_diff: luck term', g, 'move', ['signal', 'luck_diff'], 2)
        add('C2 move ~ signal + luck_diff: signal term', g, 'move', ['signal', 'luck_diff'], 1)
        add('C3 results - close ~ luck_diff (close biased?)', g, 'res_vs_close', ['luck_diff'], 1)
        add('C3 results - close ~ signal', g, 'res_vs_close', ['signal'], 1)
        add('C4 move ~ luck_diff, Aug-Oct only', g[g.early == 1], 'move', ['luck_diff'], 1)
    # betting rule: bet AGAINST the lucky side when |luck_diff| >= k
    L += ['', '  C5 rule: bet against the luckier side (AH main line) when |luck_diff| >= k',
          f"  {'group':<14}{'k':>5}{'n':>6}{'move':>15}{'CLV@B365':>15}{'CLV@Pinnacle':>15}{'ROI@B365':>15}"]
    home = m.luck_diff < 0   # home team less lucky -> back home
    cp = np.where(home, m.close_home, 1 - m.close_home)
    m['mv'] = cp - np.where(home, m.pre_home, 1 - m.pre_home)
    pb = np.where(home, m.odds_ah_home, m.odds_ah_away)
    m['clv_b'] = pb * cp - 1
    m['clv_p'] = np.where(home, m.pin_ah_home, m.pin_ah_away) * cp - 1
    m['pnl'] = [_calculate_ah(int(h), int(a_), l, 'home' if hm else 'away', o, 1)[1]
                for h, a_, l, hm, o in zip(m.home_goals, m.away_goals, m.ah_line, home, pb)]
    for gname, mask in (('EPL', m.league == 'EPL'), ('Big 5 ex-EPL', m.league != 'EPL')):
        for k in (0.0, 0.2, 0.4, 0.6):
            f = m[mask & (m.luck_diff.abs() >= k)]
            L.append(f"  {gname:<14}{k:>5.1f}{len(f):>6}{ms(f.mv)}{ms(f.clv_b)}{ms(f.clv_p)}{ms(f.pnl)}")
    L += section_c6(m)
    L += section_c7()
    L += section_c8()
    return L


def _rule_frame(alpha=0.1, comp='net'):
    from run import _calculate_ah
    cols = ['date', 'league', 'season', 'home_team', 'away_team', 'close_home', 'pre_home', 'odds_ah_home',
            'odds_ah_away', 'avg_ah_home', 'avg_ah_away', 'pin_ah_home', 'pin_ah_away', 'ah_line', 'home_goals', 'away_goals']
    m = pd.read_csv(f'{OUTDIR}/clv_edge_matches.csv', usecols=cols).dropna(subset=['close_home'])
    m = m.merge(luck_frame(alpha, comp), on=['date', 'league', 'home_team', 'away_team'], how='inner')
    m['h_score'] = [{'Win': 1, 'Half Win': .75, 'Push': .5, 'Half Loss': .25, 'Loss': 0}[_calculate_ah(int(h), int(a_), l, 'home', 2.0, 1)[0]]
                    for h, a_, l in zip(m.home_goals, m.away_goals, m.ah_line)]
    home = m.luck_diff < 0
    cp = np.where(home, m.close_home, 1 - m.close_home)
    for k, (ph, pa) in {'fair': (None, None), 'b365': ('odds_ah_home', 'odds_ah_away'), 'avg': ('avg_ah_home', 'avg_ah_away'),
                        'pin': ('pin_ah_home', 'pin_ah_away')}.items():
        price = 1 / cp if k == 'fair' else np.where(home, m[ph], m[pa])
        m['pnl_' + k] = [np.nan if not (o > 1) else _calculate_ah(int(h), int(a_), l, 'home' if hm else 'away', o, 1)[1]
                         for h, a_, l, hm, o in zip(m.home_goals, m.away_goals, m.ah_line, home, price)]
    m['month'] = pd.to_datetime(m.date).dt.month
    m['half'] = (m.ah_line.abs() % 1).round(2) == 0.5
    return m


def section_c7():
    L = ['', '  C7. SENSITIVITY (Big 5 AH). Regression: result - close ~ luck + logit(close), all lines; rule |luck| >= 0.4',
         f"  {'variant':<28}{'group':<8}{'coef':>9}{'t':>7}{'n rule':>8}{'ROI@fair close':>16}{'ROI@B365':>16}{'ROI@avg':>16}{'ROI@Pin':>16}"]
    for name, alpha, comp in (('net, alpha 0.10 (base)', 0.1, 'net'), ('net, alpha 0.05', 0.05, 'net'),
                              ('net, alpha 0.20', 0.2, 'net'), ('attack only, 0.10', 0.1, 'attack'),
                              ('defence only, 0.10', 0.1, 'defence')):
        m = _rule_frame(alpha, comp)
        for gname, mask in (('EPL', m.league == 'EPL'), ('ex-EPL', m.league != 'EPL')):
            g = m[mask]
            r = ols(g.h_score - g.close_home, [g.luck_diff, logit(g.close_home)])
            f = g[g.luck_diff.abs() >= 0.4]
            L.append(f"  {name:<28}{gname:<8}{r.params[1]:>+9.4f}{r.tvalues[1]:>+7.2f}{len(f):>8}{ms(f.pnl_fair):>16}"
                     f"{ms(f.pnl_b365):>16}{ms(f.pnl_avg):>16}{ms(f.pnl_pin):>16}")
    m = _rule_frame()
    L += ['', '  C7b. Base rule (|luck| >= 0.4) splits', f"  {'subset':<34}{'n':>6}{'ROI@fair close':>16}{'ROI@avg':>16}"]
    for gname, mask in (('EPL', m.league == 'EPL'), ('ex-EPL', m.league != 'EPL'), ('Big 5', m.league.notna())):
        g = m[mask & (m.luck_diff.abs() >= 0.4)]
        for sub, ff in (('Aug-Oct', g[g.month.isin([8, 9, 10])]), ('Nov-May', g[~g.month.isin([8, 9, 10])]),
                        ('half lines', g[g.half]), ('back home', g[g.luck_diff < 0]), ('back away', g[g.luck_diff > 0]),
                        ('|luck| >= 0.6', g[g.luck_diff.abs() >= 0.6]), ('|luck| >= 0.8', g[g.luck_diff.abs() >= 0.8])):
            L.append(f"  {gname + ' ' + sub:<34}{len(ff):>6}{ms(ff.pnl_fair):>16}{ms(ff.pnl_avg):>16}")
    return L


def section_c8():
    """Out-of-sample replication on soft leagues (Sofascore xG, different source; closing odds)."""
    L = ['', '  C8. REPLICATION ON SOFT LEAGUES (Sofascore xG; football-data closing avg odds). No parameters re-tuned.']
    a = pd.read_csv('data/processed/soft_merged.csv')
    a = a.merge(luck_frame(0.1, 'net', 'data/processed/soft_merged.csv'), on=['date', 'league', 'home_team', 'away_team'], how='left')
    a = a.dropna(subset=['luck_diff', 'home_xg'])
    # 1X2 at close: closing avg where present; Scandinavian rows already store closing odds in odds_*
    ch = a.close_avg_home.fillna(a.odds_home); cd = a.close_avg_draw.fillna(a.odds_draw); ca = a.close_avg_away.fillna(a.odds_away)
    inv = pd.concat([1 / ch, 1 / cd, 1 / ca], axis=1)
    q = inv.div(inv.sum(axis=1), axis=0)
    a['qh'], a['qa'] = q.iloc[:, 0], q.iloc[:, 2]
    a['yh'] = (a.home_goals > a.away_goals).astype(float)
    a['ya'] = (a.home_goals < a.away_goals).astype(float)
    a = a.dropna(subset=['qh'])
    L.append(f"  {'test':<44}{'group':<10}{'n':>6}{'luck coef':>11}{'t':>8}")
    for gname, mask in (('all soft', a.league.notna()), ('proxy', a.league.isin(['B1', 'N1', 'P1', 'SC0', 'T1', 'E1'])),
                        ('Scandi', a.league.isin(['DNK', 'SWE', 'NOR', 'FIN']))):
        g = a[mask]
        if len(g) < 100:
            continue
        r = ols(g.yh - g.qh, [g.luck_diff, logit(g.qh)])
        L.append(f"  {'home win - close ~ luck + logit(close)':<44}{gname:<10}{len(g):>6}{r.params[1]:>+11.4f}{r.tvalues[1]:>+8.2f}")
        r = ols(g.ya - g.qa, [-g.luck_diff, logit(g.qa)])
        L.append(f"  {'away win - close ~ (-luck) + logit(close)':<44}{gname:<10}{len(g):>6}{r.params[1]:>+11.4f}{r.tvalues[1]:>+8.2f}")
    # 1X2 rule: back the less lucky side to WIN at fair close and at closing avg price
    L += ['', '  C8b. 1X2 rule on soft leagues: back the less lucky team to win when |luck| >= 0.4',
          f"  {'league':<10}{'n':>6}{'ROI@fair close':>16}{'ROI@close avg':>16}"]
    home = a.luck_diff < 0
    qq = np.where(home, a.qh, a.qa)
    won = np.where(home, a.yh, a.ya)
    price = np.where(home, ch.loc[a.index], ca.loc[a.index])
    a['pf'] = won / qq - 1
    a['pa'] = won * price - 1
    g = a[a.luck_diff.abs() >= 0.4]
    for lg, f in g.groupby('league'):
        L.append(f"  {lg:<10}{len(f):>6}{ms(f.pf):>16}{ms(f.pa):>16}")
    L.append(f"  {'ALL':<10}{len(g):>6}{ms(g.pf):>16}{ms(g.pa):>16}")
    return L


def section_c6(m):
    """Is the CLOSE itself biased by luck? Push-free version: half lines only (score = win prob exactly), with
    logit(close) control; then fair-close ROI of the rule = return at no-vig closing odds (pure close inefficiency)."""
    from run import _calculate_ah
    L = ['', '  C6. IS THE CLOSING LINE BIASED BY LUCK? (push-free and controlled)']
    frac = (m.ah_line.abs() % 1).round(2)
    m = m.copy()
    m['half'] = frac == 0.5
    m['lc'] = logit(m.close_home)
    L.append(f"  {'spec':<52}{'group':<14}{'n':>6}{'luck coef':>11}{'t':>8}")
    for gname, mask in (('EPL', m.league == 'EPL'), ('Big 5 ex-EPL', m.league != 'EPL'), ('Big 5 all', m.league.notna())):
        g = m[mask & m.half]
        r = ols(g.h_score - g.close_home, [g.luck_diff])
        L.append(f"  {'half lines: result - close ~ luck':<52}{gname:<14}{len(g):>6}{r.params[1]:>+11.4f}{r.tvalues[1]:>+8.2f}")
        r = ols(g.h_score - g.close_home, [g.luck_diff, g.lc])
        L.append(f"  {'half lines: result - close ~ luck + logit(close)':<52}{gname:<14}{len(g):>6}{r.params[1]:>+11.4f}{r.tvalues[1]:>+8.2f}")
        g = m[mask]
        r = ols(g.h_score - g.close_home, [g.luck_diff, g.lc])
        L.append(f"  {'all lines: result - close ~ luck + logit(close)':<52}{gname:<14}{len(g):>6}{r.params[1]:>+11.4f}{r.tvalues[1]:>+8.2f}")
        rl = glm(g.h_score, {'lc': g.lc, 'luck': g.luck_diff})
        L.append(f"  {'all lines: frac-logit score ~ logit(close) + luck':<52}{gname:<14}{len(g):>6}{rl.params.iloc[2]:>+11.4f}{rl.tvalues.iloc[2]:>+8.2f}")
    # rule at FAIR closing odds (1/close prob): isolates close inefficiency from margin
    home = m.luck_diff < 0
    cp = np.where(home, m.close_home, 1 - m.close_home)
    m['pnl_fairclose'] = [_calculate_ah(int(h), int(a_), l, 'home' if hm else 'away', 1 / c, 1)[1]
                          for h, a_, l, hm, c in zip(m.home_goals, m.away_goals, m.ah_line, home, cp)]
    m['pnl_avg'] = np.nan
    L += ['', '  C6b. Rule (back the less lucky side) ROI at FAIR closing odds = pure close inefficiency, by season (EPL, |luck| >= 0.4)',
          f"  {'season':<10}{'n':>5}{'ROI@fair close':>16}{'ROI@B365 pre':>16}"]
    g = m[(m.league == 'EPL') & (m.luck_diff.abs() >= 0.4)]
    for s_, f in g.groupby('season'):
        L.append(f"  {s_:<10}{len(f):>5}{ms(f.pnl_fairclose):>16}{ms(f.pnl):>16}")
    L.append(f"  {'all':<10}{len(g):>5}{ms(g.pnl_fairclose):>16}{ms(g.pnl):>16}")
    g = m[(m.league != 'EPL') & (m.luck_diff.abs() >= 0.4)]
    L.append(f"  {'ex-EPL':<10}{len(g):>5}{ms(g.pnl_fairclose):>16}{ms(g.pnl):>16}")
    for lg, f in g.groupby('league'):
        L.append(f"  {lg:<10}{len(f):>5}{ms(f.pnl_fairclose):>16}{ms(f.pnl):>16}")
    return L


# ------------------------------------------------------------------------------------------------ D
def implied_lambdas(qh, qa, qo, n=10):
    """Fit independent-Poisson lambdas to market no-vig P(home), P(away), P(over 2.5) by least squares."""
    from scipy.optimize import minimize
    from scipy.stats import poisson
    k = np.arange(n + 1)
    def probs(l):
        ph, pa = poisson.pmf(k, l[0]), poisson.pmf(k, l[1])
        g = np.outer(ph, pa)
        g /= g.sum()
        hw = np.tril(g, -1).sum(); aw = np.triu(g, 1).sum()
        ov = sum(g[i, j] for i in range(n + 1) for j in range(n + 1) if i + j > 2)
        btts = g[1:, 1:].sum()
        return hw, aw, ov, btts
    def loss(l):
        hw, aw, ov, _ = probs(l)
        return (hw - qh) ** 2 + (aw - qa) ** 2 + (ov - qo) ** 2
    r = minimize(loss, x0=[1.5, 1.2], bounds=[(0.05, 5), (0.05, 5)], method='L-BFGS-B')
    return r.x, probs(r.x)[3], r.fun


def section_d():
    """BTTS: no BTTS odds exist in football-data. Market BTTS is implied by fitting Poisson lambdas to the Avg no-vig
    1X2 and O/U 2.5 prices; model BTTS from ratings. M3 asks whether the model adds BTTS information beyond that."""
    from model.poisson import compute_match_probs
    import glob
    a = pd.read_csv('data/processed/all_merged.csv')
    r = pd.read_csv('data/processed/ratings.csv')
    d = a.merge(r, on=['date', 'league', 'season', 'home_team', 'away_team'])
    d = d[d.season.isin(TRAIN + TEST)].dropna(subset=['home_goals', 'avg_odds_home', 'avg_odds_draw', 'avg_odds_away'])
    raw = []
    for f in glob.glob('data/raw/footballdata/*_20??-??.csv'):
        x = pd.read_csv(f, encoding='latin-1')
        if 'Avg>2.5' in x.columns:
            x['date'] = pd.to_datetime(x['Date'], dayfirst=True).dt.strftime('%Y-%m-%d')
            raw.append(x[['date', 'B365H', 'B365A', 'FTHG', 'FTAG', 'Avg>2.5', 'Avg<2.5']])
    raw = pd.concat(raw).drop_duplicates(['date', 'B365H', 'B365A', 'FTHG', 'FTAG'])
    d['date'] = pd.to_datetime(d.date).dt.strftime('%Y-%m-%d')
    d = d.merge(raw, left_on=['date', 'odds_home', 'odds_away', 'home_goals', 'away_goals'],
                right_on=['date', 'B365H', 'B365A', 'FTHG', 'FTAG']).dropna(subset=['Avg>2.5'])
    inv = 1 / d[['avg_odds_home', 'avg_odds_draw', 'avg_odds_away']]
    q = inv.div(inv.sum(axis=1), axis=0)
    io = 1 / d[['Avg>2.5', 'Avg<2.5']]
    qo = (io.iloc[:, 0] / io.sum(axis=1)).values
    fits = [implied_lambdas(h, w, o) for h, w, o in zip(q.iloc[:, 0], q.iloc[:, 2], qo)]
    d['mkt_btts'] = [f[1] for f in fits]
    d['fit_err'] = [f[2] for f in fits]
    mp = [compute_match_probs(x1, x2, x3, x4) for x1, x2, x3, x4 in zip(d.home_attack, d.home_defence, d.away_attack, d.away_defence)]
    d['mod_btts'] = [p['prob_btts_yes'] for p in mp]
    d['y'] = ((d.home_goals > 0) & (d.away_goals > 0)).astype(float)
    L = [f'  D. BTTS (market BTTS implied from Avg 1X2 + O/U 2.5 via fitted Poisson)  --  {date.today().isoformat()}',
         f'  Rows {len(d)}; median fit error {np.median(d.fit_err):.2e}; BTTS rate {d.y.mean():.3f}, '
         f'market-implied mean {d.mkt_btts.mean():.3f}, model mean {d.mod_btts.mean():.3f}',
         f"  {'group':<14}{'n':>6}{'M1 b_mkt':>10}{'M3 b_model':>12}{'SE':>8}{'t':>7}{'OOS LL mkt':>12}{'OOS LL M1':>11}{'OOS LL M3':>11}"]
    def ll(y, p):
        p = np.clip(p, 1e-6, 1 - 1e-6)
        return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
    groups = {'EPL': d.league == 'EPL', 'Big 5 ex-EPL': d.league != 'EPL'}
    for lg in sorted(d.league.unique()):
        groups[lg] = d.league == lg
    for g, mask in groups.items():
        x = d[mask]
        r1 = glm(x.y, {'m': logit(x.mkt_btts)})
        r3 = glm(x.y, {'m': logit(x.mkt_btts), 'x': logit(x.mod_btts)})
        tr, te = x[x.season.isin(TRAIN)], x[x.season.isin(TEST)]
        f1 = glm(tr.y, {'m': logit(tr.mkt_btts)}); f3 = glm(tr.y, {'m': logit(tr.mkt_btts), 'x': logit(tr.mod_btts)})
        p1 = np.asarray(f1.predict(sm.add_constant(pd.DataFrame({'m': logit(te.mkt_btts)}), has_constant='add')))
        p3 = np.asarray(f3.predict(sm.add_constant(pd.DataFrame({'m': logit(te.mkt_btts), 'x': logit(te.mod_btts)}), has_constant='add')))
        L.append(f"  {g:<14}{len(x):>6}{r1.params.iloc[1]:>+10.3f}{r3.params.iloc[2]:>+12.3f}{r3.bse.iloc[2]:>8.3f}{r3.tvalues.iloc[2]:>+7.2f}"
                 f"{ll(te.y, te.mkt_btts):>12.5f}{ll(te.y, p1):>11.5f}{ll(te.y, p3):>11.5f}")
    # crude betting view: real AU BTTS margin is ~7-9%; edge needed ~4pp
    e = d[d.league == 'EPL']
    tr, te = e[e.season.isin(TRAIN)], e[e.season.isin(TEST)].copy()
    f3 = glm(tr.y, {'m': logit(tr.mkt_btts), 'x': logit(tr.mod_btts)})
    te['cal'] = np.asarray(f3.predict(sm.add_constant(pd.DataFrame({'m': logit(te.mkt_btts), 'x': logit(te.mod_btts)}), has_constant='add')))
    te['edge'] = te.cal - te.mkt_btts
    L += ['', '  EPL OOS: |calibrated BTTS edge| distribution (yes or no side) vs ~4pp needed to clear an AU BTTS margin:']
    for th in (0.02, 0.04, 0.06):
        f = te[te.edge.abs() >= th]
        hit = np.where(f.edge > 0, f.y, 1 - f.y)
        side_p = np.where(f.edge > 0, f.mkt_btts, 1 - f.mkt_btts)
        L.append(f"   |edge| >= {th:.0%}: n {len(f):>4}  realised hit {hit.mean() if len(f) else float('nan'):.3f}  vs market-implied {side_p.mean() if len(f) else float('nan'):.3f}")
    return L


SECTIONS = {'A': section_a, 'B': section_b, 'C': section_c, 'D': section_d}

if __name__ == '__main__':
    for key in (sys.argv[1:] or list(SECTIONS)):
        out = SECTIONS[key]()
        open(f'{OUTDIR}/advanced_{key}.txt', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
        print('\n'.join(out))
