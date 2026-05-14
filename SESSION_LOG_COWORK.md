# Session 12 — 2026-05-12

## Status at session end
EPL paper trading results settled. Bug fixed in results command. 5 new bets logged for final 2 rounds. Large line calibration research documented. Ready for pre-season backtest work.

## What was done this session

### Paper trading settled — 8 bets, but results bug found
Ran `update` + `results`. football-data.co.uk now current to May 11. All 8 pending bets from May 9-10 settled.

**Bug found:** `cmd_results()` was settling and counting ALL rows in the log including `bet_flag=False` rows (below-threshold predictions logged for reference). This inflated bet count to 13 and diluted ROI to 7%.

**Fix applied:** Two edits to `run.py` — filter `unsettled_mask` loop and `settled_all` totals by `bet_flag == 'True'`.

**Corrected paper trading state (bet_flag=True only):**
- 5 bets settled: 3W 2L, +$9.10, **+18.2% ROI**
- May 9-10 results: Chelsea Win, Brentford Loss, Wolves Loss, Sunderland Win, +$-3.90 net

**Calibration confirmed:** Both flagged overconfident bets (Brentford +1.5, Wolves +1.75) lost. 65%+ zone now 0W 2L on paper trading.

### Team alias fix
`predict` was skipping Leeds, West Ham, and Brighton matches — Odds API returns full names, ratings data uses short names. Added 3 mappings to `data/aliases/team_aliases.json`.

### Predict run — 5 bets flagged for final 2 rounds
All 9 EPL matches now showing. 5 flagged bets:

| Date | Match | Bet | Edge | Note |
|---|---|---|---|---|
| May 13 | Man City vs Crystal Palace | Palace AH +2.50 | +26.2% | Odds above min ✅ |
| May 17 | Wolves vs Fulham | Wolves AH +1.50 | +10.0% | Odds below min ⚠️ |
| May 17 | Leeds vs Brighton | Leeds AH +1.50 | +8.4% | Odds below min ⚠️ |
| May 17 | Man United vs Forest | Forest AH +1.50 | +7.0% | Odds below min ⚠️ |
| May 18 | Arsenal vs Burnley | Burnley AH +2.50 | +30.6% | Odds above min ✅ |

All 5 are in the 65%+ confidence zone. 3 of 5 have API odds below their own minimum — flagging logic bug (edge check and min odds display are inconsistent). Paper trading all 5 to build data.

### Large line calibration research documented
`docs/LARGE_LINE_CALIBRATION.md` — full analysis of why 65%+ zone is overconfident and 10 signal factors to address it. Key finding: all 10 factors are computable from existing data, including historical AH lines/odds (10,617 matches) and Pinnacle closing odds (9,867 matches). No new scrapers needed.

Pinnacle odds are the key insight — can use as "true probability" benchmark to measure model calibration error historically rather than waiting for paper trading volume.

## Next session checklist
- [ ] Settle final 2 rounds of EPL (run `update` + `results` after May 18)
- [ ] Pre-season: build calibration backtest — see `docs/LARGE_LINE_CALIBRATION.md`
- [ ] Fix flagging logic bug (odds below min odds still being flagged as bets)
- [ ] Sofascore back burner: run remaining 9 leagues (N1 first) — see handoff doc

---

# Session 11 — 2026-05-11

## Status at session end
Module 2 (Sofascore) fully working. E1 current season scraped and QC passed. Script ready for all-leagues run tomorrow. EPL paper trading bets not yet settled — football-data.co.uk data only goes to May 4, matches from May 9-10 not available yet.

## What was done this session

### Root cause of Session 10 failure identified
Session 10 fixes were not applying because python commands were run inside the Claude Code CLI, which intercepted them and ran a cached version. Fix: always use plain Windows Terminal.

### Sofascore fetch method fixed (CSP block)
`fetch_json()` was using `page.evaluate()` to run JavaScript `fetch()` inside the browser. Sofascore's Content Security Policy blocks cross-origin JavaScript requests to `api.sofascore.com`. Confirmed via diagnostic: all 10 leagues returned "TypeError: Failed to fetch (api.sofascore.com)" with HTTP 0.

Fix: replaced `fetch_json()` to use `page.goto()` directly on the API URL, then reads JSON from `page.inner_text('body')`. All 10 leagues now return HTTP 200 with valid data.

All 10 league IDs confirmed correct via diagnostic.

### Qwen3 stub disaster
Sent a simple fetch_fix prompt to Qwen3-Coder. It replaced the entire script with `# ... (existing content)` stubs, destroying the file. Restored from session context with fix applied directly.

### Relative path bug fixed
Script was saving CSVs to `data/proxy/` relative to the Terminal's working directory (defaulted to `C:\Users\chris\`). Fixed: paths now anchored to `Path(__file__).resolve().parent.parent` so files always save to the project's `data/proxy/` and `data/scandinavian/` regardless of where Terminal is.

### --seasons-back flag added
Added `--seasons-back N` argument. Used with `--all-seasons` to cap how many seasons are scraped. Tomorrow's run uses `--seasons-back 5` (2021-22 to 2025-26) to keep the overnight job under 10 hours.

### E1 current season — QC PASSED
552 rows, 0% null on xG, shots, SoT, corners. Fouls 0.4% null, yellows 4.2% null, reds 90.6% null (expected — red cards are rare events). Dates, team names, league, season all correct.

### EPL paper trading — not settled
8 bets pending (May 9-10). football-data.co.uk data only goes to 2026-05-04. Run `update` + `results` again in a day or two.

## Additional work this session (continued)

### Season sort bug fixed
`get_seasons()` was sorting by Sofascore season ID descending. This is wrong — Sofascore assigns high IDs to old historical seasons added late to their DB. N1 was picking 1988/89 seasons instead of 2025/26. Fixed: now sorts by actual calendar year parsed from season name. Two-digit years ≥50 treated as 19xx, <50 as 20xx.

### Rate limit fix
Added re-navigation to sofascore.com between each league + 5s pause + 30s retry on failure. This resets the session before each league.

### DELAY increased
0.35s was too aggressive. Sofascore returned 403 challenge after heavy usage. Increased to 1.0s. Do not reduce below 1.0s.

### One-league-at-a-time approach adopted
Use `--leagues E1` flag to run one league at a time. E1 (5 seasons, 2760 rows) is already complete.

### Session ended with 403 block
After extensive testing, Sofascore flagged the session. Block is temporary — clears overnight.

## Next session checklist (Sofascore — back burner)
- [ ] Wait for 403 block to clear (overnight)
- [ ] Run remaining 9 leagues one at a time: N1, B1, P1, SC0, T1, SWE, NOR, DNK, FIN
- [ ] Command: `python "...\experiment\load_sofascore.py" --all-seasons --seasons-back 5 --leagues N1`
- [ ] Power settings → Never sleep before running
- [ ] Settle EPL paper trading bets (run update + results — football-data.co.uk still only to May 4)
- [ ] Once all-seasons data complete → Module 4 (merge_data.py)

## Priority for next session
EPL paper trading results — check last weekend's bets once data is available.

---

# Session 10 — 2026-05-10

## Status at session end
Module 2 (Sofascore stats + xG loader) script written and partially working. Three bugs fixed in the script. However, fixes are NOT being applied at runtime because the user has been running python commands from inside the Claude Code CLI — Claude Code intercepts the command and runs the old cached version. Must run from a plain Windows Terminal tomorrow.

## What was done this session

### FotMob confirmed dead
`diagnose_fotmob.py` ran against all endpoints with multiple header sets. Every endpoint returns 404 HTML regardless of headers. FotMob API is dead. All FotMob files abandoned.

### FBref xG confirmed behind Stathead paywall
`test_fbref_stealth.py` written and run. Playwright stealth patches do not bypass Cloudflare. Even with manual CAPTCHA solve, xG data confirmed behind Stathead paywall ($9/month). FBref abandoned for xG.

### Data source pivot: FotMob → Sofascore
Sofascore unofficial API confirmed working via Playwright `page.evaluate()`. Python `requests` returns 403; browser session required. Approach: open sofascore.com, then all `fetch()` calls inside `page.evaluate()` inherit session cookies automatically.

**Confirmed working via Chrome DevTools:**
- `https://api.sofascore.com/api/v1/unique-tournament/{id}/seasons` → season list
- `https://api.sofascore.com/api/v1/unique-tournament/{id}/season/{season_id}/events/round/{n}` → match list
- `https://api.sofascore.com/api/v1/event/{match_id}/statistics` → xG + all stats

### Module 2 Sofascore prompt written
`prompts/experiment/MODULE_2_SOFASCORE_QWEN3.md` — replaces FotMob prompt. Starts with `/no_think`. Specifies all 10 league IDs, STAT_MAP, OUTPUT_COLUMNS, season naming logic, and 6 Qwen3 bug guards.

### Script generated and fixed
`experiment/load_sofascore.py` — generated by Qwen3-Coder from the prompt.

**Three bugs identified and fixed in the script:**
1. **Infinite loop** — no max round cap. Sofascore returns data for rounds 60–141+ for Championship (rescheduled/playoff fixtures). Fixed: `MAX_ROUNDS = {'european': 60, 'calendar': 35, 'danish': 45}`.
2. **Duplicate matches** — rescheduled games appear under multiple round numbers. Fixed: `seen_match_ids = set()` deduplication.
3. **Season ordering** — `seasons[0]` not guaranteed to be the most recent. Fixed: sort by season ID descending in `get_seasons()`.

**Season naming:** "25/26" should convert to "2025-2026" (code is mathematically correct). But output is showing "2024-2025" — this is the execution environment issue below.

### Critical execution environment issue — NOT YET RESOLVED
The user has been running python commands from inside the **Claude Code CLI** (launched via `claude --model claude-sonnet-4-6`). Claude Code intercepts the python command and executes it through its own internal bash tool. This results in:
- The old `prompts/experiment/load_sofascore.py` being run instead of the fixed `experiment/load_sofascore.py`
- Debug print statements not appearing in output
- Script fixes not being applied
- Round cap not working, season naming wrong

**Fix for tomorrow:** Run from a plain Windows Terminal, NOT from inside Claude Code CLI. Open Windows Terminal fresh (Win key → "Terminal"), then paste commands directly.

### QC observation
First run (old script, E1 only, infinite loop eventually killed) produced 460+ rows for E1. Dates from 2024-08-10 confirm it scraped the 24/25 season. User confirmed output had `home_team`, `away_team`, `home_xg`, `away_xg` columns. All stat columns (shots, SoT, corners, fouls, cards) are in the script's STAT_MAP and should populate — not yet verified in QC.

## Next session checklist
- [ ] **CRITICAL: Open a plain Windows Terminal — do NOT use Claude Code CLI to run python scripts**
- [ ] Kill any still-running script first (Ctrl+C)
- [ ] Run fixed script: `python "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer\experiment\load_sofascore.py" --leagues E1 --current-only`
- [ ] Confirm first output lines show `DEBUG — running file: ...experiment\load_sofascore.py` and `Championship 25/26 -> 2025-2026`
- [ ] Let E1 run to completion (~15-20 min), then run all 10 leagues: `--current-only` (no `--leagues` flag)
- [ ] Colab QC: check all columns populated, xG null rate <10%, row counts reasonable
- [ ] **EPL paper trading:** Run `python run.py update` then `python run.py results` (settle May 9-10 bets)
- [ ] Note whether Brentford +1.50 and Wolves +1.75 (overconfident zone) won or lost — calibration data

---

# Session 9 — 2026-05-09

## Status at session end
Module 1 (football-data.co.uk loader) complete and verified. FBref abandoned. FotMob confirmed as unified stats + xG source. Module 2 FotMob prompt written. Modules 3–9 not started.

## What was done this session

### Scandinavian Expansion — Module 1 (COMPLETE)
`experiment/load_footballdata.py` — written by Qwen3-Coder, fixed, verified end-to-end.

**Bugs fixed during execution:**
1. `pd.compat.StringIO` → `io.StringIO` (pandas 1.0 removed compat module)
2. All-NaN columns: Qwen built output schema with `reindex()` but never renamed source columns. Fixed with explicit `STATS_COLUMN_MAP` rename before reindex.
3. T1 tried seasons from 2000: added `PROXY_LEAGUE_FIRST_SEASON = {'T1': '2017-18'}`.
4. "Expected 47 fields, saw 49" CSV error on early seasons: fixed with `on_bad_lines='skip'`.
5. Scandinavian crash (`KeyError: HomeTeam/AwayTeam`): new format uses `Home`/`Away`. Fixed with `normalise_new_format_columns()`.
6. Scandinavian odds 0%: new format uses closing odds `B365CH`/`AvgCH`. Fixed by adding to normalise function.

**Output:** 133 proxy files + 59 Scandinavian files. Colab QC passed.

**Key implementation notes (for future reference):**
- football-data.co.uk has two URL patterns: `mmz4281` (proxy, per-season) and `new/` (Scandinavian, all-seasons combined)
- New format column differences: `Home`/`Away`/`HG`/`AG` vs `HomeTeam`/`AwayTeam`/`FTHG`/`FTAG`
- New format closing odds: `B365CH`/`AvgCH` vs `B365H`/`AvgH`

### Chris used Colab for the first time this session
Walked through the full workflow: upload files, clear cell (Ctrl+A Delete), paste QC code, Shift+Enter to run.

### Qwen3-Coder bug patterns documented
6 patterns added to `docs/LOCAL_LLM_SETUP.md` with fix-in-prompt instructions:
1. `pd.compat.StringIO` (removed in pandas 1.0)
2. Column rename omitted before reindex (silent NaN output)
3. Mixed format categories applied to wrong items (European vs calendar seasons)
4. Module-level side effects (cache init, global state outside main())
5. Date format described but not converted (raw string returned)
6. Overly broad HTML/key selectors

### FBref abandoned
Attempted: cloudscraper (403), plain requests (403), Playwright headless (timeout), Playwright visible (CAPTCHA loop — detects `navigator.webdriver`). All approaches blocked. Abandoned.

### Data source pivot: FBref → FotMob
FotMob unofficial API: no auth, no CAPTCHA, covers all leagues including Scandinavian. Provides shots, SoT, corners, fouls, cards, AND xG.
- Python package: `fotmob-api` v1.0.0 (NOT `fotmob` v0.0.2 — broken imports)
- Key methods: `get_fixtures(league_id, season)`, `get_match_details(match_id)`, `get_league_all()`
- Season format: `'2022/2023'` for European leagues, `'2023'` for calendar year (SWE/NOR/FIN)
- FotMob league IDs for our 10 leagues: **UNKNOWN** — need `--discover` step

### Docs updated
- `docs/SCANDINAVIAN_EXPANSION_SPEC.md`: FBref replaced by FotMob, added "Why FBref Was Abandoned" section, module table updated
- `docs/LOCAL_LLM_SETUP.md`: added Data Source Notes and Qwen3-Coder Bug Patterns sections
- `docs/INDEX.md`: added prompts/experiment/ section

### Module 2 FotMob prompt written (this session end)
`prompts/experiment/MODULE_2_FOTMOB_QWEN3.md` — ready to paste to Qwen3-Coder.
Targets: `experiment/load_fotmob.py`
Includes: mandatory discovery step (`--discover`), diagnostic step (`--diagnose`), all 6 Qwen bug guards, both proxy + Scandinavian leagues, xG output columns.

## Next session checklist
- [ ] **Module 2:** Paste `prompts/experiment/MODULE_2_FOTMOB_QWEN3.md` to Qwen3-Coder → get `experiment/load_fotmob.py`
- [ ] Run `python experiment/load_fotmob.py --discover` → find FotMob league IDs, update constants
- [ ] Run `--diagnose` → verify stats extraction
- [ ] Test one league: `--leagues E1 --seasons 2022-2023`
- [ ] Fix any bugs, Colab QC on E1 2022-2023 output
- [ ] Run full scrape overnight
- [ ] Write Module 4 prompt (merge_data.py) — depends on Module 1 + 2 complete
- [ ] **EPL paper trading:** Run `python run.py update` then `python run.py results` (settle May 9-10 bets)
- [ ] Note whether Brentford +1.50 and Wolves +1.75 (overconfident zone) won or lost
