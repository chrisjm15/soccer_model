from model.poisson import compute_match_probs
import pandas as pd

ASSUMED_BTTS_ODDS = 1.90        # Used when no market odds available (typical bookmaker price)
DEFAULT_EDGE_THRESHOLD = 0.05   # 5% minimum edge to flag as a bet


def predict_match(
    home_attack: float,
    home_defence: float,
    away_attack: float,
    away_defence: float,
    home_advantage: float = 0.0,
    btts_odds_yes: float = ASSUMED_BTTS_ODDS,
    edge_threshold: float = DEFAULT_EDGE_THRESHOLD
) -> dict:
    # Get probabilities from the Poisson model
    probs = compute_match_probs(
        home_attack=home_attack,
        home_defence=home_defence,
        away_attack=away_attack,
        away_defence=away_defence,
        home_advantage=home_advantage
    )
    # Compute implied probability from market odds
    implied_prob = 1.0 / btts_odds_yes
    # Compute edge
    edge = probs['prob_btts_yes'] - implied_prob
    # Determine if we should bet
    should_bet = (edge >= edge_threshold)
    # Compute expected value
    expected_value = (
        probs['prob_btts_yes'] * (btts_odds_yes - 1.0)
        - (1.0 - probs['prob_btts_yes']) * 1.0
    )
    return {
        'lambda_home': probs['lambda_home'],
        'lambda_away': probs['lambda_away'],
        'prob_btts_yes': probs['prob_btts_yes'],
        'prob_btts_no': probs['prob_btts_no'],
        'implied_prob': implied_prob,
        'edge': edge,
        'expected_value': expected_value,
        'should_bet': should_bet,
        'btts_odds_yes': btts_odds_yes,
        'prob_home_win': probs['prob_home_win'],
        'prob_draw': probs['prob_draw'],
        'prob_away_win': probs['prob_away_win'],
        'prob_over_25': probs['prob_over_25'],
        'prob_under_25': probs['prob_under_25'],
    }


def run_predictions(
    ratings_df: pd.DataFrame,
    home_advantage_by_league: dict,
    btts_odds_yes: float = ASSUMED_BTTS_ODDS,
    edge_threshold: float = DEFAULT_EDGE_THRESHOLD
) -> pd.DataFrame:
    results = []
    for _, row in ratings_df.iterrows():
        league = row['league']
        home_adv = home_advantage_by_league.get(league, 0.0)
        prediction = predict_match(
            home_attack=row['home_attack'],
            home_defence=row['home_defence'],
            away_attack=row['away_attack'],
            away_defence=row['away_defence'],
            home_advantage=home_adv,
            btts_odds_yes=btts_odds_yes,
            edge_threshold=edge_threshold
        )
        result_row = row.to_dict()
        result_row.update(prediction)
        results.append(result_row)
    return pd.DataFrame(results)


if __name__ == '__main__':
    # Standalone test — simulate two matches
    test_matches = [
        {
            'date': '2024-01-15', 'league': 'EPL', 'season': '2023-24',
            'home_team': 'Arsenal', 'away_team': 'Chelsea',
            'home_attack': 2.1, 'home_defence': 1.0,
            'away_attack': 1.5, 'away_defence': 1.3,
        },
        {
            'date': '2024-01-15', 'league': 'EPL', 'season': '2023-24',
            'home_team': 'Burnley', 'away_team': 'Brentford',
            'home_attack': 0.9, 'home_defence': 1.8,
            'away_attack': 1.4, 'away_defence': 1.5,
        },
    ]
    df = pd.DataFrame(test_matches)
    home_adv = {'EPL': 0.0}
    results = run_predictions(df, home_adv)
    for _, row in results.iterrows():
        print(f"{row['home_team']} vs {row['away_team']}")
        print(f"  lambda_home={row['lambda_home']:.3f}, lambda_away={row['lambda_away']:.3f}")
        print(f"  P(BTTS Yes)={row['prob_btts_yes']:.3f}, implied={row['implied_prob']:.3f}, edge={row['edge']:+.3f}")
        print(f"  EV={row['expected_value']:+.4f}, Bet={row['should_bet']}")
        print()
