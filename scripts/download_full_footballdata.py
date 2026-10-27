"""Download football-data.co.uk CSVs UNFILTERED (all columns, incl. closing 1X2 and O/U odds) for the Big 5,
2020-21 .. 2025-26. Saves to data/raw/footballdata_full/<League>_<season>.csv (gitignored with data/raw/).
Read-only for everything else. Run:  python scripts/download_full_footballdata.py
"""
import os, sys, time
import requests

BASE_URL = 'https://www.football-data.co.uk/mmz4281'
HEADERS = {'User-Agent': 'Mozilla/5.0'}
LEAGUES = {'EPL': 'E0', 'La_Liga': 'SP1', 'Bundesliga': 'D1', 'Serie_A': 'I1', 'Ligue_1': 'F1'}
SEASONS = {'2020-21': '2021', '2021-22': '2122', '2022-23': '2223', '2023-24': '2324',
           '2024-25': '2425', '2025-26': '2526'}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'raw', 'footballdata_full')


def main():
    os.makedirs(OUT, exist_ok=True)
    fails = 0
    for lg, code in LEAGUES.items():
        for season, sc in SEASONS.items():
            path = os.path.join(OUT, f'{lg}_{season}.csv')
            if os.path.exists(path) and os.path.getsize(path) > 10000:
                print(f'  have  {lg} {season}')
                continue
            try:
                r = requests.get(f'{BASE_URL}/{sc}/{code}.csv', headers=HEADERS, timeout=30)
                r.raise_for_status()
                with open(path, 'wb') as f:
                    f.write(r.content)
                head = r.content[:2000].decode('latin-1')
                has_close = 'AvgCH' in head or 'PSCH' in head
                print(f'  saved {lg} {season}  {len(r.content)//1024} KB  closing 1X2 columns: {has_close}')
            except Exception as e:
                fails += 1
                print(f'  FAILED {lg} {season}: {e}')
            time.sleep(1.0)
    print(f'Done. Failures: {fails}')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
