from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


GROUP_PHASE_COLUMNS = {
    "team",
    "group",
    "p_place_1",
    "p_place_2",
    "p_place_3",
    "p_place_4",
    "p_advance_group",
    "p_advance_best_third",
    "p_eliminated_group",
}
KNOCKOUT_PHASE_COLUMNS = {"team", "p_r32", "p_r16", "p_qf", "p_sf", "p_final", "p_champion"}
REQUIRED_OUTPUT_FILES = {
    "metadata": "metadata.json",
    "group_phase": "group_phase_results.csv",
    "knockout_phase": "knockout_phase_results.csv",
}


@dataclass(frozen=True)
class SimulationOutput:
    path: Path
    metadata: dict[str, Any]
    group_phase: pd.DataFrame
    knockout_phase: pd.DataFrame
    team_ratings: pd.DataFrame | None = None


def _validate_probability_columns(df: pd.DataFrame, columns: set[str], label: str) -> None:
    probability_columns = [column for column in columns if column.startswith("p_")]
    for column in probability_columns:
        values = pd.to_numeric(df[column], errors="coerce")
        if values.isna().any() or ((values < -1e-12) | (values > 1 + 1e-12)).any():
            raise ValueError(f"{label} contains invalid probabilities in {column}")


def load_simulation_output(path: Path) -> SimulationOutput:
    missing_files = [filename for filename in REQUIRED_OUTPUT_FILES.values() if not (path / filename).exists()]
    if missing_files:
        raise FileNotFoundError(f"Simulation output folder {path} is missing files: {missing_files}")

    metadata = json.loads((path / REQUIRED_OUTPUT_FILES["metadata"]).read_text(encoding="utf-8"))
    group_phase = pd.read_csv(path / REQUIRED_OUTPUT_FILES["group_phase"])
    knockout_phase = pd.read_csv(path / REQUIRED_OUTPUT_FILES["knockout_phase"])
    team_ratings_path = path / "team_ratings.csv"
    team_ratings = pd.read_csv(team_ratings_path) if team_ratings_path.exists() else None

    missing_group = GROUP_PHASE_COLUMNS - set(group_phase.columns)
    if missing_group:
        raise ValueError(f"group_phase_results.csv is missing required columns: {sorted(missing_group)}")
    missing_knockout = KNOCKOUT_PHASE_COLUMNS - set(knockout_phase.columns)
    if missing_knockout:
        raise ValueError(f"knockout_phase_results.csv is missing required columns: {sorted(missing_knockout)}")
    _validate_probability_columns(group_phase, GROUP_PHASE_COLUMNS, "group_phase_results.csv")
    _validate_probability_columns(knockout_phase, KNOCKOUT_PHASE_COLUMNS, "knockout_phase_results.csv")
    if team_ratings is not None:
        base_columns = {"team", "team_id", "group"}
        missing_base = base_columns - set(team_ratings.columns)
        if missing_base:
            raise ValueError(f"team_ratings.csv is missing required columns: {sorted(missing_base)}")
        if "elo" not in team_ratings.columns and not {"attack_score", "defence_score", "overall_score", "matches_used", "rating_source"} <= set(team_ratings.columns):
            raise ValueError("team_ratings.csv must contain either elo or Attack/Defence rating columns")
    return SimulationOutput(
        path=path,
        metadata=metadata,
        group_phase=group_phase,
        knockout_phase=knockout_phase,
        team_ratings=team_ratings,
    )


def list_output_folders(outputs_dir: Path) -> list[Path]:
    if not outputs_dir.exists():
        return []
    return sorted(
        [path for path in outputs_dir.iterdir() if path.is_dir() and all((path / filename).exists() for filename in REQUIRED_OUTPUT_FILES.values())],
        key=lambda path: path.name,
    )
