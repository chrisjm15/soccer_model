"""Gold test for scrapers/understat_lineups.parse_rosters against a real page extract (Liverpool 4-2 Bournemouth,
2025-08-15, understat match 28778, fetched 2026-10-29). Values read off the page by hand."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scrapers.understat_lineups import parse_rosters, valid

html = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'understat_match_28778_rosters.html'),
            encoding='utf-8').read()
rows = parse_rosters(html)
fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}"); cond or fails.append(name)

h = [r for r in rows if r['side'] == 'h']; a = [r for r in rows if r['side'] == 'a']
check('home: 16 players listed, 11 starters', len(h) == 16 and sum(r['starter'] for r in h) == 11)
check('away: 15 players listed, 11 starters', len(a) == 15 and sum(r['starter'] for r in a) == 11)
check('valid() true', valid(rows))
al = next(r for r in h if r['player'] == 'Alisson')
check('Alisson GK starter 90 min id 1257', (al['position'], al['starter'], al['minutes'], al['player_id']) == ('GK', 1, 90, 1257))
en = next(r for r in h if r['player'] == 'Wataru Endo')
check('Endo Sub 27 min', (en['position'], en['starter'], en['minutes']) == ('Sub', 0, 27))
check('Kerkez (yellow card markup) DL 63', [(r['position'], r['minutes']) for r in h if r['player'] == 'Milos Kerkez'] == [('DL', 63)])
check('Konaté accent kept', any(r['player'] == 'Ibrahima Konaté' for r in h))
check('away GK Petrovic starter', any(r['player'] == 'Djordje Petrovic' and r['position'] == 'GK' for r in a))
check('empty html -> []', parse_rosters('<html></html>') == [])
print('\nALL LINEUP PARSER TESTS PASSED' if not fails else f'\nFAILED: {fails}')
sys.exit(1 if fails else 0)
