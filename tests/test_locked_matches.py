from __future__ import annotations

import pandas as pd

from src.config import SimulationConfig
from src.data_loader import load_all_data, load_teams
from src.locked_matches import validate_locked_matches
from src.simulation import _play_knockout_fast, run_standard_simulations


def locked_rows(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        rows,
        columns=["phase", "match_id", "group", "team_a", "team_b", "goals_a", "goals_b", "winner_team", "played_at"],
    )


def test_validate_locked_matches_rejects_duplicate_group_match():
    teams = load_teams()
    rows = locked_rows(
        [
            {"phase": "group", "match_id": "", "group": "A", "team_a": "MEX", "team_b": "RSA", "goals_a": 2, "goals_b": 0, "winner_team": "", "played_at": "2026-06-11"},
            {"phase": "group", "match_id": "", "group": "A", "team_a": "RSA", "team_b": "MEX", "goals_a": 0, "goals_b": 2, "winner_team": "", "played_at": "2026-06-11"},
        ]
    )
    try:
        validate_locked_matches(rows, teams)
    except ValueError as exc:
        assert "duplicate locked group match" in str(exc)
    else:
        raise AssertionError("expected duplicate locked group match to fail")


def test_validate_locked_matches_rejects_negative_goals():
    teams = load_teams()
    rows = locked_rows(
        [
            {"phase": "group", "match_id": "", "group": "A", "team_a": "MEX", "team_b": "RSA", "goals_a": -1, "goals_b": 0, "winner_team": "", "played_at": ""},
        ]
    )
    try:
        validate_locked_matches(rows, teams)
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("expected negative goals to fail")


def test_knockout_draw_requires_winner_team():
    teams = load_teams()
    rows = locked_rows(
        [
            {"phase": "knockout", "match_id": "M73", "group": "", "team_a": "MEX", "team_b": "KOR", "goals_a": 1, "goals_b": 1, "winner_team": "", "played_at": ""},
        ]
    )
    try:
        validate_locked_matches(rows, teams)
    except ValueError as exc:
        assert "draws require winner_team" in str(exc)
    else:
        raise AssertionError("expected knockout draw without winner_team to fail")


def test_latest_locked_match_uses_played_at_then_csv_order():
    teams = load_teams()
    locked = validate_locked_matches(
        locked_rows(
            [
                {"phase": "group", "match_id": "", "group": "A", "team_a": "MEX", "team_b": "RSA", "goals_a": 2, "goals_b": 0, "winner_team": "", "played_at": "2026-06-11"},
                {"phase": "group", "match_id": "", "group": "A", "team_a": "KOR", "team_b": "CZE", "goals_a": 2, "goals_b": 1, "winner_team": "", "played_at": "2026-06-11"},
            ]
        ),
        teams,
    )
    assert locked.latest_played_at == "2026-06-11"
    assert locked.latest_match is not None
    assert locked.latest_match.team_a == "KOR"
    assert locked.latest_match.team_b == "CZE"


def test_locked_group_match_influences_group_table():
    teams, elos, slots, mapping = load_all_data()
    locked = validate_locked_matches(
        locked_rows(
            [
                {
                    "phase": "group",
                    "match_id": "",
                    "group": "A",
                    "team_a": "MEX",
                    "team_b": "RSA",
                    "goals_a": 3,
                    "goals_b": 0,
                    "winner_team": "",
                    "played_at": "2026-06-11",
                }
            ]
        ),
        teams,
    )

    def zero_goal_model(_team_a: str, _team_b: str) -> tuple[float, float]:
        return 0.0, 0.0

    group_df, _knockout_df, diagnostics = run_standard_simulations(
        1,
        teams,
        elos,
        slots,
        mapping,
        SimulationConfig(random_seed=7),
        zero_goal_model,
        locked_matches=locked,
    )
    mexico = group_df[group_df["team"].eq("Mexico")].iloc[0]
    assert mexico["p_place_1"] == 1.0
    assert diagnostics["avg_goals_per_match"] > 0


def test_locked_knockout_incompatible_teams_fails_clearly():
    teams = load_teams()
    locked = validate_locked_matches(
        locked_rows(
            [
                {"phase": "knockout", "match_id": "M73", "group": "", "team_a": "MEX", "team_b": "KOR", "goals_a": 2, "goals_b": 0, "winner_team": "", "played_at": ""},
            ]
        ),
        teams,
    )
    try:
        _play_knockout_fast(
            "CZE",
            "RSA",
            {"CZE": 1700.0, "RSA": 1600.0},
            SimulationConfig(),
            pd.Series([0]).array,
            lambda _a, _b: (1.0, 1.0),
            "M73",
            locked.knockout_match("M73"),
        )
    except ValueError as exc:
        assert "Lock the preceding matches first" in str(exc)
    else:
        raise AssertionError("expected incompatible locked knockout match to fail")
