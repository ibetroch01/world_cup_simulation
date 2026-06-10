from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import SimulationConfig
from .elo import score_from_goals, update_elo, win_probability
from .poisson_model import expected_goals


@dataclass(frozen=True)
class MatchResult:
    match_id: str
    team_a: str
    team_b: str
    goals_a: int
    goals_b: int
    winner: str | None
    loser: str | None
    decided_by_penalties: bool = False

    @property
    def draw_90(self) -> bool:
        return self.goals_a == self.goals_b


def simulate_match(
    match_id: str,
    team_a: str,
    team_b: str,
    elos: dict[str, float],
    config: SimulationConfig,
    rng: np.random.Generator,
    knockout: bool = False,
) -> tuple[MatchResult, dict[str, float]]:
    lambda_a, lambda_b = expected_goals(
        elos[team_a], elos[team_b], config.total_expected_goals, config.elo_goal_damping
    )
    goals_a = int(rng.poisson(lambda_a))
    goals_b = int(rng.poisson(lambda_b))

    winner: str | None = None
    loser: str | None = None
    decided_by_penalties = False
    if knockout:
        if goals_a > goals_b:
            winner, loser = team_a, team_b
        elif goals_b > goals_a:
            winner, loser = team_b, team_a
        else:
            decided_by_penalties = True
            p_a = win_probability(elos[team_a], elos[team_b], config.penalty_damping)
            winner, loser = (team_a, team_b) if rng.random() < p_a else (team_b, team_a)

    next_elos = elos
    if config.update_elo_during_tournament:
        score_a, score_b = score_from_goals(goals_a, goals_b)
        new_a, new_b = update_elo(elos[team_a], elos[team_b], score_a, score_b, config.k_factor)
        next_elos = dict(elos)
        next_elos[team_a] = new_a
        next_elos[team_b] = new_b

    return (
        MatchResult(match_id, team_a, team_b, goals_a, goals_b, winner, loser, decided_by_penalties),
        next_elos,
    )

