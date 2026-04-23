"""Download and process match data CSVs from football-data.co.uk."""

import csv
import io
import os
import time

import pandas as pd
import requests
import yaml

BASE_URL = "https://www.football-data.co.uk/mmz4281"
HEADERS = {"User-Agent": "Mozilla/5.0"}
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "footballdata")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "leagues.yaml")

SEASONS = {
    "2020-21": "2021",
    "2021-22": "2122",
    "2022-23": "2223",
    "2023-24": "2324",
    "2024-25": "2425",
}

CORE_COLUMNS = [
    "Div", "Date", "Time", "HomeTeam", "AwayTeam",
    "FTHG", "FTAG", "FTR", "HTHG", "HTAG", "HTR",
    "Referee",
    "HS", "AS", "HST", "AST",
    "HC", "AC",
    "HF", "AF",
    "HY", "AY", "HR", "AR",
]

ODDS_COLUMNS = [
    "B365H", "B365D", "B365A",
    "B365>2.5", "B365<2.5",
    "AHh", "B365AHH", "B365AHA",
    "MaxH", "MaxD", "MaxA",
    "AvgH", "AvgD", "AvgA",
    "Max>2.5", "Max<2.5", "Avg>2.5", "Avg<2.5",
    "PSH", "PSD", "PSA",
]


def load_leagues():
    with open(CONFIG_PATH, "r") as f:
        cfg = yaml.safe_load(f)
    return cfg["leagues"]


def fetch_csv(league_code, season_code):
    url = f"{BASE_URL}/{season_code}/{league_code}.csv"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_csv(raw_text, league_key, season_label):
    df = pd.read_csv(io.StringIO(raw_text), encoding="utf-8-sig")
    df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam"])

    df = df.copy()
    df["league"] = league_key
    df["season"] = season_label

    return df


def log_column_availability(df, league_key, season_label):
    available = []
    missing = []
    for col in ODDS_COLUMNS:
        if col in df.columns and df[col].notna().any():
            available.append(col)
        else:
            missing.append(col)

    has_referee = "Referee" in df.columns and df["Referee"].notna().any()

    return {
        "league": league_key,
        "season": season_label,
        "odds_available": available,
        "odds_missing": missing,
        "has_referee": has_referee,
        "rows": len(df),
    }


def save_csv(df, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    keep = [c for c in CORE_COLUMNS + ["league", "season"] + ODDS_COLUMNS if c in df.columns]
    df[keep].to_csv(path, index=False)


def main():
    leagues = load_leagues()
    all_frames = []
    summary = {}
    column_reports = []

    for league_key, league_cfg in leagues.items():
        code = league_cfg["footballdata_code"]
        for season_label, season_code in SEASONS.items():
            label = f"{league_key} {season_label}"
            try:
                raw = fetch_csv(code, season_code)
                df = parse_csv(raw, league_key, season_label)
                count = len(df)
                summary[label] = count

                report = log_column_availability(df, league_key, season_label)
                column_reports.append(report)

                filename = f"{league_key}_{season_label}.csv"
                save_csv(df, os.path.join(OUTPUT_DIR, filename))
                all_frames.append(df)
                print(f"  {label}: {count} matches")
            except Exception as e:
                summary[label] = f"ERROR: {e}"
                print(f"  {label}: ERROR - {e}")

            time.sleep(1)

    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True)
        keep = [c for c in CORE_COLUMNS + ["league", "season"] + ODDS_COLUMNS if c in combined.columns]
        combined[keep].to_csv(os.path.join(OUTPUT_DIR, "all_matches.csv"), index=False)

    print(f"\n{'='*50}")
    print("FOOTBALL-DATA.CO.UK DOWNLOAD SUMMARY")
    print(f"{'='*50}")
    total = 0
    for label, count in summary.items():
        if isinstance(count, int):
            total += count
        print(f"  {label}: {count}")
    print(f"\n  TOTAL MATCHES: {total}")

    print(f"\n{'='*50}")
    print("COLUMN AVAILABILITY REPORT")
    print(f"{'='*50}")

    referee_leagues = set()
    no_referee_leagues = set()
    btts_found = False

    for r in column_reports:
        if r["has_referee"]:
            referee_leagues.add(r["league"])
        else:
            no_referee_leagues.add(r["league"])
        for col in r["odds_available"]:
            if "btts" in col.lower() or "bts" in col.lower():
                btts_found = True

    print(f"\n  Referee data available: {sorted(referee_leagues) if referee_leagues else 'NONE'}")
    print(f"  Referee data missing: {sorted(no_referee_leagues) if no_referee_leagues else 'NONE'}")
    print(f"  BTTS odds columns found: {'YES' if btts_found else 'NO — will derive from scorelines for backtesting'}")

    print(f"\n  Odds columns typically available:")
    if column_reports:
        sample = column_reports[0]
        for col in sample["odds_available"]:
            print(f"    + {col}")
        if sample["odds_missing"]:
            print(f"  Odds columns missing in {sample['league']} {sample['season']}:")
            for col in sample["odds_missing"]:
                print(f"    - {col}")

    print(f"\n  Output: {os.path.abspath(OUTPUT_DIR)}")


if __name__ == "__main__":
    main()
