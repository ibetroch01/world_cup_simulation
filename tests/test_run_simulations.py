from __future__ import annotations

import json
import subprocess
import sys

import pandas as pd

from src.config import SimulationConfig
from src.data_loader import load_all_data
from src.simulation import run_standard_simulations


def test_standard_simulation_outputs_are_valid():
    teams, elos, slots, mapping = load_all_data()
    def goal_model(_team_a: str, _team_b: str) -> tuple[float, float]:
        return 1.2, 1.2

    group_df, knockout_df, diagnostics = run_standard_simulations(
        3,
        teams,
        elos,
        slots,
        mapping,
        SimulationConfig(random_seed=7),
        goal_model,
    )
    place_cols = ["p_place_1", "p_place_2", "p_place_3", "p_place_4"]
    for _, row in group_df.iterrows():
        assert abs(sum(row[col] for col in place_cols) - 1.0) < 1e-12
    for _, row in knockout_df.iterrows():
        probs = [row[col] for col in ["p_r32", "p_r16", "p_qf", "p_sf", "p_final", "p_champion"]]
        assert all(0 <= value <= 1 for value in probs)
        assert probs == sorted(probs, reverse=True)
    assert diagnostics["avg_goals_per_match"] >= 0


def test_run_simulations_cli_writes_attack_defence_team_ratings_with_fallback(tmp_path):
    ratings_file = tmp_path / "ratings.csv"
    report_file = tmp_path / "report.json"
    output_dir = tmp_path / "ad_run"
    pd.DataFrame(
        [
            {
                "team": "Mexico",
                "attack_score": 1.2,
                "defence_score": 0.9,
                "overall_score": 1.333,
                "matches_used": 20,
            }
        ]
    ).to_csv(ratings_file, index=False)
    report_file.write_text(json.dumps({"base_rate": 1.3}))
    subprocess.run(
        [
            sys.executable,
            "scripts/run_simulations.py",
            "--runs",
            "1",
            "--seed",
            "1",
            "--ratings-file",
            str(ratings_file),
            "--training-report",
            str(report_file),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
    )
    ratings = pd.read_csv(output_dir / "team_ratings.csv")
    metadata = json.loads((output_dir / "metadata.json").read_text())
    assert metadata["model"] == "attack_defence"
    assert {"team", "team_id", "group", "attack_score", "defence_score", "overall_score", "matches_used", "rating_source"} <= set(ratings.columns)
    assert not (output_dir / "most_likely_scenario.json").exists()
    assert metadata["parameters"]["penalty_damping"] == 900.0
    assert metadata["parameters"]["strength_temperature"] == 0.8
    mexico = ratings[ratings["team"].eq("Mexico")].iloc[0]
    fallback = ratings[~ratings["team"].eq("Mexico")].iloc[0]
    assert mexico["rating_source"] == "trained"
    assert fallback["rating_source"] == "fallback"
    assert fallback["attack_score"] == 1.0


def test_run_simulations_cli_writes_live_metadata(tmp_path):
    ratings_file = tmp_path / "ratings.csv"
    report_file = tmp_path / "report.json"
    locked_file = tmp_path / "locked_matches.csv"
    output_dir = tmp_path / "live_run"
    pd.DataFrame(
        [
            {
                "team": "Mexico",
                "attack_score": 1.2,
                "defence_score": 0.9,
                "overall_score": 1.333,
                "matches_used": 20,
            }
        ]
    ).to_csv(ratings_file, index=False)
    report_file.write_text(json.dumps({"base_rate": 1.3}))
    pd.DataFrame(
        columns=["phase", "match_id", "group", "team_a", "team_b", "goals_a", "goals_b", "winner_team", "played_at"]
    ).to_csv(locked_file, index=False)
    subprocess.run(
        [
            sys.executable,
            "scripts/run_simulations.py",
            "--runs",
            "1",
            "--seed",
            "1",
            "--ratings-file",
            str(ratings_file),
            "--training-report",
            str(report_file),
            "--locked-matches",
            str(locked_file),
            "--live-early-prediction",
            "--output-dir",
            str(output_dir),
        ],
        check=True,
    )
    metadata = json.loads((output_dir / "metadata.json").read_text())
    assert metadata["live_early_prediction"] is True
    assert metadata["locked_matches_file"] == str(locked_file)
    assert metadata["locked_matches_count"] == 0
    assert metadata["latest_locked_match_at"] is None
