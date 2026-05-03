import difflib
import json
import logging
import unicodedata

import pandas as pd

logger = logging.getLogger(__name__)

_ALIAS_CACHE = {}


def _normalize(s: str) -> str:
    """Normalize Unicode to NFC and strip whitespace."""
    return unicodedata.normalize('NFC', s).strip()


def _load_aliases(alias_path: str) -> dict:
    if alias_path not in _ALIAS_CACHE:
        with open(alias_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        # Normalize all keys and values
        normalized = {}
        for league, mapping in raw.items():
            normalized[league] = {_normalize(k): _normalize(v) for k, v in mapping.items()}
        _ALIAS_CACHE[alias_path] = normalized
    return _ALIAS_CACHE[alias_path]


def map_team_name(
    api_name: str,
    league: str,
    alias_path: str = 'data/aliases/team_aliases.json'
) -> str | None:
    """
    Maps an Odds API team name to our canonical team name.
    Returns the canonical name if found, None if not mapped.
    """
    aliases = _load_aliases(alias_path)
    league_aliases = aliases.get(league, {})
    api_name = _normalize(api_name)

    # Direct match — canonical name is a key
    if api_name in league_aliases:
        return league_aliases[api_name]

    # Check if api_name is already a canonical (value) in the alias dict
    canonical_names = set(league_aliases.values()) | set(league_aliases.keys())
    if api_name in canonical_names:
        return api_name

    # Fuzzy match against all known names for this league
    all_known = list(league_aliases.keys()) + list(league_aliases.values())
    matches = difflib.get_close_matches(api_name, all_known, n=1, cutoff=0.85)
    if matches:
        candidate = matches[0]
        # If matched a key, return its value; if matched a value, return as-is
        if candidate in league_aliases:
            return league_aliases[candidate]
        return candidate

    # No alias found — return the api_name as-is (assume it is already canonical)
    return api_name


def find_unmapped_teams(
    odds_df: pd.DataFrame,
    ratings_dict: dict,
    alias_path: str = 'data/aliases/team_aliases.json'
) -> list[str]:
    """
    Checks which team names in odds_df don't map to any team in ratings_dict.
    Returns list of unmapped API team names (with their league).
    """
    unmapped = []
    seen = set()

    for _, row in odds_df.iterrows():
        league = row['league']
        for col in ['home_team', 'away_team']:
            api_name = row[col]
            key = (league, api_name)
            if key in seen:
                continue
            seen.add(key)

            canonical = map_team_name(api_name, league, alias_path)
            if canonical is None or canonical not in ratings_dict:
                unmapped.append(f"{league}: '{api_name}' -> canonical='{canonical}'")

    return unmapped
