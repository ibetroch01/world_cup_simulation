from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import pandas as pd

from .config import GROUPS, THIRD_PLACE_MATCHES


THIRD_SLOT_MATCH_TO_WINNER = {
    "M79": "1A",
    "M85": "1B",
    "M81": "1D",
    "M74": "1E",
    "M82": "1G",
    "M77": "1I",
    "M87": "1K",
    "M80": "1L",
}

THIRD_SLOT_ORDER_BY_ANNEX_TABLE = ("M79", "M85", "M81", "M74", "M82", "M77", "M87", "M80")

THIRD_SLOT_ELIGIBLE_GROUPS = {
    "M74": set("ABCDF"),
    "M77": set("CDFGH"),
    "M79": set("CEFHI"),
    "M80": set("EHIJK"),
    "M81": set("BEFIJ"),
    "M82": set("AEHIJ"),
    "M85": set("EFGIJ"),
    "M87": set("DEIJL"),
}

ROUND_OF_16_LINKS = {
    "M89": ("M74", "M77"),
    "M90": ("M73", "M75"),
    "M91": ("M76", "M78"),
    "M92": ("M79", "M80"),
    "M93": ("M83", "M84"),
    "M94": ("M81", "M82"),
    "M95": ("M86", "M88"),
    "M96": ("M85", "M87"),
}
QUARTERFINAL_LINKS = {
    "M97": ("M89", "M90"),
    "M98": ("M93", "M94"),
    "M99": ("M91", "M92"),
    "M100": ("M95", "M96"),
}
SEMIFINAL_LINKS = {"M101": ("M97", "M98"), "M102": ("M99", "M100")}
FINAL_LINKS = {"M103": ("L101", "L102"), "M104": ("M101", "M102")}


@dataclass(frozen=True)
class R32Slot:
    match_id: str
    slot_a: str
    slot_b: str


def third_groups_key(groups: list[str] | tuple[str, ...] | set[str]) -> str:
    return "-".join(sorted(groups))


def validate_third_place_mapping(mapping: pd.DataFrame) -> None:
    required = {"qualified_third_groups", "match_id", "third_group"}
    missing = required - set(mapping.columns)
    if missing:
        raise ValueError(f"Annex C mapping is missing required columns: {sorted(missing)}")

    unique_keys = set(mapping["qualified_third_groups"])
    expected_keys = {"-".join(combo) for combo in combinations(GROUPS, 8)}
    if unique_keys != expected_keys:
        missing_keys = sorted(expected_keys - unique_keys)[:5]
        extra_keys = sorted(unique_keys - expected_keys)[:5]
        raise ValueError(
            "Annex C mapping must contain exactly 495 valid qualified_third_groups combinations. "
            f"Found {len(unique_keys)}. Missing examples: {missing_keys}. Extra examples: {extra_keys}."
        )

    for key, chunk in mapping.groupby("qualified_third_groups"):
        if set(chunk["match_id"]) != set(THIRD_PLACE_MATCHES):
            raise ValueError(f"Annex C mapping for {key} does not assign all required third-place slots")
        if chunk["match_id"].duplicated().any():
            raise ValueError(f"Annex C mapping for {key} assigns the same match slot more than once")
        if chunk["third_group"].duplicated().any():
            raise ValueError(f"Annex C mapping for {key} assigns a third-placed group twice")
        qualified = set(key.split("-"))
        assigned = set(chunk["third_group"])
        if not assigned <= qualified:
            raise ValueError(f"Annex C mapping for {key} assigns a group outside the qualifying key")
        for row in chunk.itertuples(index=False):
            if row.third_group not in THIRD_SLOT_ELIGIBLE_GROUPS[row.match_id]:
                raise ValueError(
                    f"Annex C mapping for {key} assigns group {row.third_group} to ineligible {row.match_id}"
                )


def get_third_place_assignments(mapping: pd.DataFrame, qualified_groups: list[str]) -> dict[str, str]:
    key = third_groups_key(qualified_groups)
    chunk = mapping[mapping["qualified_third_groups"] == key]
    if chunk.empty:
        raise ValueError(f"Missing Annex C mapping for qualifying third-place groups: {key}")
    assignments = dict(zip(chunk["match_id"], chunk["third_group"]))
    missing = set(THIRD_PLACE_MATCHES) - set(assignments)
    if missing:
        raise ValueError(f"Annex C mapping for {key} is incomplete; missing matches {sorted(missing)}")
    if len(set(assignments.values())) != len(assignments):
        raise ValueError(f"Annex C mapping for {key} contains duplicate third-place group assignments")
    if not set(assignments.values()) <= set(qualified_groups):
        raise ValueError(f"Annex C mapping for {key} assigns a group that did not qualify")
    return assignments


def resolve_r32_slots(
    r32_slots: pd.DataFrame,
    group_tables: dict[str, pd.DataFrame],
    best_thirds: pd.DataFrame,
    third_mapping: pd.DataFrame,
) -> list[tuple[str, str, str]]:
    qualified_third_groups = list(best_thirds["group"])
    third_assignments = get_third_place_assignments(third_mapping, qualified_third_groups)
    thirds_by_group = {row.group: row.team_id for row in best_thirds.itertuples(index=False)}

    def resolve(slot: str, match_id: str) -> str:
        if slot.startswith("1") or slot.startswith("2"):
            rank = int(slot[0])
            group = slot[1]
            return str(group_tables[group].iloc[rank - 1]["team_id"])
        if slot.startswith("3"):
            group = third_assignments[match_id]
            return thirds_by_group[group]
        raise ValueError(f"Unsupported bracket slot {slot}")

    matches = []
    for row in r32_slots.sort_values("match_id").itertuples(index=False):
        matches.append((row.match_id, resolve(row.slot_a, row.match_id), resolve(row.slot_b, row.match_id)))
    return matches

