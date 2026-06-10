from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests


MARTJ42_RESULTS_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
MARTJ42_SHOOTOUTS_URL = "https://raw.githubusercontent.com/martj42/international_results/master/shootouts.csv"

HISTORICAL_MATCH_COLUMNS = [
    "date",
    "home_team",
    "away_team",
    "home_goals",
    "away_goals",
    "neutral",
    "competition",
]

COMPETITION_WEIGHTS = {
    "Major Tournament Final Stage": 3.0,
    "Qualifiers / Nations League": 2.0,
    "Friendly": 1.0,
}

COMPETITION_ALIASES = {
    "FIFA World Cup": "World Cup",
    "World Cup": "World Cup",
    "UEFA Euro": "Euro",
    "UEFA European Championship": "Euro",
    "Copa America": "Copa America",
    "Copa América": "Copa America",
    "UEFA Nations League": "Nations League",
    "CONCACAF Nations League": "Nations League",
    "FIFA World Cup qualification": "World Cup Qualifier",
    "FIFA World Cup qualification (CONMEBOL)": "World Cup Qualifier",
    "UEFA Euro qualification": "Euro Qualifier",
    "Copa America qualification": "Copa America Qualifier",
    "AFC Asian Cup qualification": "Asian Cup Qualifier",
    "African Cup of Nations qualification": "AFCON Qualifier",
    "Africa Cup of Nations qualification": "AFCON Qualifier",
    "AFC Asian Cup": "AFC Asian Cup",
    "African Cup of Nations": "Africa Cup of Nations",
    "Africa Cup of Nations": "Africa Cup of Nations",
    "Gold Cup": "Gold Cup",
    "Friendly": "Friendly",
}

TEAM_ALIASES = {
    "Czech Republic": "Czechia",
    "Türkiye": "Turkiye",
    "Turkey": "Turkiye",
    "United States": "United States",
    "USA": "United States",
    "Ivory Coast": "Ivory Coast",
    "Côte d'Ivoire": "Ivory Coast",
    "Curacao": "Curacao",
    "Curaçao": "Curacao",
    "DR Congo": "DR Congo",
    "Congo DR": "DR Congo",
    "Republic of Ireland": "Ireland",
    "Korea Republic": "South Korea",
}


@dataclass(frozen=True)
class HistoricalSourceConfig:
    start_date: str = "2022-01-01"
    end_date: str | None = None
    overrides_path: Path | None = None
    manual_input_path: Path | None = None
    allow_missing_overrides: bool = False


def normalize_team_name(name: str) -> str:
    clean = str(name).strip()
    return TEAM_ALIASES.get(clean, clean)


def normalize_competition(name: str) -> str:
    clean = str(name).strip()
    if clean in COMPETITION_ALIASES:
        return COMPETITION_ALIASES[clean]
    lower = clean.lower()
    if "world cup" in lower and "qual" in lower:
        return "World Cup Qualifier"
    if "qual" in lower:
        return "Continental Qualifier"
    if "nations league" in lower and any(token in lower for token in ("semi", "final", "third place")):
        return "Nations League KO"
    if "nations league" in lower:
        return "Nations League"
    if "friendly" in lower:
        return "Friendly"
    return clean


def fetch_martj42_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    def fetch_csv(url: str) -> pd.DataFrame:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        from io import StringIO

        return pd.read_csv(StringIO(response.text))

    try:
        results = fetch_csv(MARTJ42_RESULTS_URL)
        shootouts = fetch_csv(MARTJ42_SHOOTOUTS_URL)
    except Exception as exc:  # pragma: no cover - exercised by CLI behavior, not networked tests
        raise RuntimeError(
            "Could not fetch automatic historical match source from martj42/international_results. "
            "Provide --manual-input with the required CSV columns instead."
        ) from exc
    return results, shootouts


def write_manual_template(path: Path) -> None:
    template = pd.DataFrame(
        [
            {
                "date": "2022-01-01",
                "home_team": "Example Home",
                "away_team": "Example Away",
                "home_goals": 0,
                "away_goals": 0,
                "neutral": True,
                "competition": "Friendly",
            }
        ],
        columns=HISTORICAL_MATCH_COLUMNS,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    template.to_csv(path, index=False)


def load_manual_matches(path: Path) -> pd.DataFrame:
    if not path.exists():
        write_manual_template(path)
        raise FileNotFoundError(f"Manual historical match file not found. Template written to {path}")
    return pd.read_csv(path)


def load_overrides(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame(columns=["date", "home_team", "away_team", "home_goals", "away_goals", "reason"])
    overrides = pd.read_csv(path)
    required = {"date", "home_team", "away_team", "home_goals", "away_goals"}
    missing = required - set(overrides.columns)
    if missing:
        raise ValueError(f"90-minute override file is missing required columns: {sorted(missing)}")
    overrides = overrides.copy()
    overrides["home_team"] = overrides["home_team"].map(normalize_team_name)
    overrides["away_team"] = overrides["away_team"].map(normalize_team_name)
    return overrides


def standardize_martj42_results(results: pd.DataFrame, start_date: str, end_date: str | None) -> pd.DataFrame:
    required = {"date", "home_team", "away_team", "home_score", "away_score", "tournament", "neutral"}
    missing = required - set(results.columns)
    if missing:
        raise ValueError(f"martj42 results source is missing required columns: {sorted(missing)}")

    df = results.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].notna()]
    df = df[df["date"] >= pd.Timestamp(start_date)]
    if end_date:
        df = df[df["date"] <= pd.Timestamp(end_date)]
    else:
        df = df[df["date"] <= pd.Timestamp.today().normalize()]

    df = df[df["home_score"].notna() & df["away_score"].notna()]
    df = df[df["home_score"].astype(str).str.upper() != "NA"]
    df = df[df["away_score"].astype(str).str.upper() != "NA"]
    df["home_goals"] = pd.to_numeric(df["home_score"], errors="coerce")
    df["away_goals"] = pd.to_numeric(df["away_score"], errors="coerce")
    df = df[df["home_goals"].notna() & df["away_goals"].notna()]
    df["home_goals"] = df["home_goals"].astype(int)
    df["away_goals"] = df["away_goals"].astype(int)
    df["home_team"] = df["home_team"].map(normalize_team_name)
    df["away_team"] = df["away_team"].map(normalize_team_name)
    df["competition"] = df["tournament"].map(normalize_competition)
    df["neutral"] = df["neutral"].astype(str).str.upper().map({"TRUE": True, "FALSE": False}).fillna(df["neutral"].astype(bool))
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df[HISTORICAL_MATCH_COLUMNS]


def _match_key_frame(df: pd.DataFrame) -> pd.Series:
    return df["date"].astype(str) + "|" + df["home_team"].astype(str) + "|" + df["away_team"].astype(str)


def _reverse_match_key_frame(df: pd.DataFrame) -> pd.Series:
    return df["date"].astype(str) + "|" + df["away_team"].astype(str) + "|" + df["home_team"].astype(str)


def apply_90_minute_overrides(
    matches: pd.DataFrame,
    overrides: pd.DataFrame,
    allow_missing_overrides: bool = False,
) -> pd.DataFrame:
    if overrides.empty:
        return matches

    result = matches.copy()
    result["_key"] = _match_key_frame(result)
    result["_reverse_key"] = _reverse_match_key_frame(result)
    overrides = overrides.copy()
    overrides["_key"] = _match_key_frame(overrides)
    source_keys = set(result["_key"]) | set(result["_reverse_key"])
    missing = sorted(set(overrides["_key"]) - source_keys)
    if missing and not allow_missing_overrides:
        raise ValueError(
            "90-minute override rows were not found in the sourced match data. "
            f"Missing override keys: {missing[:10]}"
        )
    for _, row in overrides.iterrows():
        key = row["_key"]
        mask = result["_key"].eq(key)
        if not mask.any():
            reverse_mask = result["_reverse_key"].eq(key)
            if not reverse_mask.any():
                continue
            result.loc[reverse_mask, "home_goals"] = int(row["away_goals"])
            result.loc[reverse_mask, "away_goals"] = int(row["home_goals"])
            continue
        result.loc[mask, "home_goals"] = int(row["home_goals"])
        result.loc[mask, "away_goals"] = int(row["away_goals"])
    return result.drop(columns=["_key", "_reverse_key"])


def validate_historical_matches(matches: pd.DataFrame) -> pd.DataFrame:
    missing = set(HISTORICAL_MATCH_COLUMNS) - set(matches.columns)
    if missing:
        raise ValueError(f"historical matches are missing required columns: {sorted(missing)}")
    df = matches[HISTORICAL_MATCH_COLUMNS].copy()
    if df.empty:
        raise ValueError("No valid historical matches are available after filtering")
    parsed_dates = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
    if parsed_dates.isna().any():
        bad = df.loc[parsed_dates.isna(), "date"].head(5).tolist()
        raise ValueError(f"historical matches contain invalid YYYY-MM-DD dates: {bad}")
    for column in ("home_team", "away_team", "competition"):
        if df[column].isna().any() or df[column].astype(str).str.strip().eq("").any():
            raise ValueError(f"historical matches contain missing values in {column}")
    for column in ("home_goals", "away_goals"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
        if df[column].isna().any():
            raise ValueError(f"historical matches contain non-numeric values in {column}")
        if (df[column] < 0).any():
            raise ValueError(f"historical matches contain negative values in {column}")
        df[column] = df[column].astype(int)
    df["neutral"] = df["neutral"].astype(str).str.upper().map({"TRUE": True, "FALSE": False, "1": True, "0": False}).fillna(df["neutral"].astype(bool))
    duplicate_mask = df.duplicated(subset=["date", "home_team", "away_team", "competition"], keep=False)
    if duplicate_mask.any():
        examples = df.loc[duplicate_mask, ["date", "home_team", "away_team", "competition"]].head(5).to_dict("records")
        raise ValueError(f"historical matches contain duplicate rows, examples: {examples}")
    return df.sort_values(["date", "home_team", "away_team"]).reset_index(drop=True)


def remove_duplicate_matches(matches: pd.DataFrame) -> pd.DataFrame:
    key_columns = ["date", "home_team", "away_team", "competition"]
    value_columns = ["home_goals", "away_goals", "neutral"]
    conflicts = []
    for key, chunk in matches.groupby(key_columns, dropna=False):
        if len(chunk[value_columns].drop_duplicates()) > 1:
            conflicts.append(key)
    if conflicts:
        raise ValueError(f"historical matches contain conflicting duplicate rows: {conflicts[:5]}")
    return matches.drop_duplicates(subset=key_columns, keep="first").reset_index(drop=True)


def validate_shootout_rows_do_not_include_penalty_winner(matches: pd.DataFrame, shootouts: pd.DataFrame) -> None:
    # The source's shootout table includes both one-off knockout matches and two-legged ties
    # decided on aggregate penalties. The results CSV does not include penalty goals, so the
    # important validation is that no penalty winner is folded into the score columns.
    if not shootouts.empty and "winner" not in shootouts.columns:
        raise ValueError("shootouts source is missing winner column")


def build_historical_matches_dataset(
    config: HistoricalSourceConfig,
    source_results: pd.DataFrame | None = None,
    source_shootouts: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if config.manual_input_path is not None:
        matches = load_manual_matches(config.manual_input_path)
        return validate_historical_matches(matches)

    if source_results is None or source_shootouts is None:
        source_results, source_shootouts = fetch_martj42_data()

    matches = standardize_martj42_results(source_results, config.start_date, config.end_date)
    overrides = load_overrides(config.overrides_path)
    matches = apply_90_minute_overrides(matches, overrides, config.allow_missing_overrides)
    matches = remove_duplicate_matches(matches)
    matches = validate_historical_matches(matches)
    validate_shootout_rows_do_not_include_penalty_winner(matches, source_shootouts)
    return matches


def write_historical_matches(matches: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    validate_historical_matches(matches).to_csv(output_path, index=False)
