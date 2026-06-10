from __future__ import annotations

from itertools import combinations

import pandas as pd

from .config import SimulationConfig
from .match import simulate_match
from .tiebreakers import rank_best_thirds, rank_group_table


def play_group_stage(
    teams: pd.DataFrame,
    elos: dict[str, float],
    config: SimulationConfig,
    rng,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, dict[str, float], list[dict]]:
    group_tables: dict[str, pd.DataFrame] = {}
    all_matches: list[dict] = []
    working_elos = dict(elos)

    for group, group_df in teams.sort_values(["group", "team_id"]).groupby("group", sort=True):
        rows = {
            row.team_id: {
                "team_id": row.team_id,
                "team_name": row.team_name,
                "group": group,
                "played": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
                "goal_difference": 0,
                "points": 0,
                "fair_play": 0,
                "fifa_rank": int(row.fifa_rank),
            }
            for row in group_df.itertuples(index=False)
        }
        group_matches: list[dict] = []
        for ix, (team_a, team_b) in enumerate(combinations(rows.keys(), 2), start=1):
            result, working_elos = simulate_match(
                f"G{group}-{ix}", team_a, team_b, working_elos, config, rng, knockout=False
            )
            rows[team_a]["played"] += 1
            rows[team_b]["played"] += 1
            rows[team_a]["goals_for"] += result.goals_a
            rows[team_a]["goals_against"] += result.goals_b
            rows[team_b]["goals_for"] += result.goals_b
            rows[team_b]["goals_against"] += result.goals_a
            if result.goals_a > result.goals_b:
                rows[team_a]["wins"] += 1
                rows[team_b]["losses"] += 1
                rows[team_a]["points"] += 3
            elif result.goals_b > result.goals_a:
                rows[team_b]["wins"] += 1
                rows[team_a]["losses"] += 1
                rows[team_b]["points"] += 3
            else:
                rows[team_a]["draws"] += 1
                rows[team_b]["draws"] += 1
                rows[team_a]["points"] += 1
                rows[team_b]["points"] += 1
            for team_id in (team_a, team_b):
                rows[team_id]["goal_difference"] = rows[team_id]["goals_for"] - rows[team_id]["goals_against"]
            match_dict = {
                "match_id": result.match_id,
                "group": group,
                "team_a": team_a,
                "team_b": team_b,
                "goals_a": result.goals_a,
                "goals_b": result.goals_b,
            }
            group_matches.append(match_dict)
            all_matches.append(match_dict)

        table = rank_group_table(pd.DataFrame(rows.values()), group_matches)
        table["group_rank"] = range(1, len(table) + 1)
        group_tables[group] = table

    thirds = pd.concat([table.iloc[[2]] for table in group_tables.values()], ignore_index=True)
    best_thirds = rank_best_thirds(thirds).head(8)
    return group_tables, best_thirds, working_elos, all_matches

