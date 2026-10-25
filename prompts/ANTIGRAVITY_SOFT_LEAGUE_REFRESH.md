# Antigravity brief — Refresh soft-league football-data (add 2025-26) and re-merge

Written by Cowork 2026-10-25 (session 16). Tier: routine + verification. Carry out in order; report each step.
Repo root: `C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer`

## Why
QC of the Module 4 merge (`f06852c`) found `experiment/load_footballdata.py` had a frozen season list ending
2024-25 — the same bug session 15 found in the main scrapers. So **2025-26 was missing for B1, N1, P1, T1,
E1** although Sofascore has full 2025-26 xG for all five. The Scandinavian files also stop at 2026-05-04.
Cowork has already added `'2025-26': '2526', '2026-27': '2627'` to `SEASON_CODES` (uncommitted). Do not
change anything else in the loader.

## Steps
1. Download: `python experiment/load_footballdata.py --seasons 2025-26 2026-27`
   (this also re-downloads the four Scandinavian combined files). Report the per-file row counts it prints and
   any failures. Then confirm `data/proxy/{B1,N1,P1,T1,E1}_2025-26_footballdata.csv` exist with ~306–552 rows,
   and the latest `date` in `data/scandinavian/{SWE,NOR,DNK}_*_footballdata.csv`.
2. Aliases: `python experiment/build_soft_aliases.py` (**without** `--reset`, so the 7 manual overrides
   survive). Report only: new Sofascore→football-data entries (promoted clubs in 2025-26, Scandinavian 2026),
   their method/score, and the 1-to-1 check result per league. Fix any wrong fuzzy match by hand-editing the
   JSON; say which and why.
3. Merge: `python experiment/merge_data.py`. Paste the full per league-season summary table and the
   unmatched-row list **for 2025-26 / 2026 seasons only**. Target ≥ 98% match on every season with xG.
4. Confirm the pre-existing league-seasons are unchanged: for every league-season that existed before
   (2021-22..2024-25 proxy; 2021..2025 Scandinavian, except DNK 2025 / SWE 2026 / NOR 2026 which gain rows),
   matched-row counts must equal the previous run's table.
5. Commit and push:
```
git add experiment/load_footballdata.py data/aliases/soft_league_aliases.json prompts/ COWORK_HANDOFF_PROMPT.md SESSION_LOG_COWORK.md
git commit -m "Soft-league refresh: loader season list to 2026-27, re-merge incl. 2025-26"
git push
```
`data/proxy/` and `data/scandinavian/` CSVs: commit them too only if they were already tracked by git
(`git ls-files data/proxy | head`) — keep the repo's existing convention.
