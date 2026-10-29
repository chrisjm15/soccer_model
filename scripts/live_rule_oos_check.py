"""Live-rule out-of-sample check + push-consistency check of the EPL AH calibration (Cowork, 2026-10-28).
READ-ONLY research script.

Why: the session-16 CLV verdict (44 OOS flagged bets, +0.7% price CLV) used the ALL-LEAGUES calibration edge.
The live rule uses an EPL-only fit. Section C measures the live rule itself.

Question: the calibration response is actual_score (push = 0.5) and model_prob is E[score]
(p_side + 0.5*p_push), but the market regressor and the edge baseline are the two-way no-vig
probability q = W/(W+L), which EXCLUDES pushes. On a push-capable line the market's own expected score is
    market_score = q + P_push * (0.5 - q)
so (score - q) carries P_push*(0.5 - q) even with zero information: underdog sides on 0 / whole / quarter
lines look better than they are, favourites worse.

This script:
  A. computes market_score for every EPL match 2020-21..2025-26 (P_push from a Poisson grid solved to
     match q on the line, mu = 2.8, same method as model/clv.py), and sizes the gap;
  B. refits M1/M3 on all 6 seasons with the current spec (must reproduce config/calibration.yaml) and with
     the push-consistent spec (logit(market_score) instead of logit(q));
  C. out-of-sample (train 2020-21..2023-24, test 2024-25 & 2025-26, EPL-only fit, live 1% rule and market
     range guard): flagged bets, realised ROI and price CLV under each spec;
  D. re-scores the live 2026-27 log rows.
It changes nothing. Output: output/backtest_results/live_rule_oos_report.txt
Run:  python scripts/live_rule_oos_check.py
"""
import math, os, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
import statsmodels.api as sm
import yaml
from model.markets import compute_ah_probs
from model.poisson import poisson_pmf

MU = 2.8
CLIP = (0.01, 0.99)
THRESH = 0.01
TRAIN = ['2020-21', '2021-22', '2022-23', '2023-24']
TEST = ['2024-25', '2025-26']
OUT = 'output/backtest_results/live_rule_oos_report.txt'


def grid(lh, la, n=10):
    return [[poisson_pmf(h, lh) * poisson_pmf(a, la) for a in range(n + 1)] for h in range(n + 1)]


def market_score_side(q_side, ah_line, side):
    """Expected score of the bet side implied by the market's push-excluded prob q on this line."""
    q_home = q_side if side == 'home' else 1.0 - q_side

    def qh(s):
        p = compute_ah_probs(grid((MU + s) / 2, (MU - s) / 2), float(ah_line))
        return p, p['p_home'] / (p['p_home'] + p['p_away'])

    lo, hi = -MU + 1e-6, MU - 1e-6
    for _ in range(60):
        mid = (lo + hi) / 2
        if qh(mid)[1] < q_home:
            lo = mid
        else:
            hi = mid
    p, _ = qh((lo + hi) / 2)
    p_push = p['p_push']
    p_side = p['p_home'] if side == 'home' else p['p_away']
    # use q itself for the win/loss split so market_score = q + p_push*(0.5 - q) exactly
    return q_side * (1 - p_push) + 0.5 * p_push, p_push


def logit(p):
    p = np.clip(p, *CLIP)
    return np.log(p / (1 - p))


def fit(y, cols):
    X = sm.add_constant(pd.DataFrame(cols))
    r = sm.GLM(y.values, X.values, family=sm.families.Binomial()).fit(cov_type='HC1')
    return r


def sig(z):
    return 1 / (1 + np.exp(-z))


def main():
    L = []
    H = lambda t: L.extend(['', '=' * 96, '  ' + t, '=' * 96])
    cal = pd.read_csv('output/backtest_results/calibration_matches.csv')
    e = cal[cal.league == 'EPL'].copy().reset_index(drop=True)
    ms = [market_score_side(q, l, s) for q, l, s in zip(e.market_prob_novig, e.ah_line, e.bet_side)]
    e['market_score'] = [m[0] for m in ms]
    e['p_push_mkt'] = [m[1] for m in ms]
    e['gap'] = e.market_score - e.market_prob_novig
    frac = (e.ah_line.abs() % 1).round(2)
    e['ltype'] = np.where(frac == 0.5, 'half', np.where(frac == 0.0, 'whole/zero', 'quarter'))

    L.append('  PUSH-CONSISTENCY CHECK OF THE EPL AH CALIBRATION  --  ' + date.today().isoformat())
    L.append('  market_score = q + P_push*(0.5 - q);  gap = market_score - q (fake "edge" with zero information)')
    H('A. SIZE OF THE GAP  (EPL 2020-21..2025-26, model bet side, n=%d)' % len(e))
    L.append(f"  {'line type':<12}{'n':>6}{'mean P_push':>13}{'mean |gap|':>12}{'gap q<0.5':>12}{'gap q>=0.5':>12}")
    for lt, g in e.groupby('ltype'):
        lo, hi = g[g.market_prob_novig < .5], g[g.market_prob_novig >= .5]
        L.append(f"  {lt:<12}{len(g):>6}{g.p_push_mkt.mean():>13.3f}{g.gap.abs().mean():>12.4f}"
                 f"{lo.gap.mean():>+12.4f}{hi.gap.mean():>+12.4f}")
    L.append(f"  Share of matches with |gap| >= 0.5pp: {(e.gap.abs() >= 0.005).mean():.1%};  >= 1pp: {(e.gap.abs() >= 0.01).mean():.1%}")

    # ---------- B. full-sample refits
    y = e.actual_score
    lm, lmod, lms = logit(e.market_prob_novig), logit(e.model_prob), logit(e.market_score)
    m1_cur = fit(y, {'lm': lm}); m3_cur = fit(y, {'lm': lm, 'lmod': lmod})
    m1_con = fit(y, {'lms': lms}); m3_con = fit(y, {'lms': lms, 'lmod': lmod})
    cfg = yaml.safe_load(open('config/calibration.yaml'))['epl_ah']
    H('B. FULL-SAMPLE FIT, EPL 2020-21..2025-26 (fractional logit, HC1)')
    L.append(f"  config/calibration.yaml M3: intercept {cfg['m3']['intercept']:+.4f}  b_market {cfg['m3']['b_market']:.4f}  b_model {cfg['m3']['b_model']:.4f}")
    def row(name, r, k):
        b, se = r.params[k], r.bse[k]
        return f"  {name:<44} coef {b:+.4f}  SE {se:.4f}  t {b/se:+.2f}  p {r.pvalues[k]:.4f}"
    L.append(row('Current spec  M3 intercept', m3_cur, 0))
    L.append(row('Current spec  M3 b_market (logit q)', m3_cur, 1))
    L.append(row('Current spec  M3 b_model', m3_cur, 2))
    L.append(row('Consistent    M3 intercept', m3_con, 0))
    L.append(row('Consistent    M3 b_market (logit market_score)', m3_con, 1))
    L.append(row('Consistent    M3 b_model', m3_con, 2))
    L.append(row('Current spec  M1 b_market (logit q)', m1_cur, 1))
    L.append(row('Consistent    M1 b_market (logit market_score)', m1_con, 1))
    L.append(f"  Log-likelihood M3: current {m3_cur.llf:.2f}   consistent {m3_con.llf:.2f}")
    L.append(f"  Log-likelihood M1: current {m1_cur.llf:.2f}   consistent {m1_con.llf:.2f}")

    # ---------- C. OOS, live rule
    H('C. OUT-OF-SAMPLE LIVE RULE: EPL-only fit on 2020-21..2023-24 -> test 2024-25 & 2025-26, range guard')
    keep = ['date', 'home_team', 'away_team', 'close_prob_side', 'move_side', 'calibrated_edge',
            'pin_ah_home', 'pin_ah_away', 'avg_ah_home', 'avg_ah_away', 'odds_ah_home', 'odds_ah_away']
    clv = pd.read_csv('output/backtest_results/clv_edge_matches.csv')
    clv = clv[clv.league == 'EPL'][keep].rename(columns={'calibrated_edge': 'edge_all_leagues'})
    tr, te = e[e.season.isin(TRAIN)], e[e.season.isin(TEST)].copy()
    te = te.merge(clv, on=['date', 'home_team', 'away_team'], how='left')
    lo99 = np.percentile(tr.market_prob_novig, [1, 99])
    te = te[te.market_prob_novig.between(*lo99)].copy()
    home = te.bet_side == 'home'
    prices = {'B365 pre': te.market_odds,
              'Pinnacle pre': pd.Series(np.where(home, te.pin_ah_home, te.pin_ah_away), index=te.index),
              'Avg pre': pd.Series(np.where(home, te.avg_ah_home, te.avg_ah_away), index=te.index)}
    # Session 18: football-data Pinnacle/Avg prices > 1.3x Bet365 are data errors (e.g. 4.43 v 1.98) - drop them
    for k in ('Pinnacle pre', 'Avg pre'):
        prices[k] = prices[k].where(~(prices[k] / prices['B365 pre'] > 1.3))
    prices['Best of 3'] = pd.concat(prices.values(), axis=1).max(axis=1)
    for k, v in prices.items():
        te['clv_' + k] = v * te.close_prob_side - 1
    fits = {}
    for name, mcol in [('current', 'market_prob_novig'), ('consistent', 'market_score')]:
        r = fit(tr.actual_score, {'a': logit(tr[mcol]), 'b': logit(tr.model_prob)})
        fits[name] = r
        te['edge_' + name] = sig(r.params[0] + r.params[1] * logit(te[mcol]) + r.params[2] * logit(te.model_prob)) - te[mcol]
    r = fits['current']
    L.append(f"  Train EPL-only M3 (current spec): intercept {r.params[0]:+.4f}  b_market {r.params[1]:.4f}  b_model {r.params[2]:.4f}")
    L.append(f"  Range guard (train 1st-99th pct of q): [{lo99[0]:.4f}, {lo99[1]:.4f}].  Test matches in range: {len(te)}")
    L.append('  move = closing no-vig prob of bet side (Pinnacle close, fallback avg, converted to the bet line) - pre no-vig prob')
    L.append('  CLV@X = price X * closing prob - 1.  Pinnacle median margin ~2.5%, B365 ~3.6%, avg ~5.1%.  +/- = 1 SE')
    ms = lambda x: (lambda y: f"{y.mean():+.2%}+/-{y.std()/math.sqrt(len(y)):.2%}")(x.dropna())
    L.append(f"  {'rule (current spec)':<20}{'n':>5}{'move':>15}" + ''.join(f"{'CLV@'+k:>17}" for k in prices) + f"{'ROI':>8}")
    rows = [('all test matches', te)]
    rows += [(f'edge >= {t:.1%}', te[te.edge_current.round(6) >= t]) for t in (0.01, 0.015, 0.02, 0.025, 0.03)]
    rows += [('edge 1%-2% band', te[(te.edge_current >= 0.01) & (te.edge_current < 0.02)])]
    rows += [('s16 all-lg >= 1%', te[te.edge_all_leagues >= 0.01])]
    for name, f in rows:
        L.append(f"  {name:<20}{len(f):>5}{ms(f.move_side):>15}" + ''.join(f"{ms(f['clv_'+k]):>17}" for k in prices)
                 + f"{f.pnl_flat10.sum()/10/len(f):>+8.1%}")
    for s_ in TEST:
        f = te[(te.season == s_) & (te.edge_current.round(6) >= THRESH)]
        L.append(f"  live rule {s_}: n {len(f)}  move {ms(f.move_side)}  CLV@Pinnacle {ms(f['clv_Pinnacle pre'])}")
    f = te[te.edge_consistent.round(6) >= THRESH]
    L.append(f"  Push-consistent spec, edge >= 1%: n {len(f)}  move {ms(f.move_side)}  CLV@Pinnacle {ms(f['clv_Pinnacle pre'])}  "
             f"(overlap with current {int(((te.edge_current.round(6)>=THRESH)&(te.edge_consistent.round(6)>=THRESH)).sum())})")
    L.append('  Reconciliation: July 2026 "92/season, +8.9%" = current-spec EPL fit, no range guard (183 bets).')
    L.append('  Session-16 "44 flagged, +0.7%" = ALL-LEAGUES fit edge (recalibrated_test_matches.csv calibrated_edge), a')
    L.append('  stricter subset of the live rule. Neither is the live rule; the rows above are.')

    # ---------- D. live log
    H('D. LIVE LOG 2026-27: current edge vs push-consistent edge (consistent spec refit on all 6 seasons)')
    log = pd.read_csv('output/paper_trading/log_ah.csv')
    log = log[log.prediction_date >= '2026-08-01']
    L.append(f"  {'match':<36}{'bet':>15}{'q':>8}{'P_push':>8}{'gap':>8}{'edge now':>10}{'edge cons':>10}{'flag now':>9}{'flag cons':>10}")
    for _, r in log.iterrows():
        side = r.bet_side
        q = r.market_prob_consensus
        msc, pp = market_score_side(q, r.ah_line, side)
        mp = r.model_prob_ah
        # model_prob_ah in the log is the raw model score of the bet side (p_side + 0.5 p_push)
        cp_con = sig(m3_con.params[0] + m3_con.params[1] * logit(msc) + m3_con.params[2] * logit(mp))
        e_con = cp_con - msc
        team = r.home_team if side == 'home' else r.away_team
        bl = r.ah_line if side == 'home' else -r.ah_line
        flag_now = 'BET' if str(r.bet_flag) == 'True' else ('veto' if isinstance(r.notes, str) else '-')
        flag_con = 'BET' if (round(e_con, 6) >= THRESH and flag_now != 'veto') else ('veto' if flag_now == 'veto' else '-')
        L.append(f"  {r.home_team[:16]+' v '+r.away_team[:16]:<36}{team[:9]+f' {bl:+.2f}':>15}{q:>8.4f}{pp:>8.3f}"
                 f"{msc-q:>+8.4f}{r.calib_edge:>+10.4f}{e_con:>+10.4f}{flag_now:>9}{flag_con:>10}")
    L.append('')
    open(OUT, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
