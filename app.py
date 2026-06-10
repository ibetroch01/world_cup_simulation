from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import ROOT_DIR
from src.data_loader import load_initial_elos, load_teams
from src.flags import team_label
from src.results_loader import list_output_folders, load_simulation_output
from src.ui_theme import apply_minimal_theme


st.set_page_config(page_title="World Cup 2026 Results", layout="wide")
apply_minimal_theme()

OUTPUTS_DIR = ROOT_DIR / "outputs"
CURRENT_OUTPUT_FOLDER = "attack_defence_baseline"
GROUP_PROBABILITY_COLUMNS = ["p_place_1", "p_place_2", "p_place_3", "p_place_4", "p_r32", "p_eliminated_group"]
KNOCKOUT_PROBABILITY_COLUMNS = ["p_r32", "p_r16", "p_qf", "p_sf", "p_final", "p_champion"]
GROUP_COLUMN_LABELS = {
    "team": "Team",
    "p_place_1": "1st",
    "p_place_2": "2nd",
    "p_place_3": "3rd",
    "p_place_4": "4th",
    "p_r32": "R32",
    "p_eliminated_group": "Out",
}
KNOCKOUT_COLUMN_LABELS = {
    "team": "Team",
    "group": "Group",
    "elo": "ELO",
    "attack_score": "Off.",
    "defence_score": "Def.",
    "p_r32": "Round of 32",
    "p_r16": "Round of 16",
    "p_qf": "Quarter-finals",
    "p_sf": "Semi-finals",
    "p_final": "Final",
    "p_champion": "Champion",
}


@st.cache_data(show_spinner=False)
def cached_teams() -> pd.DataFrame:
    return load_teams()


@st.cache_data(show_spinner=False)
def cached_elos() -> dict[str, float]:
    return load_initial_elos()


@st.cache_data(show_spinner=False)
def cached_output(path: str, modified_token: float):
    return load_simulation_output(Path(path))


def format_probability(value: float) -> str:
    return f"{value * 100.0:.1f}%"


def format_rating(value: float) -> str:
    return "-" if pd.isna(value) else f"{value:.3f}"


def format_elo(value: float) -> str:
    return "-" if pd.isna(value) else f"{value:.0f}"


def rating_text_cell(value: float, *, lower: float, upper: float, higher_is_good: bool) -> str:
    color = heat_color(value, lower=lower, upper=upper, higher_is_good=higher_is_good)
    return f'<span class="rating-text-scale" style="color:{color};">{escape(format_rating(value))}</span>'


def heat_color(value: float, *, lower: float = 0.0, upper: float = 1.0, higher_is_good: bool = True) -> str:
    if pd.isna(value):
        return "#f3f4f6"
    if upper <= lower:
        score = 0.5
    else:
        score = max(0.0, min(1.0, (float(value) - lower) / (upper - lower)))
    if not higher_is_good:
        score = 1.0 - score
    # Red -> amber -> green. Kept muted enough for a minimal dashboard, but clear at a glance.
    stops = [
        (0.0, (127, 29, 29)),
        (0.5, (180, 127, 31)),
        (1.0, (20, 83, 45)),
    ]
    left, right = stops[0], stops[-1]
    for idx in range(len(stops) - 1):
        if stops[idx][0] <= score <= stops[idx + 1][0]:
            left, right = stops[idx], stops[idx + 1]
            break
    span = right[0] - left[0]
    mix = 0.0 if span == 0 else (score - left[0]) / span
    rgb = tuple(round(left[1][channel] + (right[1][channel] - left[1][channel]) * mix) for channel in range(3))
    return f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"


def plain_probability_cell(value: float) -> str:
    return f'<span class="plain-probability">{escape(format_probability(value))}</span>'


def green_probability_cell(value: float) -> str:
    clamped = max(0.0, min(1.0, float(value)))
    alpha = 0.08 + clamped * 0.28
    return (
        f'<span class="green-probability" style="background:rgba(90, 160, 82, {alpha:.3f});">'
        f"{escape(format_probability(value))}"
        "</span>"
    )


def team_label_from_name(team_name: str, name_to_id: dict[str, str]) -> str:
    team_id = name_to_id.get(team_name)
    return team_label(team_id, team_name) if team_id else team_name


def render_note(message: str) -> None:
    st.markdown(f'<div class="minimal-note">{escape(message)}</div>', unsafe_allow_html=True)


def build_group_display(group_phase: pd.DataFrame, name_to_id: dict[str, str]) -> pd.DataFrame:
    display = group_phase.copy()
    display["p_r32"] = display["p_advance_group"] + display["p_advance_best_third"]
    display = display[
        [
            "team",
            "p_place_1",
            "p_place_2",
            "p_place_3",
            "p_place_4",
            "p_r32",
            "p_eliminated_group",
        ]
    ]
    display["team"] = display["team"].map(lambda value: team_label_from_name(str(value), name_to_id))
    return display


def build_knockout_display(
    knockout_phase: pd.DataFrame,
    team_ratings: pd.DataFrame | None,
    name_to_id: dict[str, str],
    teams: pd.DataFrame | None = None,
    initial_elos: dict[str, float] | None = None,
) -> tuple[pd.DataFrame, bool]:
    display = knockout_phase.copy()
    has_ratings = team_ratings is not None and {"team", "attack_score", "defence_score"} <= set(team_ratings.columns)
    team_metadata = pd.DataFrame()
    if teams is not None:
        team_metadata = teams[["team_id", "team_name", "group"]].rename(columns={"team_name": "team"}).copy()
        if initial_elos is not None:
            team_metadata["elo"] = team_metadata["team_id"].map(initial_elos)
        else:
            team_metadata["elo"] = pd.NA
        display = display.merge(team_metadata[["team", "group", "elo"]], on="team", how="left")
    if has_ratings:
        ratings = team_ratings[["team", "attack_score", "defence_score"]].copy()
        display = display.merge(ratings, on="team", how="left")
        ordered_columns = [
            "team",
            "group",
            "elo",
            "attack_score",
            "defence_score",
            "p_r32",
            "p_r16",
            "p_qf",
            "p_sf",
            "p_final",
            "p_champion",
        ]
    else:
        ordered_columns = ["team"]
        if "group" in display.columns:
            ordered_columns.extend(["group", "elo"])
        ordered_columns.extend(["p_r32", "p_r16", "p_qf", "p_sf", "p_final", "p_champion"])
    display = display[ordered_columns].sort_values("p_champion", ascending=False).reset_index(drop=True)
    display["team"] = display["team"].map(lambda value: team_label_from_name(str(value), name_to_id))
    return display, bool(has_ratings)


def render_group_phase(group_phase: pd.DataFrame, name_to_id: dict[str, str]) -> None:
    display = build_group_display(group_phase, name_to_id)
    grouped = list(group_phase.sort_values(["group", "p_place_1"], ascending=[True, False]).groupby("group"))
    for row_start in range(0, len(grouped), 3):
        columns = st.columns(3)
        for column, (group, raw_group_df) in zip(columns, grouped[row_start : row_start + 3]):
            with column:
                group_display = display.loc[raw_group_df.index].copy()
                st.markdown(render_group_table(str(group), group_display), unsafe_allow_html=True)


def render_group_table(group: str, group_display: pd.DataFrame) -> str:
    headers = "".join(f"<th>{escape(GROUP_COLUMN_LABELS[column])}</th>" for column in ["team", *GROUP_PROBABILITY_COLUMNS])
    rows = []
    for _, row in group_display.iterrows():
        cells = [f'<td class="team-cell">{escape(str(row["team"]))}</td>']
        for column in GROUP_PROBABILITY_COLUMNS:
            cells.append(
                '<td class="prob-cell">'
                + plain_probability_cell(float(row[column]))
                + "</td>"
            )
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return (
        '<div class="minimal-card group-table-card">'
        f'<div class="minimal-card-title">Group {escape(group)}</div>'
        '<div class="minimal-table-wrap">'
        '<table class="minimal-table group-prob-table">'
        '<colgroup>'
        '<col style="width:30%">'
        '<col style="width:11.66%"><col style="width:11.66%"><col style="width:11.66%">'
        '<col style="width:11.66%"><col style="width:11.66%"><col style="width:11.66%">'
        "</colgroup>"
        f"<thead><tr>{headers}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "</div>"
        "</div>"
    )


def render_knockout_phase(
    knockout_phase: pd.DataFrame,
    team_ratings: pd.DataFrame | None,
    name_to_id: dict[str, str],
    teams: pd.DataFrame,
    initial_elos: dict[str, float],
) -> None:
    display, has_ratings = build_knockout_display(knockout_phase, team_ratings, name_to_id, teams, initial_elos)
    if not has_ratings:
        render_note("This output folder has no team_ratings.csv. Showing round probabilities without attack/defence scores.")
    sort_options = {
        "Champion": "p_champion",
        "Final": "p_final",
        "Semi-finals": "p_sf",
        "Quarter-finals": "p_qf",
        "Round of 16": "p_r16",
        "Round of 32": "p_r32",
        "Off.": "attack_score",
        "Def.": "defence_score",
        "ELO": "elo",
        "Group": "group",
        "Team": "team",
    }
    available_sort_options = {label: column for label, column in sort_options.items() if column in display.columns}
    sort_cols = st.columns([2.4, 1, 6], gap="small")
    with sort_cols[0]:
        sort_label = st.selectbox("Sort by", list(available_sort_options), index=0, key="knockout_sort_column")
    with sort_cols[1]:
        descending = st.toggle("Desc", value=True, key="knockout_sort_desc")
    sorted_display = display.sort_values(
        available_sort_options[sort_label],
        ascending=not descending,
        kind="mergesort",
        na_position="last",
    )
    st.markdown(render_knockout_table(sorted_display, has_ratings), unsafe_allow_html=True)


def render_knockout_table(display: pd.DataFrame, has_ratings: bool) -> str:
    columns = display.columns.tolist()
    rating_bounds = {}
    for column in ("attack_score", "defence_score"):
        if column in display:
            values = pd.to_numeric(display[column], errors="coerce")
            rating_bounds[column] = (float(values.min()), float(values.max()))
    team_rating_span = len([column for column in columns if column in {"group", "elo", "attack_score", "defence_score"}])
    probability_span = len([column for column in columns if column in KNOCKOUT_PROBABILITY_COLUMNS])
    team_rating_header = (
        f'<th colspan="{team_rating_span}" class="team-info-head">Team Rating</th>' if team_rating_span else ""
    )
    section_header = (
        '<tr class="section-header">'
        "<th></th>"
        f"{team_rating_header}"
        f'<th colspan="{probability_span}" class="simulation-info-head">Chances To Reach Knockout Stage</th>'
        "</tr>"
    )
    header_cells = []
    for column in columns:
        classes = []
        if column in {"group", "elo", "attack_score", "defence_score"}:
            classes.append("team-info-header")
        if column in KNOCKOUT_PROBABILITY_COLUMNS:
            classes.append("simulation-header")
        if column == "p_r32":
            classes.append("simulation-start")
        class_attr = f' class="{" ".join(classes)}"' if classes else ""
        header_cells.append(f"<th{class_attr}>{escape(KNOCKOUT_COLUMN_LABELS.get(column, column))}</th>")
    header = "".join(header_cells)
    rows = []
    for _, row in display.iterrows():
        cells = []
        for column in columns:
            if column == "team":
                cells.append(f'<td class="team-cell">{escape(str(row[column]))}</td>')
            elif column == "group":
                cells.append(f'<td class="rating-cell team-info-cell">{escape(str(row[column]))}</td>')
            elif column == "elo":
                cells.append(f'<td class="rating-cell team-info-cell">{escape(format_elo(float(row[column])) if pd.notna(row[column]) else "-")}</td>')
            elif column in KNOCKOUT_PROBABILITY_COLUMNS:
                start_class = " simulation-start" if column == "p_r32" else ""
                cells.append(
                    f'<td class="prob-cell simulation-cell{start_class}">'
                    + green_probability_cell(float(row[column]))
                    + "</td>"
                )
            elif column == "attack_score":
                lower, upper = rating_bounds[column]
                cells.append(
                    '<td class="rating-cell team-info-cell">'
                    + rating_text_cell(float(row[column]), lower=lower, upper=upper, higher_is_good=True)
                    + "</td>"
                )
            elif column == "defence_score":
                lower, upper = rating_bounds[column]
                cells.append(
                    '<td class="rating-cell team-info-cell">'
                    + rating_text_cell(float(row[column]), lower=lower, upper=upper, higher_is_good=False)
                    + "</td>"
                )
        rows.append(f"<tr>{''.join(cells)}</tr>")
    width_map = {
        "team": "25%",
        "group": "6%",
        "elo": "7%",
        "attack_score": "7%",
        "defence_score": "7%",
        "p_r32": "8%",
        "p_r16": "8%",
        "p_qf": "8%",
        "p_sf": "8%",
        "p_final": "8%",
        "p_champion": "8%",
    }
    colgroup = "<colgroup>" + "".join(f'<col style="width:{width_map.get(column, "8%")}">' for column in columns) + "</colgroup>"
    return (
        '<div class="minimal-table-wrap">'
        '<table class="minimal-table knockout-prob-table">'
        f"{colgroup}<thead>{section_header}<tr>{header}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "</div>"
    )
teams = cached_teams()
initial_elos = cached_elos()
name_to_id = dict(zip(teams["team_name"], teams["team_id"]))
folders = list_output_folders(OUTPUTS_DIR)

if not folders:
    render_note("No precomputed output folders found. Run scripts/run_simulations.py first.")
    st.stop()

selected = OUTPUTS_DIR / CURRENT_OUTPUT_FOLDER
if selected not in folders:
    selected = folders[0]
modified_token = max(
    (selected / filename).stat().st_mtime
    for filename in ("metadata.json", "group_phase_results.csv", "knockout_phase_results.csv")
)

try:
    output = cached_output(str(selected), modified_token)
except Exception as exc:
    st.error(str(exc))
    st.stop()

st.markdown(
    '<div class="dashboard-title-row">'
    '<h1 class="dashboard-title">World Cup 2026 Simulation Dashboard</h1>'
    '<a class="dashboard-linkedin" href="https://www.linkedin.com/in/ibe-troch-9744a8269/" target="_blank" rel="noopener noreferrer">LinkedIn</a>'
    "</div>",
    unsafe_allow_html=True,
)

group_tab, knockout_tab = st.tabs(["Group Phase", "Knock-out Phase"])
with group_tab:
    render_group_phase(output.group_phase, name_to_id)
with knockout_tab:
    render_knockout_phase(output.knockout_phase, output.team_ratings, name_to_id, teams, initial_elos)
