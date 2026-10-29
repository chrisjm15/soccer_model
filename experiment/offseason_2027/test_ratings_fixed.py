"""GOLD TESTS for experiment/offseason_2027/ratings_fixed.py (Cowork session 18, hand arithmetic).
An executor may NOT edit this file. Run: python experiment/offseason_2027/test_ratings_fixed.py

Hand case (priors ah 1.60 dh 1.30 aa 1.10 da 1.50, ALPHA 0.1, SHRINK 0.3), one league L:
 S1 d1  A v B  xG 2-1  -> A ah 1.64 dh 1.27 ; B aa 1.09 da 1.55
 S1 d2  B v C  xG 1-1  -> B ah 1.54 dh 1.27 ; C aa 1.09 da 1.45
 End-of-S1 means: ah 4.78/3 = 1.593333, dh 3.84/3 = 1.28, aa 3.28/3 = 1.093333, da 4.5/3 = 1.5
 S2 d3  A v C  xG 3-0  A shrinks: ah .7*1.64+.3*1.593333 = 1.626, dh 1.273; C: aa 1.091, da 1.465
        recorded (pre-match): 1.626, 1.273, 1.091, 1.465.  Then A ah 1.7634, dh 1.1457
 S2 d4  B v A  xG 1-1  FIXED: B ah .7*1.54+.3*1.593333 = 1.556, dh .7*1.27+.3*1.28 = 1.273; A aa 1.098, da 1.5
        OLD (bug), already at d3: C's target uses A AFTER A's shrink (same match): aa mean (1.098+1.09+1.09)/3 =
        1.092667 -> C aa .763+.3278 = 1.0908 (fixed 1.091); ah mean (1.626+1.54+1.6)/3 -> C ah 1.5966, dh 1.2943.
        d4: ah mean (1.7634+1.54+1.5966)/3 = 1.633333 -> B ah 1.078+.49 = 1.568; dh mean (1.1457+1.27+1.2943)/3
        = 1.236667 -> B dh .889+.371 = 1.26
"""
import os, sys, random
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from ratings_fixed import compute_ratings_fixed, compute_ratings_old  # noqa: E402

TOL = 1e-4
fails = []


def check(name, got, exp):
    ok = abs(got - exp) < TOL
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: got {got:.6f} expected {exp:.6f}")
    if not ok:
        fails.append(name)


hand = pd.DataFrame([
    ('2020-01-01', 'L', 'S1', 'A', 'B', 2.0, 1.0),
    ('2020-01-02', 'L', 'S1', 'B', 'C', 1.0, 1.0),
    ('2020-08-01', 'L', 'S2', 'A', 'C', 3.0, 0.0),
    ('2020-08-02', 'L', 'S2', 'B', 'A', 1.0, 1.0)],
    columns=['date', 'league', 'season', 'home_team', 'away_team', 'home_xg', 'away_xg'])

print('1. Hand case - fixed function')
f = compute_ratings_fixed(hand)
for col, exp in zip(['home_attack', 'home_defence', 'away_attack', 'away_defence'], [1.626, 1.273, 1.091, 1.465]):
    check(f'd3 {col}', f.iloc[2][col], exp)
for col, exp in zip(['home_attack', 'home_defence', 'away_attack', 'away_defence'], [1.556, 1.273, 1.098, 1.5]):
    check(f'd4 {col}', f.iloc[3][col], exp)
check('d1 home_attack = prior', f.iloc[0].home_attack, 1.60)

print('2. Hand case - old function shows the bug (documents what changes)')
o = compute_ratings_old(hand)
check('old d3 home_attack (same as fixed)', o.iloc[2].home_attack, 1.626)
check('old d3 away_attack (bug, same-match order)', o.iloc[2].away_attack, 1.0908)
check('old d4 home_attack (bug)', o.iloc[3].home_attack, 1.568)
check('old d4 home_defence (bug)', o.iloc[3].home_defence, 1.26)

print('3. Order independence: shuffle rows within each date (real data, 2 seasons EPL + La Liga)')
real = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'data', 'processed', 'all_merged.csv')
m = pd.read_csv(real).dropna(subset=['home_xg', 'away_xg'])
m = m[m.league.isin(['EPL', 'La_Liga']) & m.season.isin(['2023-24', '2024-25'])].reset_index(drop=True)
key = ['date', 'league', 'home_team', 'away_team']
NUM = ['home_attack', 'home_defence', 'away_attack', 'away_defence']
base = compute_ratings_fixed(m).assign(date=lambda x: x.date.astype(str)).set_index(key)[NUM].sort_index()
random.seed(7)
for trial in range(3):
    sh = m.sample(frac=1, random_state=trial).sort_values('date', kind='stable')
    r = compute_ratings_fixed(sh).assign(date=lambda x: x.date.astype(str)).set_index(key)[NUM].sort_index()
    check(f'fixed, shuffle {trial}: max |diff|', float((r - base.reindex(r.index))[['home_attack', 'home_defence', 'away_attack', 'away_defence']].abs().max().max()), 0.0)
ob = compute_ratings_old(m).assign(date=lambda x: x.date.astype(str)).set_index(key)[NUM].sort_index()
osh = compute_ratings_old(m.sample(frac=1, random_state=0).sort_values('date', kind='stable')).assign(date=lambda x: x.date.astype(str)).set_index(key)[NUM].sort_index()
d_old = float((osh - ob.reindex(osh.index))[['home_attack', 'home_defence', 'away_attack', 'away_defence']].abs().max().max())
print(f"  INFO  old function, same shuffle: max |diff| {d_old:.6f} (> 0 confirms the bug on real data)")
if d_old == 0:
    print('  NOTE  old function happened to be order-stable on this shuffle')

print('4. No difference before the first season transition')
first = m[m.season == '2023-24']
a, b = compute_ratings_fixed(first), compute_ratings_old(first)
check('season 1 only: max |fixed - old|', float((a[['home_attack', 'away_defence']].values - b[['home_attack', 'away_defence']].values).__abs__().max()), 0.0)

print('5. Team returning after a season away (deliberate change: target = LAST season\'s league means)')
# S1 A v D 1-1 ; S2 A v B 2-0 (D absent) ; S3 B v D 0-0.  S2 end: A aa 1.0985 da 1.4925, B aa 0.99 da 1.55
# -> means aa 1.04425 da 1.52125.  D end-S1 aa 1.09 da 1.45 -> D aa .763+.313275 = 1.076275, da 1.015+.456375 = 1.471375
# Old: target = D's own last season (S1) with LIVE ratings {A 1.0985, D 1.09} -> aa mean 1.09425 -> 1.091275
# B (played S2): ah .7*1.6 + .3*(1.5941+1.6)/2 = 1.599115 (same in old and fixed)
ret = pd.DataFrame([('2020-01-01', 'L', 'S1', 'A', 'D', 1.0, 1.0), ('2021-01-01', 'L', 'S2', 'A', 'B', 2.0, 0.0),
                    ('2022-01-01', 'L', 'S3', 'B', 'D', 0.0, 0.0)],
                   columns=['date', 'league', 'season', 'home_team', 'away_team', 'home_xg', 'away_xg'])
fr, orr = compute_ratings_fixed(ret), compute_ratings_old(ret)
check('fixed S3 D away_attack', fr.iloc[2].away_attack, 1.076275)
check('fixed S3 D away_defence', fr.iloc[2].away_defence, 1.471375)
check('fixed S3 B home_attack', fr.iloc[2].home_attack, 1.599115)
check('old S3 D away_attack (own-last-season target)', orr.iloc[2].away_attack, 1.091275)
check('old S3 B home_attack', orr.iloc[2].home_attack, 1.599115)

print('\nALL RATINGS GOLD TESTS PASSED' if not fails else f'\nFAILED: {fails}')
sys.exit(1 if fails else 0)
