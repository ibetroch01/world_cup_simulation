from __future__ import annotations


def win_probability(elo_a: float, elo_b: float, damping: float = 400.0) -> float:
    if damping <= 0:
        raise ValueError("damping must be positive")
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / damping))


def score_from_goals(goals_a: int, goals_b: int) -> tuple[float, float]:
    if goals_a > goals_b:
        return 1.0, 0.0
    if goals_a < goals_b:
        return 0.0, 1.0
    return 0.5, 0.5


def update_elo(
    elo_a: float,
    elo_b: float,
    score_a: float,
    score_b: float,
    k_factor: float = 30.0,
) -> tuple[float, float]:
    expected_a = win_probability(elo_a, elo_b, 400.0)
    expected_b = win_probability(elo_b, elo_a, 400.0)
    return (
        elo_a + k_factor * (score_a - expected_a),
        elo_b + k_factor * (score_b - expected_b),
    )

