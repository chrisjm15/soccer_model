"""Live status of the EPL AH paper-trading season. READ-ONLY: never writes the log.

Run:  python scripts/live_status.py      (or double-click STATUS.bat)

Sections
  1. Automation health  - last scheduled runs from output/scheduler_log.txt
  2. Flagged bets       - results and P/L (flat $10), current model only (prediction_date >= 2026-08-01)
  3. Checkpoint metric  - mean clv_price on flagged bets vs the ~40-bet Feb 2027 rule, split by edge band
  4. Model signal live  - clv_move ~ calib_edge across every logged match (historical OOS slope +0.67)
  5. AU prices          - from output/paper_trading/au_prices.csv (scripts/au_prices.py)
  6. Luck shadow test   - scripts/luck_shadow.py (writes output/paper_trading/luck_shadow.csv only)
"""
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import au_prices  # noqa: E402

LOG = PROJECT / 'output' / 'paper_trading' / 'log_ah.csv'
SCHED = PROJECT / 'output' / 'scheduler_log.txt'
SEASON_START = '2026-08-01'
CHECKPOINT_N = 40


def mean_se(x):
    x = pd.to_numeric(x, errors='coerce').dropna()
    n = len(x)
    if n == 0:
        return n, float('nan'), float('nan')
    sd = x.std(ddof=1) if n > 1 else float('nan')
    return n, x.mean(), sd / math.sqrt(n) if n > 1 else float('nan')


def fmt_pct(m, se):
    if math.isnan(m):
        return 'n/a'
    return f'{m:+.2%}' + ('' if math.isnan(se) else f' (SE {se:.2%})')


def section(title):
    print()
    print('=' * 78)
    print('  ' + title)
    print('=' * 78)


def automation():
    section('1. AUTOMATION (scheduled runs)')
    if not SCHED.exists():
        print('  scheduler_log.txt not found')
        return
    lines = SCHED.read_text(encoding='utf-8', errors='replace').splitlines()
    starts = [l for l in lines if 'Task started (mode:' in l]
    for l in starts[-4:]:
        print('  ' + l)
    bad = [l for l in lines[-40:] if 'exit code: ' in l and 'exit code: 0)' not in l]
    bad += [l for l in lines[-40:] if 'failed' in l.lower()]
    print('  Recent failures: ' + ('NONE' if not bad else ''))
    for l in bad:
        print('    ' + l)
    last = {}
    for l in starts:
        try:
            ts = datetime.strptime(l[1:20], '%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue
        last['predict' if 'predict' in l else 'settle'] = ts
    now = datetime.now()
    for mode, limit in (('predict', 8), ('settle', 8)):
        if mode in last:
            age = (now - last[mode]).days
            warn = '  <-- OVERDUE: check Task Scheduler' if age >= limit else ''
            print(f'  Last {mode}: {last[mode]:%a %d %b %H:%M} ({age} days ago){warn}')


def flagged_section(cur):
    section('2. FLAGGED BETS - current model (flat $10 stake)')
    f = cur[cur['bet_flag'].astype(str) == 'True']
    settled = f[f['actual_ah_result'].notna() & (f['actual_ah_result'].astype(str) != '')]
    pending = f.drop(settled.index)
    pnl = pd.to_numeric(settled['profit_loss'], errors='coerce').fillna(0)
    print(f'  Flagged: {len(f)}   settled: {len(settled)}   pending: {len(pending)}')
    if len(settled):
        print(f"  Results: {', '.join(f'{k} {int(v)}' for k, v in settled['actual_ah_result'].value_counts().items())}")
        print(f'  P/L: ${pnl.sum():+.2f} on ${10*len(settled):.0f} staked  ROI {pnl.sum()/(10*len(settled)):+.1%}'
              '   (ROI is noise at this sample size - decide on CLV)')
    for _, r in f.iterrows():
        team = r['home_team'] if r['bet_side'] == 'home' else r['away_team']
        line = au_prices.bet_line(r['ah_line'], r['bet_side'])
        res = r['actual_ah_result'] if isinstance(r['actual_ah_result'], str) else 'pending'
        clv = pd.to_numeric(pd.Series([r.get('clv_price')]), errors='coerce').iloc[0]
        clv_s = 'n/a' if pd.isna(clv) else f'{clv:+.1%}'
        print(f"    {r['match_date']}  {team} {line:+.2f} @ {float(r['odds_ah']):.2f}  edge {float(r['calib_edge']):+.1%}"
              f"  -> {res:<9} CLV {clv_s}")


def checkpoint(cur):
    section(f'3. CHECKPOINT METRIC: mean clv_price on flagged bets (target n~{CHECKPOINT_N}, ~Feb 2027)')
    f = cur[cur['bet_flag'].astype(str) == 'True'].copy()
    n, m, se = mean_se(f['clv_price'])
    print(f'  All flagged (live 1% rule): n={n}/{CHECKPOINT_N}  mean {fmt_pct(m, se)}')
    edge = pd.to_numeric(f['calib_edge'], errors='coerce')
    for name, mask in (('edge 1%-2%', edge < 0.02), ('edge >= 2% (shadow)', edge >= 0.02)):
        n2, m2, se2 = mean_se(f.loc[mask, 'clv_price'])
        print(f'    {name:<20} n={n2:<3} mean {fmt_pct(m2, se2)}')
    print('  Rule at n~40: > +1% -> plan real stakes; <= 0 -> edge does not survive our prices; between -> continue.')
    print('  Note: clv_price uses the LOGGED BEST price (mostly offshore). AU prices are lower - see section 5.')
    print('  Historical expectation for this exact rule (OOS 2024-26, live_rule_oos_report.txt): CLV at')
    print('  Pinnacle pre-close -1.6% (SE 0.7%), best of B365/Pinnacle/avg -0.3% (SE 1.0%); edge >= 2%: -0.7% / +0.9%.')


def signal(cur):
    section('4. MODEL SIGNAL LIVE: does the market move toward the model? (all logged matches)')
    d = cur[['calib_edge', 'clv_move']].apply(pd.to_numeric, errors='coerce').dropna()
    n = len(d)
    print(f'  Matches with closing data: {n}   mean clv_move {d.clv_move.mean():+.2%}' if n else '  No data yet')
    if n >= 5:
        x, y = d.calib_edge.values, d.clv_move.values
        xc = x - x.mean()
        b = (xc * (y - y.mean())).sum() / (xc ** 2).sum()
        a = y.mean() - b * x.mean()
        resid = y - a - b * x
        se = math.sqrt((resid ** 2).sum() / (n - 2) / (xc ** 2).sum()) if n > 2 else float('nan')
        print(f'  Slope clv_move ~ calib_edge: {b:+.3f} (SE {se:.3f}, t {b/se:+.2f})')
        print('  Historical OOS benchmark: +0.67 (t 3.8). Needs ~200+ matches before the slope means much.')


def main():
    print(f'SOCCER MODEL - LIVE STATUS   {datetime.now():%a %d %b %Y %H:%M}')
    log = pd.read_csv(LOG)
    cur = log[log['prediction_date'].astype(str) >= SEASON_START].copy()
    automation()
    flagged_section(cur)
    checkpoint(cur)
    signal(cur)
    section('5. AU PRICES (flagged bets)')
    au_prices.cmd_report()
    section('6. LUCK SHADOW TEST (pre-registered 2026-10-28, separate from the model)')
    import luck_shadow
    try:
        print('\n'.join(luck_shadow.report_lines(luck_shadow.build())))
    except Exception as exc:  # never let the shadow break the status report
        print(f'  luck shadow failed: {exc}')
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
