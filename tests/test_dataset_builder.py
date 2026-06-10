from __future__ import annotations

import pandas as pd
import pytest

from src.data_sources import HistoricalSourceConfig, build_historical_matches_dataset, validate_historical_matches


def test_historical_matches_validation_rejects_duplicates():
    df = pd.DataFrame(
        [
            {
                "date": "2024-01-01",
                "home_team": "A",
                "away_team": "B",
                "home_goals": 1,
                "away_goals": 0,
                "neutral": True,
                "competition": "Friendly",
            },
            {
                "date": "2024-01-01",
                "home_team": "A",
                "away_team": "B",
                "home_goals": 1,
                "away_goals": 0,
                "neutral": True,
                "competition": "Friendly",
            },
        ]
    )
    with pytest.raises(ValueError, match="duplicate"):
        validate_historical_matches(df)


def test_historical_matches_validation_rejects_negative_goals():
    df = pd.DataFrame(
        [
            {
                "date": "2024-01-01",
                "home_team": "A",
                "away_team": "B",
                "home_goals": -1,
                "away_goals": 0,
                "neutral": True,
                "competition": "Friendly",
            }
        ]
    )
    with pytest.raises(ValueError, match="negative"):
        validate_historical_matches(df)


def test_builder_fails_when_no_valid_source_data():
    source = pd.DataFrame(
        columns=["date", "home_team", "away_team", "home_score", "away_score", "tournament", "neutral"]
    )
    shootouts = pd.DataFrame(columns=["date", "home_team", "away_team", "winner"])
    with pytest.raises(ValueError, match="No valid historical matches"):
        build_historical_matches_dataset(
            HistoricalSourceConfig(start_date="2022-01-01"),
            source_results=source,
            source_shootouts=shootouts,
        )

