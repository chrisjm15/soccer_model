# Re-scrape Plan — P1 & FIN (2026-07-18)

## Why
Scrape QC found two leagues with bad data. The .bat marks a league "done" when the
script exits cleanly, not when the data is complete — so these slipped through:

| Problem | Detail |
|---|---|
| P1 2024-25 truncated | 62 of ~306 matches (2023-24 also 9 short at 297) |
| FIN badly incomplete | 2021 = 30 rows, 2024 = 144, 2025 = 15 (should be ~165/season); no 2026 file at all |

Everything else passed: no duplicates, full match counts, xG present from 2023-24
onward (older seasons have no xG on Sofascore — expected, not a scrape failure).

## Step 1 — Re-scrape P1 and FIN (you, ~2-3 hours total)

1. Press **Windows key**, type `Notepad`, press **Enter**
2. In Notepad: **File → Open**, paste this into the filename box and press Enter:
   ```
   C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer\experiment\sofascore_done.txt
   ```
3. Delete the two lines that say `P1` and `FIN` (leave all other lines alone)
4. **File → Save**, close Notepad
5. Double-click `scrape_next_league.bat` — it will re-scrape P1 (all 5 seasons,
   overwriting the bad files). When it finishes, click it again for FIN.
6. If either run shows a 403 error, Sofascore has blocked the session — wait until
   tomorrow and click again. Progress on the other leagues is safe.

## Step 2 — Verify (Claude, next Cowork session)
Tell me "re-scrape done" and I'll re-run the row-count and xG checks. Pass criteria:
P1 2024-25 ≥ ~300 rows; FIN 2021-2025 each ≥ ~130 rows with xG from 2023 onward.

## Step 3 — Decision: which leagues make the soft-league set

Usable xG seasons per league (rows without xG are dead weight for an xG model):

| League | Full seasons with xG | Verdict |
|---|---|---|
| B1, N1, DNK, T1, E1 | ~3 | **In** |
| SWE, NOR | ~2.5–3 | **In** |
| P1 | ~2 (pending re-scrape) | **In if re-scrape fixes 2024-25** |
| SC0 | 1 (2025-26 only) | **Recommend: park** — one season can't calibrate ratings. Keep scraping forward; revisit next season. |
| FIN | ~1.5 (pending re-scrape) | **Recommend: park** unless re-scrape recovers 2024/2025. Scrape has been unreliable for this league. |

This is my recommendation — override if you want SC0/FIN kept in for data-collection
purposes only (harmless, they just take no bets).

## Step 4 — Module 4 merge
Only after Step 2 passes. I'll write the Sonnet CLI prompt then — merging before the
P1/FIN fix would bake the holes into the merged dataset.
