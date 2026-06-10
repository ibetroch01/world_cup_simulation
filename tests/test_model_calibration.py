from __future__ import annotations

import pandas as pd

from src.model_calibration import (
    REQUIRED_CALIBRATION_REPORT_FIELDS,
    build_rolling_folds,
    build_gamma_grid,
    calibrate_strength_temperature_and_regularization,
    evaluate_holdout_nll,
    parse_grid_values,
    prepare_holdout_matches,
    CalibrationConfig,
)
from scripts.calibrate_strength_temperature import parse_float_grid


def test_gamma_grid_includes_checkpoints():
    grid = build_gamma_grid(0.80, 1.40, 0.01)
    assert 1.0 in grid
    assert 1.1 in grid
    assert 1.2 in grid


def test_parse_grid_values_requires_positive_values():
    assert parse_grid_values([180, 365.0]) == (180.0, 365.0)

    try:
        parse_grid_values([1.0, 0.0])
    except ValueError as exc:
        assert "positive" in str(exc)
    else:
        raise AssertionError("Expected non-positive grid value to fail")


def test_cli_parse_float_grid():
    assert parse_float_grid("180,365,500,730") == (180.0, 365.0, 500.0, 730.0)
    assert parse_float_grid("0.001,0.01,0.05,0.1") == (0.001, 0.01, 0.05, 0.1)


def test_rolling_folds_use_dataset_max_date_for_2026():
    matches = pd.DataFrame(
        [
            {"date": "2022-01-01", "home_team": "A", "away_team": "B", "home_goals": 1, "away_goals": 0, "neutral": True, "competition": "Friendly"},
            {"date": "2026-06-09", "home_team": "A", "away_team": "B", "home_goals": 1, "away_goals": 1, "neutral": True, "competition": "Friendly"},
        ]
    )
    folds = build_rolling_folds(matches)
    assert [fold.name for fold in folds] == ["test_2024", "test_2025", "test_2026"]
    assert folds[-1].test_end_date == "2026-06-09"


def test_holdout_excludes_missing_team_ratings():
    matches = pd.DataFrame(
        [
            {"date": "2025-01-01", "home_team": "A", "away_team": "B", "home_goals": 1, "away_goals": 0, "neutral": True, "competition": "Friendly"},
            {"date": "2025-01-02", "home_team": "A", "away_team": "C", "home_goals": 1, "away_goals": 1, "neutral": True, "competition": "Friendly"},
        ]
    )
    holdout = prepare_holdout_matches(matches, {"A", "B"}, "2025-01-01", "2025-12-31")
    assert len(holdout) == 1
    assert holdout.attrs["excluded_test_matches_count"] == 1


def test_evaluate_holdout_nll_prefers_expected_gamma_on_synthetic_data():
    ratings = pd.DataFrame(
        [
            {"team": "A", "attack_score": 2.0, "defence_score": 0.5, "overall_score": 4.0, "matches_used": 20},
            {"team": "B", "attack_score": 1.0, "defence_score": 1.0, "overall_score": 1.0, "matches_used": 20},
        ]
    )
    report = {"base_rate": 1.0, "home_advantage": 1.0}
    holdout = pd.DataFrame(
        [
            {"date": "2025-01-01", "home_team": "A", "away_team": "B", "home_goals": 4, "away_goals": 0, "neutral": True, "competition": "Friendly"},
            {"date": "2025-01-02", "home_team": "A", "away_team": "B", "home_goals": 3, "away_goals": 1, "neutral": True, "competition": "Friendly"},
        ]
    )
    assert evaluate_holdout_nll(ratings, report, holdout, 1.4)["holdout_nll"] < evaluate_holdout_nll(ratings, report, holdout, 0.8)["holdout_nll"]


def test_calibration_report_contains_required_fields():
    rows = []
    teams = ["A", "B", "C"]
    for ix in range(45):
        rows.append(
            {
                "date": f"2024-01-{(ix % 28) + 1:02d}",
                "home_team": teams[ix % 3],
                "away_team": teams[(ix + 1) % 3],
                "home_goals": 2 if ix % 3 == 0 else 1,
                "away_goals": 1,
                "neutral": True,
                "competition": "Friendly",
            }
        )
    for ix in range(9):
        rows.append(
            {
                "date": f"2025-01-{ix + 1:02d}",
                "home_team": teams[ix % 3],
                "away_team": teams[(ix + 1) % 3],
                "home_goals": 1,
                "away_goals": 1,
                "neutral": True,
                "competition": "Friendly",
            }
        )
    result = calibrate_strength_temperature_and_regularization(
        pd.DataFrame(rows),
        CalibrationConfig(
            train_start_date="2024-01-01",
            train_end_date="2024-12-31",
            test_start_date="2025-01-01",
            half_life_grid=(365.0,),
            regularization_grid=(0.1,),
            gamma_grid=(1.0, 1.1),
            min_matches_per_team=5,
            rolling_backtest=False,
        ),
    )
    assert REQUIRED_CALIBRATION_REPORT_FIELDS <= set(result.report)
    assert not result.grid.empty
    assert result.report["selection_metric"] == "main_holdout_test_nll"


def test_calibration_selects_lowest_rolling_total_nll():
    rows = []
    teams = ["A", "B", "C"]
    for year in [2022, 2023, 2024, 2025, 2026]:
        for ix in range(12):
            rows.append(
                {
                    "date": f"{year}-01-{(ix % 28) + 1:02d}",
                    "home_team": teams[ix % 3],
                    "away_team": teams[(ix + 1) % 3],
                    "home_goals": 2 if ix % 3 == 0 else 1,
                    "away_goals": 1,
                    "neutral": True,
                    "competition": "Friendly",
                }
            )
    result = calibrate_strength_temperature_and_regularization(
        pd.DataFrame(rows),
        CalibrationConfig(
            half_life_grid=(180.0, 365.0),
            regularization_grid=(0.01,),
            gamma_grid=(0.8, 1.0),
            min_matches_per_team=2,
            rolling_backtest=True,
        ),
    )
    combo_scores = result.grid[
        ["half_life_days", "regularization_alpha", "strength_temperature", "rolling_total_nll"]
    ].drop_duplicates()
    assert result.report["selection_metric"] == "rolling_total_test_nll"
    assert result.report["rolling_total_nll"] == combo_scores["rolling_total_nll"].min()
    assert len(result.report["rolling_folds"]) == 3
