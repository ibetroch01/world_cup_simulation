from __future__ import annotations

import base64
from dataclasses import replace
from html import escape
from pathlib import Path
import secrets

import pandas as pd
import streamlit as st

from src.config import SimulationConfig
from src.data_loader import load_all_data
from src.flags import team_label
from src.simulation import run_simulations, simulate_sample_by_index
from src.ui_theme import apply_fan_festival_theme


st.set_page_config(page_title="World Cup 2026 Simulator", layout="wide")
apply_fan_festival_theme()

HEADER_IMAGE_PATH = Path(__file__).parent / "assets" / "worldcup-header.png"


@st.cache_data(show_spinner=False)
def cached_default_data():
    teams, elos, slots, mapping = load_all_data()
    elo_df = pd.DataFrame([{"team_id": team_id, "elo": elo} for team_id, elo in elos.items()])
    return teams, elo_df, slots, mapping


def probability_column_config(columns: list[str]) -> dict[str, st.column_config.NumberColumn]:
    return {column: st.column_config.NumberColumn(column, format="%.1f%%") for column in columns}


def as_percent_display(df: pd.DataFrame, probability_columns: list[str]) -> pd.DataFrame:
    display_df = df.copy()
    for column in probability_columns:
        if column in display_df.columns:
            display_df[column] = display_df[column] * 100.0
    return display_df


def pct(value: float) -> str:
    return f"{100.0 * float(value):.1f}%"


@st.cache_data(show_spinner=False)
def image_data_uri(path: str, modified_at: float) -> str:
    image_bytes = Path(path).read_bytes()
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_hero() -> None:
    if not HEADER_IMAGE_PATH.exists():
        st.error(f"Header image not found: {HEADER_IMAGE_PATH}")
        return
    modified_at = HEADER_IMAGE_PATH.stat().st_mtime
    st.markdown(
        '<div class="wc-header-shell">'
        f'<img class="wc-header-image" src="{image_data_uri(str(HEADER_IMAGE_PATH), modified_at)}" alt="World Cup 2026 Monte Carlo Dashboard header">'
        "</div>",
        unsafe_allow_html=True,
    )


def render_card_title(title: str, pill: str | None = None) -> None:
    pill_html = f'<span class="wc-pill">{escape(pill)}</span>' if pill else ""
    st.markdown(
        f'<div class="wc-card-title"><span>{escape(title)}</span>{pill_html}</div>',
        unsafe_allow_html=True,
    )


def add_team_labels(df: pd.DataFrame) -> pd.DataFrame:
    labelled = df.copy()
    labelled["Team"] = labelled.apply(lambda row: team_label(str(row["team_id"]), str(row["team_name"])), axis=1)
    return labelled


def render_group_card(group: str, group_df: pd.DataFrame) -> None:
    rows = []
    for row in group_df.sort_values(["fifa_rank", "team_name"]).itertuples(index=False):
        label = team_label(str(row.team_id), str(row.team_name))
        elo = f"{float(row.elo):.0f}" if pd.notna(row.elo) else "NA"
        rows.append(
            '<div class="wc-team-row">'
            f'<div class="wc-team-main">{escape(label)}</div>'
            f'<div class="wc-team-meta">Elo {escape(elo)}</div>'
            f'<div class="wc-rank-chip">#{int(row.fifa_rank)}</div>'
            "</div>"
        )
    rows_html = "".join(rows)
    st.markdown(
        '<div class="wc-card wc-group-card">'
        '<div class="wc-card-title">'
        f"<span>Group {escape(group)}</span>"
        "</div>"
        f"{rows_html}"
        "</div>",
        unsafe_allow_html=True,
    )


def render_control_scoreboard(config: SimulationConfig, n_simulations: int) -> None:
    dynamic = "Dynamic" if config.update_elo_during_tournament else "Fixed"
    st.markdown(
        '<div class="wc-control-grid">'
        '<div class="wc-control-tile">'
        '<div class="wc-control-label">Simulation runs</div>'
        f'<div class="wc-control-value">{int(n_simulations):,}</div>'
        '<div class="wc-control-unit">Monte Carlo</div>'
        "</div>"
        '<div class="wc-control-tile">'
        '<div class="wc-control-label">Expected goals</div>'
        f'<div class="wc-control-value">{config.total_expected_goals:.2f}</div>'
        '<div class="wc-control-unit">total xG</div>'
        "</div>"
        '<div class="wc-control-tile">'
        '<div class="wc-control-label">Goal damping</div>'
        f'<div class="wc-control-value">{config.elo_goal_damping:.0f}</div>'
        '<div class="wc-control-unit">Elo share</div>'
        "</div>"
        '<div class="wc-control-tile">'
        '<div class="wc-control-label">Penalty damping</div>'
        f'<div class="wc-control-value">{config.penalty_damping:.0f}</div>'
        '<div class="wc-control-unit">advancement</div>'
        "</div>"
        '<div class="wc-control-tile">'
        '<div class="wc-control-label">Seed</div>'
        f'<div class="wc-control-value">{config.random_seed if config.random_seed is not None else "Random"}</div>'
        '<div class="wc-control-unit">replay</div>'
        "</div>"
        '<div class="wc-control-tile">'
        '<div class="wc-control-label">Elo mode</div>'
        f'<div class="wc-control-value">{escape(dynamic)}</div>'
        f'<div class="wc-control-unit">K {config.k_factor:.0f}</div>'
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_empty(message: str) -> None:
    st.markdown(f'<div class="wc-empty">{escape(message)}</div>', unsafe_allow_html=True)


FINISH_COLUMNS = [
    ("Group", "P(Finish Group Stage)"),
    ("R32", "P(Finish Round of 32)"),
    ("R16", "P(Finish Round of 16)"),
    ("QF", "P(Finish Quarterfinal)"),
    ("SF", "P(Finish Semifinal)"),
    ("Final", "P(Finish Final)"),
    ("Champ", "P(Finish Champion)"),
]


def render_finish_card(row) -> None:
    rows = []
    for label, column in FINISH_COLUMNS:
        value = float(getattr(row, column.replace(" ", "_").replace("(", "").replace(")", ""), 0.0))
        rows.append(
            '<div class="wc-prob-row">'
            f'<span>{escape(label)}</span>'
            '<div class="wc-prob-track">'
            f'<div class="wc-prob-fill" style="width: {min(100.0, value * 100.0):.1f}%"></div>'
            "</div>"
            f'<strong>{pct(value)}</strong>'
            "</div>"
        )
    team = team_label(str(row.team_id), str(row.team_name))
    st.markdown(
        '<div class="wc-card wc-group-card wc-result-card">'
        '<div class="wc-card-title">'
        f"<span>{escape(team)}</span>"
        f'<span class="wc-rank-chip">Group {escape(str(row.group))}</span>'
        "</div>"
        f"{''.join(rows)}"
        "</div>",
        unsafe_allow_html=True,
    )


def render_finish_probabilities(probability_table: pd.DataFrame) -> None:
    display_df = probability_table.copy()
    safe_columns = {
        column: column.replace(" ", "_").replace("(", "").replace(")", "")
        for _, column in FINISH_COLUMNS
    }
    display_df = display_df.rename(columns=safe_columns)
    columns = st.columns(4)
    for ix, row in enumerate(display_df.itertuples(index=False)):
        with columns[ix % 4]:
            render_finish_card(row)


def render_winner_probability(champion_table: pd.DataFrame) -> None:
    max_probability = float(champion_table["champion_probability"].max()) if len(champion_table) else 0.0
    rows = []
    for row in add_team_labels(champion_table.head(20)).itertuples(index=False):
        probability = float(row.champion_probability)
        width = 0.0 if max_probability == 0 else min(100.0, 100.0 * probability / max_probability)
        rows.append(
            '<div class="wc-winner-row">'
            f'<div class="wc-winner-team">{escape(row.Team)}</div>'
            '<div class="wc-winner-track">'
            f'<div class="wc-winner-fill" style="width: {width:.1f}%"></div>'
            "</div>"
            f'<div class="wc-winner-pct">{pct(probability)}</div>'
            "</div>"
        )
    st.markdown(
        '<div class="wc-card wc-group-card wc-winner-card">'
        '<div class="wc-card-title"><span>Winner Probability</span></div>'
        f"{''.join(rows)}"
        "</div>",
        unsafe_allow_html=True,
    )


def round_name(match_id: str) -> str:
    number = int(match_id.replace("M", ""))
    if 73 <= number <= 88:
        return "Round of 32"
    if 89 <= number <= 96:
        return "Round of 16"
    if 97 <= number <= 100:
        return "Quarterfinals"
    if 101 <= number <= 102:
        return "Semifinals"
    if number == 103:
        return "Third Place"
    return "Final"


def render_match_card(match, team_names: dict[str, str]) -> None:
    team_a = team_label(match.team_a, team_names.get(match.team_a, match.team_a))
    team_b = team_label(match.team_b, team_names.get(match.team_b, match.team_b))
    winner = team_label(str(match.winner), team_names.get(str(match.winner), str(match.winner)))
    team_a_class = "wc-winner" if match.winner == match.team_a else ""
    team_b_class = "wc-winner" if match.winner == match.team_b else ""
    pens = '<span class="wc-pens">pens</span>' if match.decided_by_penalties else ""
    st.markdown(
        '<div class="wc-bracket-card">'
        f'<div class="wc-match-id"><span>{escape(match.match_id)}</span>{pens}</div>'
        '<div class="wc-scoreline">'
        f'<span class="{team_a_class}">{escape(team_a)}</span>'
        f'<span class="wc-score">{int(match.goals_a)}-{int(match.goals_b)}</span>'
        f'<span class="{team_b_class}">{escape(team_b)}</span>'
        "</div>"
        f'<div class="wc-team-meta">Winner: {escape(winner)}</div>'
        "</div>",
        unsafe_allow_html=True,
    )


def render_sample_group_card(group: str, table: pd.DataFrame, team_names: dict[str, str]) -> None:
    rows = []
    for row in table.itertuples(index=False):
        team = team_label(str(row.team_id), team_names.get(str(row.team_id), str(row.team_name)))
        rows.append(
            '<div class="wc-sample-row">'
            f'<div class="wc-rank-chip">{int(row.group_rank)}</div>'
            f'<div class="wc-team-main">{escape(team)}</div>'
            f'<div class="wc-team-meta">{int(row.points)} pts</div>'
            f'<div class="wc-team-meta">GD {int(row.goal_difference):+d}</div>'
            "</div>"
        )
    st.markdown(
        '<div class="wc-card wc-group-card">'
        '<div class="wc-card-title">'
        f"<span>Group {escape(str(group))}</span>"
        "</div>"
        f"{''.join(rows)}"
        "</div>",
        unsafe_allow_html=True,
    )


def render_knockout(sample_result, teams: pd.DataFrame) -> None:
    team_names = dict(zip(teams["team_id"], teams["team_name"]))
    rounds = ["Round of 32", "Round of 16", "Quarterfinals", "Semifinals", "Third Place", "Final"]
    for stage in rounds:
        matches = [match for match in sample_result.matches if round_name(match.match_id) == stage]
        if not matches:
            continue
        st.markdown(f"### {stage}")
        column_count = min(4, max(1, len(matches)))
        columns = st.columns(column_count)
        for ix, match in enumerate(matches):
            with columns[ix % column_count]:
                render_match_card(match, team_names)


default_teams, default_elo_df, r32_slots, third_mapping = cached_default_data()
teams_df = default_teams.copy()
elo_df = default_elo_df.copy()

render_hero()

setup_tab, groups_tab, results_tab, bracket_tab = st.tabs(["Setup", "Groups", "Results", "Bracket"])

with setup_tab:
    render_card_title("Matchday Control Room")

    top_controls = st.columns(3, gap="large")
    with top_controls[0]:
        n_simulations = st.slider(
            "Simulation runs",
            min_value=1,
            max_value=5000,
            value=250,
            step=50,
            key="setup_n_simulations",
        )
    with top_controls[1]:
        random_seed = st.slider("Random seed", min_value=0, max_value=1_000_000, value=42, step=1, key="setup_seed")
    with top_controls[2]:
        elo_mode = st.radio(
            "Elo update mode",
            ["Fixed Elo", "Dynamic Elo"],
            horizontal=True,
            key="setup_elo_mode",
        )
        update_elo = elo_mode == "Dynamic Elo"

    model_controls = st.columns(4, gap="large")
    with model_controls[0]:
        total_expected_goals = st.slider(
            "Total expected goals",
            min_value=0.50,
            max_value=5.00,
            value=2.70,
            step=0.05,
            key="setup_total_expected_goals",
        )
    with model_controls[1]:
        elo_goal_damping = st.slider(
            "Elo goal damping",
            min_value=200,
            max_value=1600,
            value=800,
            step=25,
            key="setup_elo_goal_damping",
        )
    with model_controls[2]:
        penalty_damping = st.slider(
            "Penalty damping",
            min_value=200,
            max_value=1600,
            value=800,
            step=25,
            key="setup_penalty_damping",
        )
    with model_controls[3]:
        k_factor = st.slider("K factor", min_value=0, max_value=80, value=30, step=1, key="setup_k_factor")

    config = SimulationConfig(
        total_expected_goals=float(total_expected_goals),
        elo_goal_damping=float(elo_goal_damping),
        update_elo_during_tournament=bool(update_elo),
        k_factor=float(k_factor),
        penalty_damping=float(penalty_damping),
        random_seed=random_seed,
    )
    st.session_state["input_teams"] = teams_df
    st.session_state["input_elos"] = dict(zip(elo_df["team_id"], elo_df["elo"].astype(float)))
    st.session_state["sim_config"] = config
    render_control_scoreboard(config, int(n_simulations))
    if st.button("Run simulations", type="primary"):
        progress = st.progress(0.0)
        run_config = config
        if run_config.random_seed is None:
            run_config = replace(run_config, random_seed=secrets.randbits(32))
        try:
            probability_table, champion_table, sample_result = run_simulations(
                int(n_simulations),
                st.session_state["input_teams"],
                st.session_state["input_elos"],
                r32_slots,
                third_mapping,
                run_config,
                progress_callback=progress.progress,
            )
        except Exception as exc:
            st.error(str(exc))
        else:
            st.session_state["probability_table"] = probability_table
            st.session_state["champion_table"] = champion_table
            st.session_state["sample_result"] = sample_result
            st.session_state["run_config"] = run_config
            st.session_state["run_n_simulations"] = int(n_simulations)
            st.success("Simulation complete.")

with groups_tab:
    teams_view = st.session_state.get("input_teams", default_teams).merge(
        pd.DataFrame(
            [{"team_id": team_id, "elo": elo} for team_id, elo in st.session_state.get("input_elos", dict(zip(default_elo_df.team_id, default_elo_df.elo))).items()]
        ),
        on="team_id",
        how="left",
    )
    st.markdown("### Groups A-L")
    group_columns = st.columns(4)
    for ix, (group, group_df) in enumerate(teams_view.sort_values(["group", "fifa_rank"]).groupby("group")):
        with group_columns[ix % 4]:
            render_group_card(str(group), group_df)

with results_tab:
    probability_table = st.session_state.get("probability_table")
    champion_table = st.session_state.get("champion_table")
    if probability_table is None or champion_table is None:
        render_empty("Run a simulation first to unlock the finish probabilities and winner graph.")
    else:
        st.subheader("Finish Probabilities")
        render_finish_probabilities(probability_table)
        render_winner_probability(champion_table)

with bracket_tab:
    if st.session_state.get("sample_result") is None:
        render_empty("Run a simulation first, then choose which sampled tournament bracket you want to inspect.")
    else:
        run_n_simulations = st.session_state.get("run_n_simulations", 1)
        sample_index = st.number_input(
            "Sample tournament",
            min_value=1,
            max_value=int(run_n_simulations),
            value=1,
            step=1,
            help="Choose which simulation run from the latest batch to display.",
        )
        sample_result = simulate_sample_by_index(
            int(sample_index),
            st.session_state["input_teams"],
            st.session_state["input_elos"],
            r32_slots,
            third_mapping,
            st.session_state.get("run_config", st.session_state["sim_config"]),
        )
        st.subheader("Sample Group Tables")
        team_names = dict(zip(st.session_state["input_teams"]["team_id"], st.session_state["input_teams"]["team_name"]))
        group_columns = st.columns(4)
        for group, table in sample_result.group_tables.items():
            with group_columns[(ord(str(group)) - ord("A")) % 4]:
                render_sample_group_card(str(group), table, team_names)
        st.subheader("Sample Knockout Bracket")
        render_knockout(sample_result, st.session_state["input_teams"])
