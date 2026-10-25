# Antigravity brief — Module 4: soft-league merge (Sofascore xG + football-data results/odds)

Written by Cowork 2026-10-25 (session 16). Carry out every task in order; report after each.
Repo root: `C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer`
Tier: standard. A silent bad join corrupts every later backtest, so the verification section is
not optional. Independent of the two CLV briefs — can run before or after them.

## Scope
Leagues IN: **B1, N1, P1, T1, E1** (proxy, football-data has Asian Handicap odds) and **DNK, SWE,
NOR** (Scandinavian, football-data has 1X2 only — checked by Cowork: 0 non-null AH values in every
season). Parked, do not merge: SC0, FIN.

## Inputs (already on disk — do not re-scrape)
- Sofascore xG: `data/proxy/{LG}_{YYYY-YYYY}_sofascore.csv` and `data/scandinavian/{LG}_{YYYY}_sofascore.csv`.
  Columns: date, home_team, away_team, shots/sot/corners/fouls/cards, home_xg, away_xg, league, season.
  **No goals.** xG present from 2023-24 (proxy) / 2023 (Scandinavian); DNK 2022-23 mostly present;
  earlier seasons have xG blank — expected.
- football-data: `data/proxy/{LG}_{YYYY-YY}_footballdata.csv`, `data/scandinavian/{LG}_{YYYY}_footballdata.csv`.
  Built by `experiment/load_footballdata.py` — read it. Important:
  - proxy odds are **pre-closing** (B365 → Avg fallback);
  - Scandinavian odds are **closing** (`B365CH` / `AvgCH` mapped onto `odds_home` etc.).
- Team names differ between sources, e.g. B1 `Club Brugge KV` vs `Club Brugge`, SWE `Malmö FF` vs
  `Malmo FF`, T1 `Başakşehir FK` vs `Buyuksehyr`. Some need real matching, not just accent stripping.

## Read first
`experiment/load_footballdata.py`, `scrapers/team_name_mapper.py` (existing alias pattern),
`data/aliases/team_aliases.json` (format: `{league: {source_name: canonical_name}}`),
`docs/SCANDINAVIAN_EXPANSION_SPEC.md` (Module 4 section), header of `data/processed/all_merged.csv`.

## Task 1 — Alias table
Create `data/aliases/soft_league_aliases.json`, same format as `team_aliases.json`:
`{league: {sofascore_name: footballdata_name}}`. football-data names are canonical.
Build it with a script (`experiment/build_soft_aliases.py`): exact match → accent-stripped,
case-folded, common club tokens removed (FC, IF, BK, KV, SK, FK, JK, AFC, CF, SC, K., R., Royal,
Royale, etc.) → difflib best match. Then **check it is 1-to-1 within each league-season** (no two
Sofascore names mapping to the same football-data team in one season, and every football-data
team in a season has exactly one Sofascore name).
Print the **complete** table per league (sofascore → football-data → method: exact/normalised/fuzzy
+ score) and every unmatched name. Fix fuzzy mistakes by hand-editing the JSON; say in the report
which ones you overrode and why. Cowork will review this table.

## Task 2 — Merge script `experiment/merge_data.py`
Output one file: `data/processed/soft_merged.csv`, sorted by league, date, home_team.
Join per league-season on: mapped home team + mapped away team + date within ±1 day
(Sofascore dates can be UTC-shifted). Each football-data row matches at most one Sofascore row and
vice versa; if a pair is ambiguous, keep neither and list it.
Season labels: proxy `YYYY-YY` (football-data style), Scandinavian `YYYY`.
Output columns — use the `all_merged.csv` names wherever one exists:
`date, league, season, home_team, away_team, home_goals, away_goals, home_xg, away_xg,
home_shots, away_shots, home_sot, away_sot, home_corners, away_corners, home_fouls, away_fouls,
home_yellow, away_yellow, home_red, away_red, odds_home, odds_draw, odds_away, odds_over25,
odds_under25, ah_line, odds_ah_home, odds_ah_away, odds_timing, xg_source, matched`
- `date`, goals, and odds come from football-data. xG from Sofascore. Shots/etc. from football-data
  when present, else Sofascore.
- `ah_line` = football-data `odds_ah_line` (renamed).
- `odds_timing` = `pre_closing` for proxy leagues, `closing` for DNK/SWE/NOR.
- `matched` = True if a Sofascore row joined; unmatched football-data rows are **kept** with xG blank.
- All seasons that exist in both sources are included (xG-blank seasons are useful as ratings warm-up).

## Task 3 — Verify (paste actual output)
1. Per league-season table: football-data rows, Sofascore rows, matched, match rate, rows with xG.
   Target ≥ 98% match on every season where Sofascore has xG. List every unmatched row on those
   seasons (date, teams, from which source).
2. Goals sanity: for matched rows, Sofascore has no goals, so instead check xG plausibility —
   per league-season mean home_xg and away_xg (expect ~1.2–1.7 each) and any row with xG > 6 or < 0.
3. Duplicates: zero duplicate (league, date, home_team, away_team) rows.
4. Odds coverage per league-season: non-null share of odds_home and ah_line. Confirm ah_line is
   blank for DNK/SWE/NOR and ≥ 95% present for the proxy leagues.
5. Spot-check 3 random matched rows per league against both source files (show the raw rows).
6. Confirm no input file was modified (`git status`; ignore line-ending-only changes).

## Task 4 — Commit
`data/processed/` is gitignored, so commit code + aliases only:
```
git add experiment/build_soft_aliases.py experiment/merge_data.py data/aliases/soft_league_aliases.json prompts/
git commit -m "Module 4: soft-league merge (Sofascore xG + football-data) for B1 N1 P1 T1 E1 DNK SWE NOR"
git push
```

## Not in scope (next brief, after Cowork QC of this one)
Replicating `calibration_backtest` + `recalibration_test` per league. Note for that step: the
Scandinavian test must be on 1X2, and their odds are closing prices (a harder benchmark than the
pre-closing prices used for EPL, and not prices we could have bet at).
