"""RESEARCH ONLY - starting lineups from Understat match pages (Cowork session 18, 2026-10-29).
Not used by run.py or the live model. Feeds scripts/lineup_research.py.

  python scrapers/understat_lineups.py probe     (first match of each season, writes nothing)
  python scrapers/understat_lineups.py fetch [--seasons 2020-21,2021-22,...] [--limit N]
Reads match ids from data/raw/understat/EPL_*.csv, fetches https://understat.com/match/<id> (one request every
~1.5 s), parses both rosters and appends to data/raw/understat_lineups/EPL_lineups.csv. Resumable: matches already
in the file are skipped. Stops after 10 failures in a row (site down / blocked).
Rows: match_id, side (h/a), player_id, player, position, starter (1/0), minutes.
"""
import csv, glob, os, re, sys, time

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(PROJECT, 'data', 'raw', 'understat_lineups', 'EPL_lineups.csv')
FIELDS = ['match_id', 'side', 'player_id', 'player', 'position', 'starter', 'minutes']
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
DELAY = 1.5
PLAYER = re.compile(r'<label class="player" data-id="(\d+)".*?player-position">([^<]+)<.*?player-name">([^<]+)<'
                    r'.*?player-time">\s*(\d+)\'', re.S)


def parse_rosters(html):
    """Returns list of dicts (side, player_id, player, position, starter, minutes). [] if no roster section."""
    i = html.find('<div class="roster roster-home">')
    k = html.find('<div class="roster roster-away">')
    if i < 0 or k < 0:
        return []
    out = []
    for side, seg in (('h', html[i:k]), ('a', html[k:])):
        for pid, pos, name, mins in PLAYER.findall(seg):
            pos = pos.strip()
            out.append({'side': side, 'player_id': int(pid), 'player': name.strip(), 'position': pos,
                        'starter': int(pos != 'Sub'), 'minutes': int(mins)})
    return out


def parse_api(data):
    """Fallback if the page HTML has no roster section: Understat's AJAX endpoint getMatchData/<id> (shape not
    verified - accepted only if it yields 11 starters per side). Expected: {'rosters': {'h': {..}, 'a': {..}}}."""
    out = []
    ros = (data or {}).get('rosters') or {}
    for side in ('h', 'a'):
        for p in (ros.get(side) or {}).values():
            pos = str(p.get('position', '')).strip()
            out.append({'side': side, 'player_id': int(p.get('player_id', 0)), 'player': str(p.get('player', '')).strip(),
                        'position': pos, 'starter': int(pos != 'Sub'), 'minutes': int(float(p.get('time', 0) or 0))})
    return out


def get_rows(mid, session):
    r = session.get(f'https://understat.com/match/{mid}', headers=HEADERS, timeout=30)
    r.raise_for_status()
    rows = parse_rosters(r.text)
    if rows and valid(rows):
        return rows, 'html'
    try:
        j = session.get(f'https://understat.com/getMatchData/{mid}',
                        headers={**HEADERS, 'X-Requested-With': 'XMLHttpRequest'}, timeout=30)
        rows = parse_api(j.json()) if j.ok else []
        if rows and valid(rows):
            return rows, 'api'
    except Exception:
        pass
    return [], 'none'


def probe():
    """Fetch the first match of each season and say which route worked. Writes nothing."""
    import requests
    s = requests.Session()
    ids = {}
    for f in sorted(glob.glob(os.path.join(PROJECT, 'data', 'raw', 'understat', 'EPL_20*.csv'))):
        with open(f, encoding='utf-8') as fh:
            first = next(csv.DictReader(fh), None)
            if first:
                ids[first['season']] = int(first['match_id'])
    good = 0
    for season, mid in ids.items():
        try:
            rows, how = get_rows(mid, s)
        except Exception as e:
            rows, how = [], f'error {e}'
        st = [r['player'] for r in rows if r['starter'] and r['side'] == 'h']
        print(f'  {season} match {mid}: {how:<5} home starters {len(st)}  {", ".join(st[:3])}')
        good += bool(rows)
        time.sleep(DELAY)
    print('PROBE OK' if good == len(ids) else f'PROBE FAILED for {len(ids) - good} season(s) - stop and tell Claude.')
    return 0 if good == len(ids) else 1


def valid(rows):
    """Both sides must have exactly 11 starters."""
    return all(sum(r['starter'] for r in rows if r['side'] == s) == 11 for s in ('h', 'a'))


def match_ids(seasons=None):
    ids = []
    for f in sorted(glob.glob(os.path.join(PROJECT, 'data', 'raw', 'understat', 'EPL_20*.csv'))):
        with open(f, encoding='utf-8') as fh:
            for r in csv.DictReader(fh):
                if (seasons is None or r['season'] in seasons) and r.get('home_goals', '') not in ('', None):
                    ids.append(int(r['match_id']))
    return ids


def done_ids():
    if not os.path.exists(OUT):
        return set()
    with open(OUT, encoding='utf-8') as fh:
        return {int(r['match_id']) for r in csv.DictReader(fh)}


def fetch(seasons=None, limit=None):
    import requests
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    todo = [m for m in match_ids(seasons) if m not in done_ids()]
    if limit:
        todo = todo[:limit]
    print(f'{len(todo)} matches to fetch (about {len(todo) * DELAY / 60:.0f} minutes).', flush=True)
    new_file = not os.path.exists(OUT)
    fails, ok, bad = 0, 0, []
    sess = requests.Session()
    with open(OUT, 'a', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        for n, mid in enumerate(todo, 1):
            try:
                rows, how = get_rows(mid, sess)
                if not rows:
                    bad.append(mid); fails += 1
                else:
                    for x in rows:
                        w.writerow({'match_id': mid, **x})
                    fh.flush(); ok += 1; fails = 0
            except Exception as e:
                print(f'  match {mid}: {e}', flush=True); fails += 1
            if fails >= 10:
                print('STOPPED: 10 failures in a row (site down or blocking). Run again later - it resumes.'); break
            if n % 100 == 0:
                print(f'  {n}/{len(todo)} done', flush=True)
            time.sleep(DELAY)
    print(f'Fetched {ok} matches. Not 11 starters / no roster: {len(bad)} {bad[:10]}')
    return 0 if fails < 10 else 1


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'probe':
        sys.exit(probe())
    if len(sys.argv) > 1 and sys.argv[1] == 'fetch':
        seasons = None
        if '--seasons' in sys.argv:
            seasons = set(sys.argv[sys.argv.index('--seasons') + 1].split(','))
        limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
        sys.exit(fetch(seasons, limit))
    print(__doc__)
