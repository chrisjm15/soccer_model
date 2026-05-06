# Soccer Prediction Model

xG-based soccer prediction model. Currently live on EPL Asian Handicap market at 7% edge threshold. Paper trading active.

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
