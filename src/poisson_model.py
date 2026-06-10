from __future__ import annotations

import math


def elo_goal_share(elo_a: float, elo_b: float, damping: float = 800.0) -> float:
    if damping <= 0:
        raise ValueError("elo_goal_damping must be positive")
    return 1.0 / (1.0 + 10.0 ** (-(elo_a - elo_b) / damping))


def expected_goals(
    elo_a: float,
    elo_b: float,
    total_expected_goals: float = 2.70,
    damping: float = 800.0,
) -> tuple[float, float]:
    if total_expected_goals <= 0:
        raise ValueError("total_expected_goals must be positive")
    share_a = elo_goal_share(elo_a, elo_b, damping)
    lambda_a = total_expected_goals * share_a
    lambda_b = total_expected_goals * (1.0 - share_a)
    if not math.isfinite(lambda_a + lambda_b):
        raise ValueError("expected goals calculation produced a non-finite value")
    return lambda_a, lambda_b

