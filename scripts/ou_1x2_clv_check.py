"""Line-movement / CLV test for 1X2 and O/U 2.5 (Cowork, 2026-10-28). READ-ONLY research script.
Needs data/raw/footballdata_full/ (run scripts/download_full_footballdata.py first; DOWNLOAD_AND_TEST_1X2_OU.bat).

Same logic as the AH test (session 16/17):
  H1 (fit-free, all matches): move = closing no-vig prob - pre-closing no-vig prob of the outcome,
      signal = logit(model) - logit(pre market).  Slope > 0 = the market moves toward the model before kick-off.
  H2 (OOS rule): fit M3 on 2020-21..2023-24, test 2024-25 & 2025-26; bet the outcome/side with the largest
      calibrated edge >= threshold; report move and price CLV = pre price * closing no-vig prob - 1.
Pre market = Avg pre-closing no-vig. Movement is like-for-like (Avg close - Avg pre; Pinnacle close - Pinnacle pre):
mixing books creates a fake slope (seen on mock data). CLV uses the best close: Pinnacle when present, else Avg.
Output: output/backtest_results/ou_1x2_clv_report.txt
Run:    python scripts/ou_1x2_clv_check.py [full_data_dir]
"""
import glob, math, os, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
import statsmodels.api as sm
from ou_1x2_calibration_check import load, logit, fit, TRAIN, TEST

OUT = 'output/backtest_results/ou_1x2_clv_report.txt'
FULL_DIR = 'data/raw/footballdata_full'


def novig(cols_df):
    inv = 1 / cols_df
    return inv.div(inv.sum(axis=1), axis=0)


def load_full(dirpath):
    rows = []
    for f in glob.glob(os.path.join(dirpath, '*.csv')):
        x = pd.read_csv(f, encoding='latin-1')
        x = x.dropna(subset=['Date', 'HomeTeam'])
        x['date'] = pd.to_datetime(x['Date'], dayfirst=True).dt.strftime('%Y-%m-%d')
        rows.append(x)
    if not rows:
        sys.exit(f'No files in {dirpath}. Run scripts/download_full_footballdata.py first.')
    x = pd.concat(rows, ignore_index=True)
    for c in ['PSCH', 'PSCD', 'PSCA', 'AvgCH', 'AvgCD', 'AvgCA', 'MaxCH', 'PC>2.5', 'PC<2.5', 'AvgC>2.5',
              'AvgC<2.5', 'P>2.5', 'P<2.5']:
        if c not in x.columns:
            x[c] = np.nan
    keep = ['date', 'B365H', 'B365A', 'FTHG', 'FTAG', 'PSH', 'PSD', 'PSA', 'P>2.5', 'P<2.5',
            'PSCH', 'PSCD', 'PSCA', 'AvgCH', 'AvgCD', 'AvgCA', 'PC>2.5', 'PC<2.5', 'AvgC>2.5', 'AvgC<2.5']
    return x[keep].drop_duplicates(['date', 'B365H', 'B365A', 'FTHG', 'FTAG']).rename(
        columns={'PSH': 'pre_PSH', 'PSD': 'pre_PSD', 'PSA': 'pre_PSA'})


def ols(y, x):
    X = sm.add_constant(np.asarray(x, float))
    return sm.OLS(np.asarray(y, float), X).fit(cov_type='HC1')


def ms(v):
    v = pd.Series(v).dropna()
    if len(v) < 2:
        return 'n/a'
    return f'{v.mean():+.2%}+/-{v.std()/math.sqrt(len(v)):.2%}'


def main():
    full_dir = sys.argv[1] if len(sys.argv) > 1 else FULL_DIR
    d, _, _ = load()
    fx = load_full(full_dir)
    d = d.merge(fx, left_on=['date', 'odds_home', 'odds_away', 'home_goals', 'away_goals'],
                right_on=['date', 'B365H', 'B365A', 'FTHG', 'FTAG'], how='left', suffixes=('', '_full'))
    # closing no-vig: Pinnacle close where all three present, else Avg close
    pin = novig(d[['PSCH', 'PSCD', 'PSCA']])
    avg = novig(d[['AvgCH', 'AvgCD', 'AvgCA']])
    use_pin = pin.notna().all(axis=1)
    for i, k in enumerate(('home', 'draw', 'away')):
        d['c_' + k] = np.where(use_pin, pin.iloc[:, i], avg.iloc[:, i])
    pin_o = novig(d[['PC>2.5', 'PC<2.5']]).iloc[:, 0]
    avg_o = novig(d[['AvgC>2.5', 'AvgC<2.5']]).iloc[:, 0]
    d['c_over'] = np.where(pin_o.notna(), pin_o, avg_o)
    # like-for-like closes for movement (avoid book-mix artefacts)
    for i, k in enumerate(('home', 'draw', 'away')):
        d['ca_' + k] = avg.iloc[:, i]
        d['cp_' + k] = pin.iloc[:, i]
    ppre = novig(d[['pre_PSH', 'pre_PSD', 'pre_PSA']])
    for i, k in enumerate(('home', 'draw', 'away')):
        d['qp_' + k] = ppre.iloc[:, i]
    d['ca_over'] = avg_o
    d['cp_over'] = pin_o
    d['qp_over'] = novig(d[['P>2.5', 'P<2.5']]).iloc[:, 0]
    d['close_src_1x2'] = np.where(use_pin, 'pinnacle', np.where(avg.notna().all(axis=1), 'avg', 'none'))

    L = [f'  1X2 AND O/U 2.5: LINE MOVEMENT AND CLV vs MODEL  --  {date.today().isoformat()}',
         f'  Rows {len(d)}; closing 1X2 found {d.c_home.notna().mean():.1%} (Pinnacle {(d.close_src_1x2=="pinnacle").mean():.1%}),'
         f' closing O/U found {d.c_over.notna().mean():.1%}']
    H = lambda t: L.extend(['', '=' * 100, '  ' + t, '=' * 100])
    groups = {'EPL': d.league == 'EPL', 'Big 5 ex-EPL': d.league != 'EPL'}
    for lg in sorted(d.league.unique()):
        if lg != 'EPL':
            groups[lg] = d.league == lg

    H('H1. FIT-FREE: move ~ signal, all matches (OLS, HC1).  AH benchmark (session 16): EPL avg-to-avg slope +0.0047, t 3.3')
    L.append('  move_avg = Avg close no-vig - Avg pre no-vig;  move_pin = Pinnacle close - Pinnacle pre (like for like).')
    L.append('  signal = logit(model) - logit(Avg pre no-vig)  [for move_pin: logit(model) - logit(Pinnacle pre)]')
    L.append(f"  {'outcome':<8}{'group':<16}{'n':>6}{'slope avg':>11}{'t':>7}{'n pin':>7}{'slope pin':>11}{'t':>7}")
    for out in ('home', 'away', 'draw', 'over'):
        for gname, mask in groups.items():
            x = d[mask].dropna(subset=['ca_' + out, 'q_' + out])
            if len(x) < 50:
                continue
            r = ols(x['ca_' + out] - x['q_' + out], logit(x['m_' + out]) - logit(x['q_' + out]))
            y = d[mask].dropna(subset=['cp_' + out, 'qp_' + out])
            if len(y) >= 50:
                rp = ols(y['cp_' + out] - y['qp_' + out], logit(y['m_' + out]) - logit(y['qp_' + out]))
                pin_s = f"{len(y):>7}{rp.params[1]:>+11.4f}{rp.tvalues[1]:>+7.2f}"
            else:
                pin_s = f"{len(y):>7}{'n/a':>11}{'':>7}"
            L.append(f"  {out:<8}{gname:<16}{len(x):>6}{r.params[1]:>+11.4f}{r.tvalues[1]:>+7.2f}{pin_s}")

    H('H2. OOS RULE (fit 2020-21..2023-24, test 2024-25 & 2025-26): flagged bets, move and price CLV')
    L.append('  CLV@X = pre-closing price X * closing no-vig prob - 1.  Avg ~ AU corporates; Max = best; Pin = Pinnacle pre.')
    for gname in ('EPL', 'Big 5 ex-EPL'):
        mask = groups[gname]
        tr, te = d[mask & d.season.isin(TRAIN)], d[mask & d.season.isin(TEST)].copy()
        # ---- 1X2
        q3 = ['q_home', 'q_draw', 'q_away']
        tr1, te1 = tr.dropna(subset=q3), te.dropna(subset=q3 + ['c_home']).copy()
        C = {}
        for out in ('home', 'draw', 'away'):
            r = fit(tr1['y_' + out], {'lm': logit(tr1['q_' + out]), 'lx': logit(tr1['m_' + out])})
            X = sm.add_constant(pd.DataFrame({'lm': logit(te1['q_' + out]), 'lx': logit(te1['m_' + out])}), has_constant='add')
            C[out] = np.asarray(r.predict(X))
        C = pd.DataFrame(C)
        C = C.div(C.sum(axis=1), axis=0)
        E = pd.DataFrame({k: C[k].values - te1['q_' + k].values for k in ('home', 'draw', 'away')})
        best = E.idxmax(axis=1).values
        te1['edge'] = E.max(axis=1).values
        pick = lambda pref: np.array([te1[pref[b]].iloc[i] for i, b in enumerate(best)])
        te1['move'] = pick({k: 'ca_' + k for k in ('home', 'draw', 'away')}) - pick({k: 'q_' + k for k in ('home', 'draw', 'away')})
        cp = pick({k: 'c_' + k for k in ('home', 'draw', 'away')})
        for pc, cols in (('Avg', ('avg_odds_home', 'avg_odds_draw', 'avg_odds_away')),
                         ('Max', ('max_odds_home', 'max_odds_draw', 'max_odds_away')),
                         ('Pin', ('pre_PSH', 'pre_PSD', 'pre_PSA'))):
            te1['clv_' + pc] = pick(dict(zip(('home', 'draw', 'away'), cols))) * cp - 1
        te1['best'] = best
        L.append(f'  {gname} 1X2 (test n {len(te1)}):')
        L.append(f'     all matches, model pick : move(avg) {ms(te1.move)}  CLV@Avg {ms(te1.clv_Avg)}  CLV@Max {ms(te1.clv_Max)}  CLV@Pin {ms(te1.clv_Pin)}')
        for th in (0.01, 0.02, 0.03):
            f = te1[te1.edge >= th]
            if len(f) < 10:
                continue
            L.append(f'     edge >= {th:.0%}: n {len(f):>4}  mix {f.best.value_counts(normalize=True).round(2).to_dict()}')
            L.append(f'        move(avg) {ms(f.move)}  CLV@Avg {ms(f.clv_Avg)}  CLV@Max {ms(f.clv_Max)}  CLV@Pin {ms(f.clv_Pin)}')
        # ---- O/U
        tro, teo = tr.dropna(subset=['q_over']), te.dropna(subset=['q_over', 'c_over']).copy()
        r = fit(tro.y_over, {'lm': logit(tro.q_over), 'lx': logit(tro.m_over)})
        X = sm.add_constant(pd.DataFrame({'lm': logit(teo.q_over), 'lx': logit(teo.m_over)}), has_constant='add')
        e = np.asarray(r.predict(X)) - teo.q_over.values
        over = e >= 0
        teo['edge'] = np.abs(e)
        cp = np.where(over, teo.c_over, 1 - teo.c_over)
        teo['move'] = np.where(over, teo.ca_over - teo.q_over, teo.q_over - teo.ca_over)
        for pc in ('Avg', 'Max'):
            teo['clv_' + pc] = np.where(over, teo[f'{pc}>2.5'], teo[f'{pc}<2.5']) * cp - 1
        teo['over'] = over
        L.append(f'  {gname} O/U 2.5 (test n {len(teo)}):')
        for th in (0.01, 0.02, 0.03):
            f = teo[teo.edge >= th]
            if len(f) < 10:
                continue
            L.append(f'     edge >= {th:.0%}: n {len(f):>4}  over share {f.over.mean():.0%}  move {ms(f.move)}  '
                     f'CLV@Avg {ms(f.clv_Avg)}  CLV@Max {ms(f.clv_Max)}')
    L.append('')
    L.append('  Decision rule (set before seeing results, 2026-10-28): a market is worth a live paper test only if')
    L.append('  H1 EPL avg-to-avg slope > 0 with t >= 2 for that outcome AND OOS flagged CLV@Avg > 0 (AU corporates price near Avg).')
    open(OUT, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
