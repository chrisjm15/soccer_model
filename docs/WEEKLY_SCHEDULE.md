# Weekly Schedule — EPL AH Paper Trading

## Overview

Two actions per week. Everything runs from the project folder in Terminal.

```
cd "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
```

---

## Monday (AEST) — Update & Settle

Run after the weekend's EPL matches are complete (Monday morning is safe).

**Step 1 — Pull fresh data:**
```
python run.py update
```
Downloads the latest xG and result data from Understat. Takes 1–2 minutes.

**Step 2 — Settle paper trades:**
```
python run.py results
```
Looks up actual scores, calculates AH results, updates `output/paper_trading/log_ah.csv`, and prints your running P&L.

Review the output — check that any bets from the previous week settled correctly.

---

## Thursday (AEST) — Predict

Run Thursday to catch Friday evening and weekend fixture odds before they move.

**Step 1 — Get predictions:**
```
python run.py predict
```
Fetches live AH odds from UK+AU bookmakers combined (Bet365, Ladbrokes etc. — global pricing), runs the model, prints any bets flagged at 7%+ edge.

**Step 2 — Check Bet365 AU**

Before paper logging any flagged bet, verify the AH market is actually available on Bet365 AU for that specific fixture. Not every EPL match has AH on Bet365 AU. If unavailable, note it in the `notes` column of the log.

**Step 3 — Log flagged bets**

If a bet is flagged (edge ≥ 7%) and the market is available:
- Open `output/paper_trading/log_ah.csv`
- Add a new row with the prediction date, match details, AH line, odds, edge, and `bet_flag = True`
- Leave `actual_ah_result` and `profit_loss` blank — these get filled on Monday

---

## EPL Kickoff Times (AEST, May–May)

UK is on BST (UTC+1). Sydney/Brisbane is on AEST (UTC+10) — 9 hours ahead of BST from late April onward (Australian daylight saving has ended).

| UK kickoff (BST) | AEST equivalent |
|---|---|
| Saturday 12:30pm | Saturday 9:30pm |
| Saturday 3:00pm | Sunday 12:00am (midnight) |
| Saturday 5:30pm | Sunday 2:30am |
| Sunday 2:00pm | Sunday 11:00pm |
| Sunday 4:30pm | Monday 1:30am |
| Monday 8:00pm | Tuesday 5:00am |

> **Note:** Saturday 3pm and 5:30pm BST kick off after midnight AEST. These results won't be in the Understat data until Sunday/Monday AEST — run.py update on Monday morning will catch them.

---

## Odds Source — What the Model Actually Uses

The model gets AH prices from **Matchbook** (UK exchange) and **playup** (AU bookmaker) via The Odds API. It uses the best available price across both.

Bet365 and Ladbrokes do not share AH/spreads data with The Odds API — this is a known limitation, not a configuration issue. Their prices are not available here regardless of API tier.

**Before logging any paper trade:**
- Check the flagged bet in the predict output — if the model returned a price, the market exists in the data
- Note which bookmaker had the best price (the output shows this)
- If you want to cross-check against Bet365 AU manually, you can — but don't expect the line to always match (different bookmaker, potentially different line)
- Log the price the model used in `odds_ah`, not any manually checked price

---

## Quick Reference — Commands

| Command | When | What it does |
|---|---|---|
| `python run.py update` | Monday | Pulls latest xG + results data |
| `python run.py results` | Monday | Settles paper trades, prints P&L |
| `python run.py predict` | Thursday | Runs model, prints flagged bets |

---

## Reminders

- **Free API credits:** The Odds API free tier has limited monthly credits. Run `python run.py predict` once per week, not multiple times per day.
- **Edge threshold:** Only log bets with edge ≥ 7%. Below that, record nothing.
- **Flat stake:** All paper trades use a flat $10 stake for P&L tracking.
- **No live betting:** This model is for pre-match markets only. Do not use it for in-play.
