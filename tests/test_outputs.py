from __future__ import annotations

import json

import pandas as pd

from src.results_loader import load_simulation_output


def write_output_folder(path):
    path.mkdir()
    (path / "metadata.json").write_text(json.dumps({"model": "attack_defence", "runs": 2, "seed": 1, "parameters": {}}))
    pd.DataFrame(
        [
            {
                "team": "A",
                "group": "A",
                "p_place_1": 0.25,
                "p_place_2": 0.25,
                "p_place_3": 0.25,
                "p_place_4": 0.25,
                "p_advance_group": 0.5,
                "p_advance_best_third": 0.25,
                "p_eliminated_group": 0.25,
            }
        ]
    ).to_csv(path / "group_phase_results.csv", index=False)
    pd.DataFrame(
        [{"team": "A", "p_r32": 0.75, "p_r16": 0.5, "p_qf": 0.25, "p_sf": 0.1, "p_final": 0.05, "p_champion": 0.02}]
    ).to_csv(path / "knockout_phase_results.csv", index=False)


def test_dashboard_loader_reads_required_outputs(tmp_path):
    output = tmp_path / "run"
    write_output_folder(output)
    loaded = load_simulation_output(output)
    assert loaded.metadata["model"] == "attack_defence"
    assert loaded.team_ratings is None


def test_dashboard_loader_fails_clearly_if_files_missing(tmp_path):
    output = tmp_path / "run"
    output.mkdir()
    try:
        load_simulation_output(output)
    except FileNotFoundError as exc:
        assert "missing files" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")


def test_dashboard_loader_reads_optional_team_ratings(tmp_path):
    output = tmp_path / "run"
    write_output_folder(output)
    pd.DataFrame(
        [
            {
                "team": "A",
                "team_id": "AAA",
                "group": "A",
                "attack_score": 1.1,
                "defence_score": 0.9,
                "overall_score": 1.22,
                "matches_used": 20,
                "rating_source": "trained",
            }
        ]
    ).to_csv(
        output / "team_ratings.csv",
        index=False,
    )
    loaded = load_simulation_output(output)
    assert loaded.team_ratings is not None
    assert "attack_score" in loaded.team_ratings.columns
