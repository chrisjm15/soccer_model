# Soccer Prediction Model

xG-based soccer prediction model targeting BTTS, Over/Under, and Win/Draw/Loss markets across Big 5 European leagues.

## Data Sources
- **Understat** — Match-level xG data (EPL, La Liga, Bundesliga, Serie A, Ligue 1)
- **football-data.co.uk** — Results, shots, cards, referee, closing odds

## Project Structure
- `scrapers/` — Data ingestion scripts
- `model/` — Prediction models (Phase 2+)
- `backtest/` — Historical simulation engine (Phase 2+)
- `config/` — League definitions
- `data/` — Raw and processed data (gitignored)

## Usage
```bash
pip install -r requirements.txt
python scrapers/understat.py
python scrapers/footballdata.py
python scrapers/merge.py
```
