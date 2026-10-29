"""OFF-SEASON 2027 CANDIDATE - NOT WIRED IN. Do not import from run.py / model/ until the 2027 off-season refit.
(Cowork session 18, 2026-10-29.)

Fix for the ratings season-transition bug in model/ratings.py (handoff tech debt):
  OLD: at a team's first match of a new season, the regression-to-mean target is the mean of the LIVE ratings of
       last season's league teams. Some of those teams have already played (and been shrunk + updated) in the new
       season, so the target depends on which matches were processed first -> order-dependent ratings. This is why
       scrapers/merge.py carries the ratings_backup row-order hack.
  NEW: the target is the mean of each team's rating as it stood after its LAST match of the previous season
       (a frozen end-of-season snapshot per (season, league)). Nothing processed in the new season can change it.
Everything else (priors, ALPHA, SHRINK_WEIGHT, EMA updates, which league's previous season is used) is identical to
model/ratings.py, so the only difference in output is the transition target.
"""
import os
import sys
from collections import defaultdict

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from model.ratings import ALPHA, SHRINK_WEIGHT, DEFAULT_PRIORS, compute_league_means, apply_season_transition  # noqa: E402

KEYS = ['attack_home', 'defence_home', 'attack_away', 'defence_away']


def compute_ratings_fixed(df: pd.DataFrame) -> pd.DataFrame:
    """df: merged matches (date, league, season, home_team, away_team, home_xg, away_xg). Returns pre-match ratings
    with the same columns and row order (stable date sort) as model.ratings.build_ratings."""
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date', kind='stable').reset_index(drop=True)
    team_ratings, last_season = {}, {}
    end_snapshot = defaultdict(dict)   # (season, league) -> {team: ratings after its last match of that season}
    frozen_means = {}                  # (season, league) -> league means used for transitions out of that season
    rows = []
    for r in df.itertuples(index=False):
        season, league = r.season, r.league
        for team in (r.home_team, r.away_team):
            if team not in team_ratings:
                team_ratings[team] = dict(DEFAULT_PRIORS)
                last_season[team] = season
            elif last_season[team] != season:
                # Target = this league's most recent COMPLETED season (the season before `season`), frozen at its
                # end. Same as model/ratings.py for teams that played last season. For a team returning after a
                # season away, model/ratings.py used its own last season (2+ years old, with live ratings); this
                # uses last season's league instead. Deliberate - review at the 2027 refit.
                done = [k for k in end_snapshot if k[1] == league and k[0] < season]
                prev_key = max(done) if done else (last_season[team], league)
                if prev_key not in frozen_means:
                    snap = end_snapshot.get(prev_key)
                    frozen_means[prev_key] = compute_league_means(snap) if snap else dict(DEFAULT_PRIORS)
                apply_season_transition(team_ratings[team], frozen_means[prev_key], SHRINK_WEIGHT)
                last_season[team] = season
        h, a = team_ratings[r.home_team], team_ratings[r.away_team]
        rows.append({'date': r.date, 'league': league, 'season': season, 'home_team': r.home_team,
                     'away_team': r.away_team, 'home_attack': h['attack_home'], 'home_defence': h['defence_home'],
                     'away_attack': a['attack_away'], 'away_defence': a['defence_away']})
        hx, ax = float(r.home_xg), float(r.away_xg)
        h['attack_home'] = ALPHA * hx + (1 - ALPHA) * h['attack_home']
        h['defence_home'] = ALPHA * ax + (1 - ALPHA) * h['defence_home']
        a['attack_away'] = ALPHA * ax + (1 - ALPHA) * a['attack_away']
        a['defence_away'] = ALPHA * hx + (1 - ALPHA) * a['defence_away']
        for team in (r.home_team, r.away_team):
            end_snapshot[(season, league)][team] = dict(team_ratings[team])
    return pd.DataFrame(rows)


def compute_ratings_old(df: pd.DataFrame) -> pd.DataFrame:
    """Current model/ratings.py logic without file I/O (for comparison tests only)."""
    import tempfile
    from model.ratings import build_ratings
    import contextlib, io
    with tempfile.TemporaryDirectory() as t:
        src, out = os.path.join(t, 'in.csv'), os.path.join(t, 'sub', 'out.csv')
        df.to_csv(src, index=False)
        with contextlib.redirect_stdout(io.StringIO()):
            res = build_ratings(src, out)
    res['date'] = pd.to_datetime(res['date'])
    return res
