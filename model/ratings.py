import os
import pandas as pd
from collections import defaultdict

# Constants
ALPHA = 0.1           # EMA decay factor
SHRINK_WEIGHT = 0.3   # Regression-to-mean weight at season start

DEFAULT_PRIORS = {
    'attack_home': 1.60,
    'defence_home': 1.30,
    'attack_away': 1.10,
    'defence_away': 1.50,
}


def compute_league_means(team_ratings: dict) -> dict:
    """
    Given a dict of {team_name: {attack_home, defence_home, attack_away, defence_away}},
    return the mean of each dimension across all teams.
    """
    if not team_ratings:
        return dict(DEFAULT_PRIORS)

    means = {}
    for key in ['attack_home', 'defence_home', 'attack_away', 'defence_away']:
        values = [team[key] for team in team_ratings.values()]
        means[key] = sum(values) / len(values)
    return means


def apply_season_transition(
    single_team_ratings: dict,
    league_means: dict,
    shrink_weight: float = SHRINK_WEIGHT
) -> dict:
    """
    Apply regression-to-mean for a single team at the start of a new season.
    Modifies single_team_ratings in place and returns it.
    """
    for key in ['attack_home', 'defence_home', 'attack_away', 'defence_away']:
        single_team_ratings[key] = (
            (1 - shrink_weight) * single_team_ratings[key]
            + shrink_weight * league_means[key]
        )
    return single_team_ratings


def build_ratings(data_path: str, output_path: str) -> pd.DataFrame:
    """
    Main function. Loads data, computes ratings, saves output CSV.
    Returns the ratings DataFrame.
    """
    df = pd.read_csv(data_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    # team_ratings[team] = {attack_home, defence_home, attack_away, defence_away}
    team_ratings = {}

    # last_season[team] = season string of the last match seen for that team
    last_season = {}

    # season_league_teams[(season, league)] = {team, ...}
    # Used to compute per-league means at season transitions
    season_league_teams = defaultdict(set)

    output_rows = []

    for _, row in df.iterrows():
        date = row['date']
        league = row['league']
        season = row['season']
        home_team = row['home_team']
        away_team = row['away_team']
        home_xg = float(row['home_xg'])
        away_xg = float(row['away_xg'])

        # --- Initialise or transition each team ---
        for team in [home_team, away_team]:
            if team not in team_ratings:
                # First time seeing this team — use default priors
                team_ratings[team] = dict(DEFAULT_PRIORS)
                last_season[team] = season
            elif last_season[team] != season:
                # Season has changed — apply regression to this league's mean
                prev_season = last_season[team]
                prev_key = (prev_season, league)
                prev_teams = season_league_teams[prev_key]

                if prev_teams:
                    prev_team_ratings = {t: team_ratings[t] for t in prev_teams if t in team_ratings}
                    league_means = compute_league_means(prev_team_ratings)
                else:
                    league_means = dict(DEFAULT_PRIORS)

                apply_season_transition(team_ratings[team], league_means)
                last_season[team] = season

        # --- Record pre-match ratings (before this match updates them) ---
        output_rows.append({
            'date': date,
            'league': league,
            'season': season,
            'home_team': home_team,
            'away_team': away_team,
            'home_attack': team_ratings[home_team]['attack_home'],
            'home_defence': team_ratings[home_team]['defence_home'],
            'away_attack': team_ratings[away_team]['attack_away'],
            'away_defence': team_ratings[away_team]['defence_away'],
        })

        # --- Update ratings after recording (EMA) ---
        team_ratings[home_team]['attack_home'] = (
            ALPHA * home_xg + (1 - ALPHA) * team_ratings[home_team]['attack_home']
        )
        team_ratings[home_team]['defence_home'] = (
            ALPHA * away_xg + (1 - ALPHA) * team_ratings[home_team]['defence_home']
        )
        team_ratings[away_team]['attack_away'] = (
            ALPHA * away_xg + (1 - ALPHA) * team_ratings[away_team]['attack_away']
        )
        team_ratings[away_team]['defence_away'] = (
            ALPHA * home_xg + (1 - ALPHA) * team_ratings[away_team]['defence_away']
        )

        # Track which teams were in this league-season (for future mean computation)
        season_league_teams[(season, league)].add(home_team)
        season_league_teams[(season, league)].add(away_team)

    output_df = pd.DataFrame(output_rows)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    output_df.to_csv(output_path, index=False)

    # Validation output
    print(f"Total rows in output: {len(output_df)}")
    print("Unique teams per league:")
    for lg in sorted(output_df['league'].unique()):
        n_home = output_df[output_df['league'] == lg]['home_team'].nunique()
        print(f"  {lg}: {n_home} teams")
    print(f"home_attack range: [{output_df['home_attack'].min():.3f}, {output_df['home_attack'].max():.3f}]")
    print(f"away_attack range: [{output_df['away_attack'].min():.3f}, {output_df['away_attack'].max():.3f}]")
    print("\nSample rows:")
    print(output_df.head(5).to_string(index=False))

    return output_df


if __name__ == '__main__':
    df = build_ratings(
        data_path='data/processed/all_merged.csv',
        output_path='data/processed/ratings.csv'
    )
    print(f"\nRatings computed for {len(df)} matches")
    print("\nSample team ratings (last snapshot per team, EPL only):")
    epl = df[df['league'] == 'EPL']
    if len(epl) > 0:
        last_ratings = epl.groupby('home_team').last()[['home_attack', 'home_defence']].head(5)
        print(last_ratings.to_string())
