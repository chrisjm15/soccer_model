# Weekly Schedule — EPL AH Paper Trading (2026-27)

*Rewritten 2026-10-25. Everything below runs automatically via Windows Task Scheduler.*

## Automatic runs
| When (AEDT/AEST) | Task | What it does |
|---|---|---|
| Tuesday 12:00 | existing weekly task → `scripts/run_update.ps1` | `run.py update` then `run.py results` (settles last round's paper bets, computes CLV) |
| Friday 12:00 | "Soccer Model - Friday Predict" → `run_update.ps1 -Mode predict` | `run.py update` then `run.py predict` (logs this round's matches + flagged bets) |

| Tue + Fri 13:00 | "Soccer Model - Status" → `STATUS.bat` | Opens the status report (`output/status_latest.txt`) |
| Tue + Fri 13:15 | "Soccer Model - Push" → `scripts/push_quiet.bat` | `git push` → `output/push_log.txt` |
| Friday 17:00 | "Soccer Model - Telegram" → `scripts/telegram_send.bat` | Posts the round's EPL bets + EXPERIMENTAL underrated picks |

- All tasks wake the PC and catch up if missed, once `FIX_SCHEDULE.bat` has been run (session 18). The three
  13:00/13:15/17:00 tasks did NOT do this before. Wake needs "Allow wake timers" on in the Windows power plan.
- Tue/Fri runs also settle/log the Big-5 luck paper test (`scripts/luck_paper_big5.py`).
- If `update` fails, the script skips results/predict (no predictions on stale ratings).
- The PC is **not** put to sleep afterwards.
- Each Friday uses ~11 Odds API credits: predict 3 (uk, au, eu) + Big-5 luck log 8.

## What to look at (optional, ~1 min)
- `output/predict_latest.txt` — this round's predictions and flagged bets (dated copies in `output/predictions/`).
- `output/scheduler_log.txt` — every step should show `exit code: 0`.
- `output/paper_trading/log_ah.csv` — the record. Never delete rows; vetoes/notes go in `notes`.

## Rules the model applies (from `config/calibration.yaml`)
- Bet if calibrated edge ≥ 1% on the main Asian line (consensus no-vig closest to 50/50).
- No bet if market prob is outside the training range [0.4569, 0.5407] (`out_of_range`).
- No bet if a promoted team has < 10 EPL matches this season (`promoted_veto`).
- Logged price = best available at first sighting. `best_au_price` is blank when no AU book offers the line.

## Running by hand (if needed)
```
cd "C:\Users\chris\Documents\Claude\Projects\Sports Betting - Soccer"
python run.py update
python run.py predict      # or: python run.py results
```

## EPL kickoff times
AEDT (Oct–Apr) is 11h ahead of UK GMT: Sat 3pm UK = Sun 2am. AEST (Apr–Oct) is 9h ahead of UK BST:
Sat 3pm UK = Sun midnight. Friday 12:00 predict runs land before every weekend kickoff.
