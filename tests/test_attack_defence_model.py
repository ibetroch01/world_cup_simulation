from __future__ import annotations

import logging

from src.attack_defence_model import AttackDefenceModel, AttackDefenceRating


def test_stronger_attack_increases_lambda():
    model = AttackDefenceModel(
        ratings={
            "A": AttackDefenceRating(attack_score=1.5, defence_score=1.0, overall_score=1.5, matches_used=10),
            "B": AttackDefenceRating(attack_score=1.0, defence_score=1.0, overall_score=1.0, matches_used=10),
        },
        base_rate=1.2,
    )
    lambda_a, lambda_b = model.expected_goals("A", "B")
    assert lambda_a > lambda_b


def test_stronger_defence_decreases_opponent_lambda():
    weak = AttackDefenceModel(
        ratings={
            "A": AttackDefenceRating(attack_score=1.0, defence_score=1.0, overall_score=1.0, matches_used=10),
            "B": AttackDefenceRating(attack_score=1.0, defence_score=1.5, overall_score=0.67, matches_used=10),
        },
        base_rate=1.0,
    )
    strong = AttackDefenceModel(
        ratings={
            "A": AttackDefenceRating(attack_score=1.0, defence_score=1.0, overall_score=1.0, matches_used=10),
            "B": AttackDefenceRating(attack_score=1.0, defence_score=0.7, overall_score=1.43, matches_used=10),
        },
        base_rate=1.0,
    )
    lambda_vs_weak, _ = weak.expected_goals("A", "B")
    lambda_vs_strong, _ = strong.expected_goals("A", "B")
    assert lambda_vs_strong < lambda_vs_weak


def test_missing_rating_fallback_warns(caplog):
    model = AttackDefenceModel(ratings={}, base_rate=1.0)
    with caplog.at_level(logging.WARNING):
        assert model.expected_goals("Missing A", "Missing B") == (1.0, 1.0)
    assert "Missing Attack/Defence rating" in caplog.text


def test_strength_temperature_sharpens_rating_differences():
    ratings = {
        "A": AttackDefenceRating(attack_score=2.0, defence_score=0.5, overall_score=4.0, matches_used=10),
        "B": AttackDefenceRating(attack_score=1.0, defence_score=1.0, overall_score=1.0, matches_used=10),
    }
    base = AttackDefenceModel(ratings=ratings, base_rate=1.0, strength_temperature=1.0)
    sharper = AttackDefenceModel(ratings=ratings, base_rate=1.0, strength_temperature=1.2)

    base_a, base_b = base.expected_goals("A", "B")
    sharp_a, sharp_b = sharper.expected_goals("A", "B")

    assert sharp_a > base_a
    assert sharp_b < base_b
