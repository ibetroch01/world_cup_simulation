from __future__ import annotations

import pandas as pd

from src.model_training import TrainingConfig, competition_weight, fit_attack_defence_model, recency_weight


def synthetic_matches() -> pd.DataFrame:
    rows = []
    teams = ["Alpha", "Beta", "Gamma", "Delta"]
    for ix in range(16):
        home = teams[ix % 4]
        away = teams[(ix + 1) % 4]
        rows.append(
            {
                "date": f"2024-01-{ix + 1:02d}",
                "home_team": home,
                "away_team": away,
                "home_goals": 2 if home == "Alpha" else 1,
                "away_goals": 0 if away == "Beta" else 1,
                "neutral": True,
                "competition": "Friendly" if ix % 2 else "World Cup",
            }
        )
    return pd.DataFrame(rows)


def test_training_outputs_positive_normalized_ratings():
    result = fit_attack_defence_model(
        synthetic_matches(),
        TrainingConfig(start_date="2024-01-01", end_date="2024-02-01", regularization_alpha=0.5, min_matches_per_team=1),
    )
    assert (result.ratings["attack_score"] > 0).all()
    assert (result.ratings["defence_score"] > 0).all()
    assert abs(result.ratings["attack_score"].mean() - 1.0) < 1e-8
    assert abs(result.ratings["defence_score"].mean() - 1.0) < 1e-8
    assert result.report["n_matches"] == 16


def test_training_universe_filters_low_match_teams():
    rows = []
    for ix in range(12):
        rows.append(
            {
                "date": f"2024-01-{ix + 1:02d}",
                "home_team": "Alpha" if ix % 2 == 0 else "Beta",
                "away_team": "Beta" if ix % 2 == 0 else "Gamma",
                "home_goals": 1,
                "away_goals": 1,
                "neutral": True,
                "competition": "Friendly",
            }
        )
    rows.append(
        {
            "date": "2024-01-20",
            "home_team": "Delta",
            "away_team": "Alpha",
            "home_goals": 0,
            "away_goals": 2,
            "neutral": True,
            "competition": "Friendly",
        }
    )
    df = pd.DataFrame(rows)
    result = fit_attack_defence_model(
        df,
        TrainingConfig(start_date="2024-01-01", end_date="2024-02-01", regularization_alpha=0.5, min_matches_per_team=5),
    )
    assert result.report["min_matches_per_team"] == 5
    assert result.report["n_teams_training_universe"] < result.report["n_teams_before_universe_filter"]
    assert "Delta" not in set(result.ratings["team"])
    assert (result.ratings["matches_used"] >= 5).all()


def test_recency_and_competition_weights():
    recent = pd.Timestamp("2024-01-31")
    old = pd.Timestamp("2023-01-31")
    end = pd.Timestamp("2024-01-31")
    assert recency_weight(recent, end, 730) > recency_weight(old, end, 730)
    assert competition_weight("World Cup") > competition_weight("Friendly")
