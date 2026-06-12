from __future__ import annotations

import json

import pandas as pd
import pytest

from app import build_group_display, build_knockout_display, live_prediction_note, render_group_table, render_knockout_table
from src.results_loader import load_simulation_output


def test_results_loader_rejects_bad_probability(tmp_path):
    output = tmp_path / "bad"
    output.mkdir()
    (output / "metadata.json").write_text(json.dumps({"model": "attack_defence", "runs": 1, "seed": 1, "parameters": {}}))
    pd.DataFrame(
        [
            {
                "team": "A",
                "group": "A",
                "p_place_1": 1.2,
                "p_place_2": 0,
                "p_place_3": 0,
                "p_place_4": 0,
                "p_advance_group": 1,
                "p_advance_best_third": 0,
                "p_eliminated_group": 0,
            }
        ]
    ).to_csv(output / "group_phase_results.csv", index=False)
    pd.DataFrame(
        [{"team": "A", "p_r32": 1, "p_r16": 1, "p_qf": 1, "p_sf": 1, "p_final": 1, "p_champion": 1}]
    ).to_csv(output / "knockout_phase_results.csv", index=False)
    with pytest.raises(ValueError, match="invalid probabilities"):
        load_simulation_output(output)


def test_group_display_computes_r32_probability():
    group = pd.DataFrame(
        [
            {
                "team": "Spain",
                "p_place_1": 0.4,
                "p_place_2": 0.2,
                "p_place_3": 0.2,
                "p_place_4": 0.2,
                "p_advance_group": 0.6,
                "p_advance_best_third": 0.1,
                "p_eliminated_group": 0.3,
            }
        ]
    )
    display = build_group_display(group, {"Spain": "ESP"})
    assert abs(display.loc[0, "p_r32"] - 0.7) < 1e-12


def test_group_table_uses_plain_probabilities_without_heat_cells():
    group = pd.DataFrame(
        [
            {
                "team": "🇪🇸 Spain",
                "p_place_1": 0.4,
                "p_place_2": 0.2,
                "p_place_3": 0.2,
                "p_place_4": 0.2,
                "p_r32": 0.7,
                "p_eliminated_group": 0.3,
            }
        ]
    )
    html = render_group_table("H", group)
    assert "heat-cell" not in html
    assert "plain-probability" in html


def test_knockout_display_merges_ratings_when_present():
    knockout = pd.DataFrame(
        [{"team": "Spain", "p_r32": 1, "p_r16": 0.8, "p_qf": 0.5, "p_sf": 0.3, "p_final": 0.2, "p_champion": 0.1}]
    )
    ratings = pd.DataFrame([{"team": "Spain", "attack_score": 2.0, "defence_score": 0.5}])
    teams = pd.DataFrame([{"team_id": "ESP", "team_name": "Spain", "group": "H"}])
    display, has_ratings = build_knockout_display(knockout, ratings, {"Spain": "ESP"}, teams, {"ESP": 1975})
    assert has_ratings
    assert "attack_score" in display.columns
    assert "defence_score" in display.columns
    assert "group" in display.columns
    assert "elo" in display.columns
    assert display.loc[0, "group"] == "H"
    assert display.loc[0, "elo"] == 1975


def test_knockout_display_works_without_ratings():
    knockout = pd.DataFrame(
        [{"team": "Spain", "p_r32": 1, "p_r16": 0.8, "p_qf": 0.5, "p_sf": 0.3, "p_final": 0.2, "p_champion": 0.1}]
    )
    display, has_ratings = build_knockout_display(knockout, None, {"Spain": "ESP"})
    assert not has_ratings
    assert "attack_score" not in display.columns


def test_live_prediction_note_uses_latest_match_label_or_date():
    assert (
        live_prediction_note(
            {
                "locked_matches_count": 2,
                "latest_locked_match_label": "South Korea 2-1 Czechia",
                "latest_locked_match_at": "2026-06-11",
            }
        )
        == "Live prediction: 2 locked matches. Latest update: South Korea 2-1 Czechia, 2026-06-11."
    )
    assert (
        live_prediction_note({"locked_matches_count": 2, "latest_locked_match_at": "2026-06-11"})
        == "Live prediction: 2 locked matches. Latest update: 2026-06-11."
    )


def test_knockout_table_display_has_user_friendly_columns():
    display = pd.DataFrame(
        [
            {
                "team": "🇪🇸 Spain",
                "group": "H",
                "elo": 1975,
                "attack_score": 2.0,
                "defence_score": 0.5,
                "p_r32": 1,
                "p_r16": 0.8,
                "p_qf": 0.5,
                "p_sf": 0.3,
                "p_final": 0.2,
                "p_champion": 0.1,
            }
        ]
    )
    html = render_knockout_table(display, True)
    assert "Team Rating" in html
    assert "Chances To Reach Knockout Stage" in html
    assert "Round of 32" in html
    assert "Champion" in html
