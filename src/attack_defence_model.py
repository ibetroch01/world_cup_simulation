from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class AttackDefenceRating:
    attack_score: float
    defence_score: float
    overall_score: float
    matches_used: int


@dataclass(frozen=True)
class AttackDefenceModel:
    ratings: dict[str, AttackDefenceRating]
    base_rate: float
    goals_scale: float = 1.0
    strength_temperature: float = 0.83

    def rating_for(self, team: str) -> AttackDefenceRating:
        rating = self.ratings.get(team)
        if rating is not None:
            return rating
        LOGGER.warning("Missing Attack/Defence rating for %s; using attack=1.0 and defence=1.0", team)
        return AttackDefenceRating(attack_score=1.0, defence_score=1.0, overall_score=1.0, matches_used=0)

    def expected_goals(self, team_a: str, team_b: str) -> tuple[float, float]:
        rating_a = self.rating_for(team_a)
        rating_b = self.rating_for(team_b)
        attack_a = rating_a.attack_score**self.strength_temperature
        attack_b = rating_b.attack_score**self.strength_temperature
        defence_a = rating_a.defence_score**self.strength_temperature
        defence_b = rating_b.defence_score**self.strength_temperature
        lambda_a = self.goals_scale * self.base_rate * attack_a * defence_b
        lambda_b = self.goals_scale * self.base_rate * attack_b * defence_a
        if lambda_a <= 0 or lambda_b <= 0:
            raise ValueError("Attack/Defence model produced non-positive expected goals")
        return float(lambda_a), float(lambda_b)


def load_attack_defence_model(
    ratings_file: Path,
    training_report: Path,
    goals_scale: float = 1.0,
    strength_temperature: float = 0.83,
) -> AttackDefenceModel:
    ratings_df = pd.read_csv(ratings_file)
    required = {"team", "attack_score", "defence_score", "overall_score", "matches_used"}
    missing = required - set(ratings_df.columns)
    if missing:
        raise ValueError(f"Attack/Defence ratings file is missing required columns: {sorted(missing)}")
    report = json.loads(training_report.read_text(encoding="utf-8"))
    base_rate = float(report["base_rate"])
    ratings = {
        str(row.team): AttackDefenceRating(
            attack_score=float(row.attack_score),
            defence_score=float(row.defence_score),
            overall_score=float(row.overall_score),
            matches_used=int(row.matches_used),
        )
        for row in ratings_df.itertuples(index=False)
    }
    if strength_temperature <= 0:
        raise ValueError("strength_temperature must be positive")
    return AttackDefenceModel(
        ratings=ratings,
        base_rate=base_rate,
        goals_scale=float(goals_scale),
        strength_temperature=float(strength_temperature),
    )
