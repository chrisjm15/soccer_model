# Soccer Prediction Model

xG-based soccer prediction model. Live on the EPL Asian Handicap market: market-blend calibrated probabilities, 1%
calibrated-edge threshold (`config/calibration.yaml`). Paper log with closing-line value on every match. Research
findings: `docs/RESEARCH_SESSION_17.md`, `output/backtest_results/stop_date_report.txt`.

## Data Sources
- **Understat** — Match-level xG data (EPL, La Liga, Bundesliga, Serie A, Ligue 1)
- **The Odds API** — Live AH odds (free tier)

## Usage
```bash
python run.py update    # Weekly data refresh (~5 min)
python run.py predict   # Output flagged bets for upcoming fixtures
python run.py backtest  # Run historical simulation
```

## Project Structure
- `scrapers/` — Data ingestion (Understat, football-data.co.uk, Odds API)
- `model/` — EMA ratings, Poisson probability, market edge calculation
- `backtest/` — Historical simulation engine and metrics
- `config/` — League definitions and Odds API keys
- `data/` — Raw and processed data (gitignored)
- `output/` — Backtest results and paper trading log
