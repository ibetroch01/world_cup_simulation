from __future__ import annotations

import pandas as pd

from src.data_loader import load_teams
from src.flags import missing_flag_team_ids, team_label


def test_all_default_teams_have_flag_mapping():
    teams = load_teams()

    assert missing_flag_team_ids(teams) == []


def test_team_label_preserves_name_and_adds_flag_when_available():
    assert team_label("BRA", "Brazil") == "🇧🇷 Brazil"
    assert team_label("XXX", "Example FC") == "Example FC"


def test_missing_flag_team_ids_reports_unknown_teams():
    teams = pd.DataFrame([{"team_id": "BRA"}, {"team_id": "XXX"}])

    assert missing_flag_team_ids(teams) == ["XXX"]
