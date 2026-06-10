from __future__ import annotations

from collections import defaultdict

import pandas as pd


def _head_to_head_metrics(matches: list[dict], tied_teams: set[str]) -> dict[str, tuple[int, int, int]]:
    points = defaultdict(int)
    gf = defaultdict(int)
    ga = defaultdict(int)
    for match in matches:
        a = match["team_a"]
        b = match["team_b"]
        if a not in tied_teams or b not in tied_teams:
            continue
        ga_a = int(match["goals_a"])
        ga_b = int(match["goals_b"])
        gf[a] += ga_a
        ga[a] += ga_b
        gf[b] += ga_b
        ga[b] += ga_a
        if ga_a > ga_b:
            points[a] += 3
        elif ga_b > ga_a:
            points[b] += 3
        else:
            points[a] += 1
            points[b] += 1
    return {team: (points[team], gf[team] - ga[team], gf[team]) for team in tied_teams}


def rank_group_table(table: pd.DataFrame, matches: list[dict]) -> pd.DataFrame:
    required = {"team_id", "points", "goal_difference", "goals_for", "fair_play", "fifa_rank"}
    missing = required - set(table.columns)
    if missing:
        raise ValueError(f"group table is missing required columns: {sorted(missing)}")

    table = table.copy()
    ranked_chunks: list[pd.DataFrame] = []
    primary_cols = ["points", "goal_difference", "goals_for"]
    for _, chunk in table.groupby(primary_cols, sort=False, dropna=False):
        if len(chunk) == 1:
            one = chunk.copy()
            one["_tie_rank"] = 0
            ranked_chunks.append(one)
            continue
        tied = set(chunk["team_id"])
        h2h = _head_to_head_metrics(matches, tied)
        enriched = chunk.copy()
        enriched["h2h_points"] = enriched["team_id"].map(lambda team: h2h[team][0])
        enriched["h2h_goal_difference"] = enriched["team_id"].map(lambda team: h2h[team][1])
        enriched["h2h_goals_for"] = enriched["team_id"].map(lambda team: h2h[team][2])
        ranked = enriched.sort_values(
                [
                    "points",
                    "goal_difference",
                    "goals_for",
                    "h2h_points",
                    "h2h_goal_difference",
                    "h2h_goals_for",
                    "fair_play",
                    "fifa_rank",
                    "team_id",
                ],
                ascending=[False, False, False, False, False, False, False, True, True],
            )
        ranked["_tie_rank"] = range(len(ranked))
        ranked_chunks.append(ranked)
    ranked = pd.concat(ranked_chunks, ignore_index=True)
    return ranked.sort_values(
        ["points", "goal_difference", "goals_for", "_tie_rank", "fair_play", "fifa_rank", "team_id"],
        ascending=[False, False, False, True, False, True, True],
        kind="mergesort",
    ).drop(columns=["_tie_rank"], errors="ignore").reset_index(drop=True)


def rank_best_thirds(thirds: pd.DataFrame) -> pd.DataFrame:
    required = {"team_id", "group", "points", "goal_difference", "goals_for", "fair_play", "fifa_rank"}
    missing = required - set(thirds.columns)
    if missing:
        raise ValueError(f"third-place table is missing required columns: {sorted(missing)}")
    return thirds.sort_values(
        ["points", "goal_difference", "goals_for", "fair_play", "fifa_rank", "group", "team_id"],
        ascending=[False, False, False, False, True, True, True],
    ).reset_index(drop=True)
