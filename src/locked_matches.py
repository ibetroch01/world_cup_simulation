from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .bracket import FINAL_LINKS, QUARTERFINAL_LINKS, ROUND_OF_16_LINKS, SEMIFINAL_LINKS


LOCKED_MATCH_COLUMNS = {
    "phase",
    "match_id",
    "group",
    "team_a",
    "team_b",
    "goals_a",
    "goals_b",
    "winner_team",
    "played_at",
}


@dataclass(frozen=True)
class LockedMatch:
    phase: str
    match_id: str
    group: str
    team_a: str
    team_b: str
    goals_a: int
    goals_b: int
    winner_team: str
    played_at: str

    @property
    def score_winner(self) -> str | None:
        if self.goals_a > self.goals_b:
            return self.team_a
        if self.goals_b > self.goals_a:
            return self.team_b
        return None

    @property
    def winner(self) -> str | None:
        return self.score_winner or (self.winner_team if self.winner_team else None)


@dataclass(frozen=True)
class LockedMatchIndex:
    group_matches: dict[tuple[str, frozenset[str]], LockedMatch]
    knockout_matches: dict[str, LockedMatch]
    latest_played_at: str | None
    latest_match: LockedMatch | None

    @property
    def count(self) -> int:
        return len(self.group_matches) + len(self.knockout_matches)

    def group_match(self, group: str, team_a: str, team_b: str) -> LockedMatch | None:
        return self.group_matches.get((group, frozenset((team_a, team_b))))

    def knockout_match(self, match_id: str) -> LockedMatch | None:
        return self.knockout_matches.get(match_id)


def empty_locked_match_index() -> LockedMatchIndex:
    return LockedMatchIndex(group_matches={}, knockout_matches={}, latest_played_at=None, latest_match=None)


def valid_knockout_match_ids() -> set[str]:
    ids = {f"M{match_id}" for match_id in range(73, 89)}
    ids.update(ROUND_OF_16_LINKS)
    ids.update(QUARTERFINAL_LINKS)
    ids.update(SEMIFINAL_LINKS)
    ids.update(FINAL_LINKS)
    return ids


def load_locked_matches(path: Path, teams: pd.DataFrame) -> LockedMatchIndex:
    if not path.exists():
        raise FileNotFoundError(f"Locked matches file is missing: {path}")
    raw = pd.read_csv(path, dtype=str).fillna("")
    return validate_locked_matches(raw, teams)


def validate_locked_matches(raw: pd.DataFrame, teams: pd.DataFrame) -> LockedMatchIndex:
    missing = LOCKED_MATCH_COLUMNS - set(raw.columns)
    if missing:
        raise ValueError(f"locked_matches.csv is missing required columns: {sorted(missing)}")
    if raw.empty:
        return empty_locked_match_index()

    team_ids = set(teams["team_id"].astype(str))
    team_groups = dict(zip(teams["team_id"].astype(str), teams["group"].astype(str)))
    groups = set(teams["group"].astype(str))
    knockout_ids = valid_knockout_match_ids()
    group_matches: dict[tuple[str, frozenset[str]], LockedMatch] = {}
    knockout_matches: dict[str, LockedMatch] = {}
    latest_played_at: str | None = None
    latest_match: LockedMatch | None = None

    for row_number, row in enumerate(raw.itertuples(index=False), start=2):
        values = {column: str(getattr(row, column)).strip() for column in LOCKED_MATCH_COLUMNS}
        phase = values["phase"].lower()
        if phase not in {"group", "knockout"}:
            raise ValueError(f"locked_matches.csv row {row_number}: phase must be 'group' or 'knockout'")
        team_a = values["team_a"]
        team_b = values["team_b"]
        if team_a not in team_ids or team_b not in team_ids:
            raise ValueError(f"locked_matches.csv row {row_number}: team_a/team_b must be valid team_id values")
        if team_a == team_b:
            raise ValueError(f"locked_matches.csv row {row_number}: team_a and team_b must differ")
        try:
            goals_a = int(values["goals_a"])
            goals_b = int(values["goals_b"])
        except ValueError as exc:
            raise ValueError(f"locked_matches.csv row {row_number}: goals_a/goals_b must be integers") from exc
        if goals_a < 0 or goals_b < 0:
            raise ValueError(f"locked_matches.csv row {row_number}: goals must be non-negative")

        winner_team = values["winner_team"]
        if winner_team and winner_team not in {team_a, team_b}:
            raise ValueError(f"locked_matches.csv row {row_number}: winner_team must be team_a or team_b")

        match = LockedMatch(
            phase=phase,
            match_id=values["match_id"],
            group=values["group"],
            team_a=team_a,
            team_b=team_b,
            goals_a=goals_a,
            goals_b=goals_b,
            winner_team=winner_team,
            played_at=values["played_at"],
        )
        if phase == "group":
            if match.match_id:
                raise ValueError(f"locked_matches.csv row {row_number}: group matches must leave match_id empty")
            if match.group not in groups:
                raise ValueError(f"locked_matches.csv row {row_number}: group is required for group matches")
            if team_groups[team_a] != match.group or team_groups[team_b] != match.group:
                raise ValueError(f"locked_matches.csv row {row_number}: group match teams must belong to the listed group")
            if winner_team:
                raise ValueError(f"locked_matches.csv row {row_number}: group matches must leave winner_team empty")
            key = (match.group, frozenset((team_a, team_b)))
            if key in group_matches:
                raise ValueError(f"locked_matches.csv row {row_number}: duplicate locked group match")
            group_matches[key] = match
        else:
            if match.group:
                raise ValueError(f"locked_matches.csv row {row_number}: knockout matches must leave group empty")
            if match.match_id not in knockout_ids:
                raise ValueError(f"locked_matches.csv row {row_number}: match_id must be a valid knockout match ID")
            if match.goals_a == match.goals_b and not winner_team:
                raise ValueError(f"locked_matches.csv row {row_number}: knockout draws require winner_team")
            score_winner = match.score_winner
            if score_winner and winner_team and winner_team != score_winner:
                raise ValueError(f"locked_matches.csv row {row_number}: winner_team conflicts with the 90-minute score")
            if match.match_id in knockout_matches:
                raise ValueError(f"locked_matches.csv row {row_number}: duplicate locked knockout match")
            knockout_matches[match.match_id] = match

        if match.played_at and (latest_played_at is None or match.played_at >= latest_played_at):
            latest_played_at = match.played_at
            latest_match = match

    return LockedMatchIndex(
        group_matches=group_matches,
        knockout_matches=knockout_matches,
        latest_played_at=latest_played_at,
        latest_match=latest_match,
    )
