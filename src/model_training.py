from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .data_sources import COMPETITION_WEIGHTS, HISTORICAL_MATCH_COLUMNS, validate_historical_matches


@dataclass(frozen=True)
class TrainingConfig:
    start_date: str = "2022-01-01"
    end_date: str | None = None
    half_life_days: float = 730.0
    regularization_alpha: float = 0.01
    min_matches_per_team: int = 15


@dataclass(frozen=True)
class TrainingResult:
    ratings: pd.DataFrame
    report: dict


def competition_weight(competition: str) -> float:
    lower = str(competition).lower()
    if "friendly" in lower:
        return COMPETITION_WEIGHTS["Friendly"]
    if "qual" in lower or "nations league" in lower:
        return COMPETITION_WEIGHTS["Qualifiers / Nations League"]
    if competition in {
        "World Cup",
        "Euro",
        "Copa America",
        "AFC Asian Cup",
        "Africa Cup of Nations",
        "Gold Cup",
    }:
        return COMPETITION_WEIGHTS["Major Tournament Final Stage"]
    return 1.0


def recency_weight(match_date: pd.Timestamp, end_date: pd.Timestamp, half_life_days: float) -> float:
    if half_life_days <= 0:
        raise ValueError("half_life_days must be positive")
    age_days = max(0, (end_date - match_date).days)
    return float(0.5 ** (age_days / half_life_days))


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


def prepare_training_matches(matches: pd.DataFrame, config: TrainingConfig) -> pd.DataFrame:
    df = validate_historical_matches(matches)
    df["date_ts"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    start = pd.Timestamp(config.start_date)
    end = pd.Timestamp(config.end_date) if config.end_date else df["date_ts"].max()
    df = df[(df["date_ts"] >= start) & (df["date_ts"] <= end)].copy()
    if df.empty:
        raise ValueError("No historical matches remain after applying training date filters")
    if config.min_matches_per_team < 1:
        raise ValueError("min_matches_per_team must be at least 1")
    team_match_counts = pd.concat([df["home_team"], df["away_team"]]).value_counts()
    training_universe = set(team_match_counts[team_match_counts >= config.min_matches_per_team].index)
    df["home_team_in_universe"] = df["home_team"].isin(training_universe)
    df["away_team_in_universe"] = df["away_team"].isin(training_universe)
    before_filter = len(df)
    df = df[df["home_team_in_universe"] & df["away_team_in_universe"]].copy()
    if df.empty:
        raise ValueError(
            "No historical matches remain after filtering to the training universe "
            f"(teams with >= {config.min_matches_per_team} matches)"
        )
    df.attrs["n_matches_before_universe_filter"] = before_filter
    df.attrs["n_matches_removed_by_universe_filter"] = before_filter - len(df)
    df.attrs["n_teams_before_universe_filter"] = int(len(team_match_counts))
    df.attrs["n_teams_training_universe"] = int(len(training_universe))
    df["recency_weight"] = df["date_ts"].map(lambda date: recency_weight(date, end, config.half_life_days))
    df["competition_weight"] = df["competition"].map(competition_weight)
    df["weight"] = df["recency_weight"] * df["competition_weight"]
    return df.reset_index(drop=True)


def fit_attack_defence_model(matches: pd.DataFrame, config: TrainingConfig) -> TrainingResult:
    df = prepare_training_matches(matches, config)
    teams = sorted(set(df["home_team"]) | set(df["away_team"]))
    team_index = {team: ix for ix, team in enumerate(teams)}
    n_teams = len(teams)
    home_idx = df["home_team"].map(team_index).to_numpy(dtype=int)
    away_idx = df["away_team"].map(team_index).to_numpy(dtype=int)
    home_goals = df["home_goals"].to_numpy(dtype=float)
    away_goals = df["away_goals"].to_numpy(dtype=float)
    neutral = df["neutral"].to_numpy(dtype=bool)
    weights = df["weight"].to_numpy(dtype=float)
    observed_goals = home_goals + away_goals

    avg_goals_per_team = max(0.05, float(observed_goals.mean() / 2.0))
    initial = np.zeros(2 * n_teams + 2, dtype=float)
    initial[2 * n_teams] = math.log(avg_goals_per_team)
    initial[2 * n_teams + 1] = math.log(1.08)

    def unpack(params: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, float]:
        attack = np.exp(params[:n_teams])
        defence = np.exp(params[n_teams : 2 * n_teams])
        base_rate = float(np.exp(params[2 * n_teams]))
        home_advantage = float(np.exp(params[2 * n_teams + 1]))
        return attack, defence, base_rate, home_advantage

    def objective(params: np.ndarray) -> float:
        attack, defence, base_rate, home_advantage = unpack(params)
        lambda_home = base_rate * attack[home_idx] * defence[away_idx] * np.where(neutral, 1.0, home_advantage)
        lambda_away = base_rate * attack[away_idx] * defence[home_idx]
        nll = weights * (_poisson_nll(home_goals, lambda_home) + _poisson_nll(away_goals, lambda_away))
        raw_attack = params[:n_teams]
        raw_defence = params[n_teams : 2 * n_teams]
        penalty = config.regularization_alpha * float(np.sum(raw_attack**2 + raw_defence**2))
        return float(np.sum(nll) + penalty)

    result = minimize(objective, initial, method="L-BFGS-B", options={"maxiter": 1000, "maxfun": 200_000})
    if not result.success:
        raise RuntimeError(f"Attack/Defence optimization failed: {result.message}")

    attack, defence, base_rate, home_advantage = unpack(result.x)
    attack_mean = float(attack.mean())
    defence_mean = float(defence.mean())
    attack = attack / attack_mean
    defence = defence / defence_mean
    base_rate = base_rate * attack_mean * defence_mean

    matches_used = pd.concat([df["home_team"], df["away_team"]]).value_counts()
    ratings = pd.DataFrame(
        {
            "team": teams,
            "attack_score": attack,
            "defence_score": defence,
            "overall_score": attack / defence,
            "matches_used": [int(matches_used.get(team, 0)) for team in teams],
        }
    ).sort_values("overall_score", ascending=False)

    lambda_home = base_rate * attack[home_idx] * defence[away_idx] * np.where(neutral, 1.0, home_advantage)
    lambda_away = base_rate * attack[away_idx] * defence[home_idx]
    predicted_draw = _draw_probability(lambda_home, lambda_away)
    training_end = pd.Timestamp(config.end_date).strftime("%Y-%m-%d") if config.end_date else df["date_ts"].max().strftime("%Y-%m-%d")
    report = {
        "training_start_date": config.start_date,
        "training_end_date": training_end,
        "half_life_days": config.half_life_days,
        "regularization_alpha": config.regularization_alpha,
        "min_matches_per_team": config.min_matches_per_team,
        "n_matches": int(len(df)),
        "n_matches_before_universe_filter": int(df.attrs.get("n_matches_before_universe_filter", len(df))),
        "n_matches_removed_by_universe_filter": int(df.attrs.get("n_matches_removed_by_universe_filter", 0)),
        "n_teams_before_universe_filter": int(df.attrs.get("n_teams_before_universe_filter", len(teams))),
        "n_teams_training_universe": int(df.attrs.get("n_teams_training_universe", len(teams))),
        "base_rate": float(base_rate),
        "home_advantage": float(home_advantage),
        "final_nll": float(result.fun),
        "observed_goals_per_match": float(observed_goals.mean()),
        "predicted_goals_per_match": float(np.mean(lambda_home + lambda_away)),
        "observed_draw_rate": float(np.mean(home_goals == away_goals)),
        "predicted_draw_rate": float(np.mean(predicted_draw)),
    }
    return TrainingResult(ratings=ratings.reset_index(drop=True), report=report)


def train_from_csv(matches_path: Path, output_ratings: Path, output_report: Path, config: TrainingConfig) -> TrainingResult:
    matches = pd.read_csv(matches_path)
    result = fit_attack_defence_model(matches, config)
    output_ratings.parent.mkdir(parents=True, exist_ok=True)
    output_report.parent.mkdir(parents=True, exist_ok=True)
    result.ratings.to_csv(output_ratings, index=False)
    output_report.write_text(json.dumps(result.report, indent=2), encoding="utf-8")
    return result
