from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .bracket import (
    FINAL_LINKS,
    QUARTERFINAL_LINKS,
    ROUND_OF_16_LINKS,
    SEMIFINAL_LINKS,
    resolve_r32_slots,
)
from .config import SimulationConfig
from .group_stage import play_group_stage
from .match import MatchResult, simulate_match


@dataclass
class TournamentResult:
    champion: str
    group_tables: dict[str, pd.DataFrame]
    best_thirds: pd.DataFrame
    stage_reached: dict[str, str]
    group_points: dict[str, int]
    group_goals_for: dict[str, int]
    group_goals_against: dict[str, int]
    matches: list[MatchResult]
    group_matches: list[dict]


STAGE_ORDER = {
    "Group": 0,
    "Round of 32": 1,
    "Round of 16": 2,
    "Quarterfinal": 3,
    "Semifinal": 4,
    "Final": 5,
    "Champion": 6,
}


def _mark(stage_reached: dict[str, str], team_id: str, stage: str) -> None:
    if STAGE_ORDER[stage] > STAGE_ORDER[stage_reached.get(team_id, "Group")]:
        stage_reached[team_id] = stage


def _play_knockout_round(
    pairings: list[tuple[str, str, str]],
    elos: dict[str, float],
    config: SimulationConfig,
    rng,
) -> tuple[dict[str, str], dict[str, str], list[MatchResult], dict[str, float]]:
    winners: dict[str, str] = {}
    losers: dict[str, str] = {}
    results: list[MatchResult] = []
    working_elos = elos
    for match_id, team_a, team_b in pairings:
        result, working_elos = simulate_match(match_id, team_a, team_b, working_elos, config, rng, knockout=True)
        winners[match_id] = str(result.winner)
        losers[match_id] = str(result.loser)
        results.append(result)
    return winners, losers, results, working_elos


def simulate_tournament(
    teams: pd.DataFrame,
    initial_elos: dict[str, float],
    r32_slots: pd.DataFrame,
    third_mapping: pd.DataFrame,
    config: SimulationConfig,
    rng,
) -> TournamentResult:
    group_tables, best_thirds, elos, group_matches = play_group_stage(teams, initial_elos, config, rng)
    stage_reached = {team_id: "Group" for team_id in teams["team_id"]}
    group_points = {}
    group_goals_for = {}
    group_goals_against = {}
    for table in group_tables.values():
        for row in table.itertuples(index=False):
            group_points[row.team_id] = int(row.points)
            group_goals_for[row.team_id] = int(row.goals_for)
            group_goals_against[row.team_id] = int(row.goals_against)
        for row in table.head(2).itertuples(index=False):
            _mark(stage_reached, row.team_id, "Round of 32")
    for row in best_thirds.itertuples(index=False):
        _mark(stage_reached, row.team_id, "Round of 32")

    knockout_matches: list[MatchResult] = []

    r32_pairings = resolve_r32_slots(r32_slots, group_tables, best_thirds, third_mapping)
    winners, losers, results, elos = _play_knockout_round(r32_pairings, elos, config, rng)
    knockout_matches.extend(results)
    for team in winners.values():
        _mark(stage_reached, team, "Round of 16")

    r16_pairings = [(match_id, winners[a], winners[b]) for match_id, (a, b) in ROUND_OF_16_LINKS.items()]
    winners_16, losers_16, results, elos = _play_knockout_round(r16_pairings, elos, config, rng)
    knockout_matches.extend(results)
    for team in winners_16.values():
        _mark(stage_reached, team, "Quarterfinal")

    qf_pairings = [(match_id, winners_16[a], winners_16[b]) for match_id, (a, b) in QUARTERFINAL_LINKS.items()]
    winners_qf, losers_qf, results, elos = _play_knockout_round(qf_pairings, elos, config, rng)
    knockout_matches.extend(results)
    for team in winners_qf.values():
        _mark(stage_reached, team, "Semifinal")

    sf_pairings = [(match_id, winners_qf[a], winners_qf[b]) for match_id, (a, b) in SEMIFINAL_LINKS.items()]
    winners_sf, losers_sf, results, elos = _play_knockout_round(sf_pairings, elos, config, rng)
    knockout_matches.extend(results)
    for team in winners_sf.values():
        _mark(stage_reached, team, "Final")

    third_place_pairing = [("M103", losers_sf["M101"], losers_sf["M102"])]
    _, _, results, elos = _play_knockout_round(third_place_pairing, elos, config, rng)
    knockout_matches.extend(results)

    final_pairing = [("M104", winners_sf["M101"], winners_sf["M102"])]
    winners_final, _, results, _ = _play_knockout_round(final_pairing, elos, config, rng)
    knockout_matches.extend(results)
    champion = winners_final["M104"]
    _mark(stage_reached, champion, "Champion")

    return TournamentResult(
        champion=champion,
        group_tables=group_tables,
        best_thirds=best_thirds,
        stage_reached=stage_reached,
        group_points=group_points,
        group_goals_for=group_goals_for,
        group_goals_against=group_goals_against,
        matches=knockout_matches,
        group_matches=group_matches,
    )

