import math

import pytest

from src.bracket import THIRD_PLACE_MATCHES, get_third_place_assignments, validate_third_place_mapping
from src.data_loader import load_third_place_mapping


def test_missing_annex_c_mapping_raises_clear_error():
    mapping = load_third_place_mapping()
    broken = mapping[mapping["qualified_third_groups"] != "A-B-C-D-E-F-G-H"]
    with pytest.raises(ValueError, match="495 valid"):
        validate_third_place_mapping(broken)


def test_annex_c_mapping_has_495_unique_combinations():
    mapping = load_third_place_mapping()
    assert mapping["qualified_third_groups"].nunique() == math.comb(12, 8)


def test_each_mapping_combination_assigns_required_slots():
    mapping = load_third_place_mapping()
    for _, chunk in mapping.groupby("qualified_third_groups"):
        assert set(chunk["match_id"]) == set(THIRD_PLACE_MATCHES)


def test_no_duplicate_third_group_per_combination():
    mapping = load_third_place_mapping()
    for key, chunk in mapping.groupby("qualified_third_groups"):
        assert not chunk["third_group"].duplicated().any(), key


def test_assigned_third_group_belongs_to_qualifying_key():
    mapping = load_third_place_mapping()
    for key, chunk in mapping.groupby("qualified_third_groups"):
        qualified = set(key.split("-"))
        assert set(chunk["third_group"]) <= qualified


def test_lookup_missing_specific_annex_key_raises_clear_error():
    mapping = load_third_place_mapping()
    broken = mapping[mapping["qualified_third_groups"] != "A-B-C-D-E-F-G-H"]
    with pytest.raises(ValueError, match="Missing Annex C mapping"):
        get_third_place_assignments(broken, list("ABCDEFGH"))


def test_known_annex_c_rows_match_source_table():
    mapping = load_third_place_mapping()
    first = get_third_place_assignments(mapping, list("EFGHIJKL"))
    assert first == {
        "M74": "F",
        "M77": "G",
        "M79": "E",
        "M80": "K",
        "M81": "I",
        "M82": "H",
        "M85": "J",
        "M87": "L",
    }
    last = get_third_place_assignments(mapping, list("ABCDEFGH"))
    assert last == {
        "M74": "C",
        "M77": "F",
        "M79": "H",
        "M80": "E",
        "M81": "B",
        "M82": "A",
        "M85": "G",
        "M87": "D",
    }
