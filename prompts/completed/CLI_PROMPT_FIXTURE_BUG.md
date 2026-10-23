# CLI Prompt — Fix Fixture Data Bug

## Context for Chris
Paste everything between the --- lines into the CLI.

---

You are debugging a fixture data bug in a soccer prediction model. Read `CLAUDE.md` first to understand the project structure, then `SESSION_LOG_COWORK.md` to understand the specific bug.

**Summary of the bug:** The last live prediction run produced wrong fixtures — "Crystal Palace vs Everton" when Crystal Palace actually play Bournemouth, and "Real Oviedo" appearing under La Liga when they're a Segunda División club. Almost all fixtures looked incorrect. The root cause is unknown — could be the Odds API returning multiple competitions under one sport key, returning multiple rounds simultaneously, or a pairing bug in the team name mapper.

**Chris has no coding background. Fix all errors automatically. Commit and push when done.**

---

### STEP 1: Read context

Read these files before touching any code:
- `CLAUDE.md`
- `SESSION_LOG_COWORK.md`
- `scrapers/odds_api.py`
- `scrapers/team_name_mapper.py`
- `run.py`
- `config/leagues.yaml`

---

### STEP 2: Print the raw API response

Write a temporary diagnostic script `debug_fixtures.py` in the project root:

```python
import os, json
from scrapers.odds_api import fetch_all_leagues_odds  # adjust import if needed

api_key = os.environ.get("ODDS_API_KEY")
if not api_key:
    print("ERROR: ODDS_API_KEY not set")
    exit(1)

# Print raw response for every league — do NOT apply any team name mapping
raw = fetch_all_leagues_odds(api_key)  # adjust function signature if needed

for league, matches in raw.items():
    print(f"\n=== {league} ===")
    for m in matches:
        print(json.dumps(m, indent=2))
```

Run it:
```
python debug_fixtures.py
```

Read the output carefully. For each match, note:
- `commence_time` — is it actually an upcoming fixture?
- `sport_key` and `sport_title` — is the competition correct?
- `home_team` and `away_team` — are these real opponents for that league?
- Any matches from wrong divisions (e.g. Segunda División appearing under `soccer_spain_la_liga`)?

If `fetch_all_leagues_odds` doesn't return raw match data directly, look at the actual implementation in `scrapers/odds_api.py` and adapt the script to hit the API directly with `requests` and print the full JSON.

---

### STEP 3: Diagnose the root cause

Based on what you see in the raw output, identify which of these is the problem:

**Hypothesis A — Wrong sport key:** The Odds API `soccer_spain_la_liga` key is including Copa del Rey, Segunda División play-offs, or other Spanish competitions. If so, fix `config/leagues.yaml` with the correct sport keys.

**Hypothesis B — Multi-round stacking:** The API is returning fixtures from multiple upcoming rounds at once, and the team mapper or pairing logic is scrambling which teams play each other. If so, the fix is to only take fixtures where `commence_time` is within the next 7 days, and ensure `home_team`/`away_team` come from the same match object (not mixed across objects).

**Hypothesis C — Pairing bug in team name mapper:** After mapping, home and away teams from different matches are being reassembled incorrectly. If so, trace through `team_name_mapper.py` and `run.py` to find where match identity is lost.

Confirm which hypothesis is correct before writing any fix.

---

### STEP 4: Fix the bug

Apply the fix based on your diagnosis. Likely changes:

- If wrong sport keys: update `config/leagues.yaml`
- If multi-round stacking: add a date filter in `scrapers/odds_api.py` — only include matches where `commence_time` is within the next 7 days from today
- If pairing bug: fix the loop in `run.py` or `team_name_mapper.py` that assembles match predictions

After fixing, re-run:
```
python debug_fixtures.py
```

Confirm the output now shows correct, real fixtures with the right opponents for each league.

---

### STEP 5: Re-run live predictions

With the API key set, run:
```
python run.py predict
```

Verify the output:
- Check 3-5 matches against a real fixture list (e.g. mention the league and teams — I'll verify visually)
- Confirm no wrong-division clubs appearing
- Confirm match dates are upcoming, not past

---

### STEP 6: Clean up and commit

Delete `debug_fixtures.py` — it was temporary.

Then commit:
```
git add -A
git commit -m "Fix fixture data bug — [brief description of what was wrong]"
git push
```

---

### STEP 7: Report back

Print a plain-English summary:
- What the root cause was (which hypothesis was correct)
- What was changed to fix it
- The corrected predictions table for this week
- Any teams that still couldn't be mapped (with their raw API names so aliases can be added)

---
