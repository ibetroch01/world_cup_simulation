from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .data_sources import validate_historical_matches
from .model_training import TrainingConfig, TrainingResult, fit_attack_defence_model


REQUIRED_CALIBRATION_REPORT_FIELDS = {
    "best_half_life_days",
    "best_regularization_alpha",
    "best_strength_temperature",
    "rolling_total_nll",
    "main_holdout_nll",
    "rolling_folds",
}


@dataclass(frozen=True)
class CalibrationConfig:
    train_start_date: str = "2022-01-01"
    train_end_date: str = "2024-12-31"
    test_start_date: str = "2025-01-01"
    test_end_date: str | None = None
    half_life_grid: tuple[float, ...] = (180.0, 365.0, 500.0, 730.0)
    min_matches_per_team: int = 15
    regularization_grid: tuple[float, ...] = (0.001, 0.01, 0.05, 0.1)
    gamma_grid: tuple[float, ...] = (0.8, 0.9, 1.0)
    rolling_backtest: bool = True


@dataclass(frozen=True)
class RollingFold:
    name: str
    train_start_date: str
    train_end_date: str
    test_start_date: str
    test_end_date: str | None


@dataclass(frozen=True)
class CalibrationResult:
    grid: pd.DataFrame
    report: dict
    best_training_result: TrainingResult


def parse_grid_values(values: tuple[float, ...] | list[float]) -> tuple[float, ...]:
    parsed = tuple(float(value) for value in values)
    if not parsed:
        raise ValueError("Grid must contain at least one value")
    if any(value <= 0 for value in parsed):
        raise ValueError("Grid values must be positive")
    return parsed


def build_gamma_grid(
    start: float = 0.80,
    end: float = 1.40,
    step: float = 0.01,
    checkpoints: tuple[float, ...] = (1.0, 1.1, 1.2),
) -> list[float]:
    if start <= 0 or end < start or step <= 0:
        raise ValueError("Invalid gamma grid bounds")
    values = {round(float(value), 6) for value in np.arange(start, end + step / 2, step)}
    values.update(round(float(value), 6) for value in checkpoints if start <= value <= end)
    return sorted(values)


def build_rolling_folds(matches: pd.DataFrame) -> list[RollingFold]:
    df = validate_historical_matches(matches)
    max_date = pd.to_datetime(df["date"], format="%Y-%m-%d").max().strftime("%Y-%m-%d")
    return [
        RollingFold("test_2024", "2022-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),
        RollingFold("test_2025", "2022-01-01", "2024-12-31", "2025-01-01", "2025-12-31"),
        RollingFold("test_2026", "2022-01-01", "2025-12-31", "2026-01-01", max_date),
    ]


def _poisson_nll(observed: np.ndarray, expected: np.ndarray) -> np.ndarray:
    expected = np.clip(expected, 1e-12, None)
    return expected - observed * np.log(expected) + np.vectorize(math.lgamma)(observed + 1.0)


def _draw_probability(lambda_home: np.ndarray, lambda_away: np.ndarray, max_goals: int = 15) -> np.ndarray:
    probs = np.zeros_like(lambda_home, dtype=float)
    for goals in range(max_goals + 1):
        home_p = np.exp(-lambda_home) * np.power(lambda_home, goals) / math.factorial(goals)
        away_p = np.exp(-lambda_away) * np.power(lambda_away, goals) / math.factorial(goals)
        probs += home_p * away_p
    return probs


def prepare_holdout_matches(
    matches: pd.DataFrame,
    trained_teams: set[str],
    test_start_date: str,
    test_end_date: str | None,
) -> pd.DataFrame:
    df = validate_historical_matches(matches)
    df["date_ts"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    start = pd.Timestamp(test_start_date)
    end = pd.Timestamp(test_end_date) if test_end_date else df["date_ts"].max()
    df = df[(df["date_ts"] >= start) & (df["date_ts"] <= end)].copy()
    before = len(df)
    df = df[df["home_team"].isin(trained_teams) & df["away_team"].isin(trained_teams)].copy()
    if df.empty:
        raise ValueError("No holdout matches remain after excluding teams without trained ratings")
    df.attrs["test_matches_before_missing_rating_exclusion"] = before
    df.attrs["excluded_test_matches_count"] = before - len(df)
    return df.reset_index(drop=True)


def evaluate_holdout_nll(
    ratings: pd.DataFrame,
    training_report: dict,
    holdout_matches: pd.DataFrame,
    strength_temperature: float,
) -> dict:
    if strength_temperature <= 0:
        raise ValueError("strength_temperature must be positive")
    ratings_by_team = ratings.set_index("team")
    home = holdout_matches["home_team"]
    away = holdout_matches["away_team"]
    home_attack = ratings_by_team.loc[home, "attack_score"].to_numpy(dtype=float) ** strength_temperature
    home_defence = ratings_by_team.loc[home, "defence_score"].to_numpy(dtype=float) ** strength_temperature
    away_attack = ratings_by_team.loc[away, "attack_score"].to_numpy(dtype=float) ** strength_temperature
    away_defence = ratings_by_team.loc[away, "defence_score"].to_numpy(dtype=float) ** strength_temperature
    base_rate = float(training_report["base_rate"])
    home_advantage = float(training_report["home_advantage"])
    neutral = holdout_matches["neutral"].to_numpy(dtype=bool)
    lambda_home = base_rate * home_attack * away_defence * np.where(neutral, 1.0, home_advantage)
    lambda_away = base_rate * away_attack * home_defence
    home_goals = holdout_matches["home_goals"].to_numpy(dtype=float)
    away_goals = holdout_matches["away_goals"].to_numpy(dtype=float)
    nll = float(np.sum(_poisson_nll(home_goals, lambda_home) + _poisson_nll(away_goals, lambda_away)))
    observed_goals = home_goals + away_goals
    predicted_draw = _draw_probability(lambda_home, lambda_away)
    return {
        "holdout_nll": nll,
        "observed_goals_per_match": float(np.mean(observed_goals)),
        "predicted_goals_per_match": float(np.mean(lambda_home + lambda_away)),
        "observed_draw_rate": float(np.mean(home_goals == away_goals)),
        "predicted_draw_rate": float(np.mean(predicted_draw)),
    }


def _fit_for_params(
    matches: pd.DataFrame,
    train_start_date: str,
    train_end_date: str,
    half_life_days: float,
    regularization_alpha: float,
    min_matches_per_team: int,
) -> TrainingResult:
    return fit_attack_defence_model(
        matches,
        TrainingConfig(
            start_date=train_start_date,
            end_date=train_end_date,
            half_life_days=float(half_life_days),
            regularization_alpha=float(regularization_alpha),
            min_matches_per_team=min_matches_per_team,
        ),
    )


def _evaluate_grid_for_fold(
    matches: pd.DataFrame,
    fold: RollingFold,
    config: CalibrationConfig,
) -> tuple[list[dict], dict[tuple[float, float], TrainingResult]]:
    rows = []
    training_results: dict[tuple[float, float], TrainingResult] = {}
    for half_life in config.half_life_grid:
        for alpha in config.regularization_grid:
            training_result = _fit_for_params(
                matches,
                fold.train_start_date,
                fold.train_end_date,
                half_life,
                alpha,
                config.min_matches_per_team,
            )
            training_results[(float(half_life), float(alpha))] = training_result
            trained_teams = set(training_result.ratings["team"])
            holdout = prepare_holdout_matches(matches, trained_teams, fold.test_start_date, fold.test_end_date)
            for gamma in config.gamma_grid:
                metrics = evaluate_holdout_nll(training_result.ratings, training_result.report, holdout, gamma)
                rows.append(
                    {
                        "fold": fold.name,
                        "train_start_date": fold.train_start_date,
                        "train_end_date": fold.train_end_date,
                        "test_start_date": fold.test_start_date,
                        "test_end_date": fold.test_end_date,
                        "half_life_days": float(half_life),
                        "regularization_alpha": float(alpha),
                        "strength_temperature": float(gamma),
                        **metrics,
                        "train_matches": int(training_result.report["n_matches"]),
                        "trained_teams": int(training_result.report["n_teams_training_universe"]),
                        "test_matches_before_missing_rating_exclusion": int(
                            holdout.attrs["test_matches_before_missing_rating_exclusion"]
                        ),
                        "test_matches": int(len(holdout)),
                        "excluded_test_matches": int(holdout.attrs["excluded_test_matches_count"]),
                    }
                )
    return rows, training_results


def _fold_summary(best_rows: pd.DataFrame) -> list[dict]:
    summaries = []
    for row in best_rows.sort_values("fold").itertuples(index=False):
        summaries.append(
            {
                "fold": row.fold,
                "train_start_date": row.train_start_date,
                "train_end_date": row.train_end_date,
                "test_start_date": row.test_start_date,
                "test_end_date": row.test_end_date,
                "nll": float(row.holdout_nll),
                "test_matches_before_missing_rating_exclusion": int(row.test_matches_before_missing_rating_exclusion),
                "test_matches": int(row.test_matches),
                "excluded_test_matches": int(row.excluded_test_matches),
                "observed_goals_per_match": float(row.observed_goals_per_match),
                "predicted_goals_per_match": float(row.predicted_goals_per_match),
                "observed_draw_rate": float(row.observed_draw_rate),
                "predicted_draw_rate": float(row.predicted_draw_rate),
            }
        )
    return summaries


def calibrate_strength_temperature_and_regularization(
    matches: pd.DataFrame,
    config: CalibrationConfig,
) -> CalibrationResult:
    config = CalibrationConfig(
        train_start_date=config.train_start_date,
        train_end_date=config.train_end_date,
        test_start_date=config.test_start_date,
        test_end_date=config.test_end_date,
        half_life_grid=parse_grid_values(config.half_life_grid),
        min_matches_per_team=config.min_matches_per_team,
        regularization_grid=parse_grid_values(config.regularization_grid),
        gamma_grid=parse_grid_values(config.gamma_grid),
        rolling_backtest=config.rolling_backtest,
    )
    folds = (
        build_rolling_folds(matches)
        if config.rolling_backtest
        else [
            RollingFold(
                "main_holdout",
                config.train_start_date,
                config.train_end_date,
                config.test_start_date,
                config.test_end_date,
            )
        ]
    )
    grid_rows = []
    for fold in folds:
        rows, _training_results = _evaluate_grid_for_fold(matches, fold, config)
        grid_rows.extend(rows)
    fold_grid = pd.DataFrame(grid_rows)
    grouped = (
        fold_grid.groupby(["half_life_days", "regularization_alpha", "strength_temperature"], as_index=False)
        .agg(
            rolling_total_nll=("holdout_nll", "sum"),
            mean_predicted_goals_per_match=("predicted_goals_per_match", "mean"),
            mean_predicted_draw_rate=("predicted_draw_rate", "mean"),
            total_test_matches=("test_matches", "sum"),
            total_excluded_test_matches=("excluded_test_matches", "sum"),
        )
        .sort_values(["rolling_total_nll", "half_life_days", "regularization_alpha", "strength_temperature"])
        .reset_index(drop=True)
    )
    best = grouped.iloc[0]
    best_half_life = float(best["half_life_days"])
    best_alpha = float(best["regularization_alpha"])
    best_gamma = float(best["strength_temperature"])

    main_training_result = _fit_for_params(
        matches,
        config.train_start_date,
        config.train_end_date,
        best_half_life,
        best_alpha,
        config.min_matches_per_team,
    )
    main_trained_teams = set(main_training_result.ratings["team"])
    main_holdout = prepare_holdout_matches(matches, main_trained_teams, config.test_start_date, config.test_end_date)
    main_metrics = evaluate_holdout_nll(main_training_result.ratings, main_training_result.report, main_holdout, best_gamma)
    best_rows = fold_grid[
        fold_grid["half_life_days"].eq(best_half_life)
        & fold_grid["regularization_alpha"].eq(best_alpha)
        & fold_grid["strength_temperature"].eq(best_gamma)
    ]
    report = {
        "selection_metric": "rolling_total_test_nll" if config.rolling_backtest else "main_holdout_test_nll",
        "best_half_life_days": best_half_life,
        "best_regularization_alpha": best_alpha,
        "best_strength_temperature": best_gamma,
        "rolling_total_nll": float(best["rolling_total_nll"]),
        "main_holdout_nll": float(main_metrics["holdout_nll"]),
        "main_holdout": {
            "train_start_date": config.train_start_date,
            "train_end_date": config.train_end_date,
            "test_start_date": config.test_start_date,
            "test_end_date": main_holdout["date_ts"].max().strftime("%Y-%m-%d"),
            "test_matches_before_missing_rating_exclusion": int(
                main_holdout.attrs["test_matches_before_missing_rating_exclusion"]
            ),
            "test_matches": int(len(main_holdout)),
            "excluded_test_matches": int(main_holdout.attrs["excluded_test_matches_count"]),
            **main_metrics,
        },
        "rolling_folds": _fold_summary(best_rows),
        "half_life_grid": [float(value) for value in config.half_life_grid],
        "regularization_grid": [float(value) for value in config.regularization_grid],
        "gamma_grid": [float(value) for value in config.gamma_grid],
        "min_matches_per_team": config.min_matches_per_team,
    }
    full_grid = fold_grid.merge(grouped, on=["half_life_days", "regularization_alpha", "strength_temperature"], how="left")
    return CalibrationResult(grid=full_grid, report=report, best_training_result=main_training_result)


def write_calibration_outputs(result: CalibrationResult, report_path: Path, grid_path: Path | None = None) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result.report, indent=2), encoding="utf-8")
    if grid_path is not None:
        grid_path.parent.mkdir(parents=True, exist_ok=True)
        result.grid.to_csv(grid_path, index=False)
