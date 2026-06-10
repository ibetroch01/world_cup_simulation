from src.data_loader import load_r32_slots


def test_r32_slots_have_official_match_count():
    slots = load_r32_slots()
    assert len(slots) == 16
    assert set(slots["match_id"]) == {f"M{i}" for i in range(73, 89)}

