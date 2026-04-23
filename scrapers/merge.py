"""Merge Understat xG data with football-data.co.uk match data.

Steps:
1. Build team name alias table (fuzzy matching between sources)
2. Join on date + home team + away team
3. Validate scorelines match
4. Output merged CSVs to data/processed/
"""

import difflib
import json
import os

import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
UNDERSTAT_DIR = os.path.join(BASE_DIR, "data", "raw", "understat")
FOOTBALLDATA_DIR = os.path.join(BASE_DIR, "data", "raw", "footballdata")
ALIASES_PATH = os.path.join(BASE_DIR, "data", "aliases", "team_aliases.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "processed")

SEASON_MAP = {
    "2020-21": "2020-21",
    "2021-22": "2021-22",
    "2022-23": "2022-23",
    "2023-24": "2023-24",
    "2024-25": "2024-25",
}

LEAGUES = ["EPL", "La_Liga", "Bundesliga", "Serie_A", "Ligue_1"]


def load_understat(league, season):
    year = int(season[:4])
    path = os.path.join(UNDERSTAT_DIR, f"{league}_{year}.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return df


def load_footballdata(league, season):
    path = os.path.join(FOOTBALLDATA_DIR, f"{league}_{season}.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    for fmt in ["%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"]:
        try:
            df["Date"] = pd.to_datetime(df["Date"], format=fmt)
            break
        except (ValueError, TypeError):
            continue
    df["date_str"] = df["Date"].dt.strftime("%Y-%m-%d")
    return df


def build_alias_table(understat_teams, footballdata_teams, league):
    """Fuzzy-match team names between sources. Returns {fd_name: understat_name}."""
    mapping = {}
    unmatched_fd = []
    unmatched_us = list(understat_teams)

    for fd_name in sorted(footballdata_teams):
        best = difflib.get_close_matches(fd_name, unmatched_us, n=1, cutoff=0.5)
        if best:
            mapping[fd_name] = best[0]
            if best[0] in unmatched_us:
                unmatched_us.remove(best[0])
        else:
            unmatched_fd.append(fd_name)

    return mapping, unmatched_fd, unmatched_us


KNOWN_ALIASES = {
    "EPL": {
        "Man United": "Manchester United",
        "Man City": "Manchester City",
        "Nott'm Forest": "Nottingham Forest",
        "Newcastle": "Newcastle United",
        "Wolves": "Wolverhampton Wanderers",
        "West Brom": "West Bromwich Albion",
    },
    "La_Liga": {
        "Ath Bilbao": "Athletic Club",
        "Ath Madrid": "Atletico Madrid",
        "Betis": "Real Betis",
        "Celta": "Celta Vigo",
        "Espanol": "Espanyol",
        "Huesca": "SD Huesca",
        "Sociedad": "Real Sociedad",
        "Vallecano": "Rayo Vallecano",
        "Valladolid": "Real Valladolid",
    },
    "Bundesliga": {
        "Bielefeld": "Arminia Bielefeld",
        "Dortmund": "Borussia Dortmund",
        "Ein Frankfurt": "Eintracht Frankfurt",
        "FC Koln": "FC Cologne",
        "Greuther Furth": "Greuther Fuerth",
        "Heidenheim": "FC Heidenheim",
        "Hertha": "Hertha Berlin",
        "Leverkusen": "Bayer Leverkusen",
        "M'gladbach": "Borussia M.Gladbach",
        "Mainz": "Mainz 05",
        "RB Leipzig": "RasenBallsport Leipzig",
        "St Pauli": "St. Pauli",
        "Stuttgart": "VfB Stuttgart",
    },
    "Serie_A": {
        "Milan": "AC Milan",
        "Parma": "Parma Calcio 1913",
    },
    "Ligue_1": {
        "Paris SG": "Paris Saint Germain",
        "St Etienne": "Saint-Etienne",
        "Clermont": "Clermont Foot",
    },
}


def resolve_name(fd_name, league, fuzzy_map, known_aliases):
    if league in known_aliases and fd_name in known_aliases[league]:
        return known_aliases[league][fd_name]
    if fd_name in fuzzy_map:
        return fuzzy_map[fd_name]
    return fd_name


def merge_league_season(league, season):
    us_df = load_understat(league, season)
    fd_df = load_footballdata(league, season)

    if us_df is None or fd_df is None:
        status = []
        if us_df is None:
            status.append("no Understat data")
        if fd_df is None:
            status.append("no football-data")
        return None, {"status": ", ".join(status), "us_count": 0, "fd_count": 0}

    us_teams = set(us_df["home_team"].unique()) | set(us_df["away_team"].unique())
    fd_teams = set(fd_df["HomeTeam"].unique()) | set(fd_df["AwayTeam"].unique())

    fuzzy_map, unmatched_fd, unmatched_us = build_alias_table(us_teams, fd_teams, league)

    fd_df["home_team_norm"] = fd_df["HomeTeam"].apply(
        lambda x: resolve_name(x, league, fuzzy_map, KNOWN_ALIASES)
    )
    fd_df["away_team_norm"] = fd_df["AwayTeam"].apply(
        lambda x: resolve_name(x, league, fuzzy_map, KNOWN_ALIASES)
    )

    merged = pd.merge(
        us_df,
        fd_df,
        left_on=["date", "home_team", "away_team"],
        right_on=["date_str", "home_team_norm", "away_team_norm"],
        how="inner",
    )

    us_only = len(us_df) - len(merged)
    fd_only = len(fd_df) - len(merged)

    mismatches = merged[
        (merged["home_goals"] != merged["FTHG"]) | (merged["away_goals"] != merged["FTAG"])
    ]

    report = {
        "status": "ok",
        "us_count": len(us_df),
        "fd_count": len(fd_df),
        "merged": len(merged),
        "us_orphans": us_only,
        "fd_orphans": fd_only,
        "score_mismatches": len(mismatches),
        "unmatched_fd_teams": unmatched_fd,
        "unmatched_us_teams": unmatched_us,
    }

    if len(merged) == 0:
        return None, report

    output_cols = [
        "date", "league_x", "season_x",
        "home_team", "away_team",
        "home_goals", "away_goals",
        "home_xg", "away_xg", "home_xga", "away_xga",
        "FTR",
    ]

    stats_cols = ["HS", "AS", "HST", "AST", "HC", "AC", "HF", "AF", "HY", "AY", "HR", "AR"]
    for c in stats_cols:
        if c in merged.columns:
            output_cols.append(c)

    if "Referee" in merged.columns:
        output_cols.append("Referee")

    odds_cols = [
        "B365H", "B365D", "B365A",
        "B365>2.5", "B365<2.5",
        "AHh", "B365AHH", "B365AHA",
        "PSH", "PSD", "PSA",
        "MaxH", "MaxD", "MaxA", "AvgH", "AvgD", "AvgA",
    ]
    for c in odds_cols:
        if c in merged.columns:
            output_cols.append(c)

    existing = [c for c in output_cols if c in merged.columns]
    result = merged[existing].copy()

    rename_map = {
        "league_x": "league",
        "season_x": "season",
        "FTR": "result",
        "HS": "home_shots", "AS": "away_shots",
        "HST": "home_sot", "AST": "away_sot",
        "HC": "home_corners", "AC": "away_corners",
        "HF": "home_fouls", "AF": "away_fouls",
        "HY": "home_yellow", "AY": "away_yellow",
        "HR": "home_red", "AR": "away_red",
        "Referee": "referee",
        "B365H": "odds_home", "B365D": "odds_draw", "B365A": "odds_away",
        "B365>2.5": "odds_over25", "B365<2.5": "odds_under25",
        "AHh": "ah_line", "B365AHH": "odds_ah_home", "B365AHA": "odds_ah_away",
        "PSH": "pinnacle_home", "PSD": "pinnacle_draw", "PSA": "pinnacle_away",
        "MaxH": "max_odds_home", "MaxD": "max_odds_draw", "MaxA": "max_odds_away",
        "AvgH": "avg_odds_home", "AvgD": "avg_odds_draw", "AvgA": "avg_odds_away",
    }
    result = result.rename(columns={k: v for k, v in rename_map.items() if k in result.columns})

    return result, report


def find_orphans(us_df, fd_df, merged_df, league, fuzzy_map):
    """Find specific unmatched matches for debugging."""
    if us_df is None or fd_df is None or merged_df is None:
        return [], []

    merged_keys = set(
        zip(merged_df["date"], merged_df["home_team"], merged_df["away_team"])
    )

    us_orphans = []
    for _, row in us_df.iterrows():
        key = (row["date"], row["home_team"], row["away_team"])
        if key not in merged_keys:
            us_orphans.append(f"  {row['date']} {row['home_team']} vs {row['away_team']}")

    return us_orphans[:10]


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(ALIASES_PATH), exist_ok=True)

    all_frames = []
    all_reports = {}
    all_aliases = {}

    for league in LEAGUES:
        all_aliases[league] = {}
        for season in SEASON_MAP.values():
            label = f"{league} {season}"
            result, report = merge_league_season(league, season)
            all_reports[label] = report

            if result is not None and len(result) > 0:
                path = os.path.join(OUTPUT_DIR, f"{league}_{season}.csv")
                result.to_csv(path, index=False)
                all_frames.append(result)
                print(f"  {label}: {report['merged']}/{report['us_count']} merged "
                      f"({report['us_orphans']} US orphans, {report['fd_orphans']} FD orphans)")
            else:
                print(f"  {label}: {report['status']}")

            if "unmatched_fd_teams" in report and report["unmatched_fd_teams"]:
                print(f"    Unmatched FD teams: {report['unmatched_fd_teams']}")
            if "unmatched_us_teams" in report and report["unmatched_us_teams"]:
                print(f"    Unmatched US teams: {report['unmatched_us_teams']}")

    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True)
        combined.to_csv(os.path.join(OUTPUT_DIR, "all_merged.csv"), index=False)

    with open(ALIASES_PATH, "w") as f:
        json.dump(KNOWN_ALIASES, f, indent=2)

    print(f"\n{'='*60}")
    print("MERGE SUMMARY")
    print(f"{'='*60}")

    total_us = 0
    total_fd = 0
    total_merged = 0
    total_orphans = 0
    total_mismatches = 0

    for label, r in all_reports.items():
        if r["status"] == "ok":
            total_us += r["us_count"]
            total_fd += r["fd_count"]
            total_merged += r["merged"]
            total_orphans += r["us_orphans"] + r["fd_orphans"]
            total_mismatches += r["score_mismatches"]

    print(f"\n  Understat matches:      {total_us}")
    print(f"  Football-data matches:  {total_fd}")
    print(f"  Successfully merged:    {total_merged}")
    print(f"  Orphan matches:         {total_orphans}")
    print(f"  Score mismatches:       {total_mismatches}")

    if total_us > 0:
        rate = total_merged / total_us * 100
        print(f"  Merge rate:             {rate:.1f}%")

    print(f"\n  Output: {os.path.abspath(OUTPUT_DIR)}")

    if total_mismatches > 0:
        print(f"\n  WARNING: {total_mismatches} score mismatches found -- investigate manually")

    name_issues = []
    for label, r in all_reports.items():
        if r.get("unmatched_fd_teams") or r.get("unmatched_us_teams"):
            name_issues.append(label)
    if name_issues:
        print(f"\n  Team name issues in: {', '.join(name_issues)}")


if __name__ == "__main__":
    main()
