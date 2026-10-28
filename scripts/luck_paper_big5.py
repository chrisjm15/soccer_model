"""LUCK PAPER LOG - La Liga, Bundesliga, Serie A, Ligue 1 (Cowork session 17, 2026-10-28). Paper only.
Same pre-registered rule as scripts/luck_shadow.py (EPL), extended to the other Big 5 leagues to get ~4x the sample.
Never touches the live model, run.py or output/paper_trading/log_ah.csv.

FIXED RULE (registered 2026-10-28, do not tune mid-season):
  luck(team) = EMA alpha 0.10 of (goals for - xG for) minus EMA of (goals against - xG against), pre-match, all
               Big-5 matches in data/processed/all_merged.csv.   luck_diff = luck(home) - luck(away)
  bet        = back the LESS lucky side on the main AH line when |luck_diff| >= 0.40,
               at the best price found at the Friday run (first sighting locks the row, like the live log).
  Every fixture is logged (flagged or not) so the market-movement test can use all of them.
VERDICT (with the EPL shadow, season end): pooled mean clv_price > 0 AND ROI > 0 -> build into the 2027-28 model.
  Historical expectation (2020-26): ex-EPL ROI +1.7% at average prices, +2.6% at Pinnacle; EPL +7.9%.

Modes:   python scripts/luck_paper_big5.py log [--dry-run]   (Friday, after the predict run; uses ~8 Odds API credits)
         python scripts/luck_paper_big5.py settle            (Tuesday, after run.py update)
         python scripts/luck_paper_big5.py report
Log: output/paper_trading/luck_big5_log.csv
"""
import math, os, sys, unicodedata, difflib
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(Path(__file__).resolve().parent))
os.chdir(PROJECT)

ALPHA, THRESH = 0.10, 0.40
LEAGUES = {'La_Liga': 'soccer_spain_la_liga', 'Bundesliga': 'soccer_germany_bundesliga',
           'Serie_A': 'soccer_italy_serie_a', 'Ligue_1': 'soccer_france_ligue_one'}
REGIONS = 'uk,eu'   # 2 credits per league per run; AU books carry no AH for these leagues
LOG = PROJECT / 'output' / 'paper_trading' / 'luck_big5_log.csv'
MERGED = PROJECT / 'data' / 'processed' / 'all_merged.csv'
COLS = ['prediction_date', 'match_date', 'league', 'home_team', 'away_team', 'api_home', 'api_away', 'ah_line',
        'odds_home_best', 'odds_away_best', 'book_home', 'book_away', 'n_books', 'market_prob_home',
        'luck_home', 'luck_away', 'luck_diff', 'shadow_side', 'shadow_flag', 'shadow_odds', 'market_prob_side',
        'home_goals', 'away_goals', 'result', 'pnl_unit', 'closing_line', 'closing_home_odds', 'closing_away_odds',
        'closing_source', 'clv_move', 'clv_price']


# ---------------------------------------------------------------------------------------------- pure helpers
def _plain(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    for w in (' fc', 'fc ', ' cf', 'cf ', ' ac', ' as ', 'as ', ' ssc', 'ssc ', ' calcio', ' 1913', ' 1907', ' 1909'):
        s = s.replace(w, ' ')
    return ' '.join(s.replace('-', ' ').replace('.', ' ').split())


MANUAL = {'inter milan': 'Inter', 'internazionale': 'Inter', 'rb leipzig': 'RasenBallsport Leipzig',
          'borussia monchengladbach': 'Borussia M.Gladbach', 'koln': 'FC Cologne', '1 koln': 'FC Cologne',
          'athletic bilbao': 'Athletic Club', 'paris saint germain': 'Paris Saint Germain', 'psg': 'Paris Saint Germain',
          'parma': 'Parma Calcio 1913', 'hellas verona': 'Verona', 'tsg hoffenheim': 'Hoffenheim',
          '1899 hoffenheim': 'Hoffenheim', 'mainz': 'Mainz 05', 'deportivo': 'Deportivo La Coruna',
          'racing': 'Racing Santander', 'sc paderborn': 'Paderborn', 'paderborn 07': 'Paderborn'}


def map_name(api_name, league, canon):
    """Odds API name -> canonical all_merged name. Alias table first, then manual, then normalised fuzzy."""
    try:
        from scrapers.team_name_mapper import map_team_name
        m = map_team_name(api_name, league)
        if m in canon:
            return m
    except Exception:
        pass
    p = _plain(api_name)
    if p in MANUAL and MANUAL[p] in canon:
        return MANUAL[p]
    plain = {_plain(c): c for c in canon}
    if p in plain:
        return plain[p]
    hit = difflib.get_close_matches(p, list(plain), n=1, cutoff=0.8)
    return plain[hit[0]] if hit else None


def luck_state(history, before_date, alpha=ALPHA):
    """{team: net luck} using matches dated strictly before before_date (string YYYY-MM-DD)."""
    st = {}
    for r in history[history['date'] < before_date].itertuples(index=False):
        x = st.setdefault(r.home_team, [0.0, 0.0]); y = st.setdefault(r.away_team, [0.0, 0.0])
        x[0] = alpha * (r.home_goals - r.home_xg) + (1 - alpha) * x[0]
        x[1] = alpha * (r.away_goals - r.away_xg) + (1 - alpha) * x[1]
        y[0] = alpha * (r.away_goals - r.away_xg) + (1 - alpha) * y[0]
        y[1] = alpha * (r.home_goals - r.home_xg) + (1 - alpha) * y[1]
    return {t: v[0] - v[1] for t, v in st.items()}


def shadow_pick(luck_home, luck_away, odds_home, odds_away, q_home):
    """Returns (luck_diff, side, flag, odds, market_prob_side). Ties (diff == 0) go away, as luck_shadow.py."""
    diff = luck_home - luck_away
    side = 'home' if diff < 0 else 'away'
    return (diff, side, abs(diff) >= THRESH, odds_home if side == 'home' else odds_away,
            q_home if side == 'home' else 1 - q_home)


def settle_row(row, sr):
    """row: log row (dict-like). sr: all_merged row (dict-like). Returns dict of settlement fields or {}."""
    from run import _calculate_ah
    from model.clv import clv_for_row
    out = {}
    try:
        hg, ag = int(sr['home_goals']), int(sr['away_goals'])
    except (TypeError, ValueError):
        return out
    out['home_goals'], out['away_goals'] = hg, ag
    res, pnl = _calculate_ah(hg, ag, float(row['ah_line']), row['shadow_side'], float(row['shadow_odds']), stake=1.0)
    out['result'], out['pnl_unit'] = res, pnl
    def ok(v):
        try:
            v = float(v); return v if v > 1.0 and not math.isnan(v) else None
        except (TypeError, ValueError):
            return None
    cl = sr.get('close_ah_line')
    try:
        cl = float(cl)
    except (TypeError, ValueError):
        return out
    if math.isnan(cl):
        return out
    ph, pa, ah, aa = (ok(sr.get(k)) for k in ('close_pin_ah_home', 'close_pin_ah_away', 'close_avg_ah_home', 'close_avg_ah_away'))
    if ph and pa:
        src, ch, ca = 'pinnacle', ph, pa
    elif ah and aa:
        src, ch, ca = 'avg', ah, aa
    else:
        return out
    c = clv_for_row(bet_side=row['shadow_side'], bet_line=float(row['ah_line']), bet_odds=float(row['shadow_odds']),
                    bet_market_prob=float(row['market_prob_side']), close_line=cl, close_home_odds=ch, close_away_odds=ca)
    out.update({'closing_line': cl, 'closing_home_odds': ch, 'closing_away_odds': ca, 'closing_source': src,
                'clv_move': c['clv_move'], 'clv_price': c['clv_price']})
    return out


# ---------------------------------------------------------------------------------------------- I/O
def read_log():
    if LOG.exists():
        return pd.read_csv(LOG, dtype=str, keep_default_na=False)
    return pd.DataFrame(columns=COLS)


def history():
    h = pd.read_csv(MERGED).dropna(subset=['home_xg', 'away_xg', 'home_goals', 'away_goals'])
    h['date'] = pd.to_datetime(h['date']).dt.strftime('%Y-%m-%d')
    return h.sort_values('date', kind='stable')


def cmd_log(dry_run=False, fetch=None):
    from model.calibration import consensus_novig
    if fetch is None:
        try:
            from dotenv import load_dotenv; load_dotenv()
        except ImportError:
            pass
        key = os.environ.get('ODDS_API_KEY')
        if not key:
            print('ERROR: ODDS_API_KEY not set (.env)'); return 1
        from scrapers.odds_api import fetch_epl_ah_odds
        fetch = lambda sport, lg: fetch_epl_ah_odds(key, sport, lg, regions=REGIONS)
    h = history()
    merged_all = pd.read_csv(MERGED)
    log = read_log()
    seen = set(zip(log.match_date, log.home_team, log.away_team))
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    new, unmapped = [], []
    for lg, sport in LEAGUES.items():
        canon = set(merged_all[(merged_all.league == lg) & (merged_all.season == merged_all[merged_all.league == lg].season.max())][['home_team', 'away_team']].values.ravel())
        for m in fetch(sport, lg) or []:
            ht, at = map_name(m['home_team'], lg, canon), map_name(m['away_team'], lg, canon)
            if ht is None or at is None:
                unmapped.append(f"{lg}: {m['home_team'] if ht is None else ''} {m['away_team'] if at is None else ''}".strip())
                continue
            if (m['date'], ht, at) in seen:
                continue
            luck = luck_state(h, m['date'])
            q = consensus_novig(m['book_prices'])
            diff, side, flag, odds, qs = shadow_pick(luck.get(ht, 0.0), luck.get(at, 0.0),
                                                     m['odds_ah_home_best'], m['odds_ah_away_best'], q)
            row = {c: '' for c in COLS}
            row.update({'prediction_date': today, 'match_date': m['date'], 'league': lg, 'home_team': ht, 'away_team': at,
                        'api_home': m['home_team'], 'api_away': m['away_team'], 'ah_line': m['ah_line'],
                        'odds_home_best': m['odds_ah_home_best'], 'odds_away_best': m['odds_ah_away_best'],
                        'book_home': m['best_home_book'], 'book_away': m['best_away_book'], 'n_books': m['n_bookmakers'],
                        'market_prob_home': round(q, 6), 'luck_home': round(luck.get(ht, 0.0), 4),
                        'luck_away': round(luck.get(at, 0.0), 4), 'luck_diff': round(diff, 4), 'shadow_side': side,
                        'shadow_flag': flag, 'shadow_odds': odds, 'market_prob_side': round(qs, 6)})
            new.append(row); seen.add((m['date'], ht, at))
    print(f'Luck paper log: {len(new)} new fixtures, {sum(r["shadow_flag"] for r in new)} flagged.')
    for r in new:
        if r['shadow_flag']:
            team = r['home_team'] if r['shadow_side'] == 'home' else r['away_team']
            line = float(r['ah_line']) if r['shadow_side'] == 'home' else -float(r['ah_line'])
            print(f"  {r['match_date']} {r['league']:<11} {team} {line + 0.0:+.2f} @ {r['shadow_odds']}  luck {r['luck_diff']:+.2f}")
    if unmapped:
        print('  UNMAPPED team names (fixture skipped - tell Claude):', '; '.join(unmapped))
    if dry_run:
        print('  DRY RUN - nothing written.'); return 0
    if new:
        out = pd.concat([log, pd.DataFrame(new, columns=COLS).astype(str)], ignore_index=True)
        out.to_csv(LOG, index=False)
    return 0


def cmd_settle():
    log = read_log()
    if log.empty:
        print('Luck paper log empty.'); return 0
    m = pd.read_csv(MERGED)
    m['date'] = pd.to_datetime(m['date']).dt.strftime('%Y-%m-%d')
    idx = {(r.date, r.home_team, r.away_team): r._asdict() for r in m.itertuples(index=False)}
    n = 0
    for i, row in log.iterrows():
        if row['clv_price'] != '' and row['result'] != '':
            continue
        d = row['match_date']
        alt = [(d, row.home_team, row.away_team)]
        dd = datetime.strptime(d, '%Y-%m-%d')
        for k in (-1, 1):
            alt.append(((dd + pd.Timedelta(days=k)).strftime('%Y-%m-%d'), row.home_team, row.away_team))
        sr = next((idx[k] for k in alt if k in idx), None)
        if sr is None:
            continue
        upd = settle_row(row, sr)
        for k, v in upd.items():
            log.at[i, k] = '' if v is None else str(round(v, 6) if isinstance(v, float) else v)
        n += bool(upd)
    log.to_csv(LOG, index=False)
    print(f'Luck paper log: {n} rows settled/updated.')
    return 0


def report_lines():
    log = read_log()
    L = [f'  Rule: back the less lucky side when |luck_diff| >= {THRESH}; La Liga, Bundesliga, Serie A, Ligue 1. Paper only.']
    if log.empty:
        return L + ['  No fixtures logged yet (first run: Friday after the predict run).']
    f = log[log.shadow_flag == 'True']
    num = lambda c: pd.to_numeric(f[c], errors='coerce').dropna()
    L.append(f'  Logged fixtures: {len(log)}   flagged: {len(f)}   settled: {(f.result != "").sum()}')
    for name, col in (('clv_price', 'clv_price'), ('clv_move', 'clv_move'), ('P/L per unit', 'pnl_unit')):
        v = num(col)
        if len(v):
            se = v.std() / math.sqrt(len(v)) if len(v) > 1 else float('nan')
            L.append(f'  {name:<13} n={len(v):<4} mean {v.mean():+.2%}' + ('' if math.isnan(se) else f' (SE {se:.2%})'))
    for lg, g in f.groupby('league'):
        p = pd.to_numeric(g.pnl_unit, errors='coerce').dropna()
        L.append(f'    {lg:<11} flagged {len(g):>3}  settled {len(p):>3}  P/L {p.sum():+.2f} units')
    return L


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'report'
    if mode == 'log':
        sys.exit(cmd_log(dry_run='--dry-run' in sys.argv))
    if mode == 'settle':
        sys.exit(cmd_settle())
    print('\n'.join(report_lines()))
