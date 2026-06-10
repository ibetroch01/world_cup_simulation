from __future__ import annotations

import streamlit as st


def apply_minimal_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ui-bg: #f7f8fa;
            --ui-surface: #ffffff;
            --ui-ink: #111827;
            --ui-muted: #6b7280;
            --ui-line: #e5e7eb;
            --ui-soft: #f3f4f6;
            --ui-accent: #2563eb;
        }

        .stApp {
            background: var(--ui-bg);
            color: var(--ui-ink);
        }

        header[data-testid="stHeader"],
        div[data-testid="stToolbar"],
        div[data-testid="stDecoration"],
        #MainMenu {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
        }

        .block-container {
            max-width: 1440px;
            padding-top: 0.9rem;
            padding-bottom: 2.5rem;
        }

        h1, h2, h3 {
            color: var(--ui-ink);
            letter-spacing: 0;
        }

        h3 {
            font-size: 1rem;
            font-weight: 700;
            margin-top: 1.2rem;
            margin-bottom: 0.45rem;
        }

        .dashboard-title-row {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin: 0 0 0.9rem;
        }

        .dashboard-title {
            margin: 0;
            color: var(--ui-ink);
            font-size: 1.35rem;
            font-weight: 760;
            letter-spacing: 0;
        }

        .dashboard-linkedin {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border: 1px solid var(--ui-line);
            border-radius: 999px;
            padding: 0.28rem 0.62rem;
            background: var(--ui-surface);
            color: var(--ui-muted) !important;
            font-size: 0.78rem;
            font-weight: 700;
            line-height: 1;
            text-decoration: none !important;
        }

        .dashboard-linkedin:hover {
            border-color: #0a66c2;
            color: #0a66c2 !important;
        }

        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 0.25rem;
            border-bottom: 1px solid var(--ui-line);
        }

        div[data-testid="stTabs"] button[role="tab"] {
            background: transparent;
            border-radius: 0;
            color: var(--ui-muted);
            padding: 0.5rem 0.75rem;
            font-weight: 650;
        }

        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            color: var(--ui-ink);
        }

        div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
            background-color: var(--ui-accent) !important;
            height: 2px;
        }

        div[data-testid="stTabs"] [data-baseweb="tab-border"] {
            background-color: transparent !important;
        }

        div[data-testid="stSelectbox"] label,
        div[data-testid="stSelectbox"] label *,
        div[data-testid="stToggle"] label,
        div[data-testid="stToggle"] label * {
            color: var(--ui-muted) !important;
            font-weight: 650 !important;
        }

        .minimal-card {
            background: var(--ui-surface);
            border: 1px solid var(--ui-line);
            border-radius: 10px;
            padding: 0.85rem;
            margin-bottom: 0.85rem;
        }

        .minimal-card-title {
            color: var(--ui-ink);
            font-weight: 750;
            margin-bottom: 0.7rem;
        }

        .minimal-table-wrap {
            width: 100%;
            overflow-x: auto;
            border: 1px solid var(--ui-line);
            border-radius: 10px;
            background: var(--ui-surface);
        }

        .minimal-table {
            width: 100%;
            border-collapse: collapse;
            border-spacing: 0;
            table-layout: fixed;
            background: var(--ui-surface);
            font-size: 0.82rem;
            margin: 0 !important;
        }

        .minimal-table th,
        .minimal-table td {
            border-bottom: 1px solid var(--ui-line);
            padding: 0.46rem 0.5rem;
            vertical-align: middle;
        }

        .minimal-table th {
            color: var(--ui-muted);
            background: #fbfbfc;
            font-size: 0.69rem;
            font-weight: 760;
            letter-spacing: 0.02em;
            text-align: right;
            text-transform: uppercase;
            white-space: nowrap;
        }

        .minimal-table th:first-child,
        .minimal-table td:first-child {
            text-align: left;
        }

        .minimal-table tbody tr:last-child td {
            border-bottom: 0;
        }

        .minimal-table tbody tr:hover td {
            background: #fafafa;
        }

        .group-table-card {
            padding: 0.72rem;
        }

        .group-table-card .minimal-table-wrap {
            overflow: hidden;
        }

        .group-prob-table {
            font-size: 0.76rem;
            line-height: 1.08;
        }

        .group-prob-table th,
        .group-prob-table td {
            padding: 0.34rem 0.3rem;
        }

        .group-prob-table th:not(:first-child),
        .group-prob-table td:not(:first-child) {
            text-align: center;
        }

        .team-cell {
            color: var(--ui-ink);
            font-weight: 680;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .prob-cell,
        .rating-cell {
            text-align: right;
            font-variant-numeric: tabular-nums;
        }

        .plain-probability {
            display: inline-block;
            color: var(--ui-ink);
            font-weight: 650;
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
        }

        .green-probability {
            display: block;
            margin: -0.46rem -0.5rem;
            padding: 0.46rem 0.5rem;
            color: var(--ui-ink);
            font-weight: 680;
            font-variant-numeric: tabular-nums;
        }

        .rating-text-scale {
            font-weight: 850;
            font-variant-numeric: tabular-nums;
        }

        .knockout-prob-table {
            min-width: 72rem;
            font-size: 0.84rem;
        }

        .knockout-prob-table .section-header th {
            background: var(--ui-bg);
            color: var(--ui-ink);
            font-size: 0.78rem;
            text-align: center;
            border-bottom: 1px solid var(--ui-line);
            text-transform: none;
            letter-spacing: 0;
        }

        .knockout-prob-table .team-info-head {
            border-right: 1px solid var(--ui-line);
        }

        .knockout-prob-table .simulation-start {
            border-left: 1px solid var(--ui-line);
        }

        .team-info-cell {
            background: #fbfbfc;
        }

        .knockout-prob-table th {
            color: var(--ui-ink);
            font-size: 0.8rem;
            text-transform: none;
            letter-spacing: 0;
        }

        .knockout-prob-table td {
            font-size: 0.86rem;
        }

        .minimal-note {
            color: var(--ui-muted);
            background: var(--ui-soft);
            border: 1px solid var(--ui-line);
            border-radius: 10px;
            padding: 0.75rem;
            margin-bottom: 0.85rem;
            font-size: 0.88rem;
        }

        @media (max-width: 560px) {
            .block-container {
                padding-left: 0.75rem;
                padding-right: 0.75rem;
            }

            .minimal-table {
                min-width: 42rem;
            }

            .group-prob-table {
                min-width: 36rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
