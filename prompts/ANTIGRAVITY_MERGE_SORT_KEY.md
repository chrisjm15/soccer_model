# Antigravity brief — Replace the ratings_backup row-order hack in scrapers/merge.py

Written by Cowork 2026-10-25 (session 16). Low priority tech debt. **Run only after
`ANTIGRAVITY_CLOSING_LINE_CLV.md` is committed** (that brief also edits merge.py).
Repo root: `C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer`. Tier: standard.

## Problem
`scrapers/merge.py` (~lines 292–309) orders `all_merged.csv` by reading `data/processed/ratings_backup.csv`
(or `ratings.csv`) and replaying that file's row order, then appends new rows by date. This was added
to keep historical ratings bit-identical. It is fragile: a stale backup dictates row order, and
the output depends on a file the merge itself does not own.

## Task
1. Back up `data/processed/ratings.csv` → `data/processed/ratings_before_sortkey.csv`.
2. Replace the block with a deterministic sort: `date, league, season, home_team, away_team`
   (stable sort). Remove the dependency on ratings_backup.csv / ratings.csv in merge.py.
3. Run `python run.py update`.
4. Compare new `ratings.csv` to the backup, joined on its key columns (not by row position):
   report row counts and the max absolute difference for every numeric column.
   - All max diffs < 1e-6 → pass.
   - Otherwise **stop, restore the original merge.py and ratings.csv, and report** the columns,
     the size of the differences, and which rows differ most. Row order evidently matters to the
     ratings engine more than float noise, and Cowork will decide.
5. Run `python scripts/test_calibration.py`, `python scripts/test_line_selection.py`,
   `python scripts/test_clv.py` (all must pass; do not edit them).

## Commit (only on pass)
Delete `data/processed/ratings_before_sortkey.csv`, then:
```
git add scrapers/merge.py prompts/
git commit -m "merge.py: deterministic sort key instead of ratings_backup row-order replay"
git push
```
