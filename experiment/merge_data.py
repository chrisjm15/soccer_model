"""
Module 4 — Soft-League Merge (Sofascore xG + football-data.co.uk results/odds)

Merges B1, N1, P1, T1, E1 (proxy leagues) and DNK, SWE, NOR (Scandinavian leagues)
across all seasons present in both sources, outputting data/processed/soft_merged.csv
and running the full verification suite.
"""

import json
import os
import random
import pandas as pd

PROXY_LEAGUES = ['B1', 'N1', 'P1', 'T1', 'E1']
SCAND_LEAGUES = ['DNK', 'SWE', 'NOR']
ALL_LEAGUES = PROXY_LEAGUES + SCAND_LEAGUES

ALIAS_PATH = os.path.join('data', 'aliases', 'soft_league_aliases.json')
OUTPUT_PATH = os.path.join('data', 'processed', 'soft_merged.csv')

OUTPUT_COLUMNS = [
    'date', 'league', 'season', 'home_team', 'away_team',
    'home_goals', 'away_goals', 'home_xg', 'away_xg',
    'home_shots', 'away_shots', 'home_sot', 'away_sot',
    'home_corners', 'away_corners', 'home_fouls', 'away_fouls',
    'home_yellow', 'away_yellow', 'home_red', 'away_red',
    'odds_home', 'odds_draw', 'odds_away',
    'odds_over25', 'odds_under25',
    'ah_line', 'odds_ah_home', 'odds_ah_away',
    'odds_timing', 'xg_source', 'matched',
    'close_ah_line',
    'close_avg_ah_home', 'close_avg_ah_away',
    'avg_ah_home', 'avg_ah_away',
    'close_avg_home', 'close_avg_draw', 'close_avg_away',
    'avg_home', 'avg_draw', 'avg_away',
]

EXTRA_ODDS_COLS = [
    'close_ah_line',
    'close_avg_ah_home', 'close_avg_ah_away',
    'avg_ah_home', 'avg_ah_away',
    'close_avg_home', 'close_avg_draw', 'close_avg_away',
    'avg_home', 'avg_draw', 'avg_away',
]

STAT_COLS = [
    'home_shots', 'away_shots', 'home_sot', 'away_sot',
    'home_corners', 'away_corners', 'home_fouls', 'away_fouls',
    'home_yellow', 'away_yellow', 'home_red', 'away_red',
]


def get_season_file_pairs(league: str) -> list[tuple[str, str, str]]:
    """Return list of (season_label, footballdata_path, sofascore_path) existing in both sources."""
    pairs = []
    if league in PROXY_LEAGUES:
        for start_yr in range(2000, 2027):
            end_yr = start_yr + 1
            fd_season = f"{start_yr}-{str(end_yr)[-2:]}"
            sf_season = f"{start_yr}-{end_yr}"
            fd_path = os.path.join('data', 'proxy', f"{league}_{fd_season}_footballdata.csv")
            sf_path = os.path.join('data', 'proxy', f"{league}_{sf_season}_sofascore.csv")
            if os.path.exists(fd_path) and os.path.exists(sf_path):
                pairs.append((fd_season, fd_path, sf_path))
    elif league == 'DNK':
        for start_yr in range(2012, 2027):
            end_yr = start_yr + 1
            season_label = str(start_yr)
            fd_path = os.path.join('data', 'scandinavian', f"DNK_{season_label}_footballdata.csv")
            sf_path = os.path.join('data', 'proxy', f"DNK_{start_yr}-{end_yr}_sofascore.csv")
            if not os.path.exists(sf_path):
                sf_path = os.path.join('data', 'scandinavian', f"DNK_{season_label}_sofascore.csv")
            if os.path.exists(fd_path) and os.path.exists(sf_path):
                pairs.append((season_label, fd_path, sf_path))
    else:
        for yr in range(2012, 2027):
            season_label = str(yr)
            fd_path = os.path.join('data', 'scandinavian', f"{league}_{season_label}_footballdata.csv")
            sf_path = os.path.join('data', 'scandinavian', f"{league}_{season_label}_sofascore.csv")
            if os.path.exists(fd_path) and os.path.exists(sf_path):
                pairs.append((season_label, fd_path, sf_path))
    return pairs


def merge_season(
    league: str,
    season_label: str,
    fd_path: str,
    sf_path: str,
    league_aliases: dict[str, str],
):
    """Merge one league-season and return (merged_df, stats_dict, unmatched_records, ambig_records, spot_candidates)."""
    fd_df = pd.read_csv(fd_path)
    sf_df = pd.read_csv(sf_path)

    fd_df['home_canon'] = fd_df['home_team'].astype(str).str.strip().map(lambda x: league_aliases.get(x, x))
    fd_df['away_canon'] = fd_df['away_team'].astype(str).str.strip().map(lambda x: league_aliases.get(x, x))
    sf_df['home_canon'] = sf_df['home_team'].astype(str).str.strip().map(lambda x: league_aliases.get(x, x))
    sf_df['away_canon'] = sf_df['away_team'].astype(str).str.strip().map(lambda x: league_aliases.get(x, x))

    fd_df['dt'] = pd.to_datetime(fd_df['date'], errors='coerce')
    sf_df['dt'] = pd.to_datetime(sf_df['date'], errors='coerce')

    # Group Sofascore rows by (home_canon, away_canon) for fast lookup
    sf_groups = {}
    for j, s_row in sf_df.iterrows():
        key = (s_row['home_canon'], s_row['away_canon'])
        sf_groups.setdefault(key, []).append((j, s_row['dt']))

    fd_candidates = {i: [] for i in fd_df.index}
    sf_candidates = {j: [] for j in sf_df.index}

    for i, f_row in fd_df.iterrows():
        key = (f_row['home_canon'], f_row['away_canon'])
        for j, s_dt in sf_groups.get(key, []):
            diff_days = abs((f_row['dt'] - s_dt).days)
            if diff_days <= 1:
                fd_candidates[i].append((j, diff_days))
                sf_candidates[j].append((i, diff_days))

    ambig_fd = set()
    ambig_sf = set()
    ambig_records = []

    for i, cands in fd_candidates.items():
        if len(cands) > 1:
            ambig_fd.add(i)
            for j, _ in cands:
                ambig_sf.add(j)
            f_row = fd_df.loc[i]
            ambig_records.append(
                f"Ambiguous FD row in {league} {season_label}: {f_row['date']} {f_row['home_team']} vs {f_row['away_team']} matched {len(cands)} SF rows"
            )

    for j, cands in sf_candidates.items():
        if len(cands) > 1:
            ambig_sf.add(j)
            for i, _ in cands:
                ambig_fd.add(i)
            s_row = sf_df.loc[j]
            ambig_records.append(
                f"Ambiguous SF row in {league} {season_label}: {s_row['date']} {s_row['home_team']} vs {s_row['away_team']} matched {len(cands)} FD rows"
            )

    matched_pairs = {}  # fd_idx -> sf_idx
    matched_sf_indices = set()
    for i, cands in fd_candidates.items():
        if i in ambig_fd:
            continue
        if len(cands) == 1:
            j = cands[0][0]
            if j not in ambig_sf and len(sf_candidates[j]) == 1:
                matched_pairs[i] = j
                matched_sf_indices.add(j)

    odds_timing = 'pre_closing' if league in PROXY_LEAGUES else 'closing'
    out_rows = []
    spot_candidates = []

    for i, f_row in fd_df.iterrows():
        if i in ambig_fd:
            # Keep neither if ambiguous
            continue

        is_matched = i in matched_pairs
        s_row = sf_df.loc[matched_pairs[i]] if is_matched else None

        row = {
            'date': f_row['date'],
            'league': league,
            'season': season_label,
            'home_team': f_row['home_canon'],
            'away_team': f_row['away_canon'],
            'home_goals': f_row.get('home_goals'),
            'away_goals': f_row.get('away_goals'),
            'home_xg': s_row['home_xg'] if is_matched else pd.NA,
            'away_xg': s_row['away_xg'] if is_matched else pd.NA,
            'odds_home': f_row.get('odds_home'),
            'odds_draw': f_row.get('odds_draw'),
            'odds_away': f_row.get('odds_away'),
            'odds_over25': f_row.get('odds_over25'),
            'odds_under25': f_row.get('odds_under25'),
            'ah_line': f_row.get('odds_ah_line'),
            'odds_ah_home': f_row.get('odds_ah_home'),
            'odds_ah_away': f_row.get('odds_ah_away'),
            'odds_timing': odds_timing,
            'matched': is_matched,
        }

        for col in EXTRA_ODDS_COLS:
            row[col] = f_row.get(col, pd.NA) if league in PROXY_LEAGUES else pd.NA

        for col in STAT_COLS:
            f_val = f_row.get(col)
            if pd.notna(f_val):
                row[col] = f_val
            elif is_matched and pd.notna(s_row.get(col)):
                row[col] = s_row.get(col)
            else:
                row[col] = pd.NA

        has_xg_val = pd.notna(row['home_xg']) and pd.notna(row['away_xg'])
        row['xg_source'] = 'sofascore' if has_xg_val else pd.NA

        out_rows.append(row)

        if is_matched and has_xg_val:
            spot_candidates.append((row, f_row.to_dict(), s_row.to_dict(), fd_path, sf_path))

    merged_df = pd.DataFrame(out_rows)
    merged_df = merged_df.reindex(columns=OUTPUT_COLUMNS)

    sf_has_xg = sf_df['home_xg'].notna().sum() > 0
    unmatched_records = []
    if sf_has_xg:
        for i, f_row in fd_df.iterrows():
            if i not in matched_pairs:
                unmatched_records.append({
                    'league': league,
                    'season': season_label,
                    'source': 'football-data',
                    'date': f_row['date'],
                    'home_team': f_row['home_team'],
                    'away_team': f_row['away_team'],
                    'mapped': f"{f_row['home_canon']} vs {f_row['away_canon']}",
                })
        for j, s_row in sf_df.iterrows():
            if j not in matched_sf_indices:
                unmatched_records.append({
                    'league': league,
                    'season': season_label,
                    'source': 'sofascore',
                    'date': s_row['date'],
                    'home_team': s_row['home_team'],
                    'away_team': s_row['away_team'],
                    'mapped': f"{s_row['home_canon']} vs {s_row['away_canon']}",
                })

    n_fd = len(fd_df)
    n_sf = len(sf_df)
    n_matched = len(matched_pairs)
    n_with_xg = int(merged_df['home_xg'].notna().sum()) if not merged_df.empty else 0
    match_rate = (n_matched / n_fd * 100.0) if n_fd > 0 else 0.0

    stats = {
        'league': league,
        'season': season_label,
        'fd_rows': n_fd,
        'sf_rows': n_sf,
        'matched': n_matched,
        'match_rate': match_rate,
        'rows_with_xg': n_with_xg,
        'sf_has_xg': sf_has_xg,
        'mean_home_xg': merged_df['home_xg'].dropna().astype(float).mean() if n_with_xg > 0 else None,
        'mean_away_xg': merged_df['away_xg'].dropna().astype(float).mean() if n_with_xg > 0 else None,
        'odds_home_pct': merged_df['odds_home'].notna().mean() * 100.0 if not merged_df.empty else 0.0,
        'ah_line_pct': merged_df['ah_line'].notna().mean() * 100.0 if not merged_df.empty else 0.0,
    }

    return merged_df, stats, unmatched_records, ambig_records, spot_candidates


def main():
    with open(ALIAS_PATH, 'r', encoding='utf-8') as f:
        aliases = json.load(f)

    all_dfs = []
    all_stats = []
    all_unmatched_xg_seasons = []
    all_ambig = []
    spots_by_league = {}

    for league in ALL_LEAGUES:
        league_aliases = aliases.get(league, {})
        pairs = get_season_file_pairs(league)
        spots_by_league[league] = []
        for season_label, fd_path, sf_path in pairs:
            mdf, st, unm, amb, spots = merge_season(league, season_label, fd_path, sf_path, league_aliases)
            all_dfs.append(mdf)
            all_stats.append(st)
            all_unmatched_xg_seasons.extend(unm)
            all_ambig.extend(amb)
            spots_by_league[league].extend(spots)

    full_df = pd.concat(all_dfs, ignore_index=True)
    full_df = full_df.sort_values(['league', 'date', 'home_team'], kind='mergesort').reset_index(drop=True)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    full_df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved merged dataset to {OUTPUT_PATH} ({len(full_df):,} total rows)\n")

    # === TASK 3: VERIFICATION SUITE ===
    print("=" * 105)
    print("CHECK 1 & 2 & 4 — PER LEAGUE-SEASON SUMMARY (MATCH RATE, xG PLAUSIBILITY, ODDS COVERAGE)")
    print("=" * 105)
    header = (
        f"{'League':<6} {'Season':<8} | {'FD':>4} {'SF':>4} {'Match':>5} {'Rate%':>7} {'w/xG':>5} | "
        f"{'Mean H_xG':>9} {'Mean A_xG':>9} | {'odds_home%':>10} {'ah_line%':>9}"
    )
    print(header)
    print("-" * len(header))
    for st in all_stats:
        mh = f"{st['mean_home_xg']:.3f}" if st['mean_home_xg'] is not None else "   -   "
        ma = f"{st['mean_away_xg']:.3f}" if st['mean_away_xg'] is not None else "   -   "
        flag = ""
        if st['sf_has_xg'] and st['match_rate'] < 98.0:
            flag = " <-- BELOW 98%"
        print(
            f"{st['league']:<6} {st['season']:<8} | {st['fd_rows']:>4d} {st['sf_rows']:>4d} "
            f"{st['matched']:>5d} {st['match_rate']:>6.2f}% {st['rows_with_xg']:>5d} | "
            f"{mh:>9} {ma:>9} | {st['odds_home_pct']:>9.2f}% {st['ah_line_pct']:>8.2f}%{flag}"
        )

    print(f"\nAmbiguous pairs discarded across all league-seasons: {len(all_ambig)}")
    for a in all_ambig:
        print(f"  - {a}")

    print("\n" + "=" * 105)
    print("CHECK 1b — ALL UNMATCHED ROWS ON SEASONS WHERE SOFASCORE HAS xG")
    print("=" * 105)
    fd_unm = [u for u in all_unmatched_xg_seasons if u['source'] == 'football-data']
    sf_unm = [u for u in all_unmatched_xg_seasons if u['source'] == 'sofascore']
    print(f"Unmatched football-data rows on xG seasons ({len(fd_unm)}):")
    for u in fd_unm:
        print(f"  [{u['league']} {u['season']}] source={u['source']:<13} date={u['date']}  {u['home_team']} vs {u['away_team']} (mapped: {u['mapped']})")

    print(f"\nUnmatched Sofascore rows on xG seasons ({len(sf_unm)}):")
    for u in sf_unm:
        print(f"  [{u['league']} {u['season']}] source={u['source']:<13} date={u['date']}  {u['home_team']} vs {u['away_team']} (mapped: {u['mapped']})")

    print("\n" + "=" * 105)
    print("CHECK 2b — xG OUTLIERS (home_xg or away_xg > 6.0 or < 0.0)")
    print("=" * 105)
    xg_rows = full_df[full_df['home_xg'].notna() | full_df['away_xg'].notna()].copy()
    xg_rows['home_xg_num'] = pd.to_numeric(xg_rows['home_xg'], errors='coerce')
    xg_rows['away_xg_num'] = pd.to_numeric(xg_rows['away_xg'], errors='coerce')
    outliers = xg_rows[
        (xg_rows['home_xg_num'] > 6.0) | (xg_rows['home_xg_num'] < 0.0) |
        (xg_rows['away_xg_num'] > 6.0) | (xg_rows['away_xg_num'] < 0.0)
    ]
    print(f"Rows with xG > 6 or < 0: {len(outliers)}")
    if not outliers.empty:
        for _, r in outliers.iterrows():
            print(f"  {r['league']} {r['season']} {r['date']}: {r['home_team']} vs {r['away_team']} (home_xg={r['home_xg']}, away_xg={r['away_xg']})")

    print("\n" + "=" * 105)
    print("CHECK 3 — DUPLICATE (league, date, home_team, away_team) ROWS")
    print("=" * 105)
    dups = full_df[full_df.duplicated(subset=['league', 'date', 'home_team', 'away_team'], keep=False)]
    print(f"Duplicate (league, date, home_team, away_team) rows: {len(dups)}")

    print("\n" + "=" * 105)
    print("CHECK 5 — SPOT-CHECK 3 RANDOM MATCHED ROWS PER LEAGUE AGAINST RAW SOURCE FILES")
    print("=" * 105)
    rng = random.Random(42)
    for league in ALL_LEAGUES:
        cands = spots_by_league[league]
        sample = rng.sample(cands, min(3, len(cands)))
        print(f"\n--- {league} (3 random matched rows) ---")
        for idx, (m_row, f_raw, s_raw, fd_p, sf_p) in enumerate(sample, 1):
            print(f"  [{league} #{idx}] Merged: date={m_row['date']} season={m_row['season']} {m_row['home_team']} vs {m_row['away_team']} | "
                  f"goals={m_row['home_goals']}-{m_row['away_goals']} | xG={m_row['home_xg']}-{m_row['away_xg']} | "
                  f"shots={m_row['home_shots']}-{m_row['away_shots']} | 1X2={m_row['odds_home']}/{m_row['odds_draw']}/{m_row['odds_away']} | "
                  f"AH={m_row['ah_line']} ({m_row['odds_ah_home']}/{m_row['odds_ah_away']}) | timing={m_row['odds_timing']}")
            print(f"    Raw FD ({os.path.basename(fd_p)}): date={f_raw['date']} {f_raw['home_team']} vs {f_raw['away_team']} | "
                  f"goals={f_raw['home_goals']}-{f_raw['away_goals']} | shots={f_raw['home_shots']}-{f_raw['away_shots']} | "
                  f"1X2={f_raw['odds_home']}/{f_raw['odds_draw']}/{f_raw['odds_away']} | AH={f_raw['odds_ah_line']} ({f_raw['odds_ah_home']}/{f_raw['odds_ah_away']})")
            print(f"    Raw SF ({os.path.basename(sf_p)}): date={s_raw['date']} {s_raw['home_team']} vs {s_raw['away_team']} | "
                  f"xG={s_raw['home_xg']}-{s_raw['away_xg']} | shots={s_raw['home_shots']}-{s_raw['away_shots']} | "
                  f"sot={s_raw['home_sot']}-{s_raw['away_sot']} | corners={s_raw['home_corners']}-{s_raw['away_corners']}")


if __name__ == '__main__':
    main()
