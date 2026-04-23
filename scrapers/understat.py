"""Scrape match-level xG data from Understat for Big 5 leagues."""

import csv
import json
import os
import time

import requests
import yaml

BASE_URL = "https://understat.com/getLeagueData"
HEADERS = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "understat")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "leagues.yaml")

SEASONS = list(range(2020, 2026))  # 2020 = 2020-21 season, ..., 2025 = 2025-26

FIELDNAMES = [
    "match_id", "date", "league", "season",
    "home_team", "away_team",
    "home_goals", "away_goals",
    "home_xg", "away_xg",
    "home_xga", "away_xga",
]


def load_leagues():
    with open(CONFIG_PATH, "r") as f:
        cfg = yaml.safe_load(f)
    return cfg["leagues"]


def fetch_season(league_slug, season):
    url = f"{BASE_URL}/{league_slug}/{season}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def parse_matches(data, league_key, season):
    rows = []
    for match in data.get("dates", []):
        if not match.get("isResult"):
            continue
        rows.append({
            "match_id": match["id"],
            "date": match["datetime"][:10],
            "league": league_key,
            "season": f"{season}-{str(season + 1)[-2:]}",
            "home_team": match["h"]["title"],
            "away_team": match["a"]["title"],
            "home_goals": int(match["goals"]["h"]),
            "away_goals": int(match["goals"]["a"]),
            "home_xg": round(float(match["xG"]["h"]), 4),
            "away_xg": round(float(match["xG"]["a"]), 4),
            "home_xga": round(float(match["xG"]["a"]), 4),
            "away_xga": round(float(match["xG"]["h"]), 4),
        })
    return rows


def save_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main():
    leagues = load_leagues()
    all_rows = []
    summary = {}

    for league_key, league_cfg in leagues.items():
        slug = league_cfg["understat_name"]
        for season in SEASONS:
            label = f"{league_key} {season}-{str(season + 1)[-2:]}"
            try:
                data = fetch_season(slug, season)
                rows = parse_matches(data, league_key, season)
                count = len(rows)
                summary[label] = count

                filename = f"{league_key}_{season}.csv"
                save_csv(rows, os.path.join(OUTPUT_DIR, filename))
                all_rows.extend(rows)
                print(f"  {label}: {count} matches")
            except Exception as e:
                summary[label] = f"ERROR: {e}"
                print(f"  {label}: ERROR - {e}")

            time.sleep(2)

    save_csv(all_rows, os.path.join(OUTPUT_DIR, "all_matches.csv"))

    print(f"\n{'='*50}")
    print(f"UNDERSTAT SCRAPING SUMMARY")
    print(f"{'='*50}")
    total = 0
    for label, count in summary.items():
        if isinstance(count, int):
            total += count
        print(f"  {label}: {count}")
    print(f"\n  TOTAL MATCHES: {total}")
    print(f"  Output: {os.path.abspath(OUTPUT_DIR)}")


if __name__ == "__main__":
    main()
