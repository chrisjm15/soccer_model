import logging
import pandas as pd

logger = logging.getLogger(__name__)


def get_latest_ratings(ratings_path: str = 'data/processed/ratings.csv') -> dict:
    """
    Returns the most recent pre-match ratings for every team.

    For each team, returns their rating from the last match they appeared in
    (either as home or away team).

    Return structure:
    {
        'Arsenal': {
            'attack_home': float,
            'defence_home': float,
            'attack_away': float,
            'defence_away': float,
            'last_seen': str
        },
        ...
    }
    """
    df = pd.read_csv(ratings_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date', ascending=True)

    home_ratings = {}
    away_ratings = {}

    for _, row in df.iterrows():
        home_ratings[row['home_team']] = {
            'attack_home': row['home_attack'],
            'defence_home': row['home_defence'],
            'last_seen_home': row['date'].date().isoformat(),
        }
        away_ratings[row['away_team']] = {
            'attack_away': row['away_attack'],
            'defence_away': row['away_defence'],
            'last_seen_away': row['date'].date().isoformat(),
        }

    all_teams = set(home_ratings) | set(away_ratings)
    result = {}

    for team in all_teams:
        h = home_ratings.get(team)
        a = away_ratings.get(team)

        if h and a:
            last_seen = max(h['last_seen_home'], a['last_seen_away'])
            result[team] = {
                'attack_home': h['attack_home'],
                'defence_home': h['defence_home'],
                'attack_away': a['attack_away'],
                'defence_away': a['defence_away'],
                'last_seen': last_seen,
            }
        elif h:
            logger.warning(f"{team}: no away matches found — using home ratings as proxy for away")
            result[team] = {
                'attack_home': h['attack_home'],
                'defence_home': h['defence_home'],
                'attack_away': h['attack_home'],
                'defence_away': h['defence_home'],
                'last_seen': h['last_seen_home'],
            }
        else:
            logger.warning(f"{team}: no home matches found — using away ratings as proxy for home")
            result[team] = {
                'attack_home': a['attack_away'],
                'defence_home': a['defence_away'],
                'attack_away': a['attack_away'],
                'defence_away': a['defence_away'],
                'last_seen': a['last_seen_away'],
            }

    return result


if __name__ == '__main__':
    ratings = get_latest_ratings()
    print(f"Loaded ratings for {len(ratings)} teams")
    for team in ['Arsenal', 'Manchester City', 'Real Madrid', 'Bayern Munich']:
        if team in ratings:
            r = ratings[team]
            print(f"  {team}: atk_h={r['attack_home']:.3f} def_h={r['defence_home']:.3f} "
                  f"atk_a={r['attack_away']:.3f} def_a={r['defence_away']:.3f} "
                  f"last_seen={r['last_seen']}")
