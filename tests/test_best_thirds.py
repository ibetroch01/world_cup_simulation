import pandas as pd

from src.tiebreakers import rank_best_thirds


def test_best_third_ranking():
    thirds = pd.DataFrame(
        [
            {"team_id": "A3", "group": "A", "points": 4, "goal_difference": 0, "goals_for": 3, "fair_play": 0, "fifa_rank": 30},
            {"team_id": "B3", "group": "B", "points": 4, "goal_difference": 1, "goals_for": 2, "fair_play": 0, "fifa_rank": 40},
            {"team_id": "C3", "group": "C", "points": 3, "goal_difference": 4, "goals_for": 5, "fair_play": 0, "fifa_rank": 10},
        ]
    )
    ranked = rank_best_thirds(thirds)
    assert list(ranked["team_id"]) == ["B3", "A3", "C3"]

