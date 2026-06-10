from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
GROUPS = tuple("ABCDEFGHIJKL")
THIRD_PLACE_MATCHES = ("M74", "M77", "M79", "M80", "M81", "M82", "M85", "M87")


@dataclass(frozen=True)
class SimulationConfig:
    penalty_damping: float = 900.0
    random_seed: int | None = None
