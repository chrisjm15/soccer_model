"""
Build and verify the team name alias table for soft leagues (B1, N1, P1, T1, E1, DNK, SWE, NOR).
Maps Sofascore team names -> canonical football-data.co.uk team names.

Matching cascade:
  1. Exact match
  2. Normalised match (accent-stripped, case-folded, common club tokens removed)
  3. Fuzzy match (difflib.SequenceMatcher best match)

If data/aliases/soft_league_aliases.json already exists and --reset is not passed,
any hand-edited overrides in the JSON are preserved and flagged as manual overrides.
"""

import argparse
import difflib
import json
import os
import re
import unicodedata

import pandas as pd

PROXY_LEAGUES = ['B1', 'N1', 'P1', 'T1', 'E1']
SCAND_LEAGUES = ['DNK', 'SWE', 'NOR']
ALL_LEAGUES = PROXY_LEAGUES + SCAND_LEAGUES

ALIAS_PATH = os.path.join('data', 'aliases', 'soft_league_aliases.json')

# Common club tokens removed during normalisation
CLUB_TOKENS = {
    'fc', 'if', 'bk', 'kv', 'sk', 'fk', 'jk', 'afc', 'cf', 'sc', 'k', 'r',
    'royal', 'royale', 'kaa', 'kas', 'krc', 'kvc', 'rc', 'rfc', 'rsc', 'sv',
    'vv', 'fcv', 'va', 'nec', 'pec', 'rkc', 'cd', 'cs', 'sad', 'cp', 'mke',
    'ac', 'ifk', 'ik', 'gif', 'aif', 'bois', 'is', 'ff', 'il', 'fotball',
    'fodbold', 'boldklub', 'town', 'city', 'united', 'athletic', 'albion',
    'rovers', 'wanderers', 'county', 'argyle', 'north', 'end', 'futebol',
    'sporting', 'de',
}


def strip_accents(s: str) -> str:
    """Strip diacritics and Nordic/Turkish/German special characters."""
    replacements = {
        'ø': 'o', 'Ø': 'O',
        'æ': 'ae', 'Æ': 'Ae',
        'å': 'a', 'Å': 'A',
        'ß': 'ss',
        'ı': 'i', 'İ': 'i',
    }
    for src, dst in replacements.items():
        s = s.replace(src, dst)
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )


def normalize_name(s: str) -> str:
    """Accent-strip, case-fold, strip punctuation, remove common club tokens."""
    s_clean = strip_accents(s).lower()
    s_clean = re.sub(r'[^a-z0-9\s]', ' ', s_clean)
    tokens = [t for t in s_clean.split() if t not in CLUB_TOKENS]
    if not tokens:
        return s_clean.strip()
    return ' '.join(tokens)


def get_season_file_pairs(league: str) -> list[tuple[str, str, str]]:
    """Return list of (season_label, footballdata_path, sofascore_path) that exist in both sources."""
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


def auto_match_team(sf_name: str, fd_teams: list[str], norm_fd_map: dict[str, list[str]]) -> tuple[str, str, float]:
    """Return (matched_fd_name, method, score) for a Sofascore team name."""
    # 1. Exact match
    if sf_name in fd_teams:
        return sf_name, 'exact', 1.0

    # 2. Normalised match (unique)
    ns = normalize_name(sf_name)
    if ns in norm_fd_map and len(norm_fd_map[ns]) == 1:
        return norm_fd_map[ns][0], 'normalised', 1.0

    # 3. Difflib best match across normalised and accent-stripped strings
    best_fd = None
    best_score = -1.0
    sf_ascii = strip_accents(sf_name).lower()
    for fd_name in fd_teams:
        fd_norm = normalize_name(fd_name)
        fd_ascii = strip_accents(fd_name).lower()
        sc_norm = difflib.SequenceMatcher(None, ns, fd_norm).ratio()
        sc_raw = difflib.SequenceMatcher(None, sf_ascii, fd_ascii).ratio()
        score = max(sc_norm, sc_raw)
        if score > best_score:
            best_score = score
            best_fd = fd_name
    return best_fd, 'fuzzy', best_score


def main():
    parser = argparse.ArgumentParser(description='Build and verify soft-league team aliases')
    parser.add_argument('--reset', action='store_true', help='Ignore existing JSON and write pure auto-matches')
    args = parser.parse_args()

    existing_aliases = {}
    if not args.reset and os.path.exists(ALIAS_PATH):
        with open(ALIAS_PATH, 'r', encoding='utf-8') as f:
            existing_aliases = json.load(f)

    final_aliases = {}

    print("=" * 100)
    print("SOFT LEAGUE TEAM ALIAS TABLE (Sofascore -> football-data)")
    print("=" * 100)

    for league in ALL_LEAGUES:
        pairs = get_season_file_pairs(league)
        fd_teams_all = set()
        sf_teams_all = set()
        season_teams = []

        for season_label, fd_path, sf_path in pairs:
            fd_df = pd.read_csv(fd_path)
            sf_df = pd.read_csv(sf_path)
            fd_t = set(fd_df['home_team'].dropna().str.strip()) | set(fd_df['away_team'].dropna().str.strip())
            sf_t = set(sf_df['home_team'].dropna().str.strip()) | set(sf_df['away_team'].dropna().str.strip())
            fd_teams_all |= fd_t
            sf_teams_all |= sf_t
            season_teams.append((season_label, fd_t, sf_t))

        fd_sorted = sorted(fd_teams_all)
        sf_sorted = sorted(sf_teams_all)

        norm_fd_map = {}
        for f_name in fd_sorted:
            nf = normalize_name(f_name)
            norm_fd_map.setdefault(nf, []).append(f_name)

        league_existing = existing_aliases.get(league, {})
        league_map = {}

        print(f"\n--- {league} ({len(sf_sorted)} Sofascore teams, {len(fd_sorted)} football-data teams across {len(pairs)} seasons) ---")
        print(f"  {'Sofascore Name':<32} -> {'football-data Name':<25} | {'Method':<12} | {'Score':<6} | Notes")
        print(f"  {'-'*32}    {'-'*25}   {'-'*12}   {'-'*6}   {'-'*25}")

        for sf_name in sf_sorted:
            auto_fd, method, score = auto_match_team(sf_name, fd_sorted, norm_fd_map)
            chosen_fd = league_existing.get(sf_name, auto_fd)
            note = ""
            if chosen_fd != auto_fd:
                note = f"manual override (auto: {auto_fd} [{method}, {score:.2f}])"
                method_display = "manual"
            else:
                method_display = method
            league_map[sf_name] = chosen_fd
            print(f"  {sf_name:<32} -> {chosen_fd:<25} | {method_display:<12} | {score:<6.2f} | {note}")

        # Preserve any extra FD-to-FD normalisation entries (e.g. NOR 'Ham-Kam' -> 'HamKam')
        for k, v in league_existing.items():
            if k not in league_map:
                league_map[k] = v
                print(f"  {k:<32} -> {v:<25} | {'fd_norm':<12} | {1.00:<6.2f} | football-data internal alias")

        final_aliases[league] = league_map

        # Unmatched football-data names across all seasons
        mapped_fd_all = {league_map.get(s, s) for s in sf_sorted}
        canon_fd_all = {league_map.get(f, f) for f in fd_sorted}
        unmatched_fd = sorted(canon_fd_all - mapped_fd_all)
        if unmatched_fd:
            print(f"  Unmatched football-data names in {league}: {unmatched_fd}")
        else:
            print(f"  Unmatched football-data names in {league}: none")

        # Check 1-to-1 within each league-season
        season_issues = []
        for season_label, fd_t, sf_t in season_teams:
            # Map Sofascore names
            sf_to_fd = {}
            fd_from_sf = {}
            for s in sorted(sf_t):
                target = league_map.get(s, s)
                sf_to_fd[s] = target
                fd_from_sf.setdefault(target, []).append(s)

            # Check no two Sofascore names map to the same football-data team in one season
            for target, sources in fd_from_sf.items():
                if len(sources) > 1:
                    season_issues.append(
                        f"{league} {season_label}: collision — Sofascore {sources} both map to '{target}'"
                    )

            # Canonicalise FD names if an internal FD alias exists in league_map
            fd_canon_in_season = {league_map.get(f, f) for f in fd_t}

            # Check every Sofascore mapped name exists in FD for that season
            missing_in_fd = sorted(set(fd_from_sf.keys()) - fd_canon_in_season)
            if missing_in_fd:
                season_issues.append(
                    f"{league} {season_label}: Sofascore mapped team(s) not in FD season: {missing_in_fd}"
                )

            # Check every FD team in that season has a Sofascore name
            missing_in_sf = sorted(fd_canon_in_season - set(fd_from_sf.keys()))
            if missing_in_sf:
                season_issues.append(
                    f"{league} {season_label}: FD team(s) with no Sofascore team in season: {missing_in_sf}"
                )

        if season_issues:
            print(f"  1-to-1 season check notes for {league}:")
            for issue in season_issues:
                print(f"    - {issue}")
        else:
            print(f"  1-to-1 season check for {league}: PASS (exact 1-to-1 in all {len(pairs)} seasons)")

    os.makedirs(os.path.dirname(ALIAS_PATH), exist_ok=True)
    with open(ALIAS_PATH, 'w', encoding='utf-8') as f:
        json.dump(final_aliases, f, indent=2, ensure_ascii=False)
    print(f"\nSaved alias table to {ALIAS_PATH}")


if __name__ == '__main__':
    main()
