from __future__ import annotations

import pandas as pd

from .bracket import validate_third_place_mapping
from .config import DATA_DIR, GROUPS


def load_csv(name: str, data_dir=DATA_DIR) -> pd.DataFrame:
    path = data_dir / name
    if not path.exists():
        raise FileNotFoundError(f"Required data file is missing: {path}")
    return pd.read_csv(path)


def load_teams(data_dir=DATA_DIR) -> pd.DataFrame:
    teams = load_csv("teams.csv", data_dir)
    required = {"team_id", "team_name", "group", "fifa_rank"}
    missing = required - set(teams.columns)
    if missing:
        raise ValueError(f"teams.csv is missing required columns: {sorted(missing)}")
    if len(teams) != 48:
        raise ValueError(f"teams.csv must contain 48 teams; found {len(teams)}")
    if set(teams["group"]) != set(GROUPS):
        raise ValueError("teams.csv must cover groups A-L")
    counts = teams.groupby("group")["team_id"].count()
    bad = counts[counts != 4]
    if not bad.empty:
        raise ValueError(f"Each group must contain exactly four teams; bad groups: {bad.to_dict()}")
    if teams["team_id"].duplicated().any():
        raise ValueError("teams.csv contains duplicate team_id values")
    return teams


def load_initial_elos(data_dir=DATA_DIR) -> dict[str, float]:
    elos = load_csv("initial_elo.csv", data_dir)
    required = {"team_id", "elo"}
    missing = required - set(elos.columns)
    if missing:
        raise ValueError(f"initial_elo.csv is missing required columns: {sorted(missing)}")
    return dict(zip(elos["team_id"], elos["elo"].astype(float)))


def load_r32_slots(data_dir=DATA_DIR) -> pd.DataFrame:
    slots = load_csv("fifa_r32_slots.csv", data_dir)
    required = {"match_id", "slot_a", "slot_b"}
    missing = required - set(slots.columns)
    if missing:
        raise ValueError(f"fifa_r32_slots.csv is missing required columns: {sorted(missing)}")
    if len(slots) != 16:
        raise ValueError(f"fifa_r32_slots.csv must contain 16 Round of 32 matches; found {len(slots)}")
    return slots


def load_third_place_mapping(data_dir=DATA_DIR) -> pd.DataFrame:
    mapping = load_csv("fifa_third_place_mapping.csv", data_dir)
    validate_third_place_mapping(mapping)
    return mapping


def load_all_data(data_dir=DATA_DIR) -> tuple[pd.DataFrame, dict[str, float], pd.DataFrame, pd.DataFrame]:
    teams = load_teams(data_dir)
    elos = load_initial_elos(data_dir)
    missing_elos = set(teams["team_id"]) - set(elos)
    if missing_elos:
        raise ValueError(f"initial_elo.csv is missing Elo values for teams: {sorted(missing_elos)}")
    slots = load_r32_slots(data_dir)
    mapping = load_third_place_mapping(data_dir)
    return teams, elos, slots, mapping

