from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd

from .config import SimulationConfig
from .tournament import STAGE_ORDER, TournamentResult, simulate_tournament


PROBABILITY_STAGES = ["Round of 32", "Round of 16", "Quarterfinal", "Semifinal", "Final", "Champion"]
FINISH_STAGES = ["Group", "Round of 32", "Round of 16", "Quarterfinal", "Semifinal", "Final", "Champion"]
FINISH_LABELS = {
    "Group": "Group Stage",
    "Round of 32": "Round of 32",
    "Round of 16": "Round of 16",
    "Quarterfinal": "Quarterfinal",
    "Semifinal": "Semifinal",
    "Final": "Final",
    "Champion": "Champion",
}


def simulate_sample_by_index(
    sample_index: int,
    teams: pd.DataFrame,
    initial_elos: dict[str, float],
    r32_slots: pd.DataFrame,
    third_mapping: pd.DataFrame,
    config: SimulationConfig,
) -> TournamentResult:
    if sample_index <= 0:
        raise ValueError("sample_index must be 1 or greater")
    seed_sequence = np.random.SeedSequence(config.random_seed)
    child_seed = seed_sequence.spawn(sample_index)[sample_index - 1]
    rng = np.random.default_rng(child_seed)
    return simulate_tournament(teams, initial_elos, r32_slots, third_mapping, config, rng)


def run_simulations(
    n_simulations: int,
    teams: pd.DataFrame,
    initial_elos: dict[str, float],
    r32_slots: pd.DataFrame,
    third_mapping: pd.DataFrame,
    config: SimulationConfig,
    progress_callback=None,
) -> tuple[pd.DataFrame, pd.DataFrame, TournamentResult]:
    if n_simulations <= 0:
        raise ValueError("number of simulations must be positive")

    seed_sequence = np.random.SeedSequence(config.random_seed)
    team_ids = list(teams["team_id"])
    reach_counts = {stage: Counter() for stage in PROBABILITY_STAGES}
    finish_counts = {stage: Counter() for stage in FINISH_STAGES}
    points = Counter()
    goals_for = Counter()
    goals_against = Counter()
    champions = Counter()
    total_goals = 0
    total_matches = 0
    draws_90 = 0
    sample_result: TournamentResult | None = None

    for ix in range(n_simulations):
        child_seed = seed_sequence.spawn(1)[0]
        rng = np.random.default_rng(child_seed)
        result = simulate_tournament(teams, initial_elos, r32_slots, third_mapping, config, rng)
        if sample_result is None:
            sample_result = result
        champions[result.champion] += 1
        for team_id in team_ids:
            reached = result.stage_reached.get(team_id, "Group")
            finish_counts[reached][team_id] += 1
            for stage in PROBABILITY_STAGES:
                if STAGE_ORDER[reached] >= STAGE_ORDER[stage]:
                    reach_counts[stage][team_id] += 1
            points[team_id] += result.group_points.get(team_id, 0)
            goals_for[team_id] += result.group_goals_for.get(team_id, 0)
            goals_against[team_id] += result.group_goals_against.get(team_id, 0)
        for match in result.group_matches:
            total_goals += int(match["goals_a"]) + int(match["goals_b"])
            total_matches += 1
            if int(match["goals_a"]) == int(match["goals_b"]):
                draws_90 += 1
        for match in result.matches:
            total_goals += match.goals_a + match.goals_b
            total_matches += 1
            if match.draw_90:
                draws_90 += 1
        if progress_callback is not None:
            progress_callback((ix + 1) / n_simulations)

    rows = []
    names = dict(zip(teams["team_id"], teams["team_name"]))
    groups = dict(zip(teams["team_id"], teams["group"]))
    for team_id in team_ids:
        rows.append(
            {
                "team_id": team_id,
                "team_name": names[team_id],
                "group": groups[team_id],
                **{
                    f"P(Finish {FINISH_LABELS[stage]})": finish_counts[stage][team_id] / n_simulations
                    for stage in FINISH_STAGES
                },
                **{f"P({stage})": reach_counts[stage][team_id] / n_simulations for stage in PROBABILITY_STAGES},
                "expected_points": points[team_id] / n_simulations,
                "avg_goals_for": goals_for[team_id] / n_simulations,
                "avg_goals_against": goals_against[team_id] / n_simulations,
            }
        )
    probability_table = pd.DataFrame(rows).sort_values("P(Champion)", ascending=False).reset_index(drop=True)

    champion_table = pd.DataFrame(
        [
            {"team_id": team_id, "team_name": names[team_id], "champion_probability": count / n_simulations}
            for team_id, count in champions.most_common()
        ]
    )
    diagnostics = {
        "avg_goals_per_match": total_goals / total_matches if total_matches else 0.0,
        "draw_rate_90": draws_90 / total_matches if total_matches else 0.0,
    }
    probability_table.attrs["diagnostics"] = diagnostics
    if sample_result is None:
        raise RuntimeError("simulation did not produce a sample tournament")
    return probability_table, champion_table, sample_result
