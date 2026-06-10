from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd

from .bracket import (
    QUARTERFINAL_LINKS,
    ROUND_OF_16_LINKS,
    SEMIFINAL_LINKS,
)
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

REACH_STAGE_LEVELS = [STAGE_ORDER[stage] for stage in PROBABILITY_STAGES]


def _goal_pair(team_a: str, team_b: str, elos: dict[str, float], config: SimulationConfig, rng) -> tuple[int, int]:
    share_a = 1.0 / (1.0 + 10.0 ** (-(elos[team_a] - elos[team_b]) / config.elo_goal_damping))
    goals_a = int(rng.poisson(config.total_expected_goals * share_a))
    goals_b = int(rng.poisson(config.total_expected_goals * (1.0 - share_a)))
    return goals_a, goals_b


def _maybe_update_elos(
    team_a: str,
    team_b: str,
    goals_a: int,
    goals_b: int,
    elos: dict[str, float],
    config: SimulationConfig,
) -> None:
    if not config.update_elo_during_tournament:
        return
    expected_a = 1.0 / (1.0 + 10.0 ** ((elos[team_b] - elos[team_a]) / 400.0))
    expected_b = 1.0 - expected_a
    score_a = 1.0 if goals_a > goals_b else 0.0 if goals_a < goals_b else 0.5
    score_b = 1.0 - score_a
    elos[team_a] = elos[team_a] + config.k_factor * (score_a - expected_a)
    elos[team_b] = elos[team_b] + config.k_factor * (score_b - expected_b)


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
    names = dict(zip(teams["team_id"], teams["team_name"]))
    team_groups = dict(zip(teams["team_id"], teams["group"]))
    fifa_ranks = {str(row.team_id): int(row.fifa_rank) for row in teams.itertuples(index=False)}
    slots = [(str(row.match_id), str(row.slot_a), str(row.slot_b)) for row in r32_slots.sort_values("match_id").itertuples(index=False)]
    third_lookup = {
        key: dict(zip(chunk["match_id"], chunk["third_group"]))
        for key, chunk in third_mapping.groupby("qualified_third_groups", sort=False)
    }
    return {
        "team_ids": [str(team_id) for team_id in teams["team_id"]],
        "groups": groups,
        "names": names,
        "team_groups": team_groups,
        "fifa_ranks": fifa_ranks,
        "slots": slots,
        "third_lookup": third_lookup,
    }


def _play_knockout_fast(
    match_id: str,
    team_a: str,
    team_b: str,
    elos: dict[str, float],
    config: SimulationConfig,
    rng,
) -> tuple[str, str, int, int, bool]:
    goals_a, goals_b = _goal_pair(team_a, team_b, elos, config, rng)
    if goals_a > goals_b:
        winner, loser = team_a, team_b
    elif goals_b > goals_a:
        winner, loser = team_b, team_a
    else:
        p_a = 1.0 / (1.0 + 10.0 ** (-(elos[team_a] - elos[team_b]) / config.penalty_damping))
        winner, loser = (team_a, team_b) if rng.random() < p_a else (team_b, team_a)
    _maybe_update_elos(team_a, team_b, goals_a, goals_b, elos, config)
    return winner, loser, goals_a, goals_b, goals_a == goals_b


def _simulate_tournament_summary(prepared: dict[str, Any], initial_elos: dict[str, float], config: SimulationConfig, rng) -> dict[str, Any]:
    elos = dict(initial_elos)
    stage_levels = {team_id: 0 for team_id in prepared["team_ids"]}
    group_points: dict[str, int] = {}
    group_goals_for: dict[str, int] = {}
    group_goals_against: dict[str, int] = {}
    group_tables: dict[str, list[dict[str, Any]]] = {}
    total_goals = 0
    total_matches = 0
    draws_90 = 0

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
            goals_a, goals_b = _goal_pair(team_a, team_b, elos, config, rng)
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
            _maybe_update_elos(team_a, team_b, goals_a, goals_b, elos, config)
            group_matches.append((team_a, team_b, goals_a, goals_b))
        for row in rows.values():
            row["goal_difference"] = row["goals_for"] - row["goals_against"]
        ranked = _rank_group_fast(list(rows.values()), group_matches)
        group_tables[group] = ranked
        for row in ranked:
            team_id = row["team_id"]
            group_points[team_id] = row["points"]
            group_goals_for[team_id] = row["goals_for"]
            group_goals_against[team_id] = row["goals_against"]
        for row in ranked[:2]:
            stage_levels[row["team_id"]] = max(stage_levels[row["team_id"]], 1)

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

    qualified_groups = [row["group"] for row in best_thirds]
    key = "-".join(sorted(qualified_groups))
    third_assignments = prepared["third_lookup"].get(key)
    if third_assignments is None:
        raise ValueError(f"Missing Annex C mapping for qualifying third-place groups: {key}")
    thirds_by_group = {row["group"]: row["team_id"] for row in best_thirds}

    def resolve(slot: str, match_id: str) -> str:
        if slot.startswith("1") or slot.startswith("2"):
            return group_tables[slot[1]][int(slot[0]) - 1]["team_id"]
        group = third_assignments[match_id]
        return thirds_by_group[group]

    def play_round(pairings: list[tuple[str, str, str]]) -> tuple[dict[str, str], dict[str, str]]:
        nonlocal total_goals, total_matches, draws_90
        winners = {}
        losers = {}
        for match_id, team_a, team_b in pairings:
            winner, loser, goals_a, goals_b, draw_90 = _play_knockout_fast(match_id, team_a, team_b, elos, config, rng)
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
    champion = winners_final["M104"]
    stage_levels[champion] = 6

    return {
        "champion": champion,
        "stage_levels": stage_levels,
        "group_points": group_points,
        "group_goals_for": group_goals_for,
        "group_goals_against": group_goals_against,
        "total_goals": total_goals,
        "total_matches": total_matches,
        "draws_90": draws_90,
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
    child_seeds = seed_sequence.spawn(n_simulations)
    prepared = _preprocess_inputs(teams, r32_slots, third_mapping)
    team_ids = list(teams["team_id"])
    team_index = {team_id: ix for ix, team_id in enumerate(team_ids)}
    reach_counts = np.zeros((len(PROBABILITY_STAGES), len(team_ids)), dtype=np.int64)
    finish_counts = np.zeros((len(FINISH_STAGES), len(team_ids)), dtype=np.int64)
    points = Counter()
    goals_for = Counter()
    goals_against = Counter()
    champions = Counter()
    total_goals = 0
    total_matches = 0
    draws_90 = 0
    sample_rng = np.random.default_rng(child_seeds[0])
    sample_result = simulate_tournament(teams, initial_elos, r32_slots, third_mapping, config, sample_rng)
    progress_step = max(1, n_simulations // 100)

    for ix in range(n_simulations):
        rng = np.random.default_rng(child_seeds[ix])
        result = _simulate_tournament_summary(prepared, initial_elos, config, rng)
        champions[result["champion"]] += 1
        for team_id in team_ids:
            level = result["stage_levels"].get(team_id, 0)
            team_ix = team_index[team_id]
            finish_counts[level, team_ix] += 1
            for stage_ix, stage_level in enumerate(REACH_STAGE_LEVELS):
                if level >= stage_level:
                    reach_counts[stage_ix, team_ix] += 1
            points[team_id] += result["group_points"].get(team_id, 0)
            goals_for[team_id] += result["group_goals_for"].get(team_id, 0)
            goals_against[team_id] += result["group_goals_against"].get(team_id, 0)
        total_goals += result["total_goals"]
        total_matches += result["total_matches"]
        draws_90 += result["draws_90"]
        if progress_callback is not None and ((ix + 1) % progress_step == 0 or ix + 1 == n_simulations):
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
                    f"P(Finish {FINISH_LABELS[stage]})": finish_counts[stage_ix, team_index[team_id]] / n_simulations
                    for stage_ix, stage in enumerate(FINISH_STAGES)
                },
                **{
                    f"P({stage})": reach_counts[stage_ix, team_index[team_id]] / n_simulations
                    for stage_ix, stage in enumerate(PROBABILITY_STAGES)
                },
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
    return probability_table, champion_table, sample_result
