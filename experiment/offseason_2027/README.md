# Off-season 2027 candidates — NOT LIVE

Built by Cowork session 18 (2026-10-29). Nothing in this folder is used by `run.py`, `model/` or the scheduled tasks.
Do not wire any of it in mid-season: it would change the model under test.

## Ratings season-transition fix
| File | Purpose |
|---|---|
| `ratings_fixed.py` | `compute_ratings_fixed(df)`: same as `model/ratings.py` except the regression-to-mean target |
| `test_ratings_fixed.py` | Gold tests (hand arithmetic + shuffle test on real data). An executor may not edit it |
| `impact_report.txt` | Fixed vs live `data/processed/ratings.csv` |

What changes:
1. The target is frozen at the end of last season (old code read live ratings, some already updated in the new
   season, and even the teammate shrunk earlier in the same match). Result: ratings no longer depend on row order
   (shuffle test: max diff 0.000000; old code 0.0126 on the same shuffle).
2. A team returning after a season away regresses to LAST season's league means (old code: its own last season,
   2+ years back). Deliberate; confirm at the refit.

Impact: mean |diff| 0.003 xG, max 0.038; EPL rows with |diff| > 0.01: 4.4%, mostly promoted/returning teams.

## Steps at the 2027 off-season (in order)
1. `python experiment/offseason_2027/test_ratings_fixed.py` must print ALL RATINGS GOLD TESTS PASSED.
2. Replace the transition block in `model/ratings.py` with the fixed logic. Re-run the gold tests against it.
3. Remove the `ratings_backup` row-order hack in `scrapers/merge.py` (no longer needed).
4. Rebuild ratings, then refit `config/calibration.yaml` with the push-consistent baseline (handoff tech debt).
5. Re-run `scripts/live_rule_oos_check.py`, `scripts/stop_date_analysis.py`, `scripts/advanced_research.py A`.
