from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
GROUPS = tuple("ABCDEFGHIJKL")
THIRD_PLACE_MATCHES = ("M74", "M77", "M79", "M80", "M81", "M82", "M85", "M87")


@dataclass(frozen=True)
class SimulationConfig:
    total_expected_goals: float = 2.70
    elo_goal_damping: float = 800.0
    update_elo_during_tournament: bool = False
    k_factor: float = 30.0
    penalty_damping: float = 800.0
    random_seed: int | None = None

