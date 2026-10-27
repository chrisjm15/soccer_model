"""Does the xG model add information beyond the market in O/U 2.5 and 1X2? (Cowork, 2026-10-28)
READ-ONLY research script. Same method as the AH recalibration test (session 14), applied to markets that every
AU bookmaker offers (the AH edge is blocked by AU price access).

Market probability = no-vig from football-data AVERAGE pre-closing odds (Avg>2.5/Avg<2.5, AvgH/AvgD/AvgA).
  Pinnacle is not used: football-data dropped it mid 2025-26.
Model probability  = independent Poisson from data/processed/ratings.csv (same as run.py / calibration_backtest).
M1: y ~ logit(market)         M3: y ~ logit(market) + logit(model)      (logit GLM, HC1 SEs)
  b_model > 0 and significant in M3 = the model knows something the price does not.
OOS: fit on 2020-21..2023-24, test 2024-25 & 2025-26. Bet the side/outcome with the largest calibrated edge;
  ROI at Avg (typical AU-like) and Max (best price) pre-closing odds. ROI is noisy: read the SE.
No closing odds for O/U or 1X2 are stored locally, so there is no CLV here (see DOWNLOAD_FULL_FOOTBALLDATA.bat).
Output: output/backtest_results/ou_1x2_calibration_report.txt
"""
import glob, math, os, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
import statsmodels.api as sm
from model.poisson import compute_match_probs

TRAIN = ['2020-21', '2021-22', '2022-23', '2023-24']
TEST = ['2024-25', '2025-26']
OUT = 'output/backtest_results/ou_1x2_calibration_report.txt'
CLIP = (0.01, 0.99)


def logit(p):
    p = np.clip(np.asarray(p, float), *CLIP)
    return np.log(p / (1 - p))


def fit(y, X):
    X = sm.add_constant(pd.DataFrame(X).reset_index(drop=True))
    return sm.GLM(np.asarray(y, float), X, family=sm.families.Binomial()).fit(cov_type='HC1')


def load():
    m = pd.read_csv('data/processed/all_merged.csv')
    r = pd.read_csv('data/processed/ratings.csv')
    d = m.merge(r, on=['date', 'league', 'season', 'home_team', 'away_team'], how='inner')
    d = d[d.season.isin(TRAIN + TEST)].dropna(subset=['home_goals', 'away_goals', 'home_attack'])
    raw = []
    for f in glob.glob('data/raw/footballdata/*_20??-??.csv'):
        x = pd.read_csv(f, encoding='latin-1')
        if 'Avg>2.5' not in x.columns:
            continue
        x['date'] = pd.to_datetime(x['Date'], dayfirst=True).dt.strftime('%Y-%m-%d')
        raw.append(x[['date', 'B365H', 'B365A', 'FTHG', 'FTAG', 'Avg>2.5', 'Avg<2.5', 'Max>2.5', 'Max<2.5']])
    raw = pd.concat(raw).drop_duplicates(['date', 'B365H', 'B365A', 'FTHG', 'FTAG'])
    d['date'] = pd.to_datetime(d['date']).dt.strftime('%Y-%m-%d')
    n0 = len(d)
    d = d.merge(raw, left_on=['date', 'odds_home', 'odds_away', 'home_goals', 'away_goals'],
                right_on=['date', 'B365H', 'B365A', 'FTHG', 'FTAG'], how='left')
    join_rate = d['Avg>2.5'].notna().mean()
    probs = [compute_match_probs(a, b, c, e) for a, b, c, e in
             zip(d.home_attack, d.home_defence, d.away_attack, d.away_defence)]
    d['m_over'] = [p['prob_over_25'] for p in probs]
    d['m_home'] = [p['prob_home_win'] for p in probs]
    d['m_draw'] = [p['prob_draw'] for p in probs]
    d['m_away'] = [p['prob_away_win'] for p in probs]
    ov = 1 / d['Avg>2.5'] + 1 / d['Avg<2.5']
    d['q_over'] = (1 / d['Avg>2.5']) / ov
    t = 1 / d.avg_odds_home + 1 / d.avg_odds_draw + 1 / d.avg_odds_away
    for k, c in (('home', 'avg_odds_home'), ('draw', 'avg_odds_draw'), ('away', 'avg_odds_away')):
        d['q_' + k] = (1 / d[c]) / t
    g = d.home_goals + d.away_goals
    d['y_over'] = (g > 2.5).astype(float)
    d['y_home'] = (d.home_goals > d.away_goals).astype(float)
    d['y_draw'] = (d.home_goals == d.away_goals).astype(float)
    d['y_away'] = (d.home_goals < d.away_goals).astype(float)
    return d, n0, join_rate


def m3_line(name, r):
    b, se = r.params.iloc[2], r.bse.iloc[2]
    return (f"  {name:<30} n {int(r.nobs):>5}  b_market {r.params.iloc[1]:+.3f} ({r.bse.iloc[1]:.3f})  "
            f"b_model {b:+.3f} (SE {se:.3f}, t {b/se:+.2f}, p {r.pvalues.iloc[2]:.3f})")


def ll(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))


def main():
    d, n0, jr = load()
    L = [f'  O/U 2.5 AND 1X2: DOES THE MODEL ADD INFORMATION BEYOND THE MARKET?  --  {date.today().isoformat()}',
         f'  Rows: {len(d)} (Big 5, 2020-21..2025-26, with ratings).  Avg O/U odds joined: {jr:.1%}']
    H = lambda t: L.extend(['', '=' * 100, '  ' + t, '=' * 100])
    groups = {'EPL': d.league == 'EPL', 'Big 5 ex-EPL': d.league != 'EPL'}
    for lg in sorted(d.league.unique()):
        if lg != 'EPL':
            groups[lg] = d.league == lg

    # ---------------- full-sample M3, per outcome, home perspective (no side selection)
    H('A. FULL SAMPLE M3 (all 6 seasons), each outcome on its own; y = outcome happened')
    for out in ('over', 'home', 'draw', 'away'):
        L.append(f'  -- {out.upper()}  (market = Avg no-vig; model = Poisson)')
        for gname, mask in groups.items():
            x = d[mask].dropna(subset=['q_' + out])
            r = fit(x['y_' + out], {'lm': logit(x['q_' + out]), 'lx': logit(x['m_' + out])})
            L.append(m3_line(gname, r))

    # ---------------- OOS
    H('B. OUT OF SAMPLE: fit 2020-21..2023-24 per league group, test 2024-25 & 2025-26')
    L.append('  Bet = side/outcome with the largest calibrated edge (calib - market no-vig).  ROI flat stakes, +/- 1 SE.')
    L.append('  Price: Avg = market average pre-closing (AU corporates are roughly here or worse); Max = best price.')
    for gname in ('EPL', 'Big 5 ex-EPL'):
        mask = groups[gname]
        tr, te = d[mask & d.season.isin(TRAIN)], d[mask & d.season.isin(TEST)].copy()
        # O/U: over and under are complements; fit on over, under = 1 - calib_over
        x = tr.dropna(subset=['q_over'])
        r = fit(x.y_over, {'lm': logit(x.q_over), 'lx': logit(x.m_over)})
        r1 = fit(x.y_over, {'lm': logit(x.q_over)})
        te = te.dropna(subset=['q_over']).copy()
        X3 = sm.add_constant(pd.DataFrame({'lm': logit(te.q_over), 'lx': logit(te.m_over)}), has_constant='add')
        X1 = sm.add_constant(pd.DataFrame({'lm': logit(te.q_over)}), has_constant='add')
        c = np.asarray(r.predict(X3))
        c1 = np.asarray(r1.predict(X1))
        L.append(f'  {gname} O/U 2.5 test n={len(te)}: log-loss market {ll(te.y_over, te.q_over):.5f}  M1 {ll(te.y_over, c1):.5f}'
                 f'  M3 {ll(te.y_over, c):.5f}   (lower is better)')
        e_over = c - te.q_over.values
        side_over = e_over >= 0
        edge = np.where(side_over, e_over, -e_over)
        won = np.where(side_over, te.y_over.values, 1 - te.y_over.values)
        for pc in ('Avg', 'Max'):
            o = np.where(side_over, te[f'{pc}>2.5'].values, te[f'{pc}<2.5'].values)
            te[f'pnl_{pc}'] = won * (o - 1) - (1 - won)
        te['edge'] = edge
        for th in (0.01, 0.02, 0.03, 0.05):
            f = te[te.edge >= th]
            if len(f) < 5:
                continue
            s = '  '.join(f"ROI@{pc} {f[f'pnl_{pc}'].mean():+.1%}+/-{f[f'pnl_{pc}'].std()/math.sqrt(len(f)):.1%}" for pc in ('Avg', 'Max'))
            L.append(f'     O/U edge >= {th:.0%}: n {len(f):>4} ({len(f)/2:.0f}/season)  over share {np.mean(side_over[te.edge >= th]):.0%}  {s}')

        # 1X2: fit each outcome separately on train, choose outcome with largest calibrated edge
        q3 = ['q_home', 'q_draw', 'q_away', 'max_odds_home', 'max_odds_draw', 'max_odds_away']
        tr = tr.dropna(subset=q3)
        te = d[mask & d.season.isin(TEST)].dropna(subset=q3).copy()
        cal = {}
        for out in ('home', 'draw', 'away'):
            rr = fit(tr['y_' + out], {'lm': logit(tr['q_' + out]), 'lx': logit(tr['m_' + out])})
            Xo = sm.add_constant(pd.DataFrame({'lm': logit(te['q_' + out]), 'lx': logit(te['m_' + out])}), has_constant='add')
            cal[out] = np.asarray(rr.predict(Xo))
        C = pd.DataFrame(cal)
        C = C.div(C.sum(axis=1), axis=0)   # separate binary fits do not sum to 1: renormalise
        E = pd.DataFrame({k: C[k].values - te['q_' + k].values for k in ('home', 'draw', 'away')})
        L.append(f'  {gname} 1X2 test: mean sum of raw calibrated probs before renormalising '
                 f'{pd.DataFrame(cal).sum(axis=1).mean():.4f}')
        best = E.idxmax(axis=1).values
        te['edge'] = E.max(axis=1).values
        won = np.array([te['y_' + b].iloc[i] for i, b in enumerate(best)])
        for pc, cols in (('Avg', ('avg_odds_home', 'avg_odds_draw', 'avg_odds_away')),
                         ('Max', ('max_odds_home', 'max_odds_draw', 'max_odds_away'))):
            mp = dict(zip(('home', 'draw', 'away'), cols))
            o = np.array([te[mp[b]].iloc[i] for i, b in enumerate(best)])
            te[f'pnl_{pc}'] = won * (o - 1) - (1 - won)
        te['best'] = best
        L.append(f'  {gname} 1X2 test n={len(te)}:')
        for th in (0.01, 0.02, 0.03, 0.05):
            f = te[te.edge >= th]
            if len(f) < 5:
                continue
            mix = f.best.value_counts(normalize=True).round(2).to_dict()
            s = '  '.join(f"ROI@{pc} {f[f'pnl_{pc}'].mean():+.1%}+/-{f[f'pnl_{pc}'].std()/math.sqrt(len(f)):.1%}" for pc in ('Avg', 'Max'))
            L.append(f'     1X2 edge >= {th:.0%}: n {len(f):>4} ({len(f)/2:.0f}/season)  mix {mix}  {s}')
    L.append('')
    L.append('  Reading: AH (session 14/16) for comparison: EPL M3 b_model +0.245 (t 2.30) on the AH main line.')
    open(OUT, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
