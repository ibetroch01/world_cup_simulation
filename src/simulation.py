from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd

from .bracket import QUARTERFINAL_LINKS, ROUND_OF_16_LINKS, SEMIFINAL_LINKS
from .config import SimulationConfig
from .locked_matches import LockedMatch, LockedMatchIndex


PROBABILITY_STAGES = ["Round of 32", "Round of 16", "Quarterfinal", "Semifinal", "Final", "Champion"]
REACH_STAGE_LEVELS = [1, 2, 3, 4, 5, 6]
GoalModel = Callable[[str, str], tuple[float, float]]


def _goal_pair(team_a: str, team_b: str, rng, goal_model: GoalModel) -> tuple[int, int]:
    lambda_a, lambda_b = goal_model(team_a, team_b)
    return int(rng.poisson(lambda_a)), int(rng.poisson(lambda_b))


def _rank_group_fast(rows: list[dict[str, Any]], matches: list[tuple[str, str, int, int]]) -> list[dict[str, Any]]:
    tie_rank: dict[str, int] = {}
    primary_groups: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
    for row in rows:
        primary_groups.setdefault((row["points"], row["goal_difference"], row["goals_for"]), []).append(row)

    for chunk in primary_groups.values():
        if len(chunk) == 1:
            tie_rank[chunk[0]["team_id"]] = 0
            continue
        tied = {row["team_id"] for row in chunk}
        h_points = {team_id: 0 for team_id in tied}
        h_gf = {team_id: 0 for team_id in tied}
        h_ga = {team_id: 0 for team_id in tied}
        for team_a, team_b, goals_a, goals_b in matches:
            if team_a not in tied or team_b not in tied:
                continue
            h_gf[team_a] += goals_a
            h_ga[team_a] += goals_b
            h_gf[team_b] += goals_b
            h_ga[team_b] += goals_a
            if goals_a > goals_b:
                h_points[team_a] += 3
            elif goals_b > goals_a:
                h_points[team_b] += 3
            else:
                h_points[team_a] += 1
                h_points[team_b] += 1
        ranked_chunk = sorted(
            chunk,
            key=lambda row: (
                -row["points"],
                -row["goal_difference"],
                -row["goals_for"],
                -h_points[row["team_id"]],
                -(h_gf[row["team_id"]] - h_ga[row["team_id"]]),
                -h_gf[row["team_id"]],
                -row["fair_play"],
                row["fifa_rank"],
                row["team_id"],
            ),
        )
        for ix, row in enumerate(ranked_chunk):
            tie_rank[row["team_id"]] = ix

    return sorted(
        rows,
        key=lambda row: (
            -row["points"],
            -row["goal_difference"],
            -row["goals_for"],
            tie_rank[row["team_id"]],
            -row["fair_play"],
            row["fifa_rank"],
            row["team_id"],
        ),
    )


def _preprocess_inputs(teams: pd.DataFrame, r32_slots: pd.DataFrame, third_mapping: pd.DataFrame) -> dict[str, Any]:
    teams_sorted = teams.sort_values(["group", "team_id"])
    groups = {
        str(group): [str(team_id) for team_id in group_df["team_id"]]
        for group, group_df in teams_sorted.groupby("group", sort=True)
    }
    third_lookup = {
        key: dict(zip(chunk["match_id"], chunk["third_group"]))
        for key, chunk in third_mapping.groupby("qualified_third_groups", sort=False)
    }
    return {
        "team_ids": [str(team_id) for team_id in teams["team_id"]],
        "groups": groups,
        "names": dict(zip(teams["team_id"], teams["team_name"])),
        "team_groups": dict(zip(teams["team_id"], teams["group"])),
        "fifa_ranks": {str(row.team_id): int(row.fifa_rank) for row in teams.itertuples(index=False)},
        "slots": [(str(row.match_id), str(row.slot_a), str(row.slot_b)) for row in r32_slots.sort_values("match_id").itertuples(index=False)],
        "third_lookup": third_lookup,
    }


def _play_knockout_fast(
    team_a: str,
    team_b: str,
    elos: dict[str, float],
    config: SimulationConfig,
    rng,
    goal_model: GoalModel,
    match_id: str,
    locked_match: LockedMatch | None = None,
) -> tuple[str, int, int, bool]:
    if locked_match is not None:
        if {team_a, team_b} != {locked_match.team_a, locked_match.team_b}:
            raise ValueError(
                f"Locked knockout match {match_id} expects {locked_match.team_a} vs {locked_match.team_b}, "
                f"but this simulation produced {team_a} vs {team_b}. Lock the preceding matches first."
            )
        if team_a == locked_match.team_a:
            goals_a, goals_b = locked_match.goals_a, locked_match.goals_b
        else:
            goals_a, goals_b = locked_match.goals_b, locked_match.goals_a
        winner = locked_match.winner
        if winner is None:
            raise ValueError(f"Locked knockout match {match_id} has no winner")
        return winner, goals_a, goals_b, goals_a == goals_b

    goals_a, goals_b = _goal_pair(team_a, team_b, rng, goal_model)
    if goals_a > goals_b:
        winner = team_a
    elif goals_b > goals_a:
        winner = team_b
    else:
        p_a = 1.0 / (1.0 + 10.0 ** (-(elos[team_a] - elos[team_b]) / config.penalty_damping))
        winner = team_a if rng.random() < p_a else team_b
    return winner, goals_a, goals_b, goals_a == goals_b


def _simulate_tournament_summary(
    prepared: dict[str, Any],
    initial_elos: dict[str, float],
    config: SimulationConfig,
    rng,
    goal_model: GoalModel,
    locked_matches: LockedMatchIndex | None = None,
) -> dict[str, Any]:
    stage_levels = {team_id: 0 for team_id in prepared["team_ids"]}
    group_tables: dict[str, list[dict[str, Any]]] = {}
    total_goals = 0
    total_matches = 0
    draws_90 = 0
    group_places: dict[str, int] = {}
    advance_group: set[str] = set()
    advance_best_third: set[str] = set()

    for group, team_ids in prepared["groups"].items():
        rows = {
            team_id: {
                "team_id": team_id,
                "group": group,
                "goals_for": 0,
                "goals_against": 0,
                "goal_difference": 0,
                "points": 0,
                "fair_play": 0,
                "fifa_rank": prepared["fifa_ranks"][team_id],
            }
            for team_id in team_ids
        }
        group_matches = []
        for team_a, team_b in combinations(team_ids, 2):
            locked_match = locked_matches.group_match(group, team_a, team_b) if locked_matches is not None else None
            if locked_match is not None:
                if team_a == locked_match.team_a:
                    goals_a, goals_b = locked_match.goals_a, locked_match.goals_b
                else:
                    goals_a, goals_b = locked_match.goals_b, locked_match.goals_a
            else:
                goals_a, goals_b = _goal_pair(team_a, team_b, rng, goal_model)
            total_goals += goals_a + goals_b
            total_matches += 1
            draws_90 += int(goals_a == goals_b)
            rows[team_a]["goals_for"] += goals_a
            rows[team_a]["goals_against"] += goals_b
            rows[team_b]["goals_for"] += goals_b
            rows[team_b]["goals_against"] += goals_a
            if goals_a > goals_b:
                rows[team_a]["points"] += 3
            elif goals_b > goals_a:
                rows[team_b]["points"] += 3
            else:
                rows[team_a]["points"] += 1
                rows[team_b]["points"] += 1
            group_matches.append((team_a, team_b, goals_a, goals_b))
        for row in rows.values():
            row["goal_difference"] = row["goals_for"] - row["goals_against"]
        ranked = _rank_group_fast(list(rows.values()), group_matches)
        group_tables[group] = ranked
        for place, row in enumerate(ranked, start=1):
            group_places[row["team_id"]] = place
        for row in ranked[:2]:
            stage_levels[row["team_id"]] = max(stage_levels[row["team_id"]], 1)
            advance_group.add(row["team_id"])

    thirds = [ranked[2] for ranked in group_tables.values()]
    best_thirds = sorted(
        thirds,
        key=lambda row: (
            -row["points"],
            -row["goal_difference"],
            -row["goals_for"],
            -row["fair_play"],
            row["fifa_rank"],
            row["group"],
            row["team_id"],
        ),
    )[:8]
    for row in best_thirds:
        stage_levels[row["team_id"]] = max(stage_levels[row["team_id"]], 1)
        advance_best_third.add(row["team_id"])

    key = "-".join(sorted(row["group"] for row in best_thirds))
    third_assignments = prepared["third_lookup"].get(key)
    if third_assignments is None:
        raise ValueError(f"Missing Annex C mapping for qualifying third-place groups: {key}")
    thirds_by_group = {row["group"]: row["team_id"] for row in best_thirds}

    def resolve(slot: str, match_id: str) -> str:
        if slot.startswith("1") or slot.startswith("2"):
            return group_tables[slot[1]][int(slot[0]) - 1]["team_id"]
        return thirds_by_group[third_assignments[match_id]]

    def play_round(pairings: list[tuple[str, str, str]]) -> tuple[dict[str, str], dict[str, str]]:
        nonlocal total_goals, total_matches, draws_90
        winners = {}
        losers = {}
        for match_id, team_a, team_b in pairings:
            locked_match = locked_matches.knockout_match(match_id) if locked_matches is not None else None
            winner, goals_a, goals_b, draw_90 = _play_knockout_fast(
                team_a,
                team_b,
                initial_elos,
                config,
                rng,
                goal_model,
                match_id,
                locked_match,
            )
            loser = team_b if winner == team_a else team_a
            winners[match_id] = winner
            losers[match_id] = loser
            total_goals += goals_a + goals_b
            total_matches += 1
            draws_90 += int(draw_90)
        return winners, losers

    r32_pairings = [(match_id, resolve(slot_a, match_id), resolve(slot_b, match_id)) for match_id, slot_a, slot_b in prepared["slots"]]
    winners, _ = play_round(r32_pairings)
    for team_id in winners.values():
        stage_levels[team_id] = max(stage_levels[team_id], 2)

    r16_pairings = [(match_id, winners[a], winners[b]) for match_id, (a, b) in ROUND_OF_16_LINKS.items()]
    winners_16, _ = play_round(r16_pairings)
    for team_id in winners_16.values():
        stage_levels[team_id] = max(stage_levels[team_id], 3)

    qf_pairings = [(match_id, winners_16[a], winners_16[b]) for match_id, (a, b) in QUARTERFINAL_LINKS.items()]
    winners_qf, _ = play_round(qf_pairings)
    for team_id in winners_qf.values():
        stage_levels[team_id] = max(stage_levels[team_id], 4)

    sf_pairings = [(match_id, winners_qf[a], winners_qf[b]) for match_id, (a, b) in SEMIFINAL_LINKS.items()]
    winners_sf, losers_sf = play_round(sf_pairings)
    for team_id in winners_sf.values():
        stage_levels[team_id] = max(stage_levels[team_id], 5)

    play_round([("M103", losers_sf["M101"], losers_sf["M102"])])
    winners_final, _ = play_round([("M104", winners_sf["M101"], winners_sf["M102"])])
    stage_levels[winners_final["M104"]] = 6

    return {
        "stage_levels": stage_levels,
        "total_goals": total_goals,
        "total_matches": total_matches,
        "draws_90": draws_90,
        "group_places": group_places,
        "advance_group": advance_group,
        "advance_best_third": advance_best_third,
    }


def run_standard_simulations(
    n_simulations: int,
    teams: pd.DataFrame,
    initial_elos: dict[str, float],
    r32_slots: pd.DataFrame,
    third_mapping: pd.DataFrame,
    config: SimulationConfig,
    goal_model: GoalModel,
    locked_matches: LockedMatchIndex | None = None,
    progress_callback=None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    if n_simulations <= 0:
        raise ValueError("number of simulations must be positive")

    seed_sequence = np.random.SeedSequence(config.random_seed)
    child_seeds = seed_sequence.spawn(n_simulations)
    prepared = _preprocess_inputs(teams, r32_slots, third_mapping)
    team_ids = list(prepared["team_ids"])
    team_index = {team_id: ix for ix, team_id in enumerate(team_ids)}
    reach_counts = np.zeros((len(PROBABILITY_STAGES), len(team_ids)), dtype=np.int64)
    place_counts = np.zeros((4, len(team_ids)), dtype=np.int64)
    advance_group_counts = np.zeros(len(team_ids), dtype=np.int64)
    advance_best_third_counts = np.zeros(len(team_ids), dtype=np.int64)
    total_goals = 0
    total_matches = 0
    draws_90 = 0
    progress_step = max(1, n_simulations // 100)

    for ix in range(n_simulations):
        rng = np.random.default_rng(child_seeds[ix])
        result = _simulate_tournament_summary(prepared, initial_elos, config, rng, goal_model, locked_matches)
        for team_id in team_ids:
            team_ix = team_index[team_id]
            place = result["group_places"].get(team_id)
            if place is not None:
                place_counts[int(place) - 1, team_ix] += 1
            if team_id in result["advance_group"]:
                advance_group_counts[team_ix] += 1
            if team_id in result["advance_best_third"]:
                advance_best_third_counts[team_ix] += 1
            level = result["stage_levels"].get(team_id, 0)
            for stage_ix, stage_level in enumerate(REACH_STAGE_LEVELS):
                if level >= stage_level:
                    reach_counts[stage_ix, team_ix] += 1
        total_goals += result["total_goals"]
        total_matches += result["total_matches"]
        draws_90 += result["draws_90"]
        if progress_callback is not None and ((ix + 1) % progress_step == 0 or ix + 1 == n_simulations):
            progress_callback((ix + 1) / n_simulations)

    names = prepared["names"]
    groups = prepared["team_groups"]
    group_rows = []
    knockout_rows = []
    for team_id in team_ids:
        team_ix = team_index[team_id]
        p_advance_group = advance_group_counts[team_ix] / n_simulations
        p_advance_best_third = advance_best_third_counts[team_ix] / n_simulations
        group_rows.append(
            {
                "team": names[team_id],
                "group": groups[team_id],
                "p_place_1": place_counts[0, team_ix] / n_simulations,
                "p_place_2": place_counts[1, team_ix] / n_simulations,
                "p_place_3": place_counts[2, team_ix] / n_simulations,
                "p_place_4": place_counts[3, team_ix] / n_simulations,
                "p_advance_group": p_advance_group,
                "p_advance_best_third": p_advance_best_third,
                "p_eliminated_group": max(0.0, 1.0 - p_advance_group - p_advance_best_third),
            }
        )
        knockout_rows.append(
            {
                "team": names[team_id],
                "p_r32": reach_counts[0, team_ix] / n_simulations,
                "p_r16": reach_counts[1, team_ix] / n_simulations,
                "p_qf": reach_counts[2, team_ix] / n_simulations,
                "p_sf": reach_counts[3, team_ix] / n_simulations,
                "p_final": reach_counts[4, team_ix] / n_simulations,
                "p_champion": reach_counts[5, team_ix] / n_simulations,
            }
        )

    diagnostics = {
        "avg_goals_per_match": total_goals / total_matches if total_matches else 0.0,
        "draw_rate_90": draws_90 / total_matches if total_matches else 0.0,
    }
    return (
        pd.DataFrame(group_rows).sort_values(["group", "team"]).reset_index(drop=True),
        pd.DataFrame(knockout_rows).sort_values("p_champion", ascending=False).reset_index(drop=True),
        diagnostics,
    )
