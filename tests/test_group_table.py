import pandas as pd

from src.tiebreakers import rank_group_table


def test_group_ranking_by_points_goal_difference_goals_for():
    table = pd.DataFrame(
        [
            {"team_id": "A", "points": 6, "goal_difference": 2, "goals_for": 4, "fair_play": 0, "fifa_rank": 10},
            {"team_id": "B", "points": 6, "goal_difference": 3, "goals_for": 3, "fair_play": 0, "fifa_rank": 20},
            {"team_id": "C", "points": 4, "goal_difference": 1, "goals_for": 5, "fair_play": 0, "fifa_rank": 30},
            {"team_id": "D", "points": 1, "goal_difference": -6, "goals_for": 1, "fair_play": 0, "fifa_rank": 40},
        ]
    )
    ranked = rank_group_table(table, [])
    assert list(ranked["team_id"]) == ["B", "A", "C", "D"]

