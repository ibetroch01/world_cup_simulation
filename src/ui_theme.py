from __future__ import annotations

import streamlit as st


def apply_fan_festival_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --wc-black: #071014;
            --wc-midnight: #071426;
            --wc-plum: #26051f;
            --wc-forest: #0f4328;
            --wc-ink: #101c23;
            --wc-panel: #fffdf7;
            --wc-cream: #f7f0e2;
            --wc-gold: #d8ae42;
            --wc-gold-bright: #f5d36b;
            --wc-green: #16713e;
            --wc-blue: #0a4f82;
            --wc-cyan: #38bcc1;
            --wc-pitch: #0b7d45;
            --wc-muted: #65737a;
            --wc-line: rgba(7, 16, 20, 0.14);
            --wc-header-gradient: linear-gradient(115deg, var(--wc-plum) 0%, var(--wc-black) 30%, var(--wc-forest) 62%, var(--wc-midnight) 100%);
            --wc-gold-gradient: linear-gradient(90deg, #8b6a20 0%, var(--wc-gold) 45%, var(--wc-gold-bright) 100%);
        }

        .stApp {
            background:
                radial-gradient(circle at 5% 0%, rgba(216, 174, 66, 0.22), transparent 24rem),
                radial-gradient(circle at 18% 3%, rgba(38, 5, 31, 0.16), transparent 20rem),
                radial-gradient(circle at 58% 0%, rgba(22, 113, 62, 0.18), transparent 27rem),
                radial-gradient(circle at 96% 2%, rgba(10, 79, 130, 0.22), transparent 27rem),
                linear-gradient(135deg, #fbf5e8 0%, #fffdf7 48%, #edf7f2 100%);
            color: var(--wc-ink);
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3 {
            letter-spacing: 0;
        }

        h3 {
            color: var(--wc-black);
            font-weight: 1000;
        }

        div[data-testid="stTabs"] button[role="tab"] {
            border-radius: 999px;
            border: 1px solid rgba(216, 174, 66, 0.16);
            background: rgba(255, 253, 247, 0.82);
            color: var(--wc-ink);
            margin-right: 0.25rem;
            padding: 0.35rem 0.75rem;
            box-shadow: 0 8px 22px rgba(7, 16, 20, 0.05);
        }

        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            background: var(--wc-header-gradient);
            color: var(--wc-gold);
            font-weight: 800;
            border: 1px solid rgba(245, 197, 66, 0.52);
            box-shadow: 0 10px 28px rgba(7, 16, 20, 0.16);
        }

        div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
            background-color: var(--wc-gold) !important;
        }

        div[data-testid="stTabs"] [data-baseweb="tab-border"] {
            background-color: rgba(7, 16, 20, 0.10) !important;
        }

        .stButton > button {
            border: 1px solid rgba(245, 197, 66, 0.58);
            border-radius: 999px;
            background: var(--wc-header-gradient);
            color: var(--wc-gold);
            font-weight: 900;
            min-height: 3rem;
            box-shadow: 0 14px 30px rgba(7, 16, 20, 0.20);
        }

        .stButton > button:hover {
            color: #fff3b0;
            border-color: rgba(245, 197, 66, 0.86);
            filter: saturate(1.08) brightness(1.04);
            transform: translateY(-1px);
        }

        div[data-testid="stMetric"] {
            background: var(--wc-panel);
            border: 1px solid var(--wc-line);
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 12px 34px rgba(7, 16, 20, 0.08);
        }

        div[data-testid="stNumberInput"] label,
        div[data-testid="stTextInput"] label,
        div[data-testid="stSlider"] label,
        div[data-testid="stCheckbox"] label,
        div[data-testid="stRadio"] label {
            color: var(--wc-ink) !important;
            font-weight: 1000 !important;
        }

        div[data-testid="stNumberInput"] label *,
        div[data-testid="stTextInput"] label *,
        div[data-testid="stSlider"] label *,
        div[data-testid="stCheckbox"] label *,
        div[data-testid="stRadio"] label * {
            color: var(--wc-ink) !important;
            font-weight: 1000 !important;
        }

        div[data-testid="stRadio"] p,
        div[data-testid="stRadio"] span {
            color: var(--wc-ink) !important;
            font-weight: 1000 !important;
        }

        div[data-testid="stRadio"] [role="radiogroup"] {
            display: flex;
            gap: 0.5rem;
            padding-top: 0.22rem;
            align-items: center;
            transform: translateY(-0.55rem);
        }

        div[data-testid="stRadio"] [role="radio"] {
            border: 1px solid rgba(216,174,66,0.22);
            border-radius: 999px;
            background: rgba(255,253,247,0.72);
            padding: 0.24rem 0.7rem;
            min-height: 1.65rem;
            display: inline-flex;
            align-items: center;
        }

        div[data-testid="stRadio"] [role="radio"][aria-checked="true"] {
            border-color: rgba(245, 197, 66, 0.72) !important;
            background: rgba(216, 174, 66, 0.13) !important;
            color: var(--wc-black) !important;
        }

        div[data-testid="stSlider"],
        div[data-testid="stSlider"] > div,
        div[data-testid="stSlider"] [data-baseweb="slider"],
        div[data-testid="stSlider"] [data-baseweb="slider"] > div {
            background: transparent !important;
        }

        div[data-testid="stSlider"] [data-baseweb="slider"] div[style*="background"] {
            background: var(--wc-gold-gradient) !important;
        }

        div[data-testid="stSlider"] [role="slider"] {
            background-color: var(--wc-gold) !important;
            border: 2px solid var(--wc-midnight) !important;
            box-shadow: 0 0 0 3px rgba(216,174,66,0.22) !important;
        }

        div[data-testid="stNumberInput"] input,
        div[data-testid="stTextInput"] input {
            background: var(--wc-panel);
            color: var(--wc-ink);
            border: 1px solid var(--wc-line);
            border-radius: 8px;
            font-weight: 850;
        }

        div[data-testid="stNumberInput"] button {
            background: var(--wc-midnight);
            color: var(--wc-gold);
        }

        .stProgress > div > div > div > div {
            background: var(--wc-gold-gradient);
        }

        .wc-header-shell {
            margin-bottom: 1.35rem;
        }

        .wc-header-image {
            display: block;
            width: 100%;
            height: auto;
            border-radius: 18px;
            box-shadow: 0 22px 60px rgba(7, 16, 20, 0.24);
        }

        .wc-card {
            background:
                linear-gradient(180deg, rgba(255,253,247,0.97), rgba(255,253,247,0.90));
            border: 1px solid rgba(7,16,20,0.13);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 16px 40px rgba(7, 16, 20, 0.09);
        }

        .wc-control-room {
            position: relative;
            overflow: hidden;
            background:
                linear-gradient(180deg, rgba(255,255,255,0.98), rgba(255,255,255,0.94)),
                radial-gradient(circle at 0% 0%, rgba(245,197,66,0.14), transparent 18rem),
                radial-gradient(circle at 100% 0%, rgba(0,103,177,0.16), transparent 18rem);
        }

        .wc-control-grid {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 0.7rem;
            margin-bottom: 1rem;
        }

        .wc-control-tile {
            border: 1px solid rgba(216,174,66,0.28);
            border-radius: 8px;
            padding: 0.75rem;
            background:
                linear-gradient(180deg, rgba(7,20,38,0.98), rgba(7,16,20,0.94)),
                radial-gradient(circle at 100% 0%, rgba(216,174,66,0.16), transparent 8rem);
            box-shadow: 0 14px 28px rgba(7,16,20,0.13);
        }

        .wc-control-label {
            color: rgba(245,211,107,0.78);
            font-size: 0.72rem;
            font-weight: 900;
            text-transform: uppercase;
        }

        .wc-control-value {
            color: #fffaf0;
            font-size: 1.45rem;
            font-weight: 1000;
            line-height: 1.05;
            margin-top: 0.18rem;
        }

        .wc-control-unit {
            color: var(--wc-gold-bright);
            font-size: 0.75rem;
            font-weight: 900;
            margin-top: 0.18rem;
        }

        .wc-group-card {
            position: relative;
            overflow: hidden;
            padding-top: 1.15rem;
        }

        .wc-group-card::before {
            content: "";
            position: absolute;
            inset: 0 0 auto 0;
            height: 0.35rem;
            background: linear-gradient(90deg, var(--wc-plum), var(--wc-black), var(--wc-forest), var(--wc-gold), var(--wc-blue));
        }

        .wc-card-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            margin-bottom: 0.85rem;
            font-size: 1rem;
            font-weight: 900;
            color: var(--wc-black);
        }

        .wc-pill {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 0.18rem 0.55rem;
            background: var(--wc-header-gradient);
            color: var(--wc-gold);
            font-size: 0.74rem;
            font-weight: 900;
            white-space: nowrap;
        }

        .wc-team-row {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto auto;
            gap: 0.5rem;
            align-items: center;
            padding: 0.48rem 0;
            border-top: 1px solid rgba(7, 16, 20, 0.08);
        }

        .wc-team-main {
            min-width: 0;
            font-weight: 850;
            color: var(--wc-ink);
            overflow-wrap: anywhere;
            font-size: 0.92rem;
        }

        .wc-team-meta {
            color: var(--wc-muted);
            font-weight: 750;
            font-size: 0.76rem;
        }

        .wc-rank-chip {
            min-width: 2.5rem;
            text-align: center;
            border-radius: 999px;
            padding: 0.18rem 0.45rem;
            background: rgba(7,20,38,0.94);
            color: var(--wc-gold-bright);
            border: 1px solid rgba(216,174,66,0.28);
            font-weight: 900;
            font-size: 0.74rem;
        }

        .wc-result-card {
            min-height: 17.2rem;
        }

        .wc-prob-row {
            display: grid;
            grid-template-columns: 3.1rem minmax(0, 1fr) 3.4rem;
            gap: 0.55rem;
            align-items: center;
            padding: 0.36rem 0;
            border-top: 1px solid rgba(7,16,20,0.07);
            font-size: 0.78rem;
            font-weight: 900;
        }

        .wc-prob-track,
        .wc-winner-track {
            height: 0.45rem;
            border-radius: 999px;
            background: rgba(7, 20, 38, 0.12);
            overflow: hidden;
        }

        .wc-prob-fill,
        .wc-winner-fill {
            height: 100%;
            border-radius: 999px;
            background: var(--wc-gold-gradient);
        }

        .wc-winner-card {
            margin-top: 1.1rem;
        }

        .wc-winner-row {
            display: grid;
            grid-template-columns: minmax(12rem, 1.2fr) minmax(0, 2fr) 4rem;
            gap: 0.8rem;
            align-items: center;
            padding: 0.55rem 0;
            border-top: 1px solid rgba(7,16,20,0.07);
        }

        .wc-winner-team {
            color: var(--wc-ink);
            font-weight: 950;
            overflow-wrap: anywhere;
        }

        .wc-winner-pct {
            color: var(--wc-forest);
            font-weight: 1000;
            text-align: right;
        }

        .wc-sample-row {
            display: grid;
            grid-template-columns: auto minmax(0, 1fr) auto auto;
            gap: 0.55rem;
            align-items: center;
            padding: 0.46rem 0;
            border-top: 1px solid rgba(7, 16, 20, 0.08);
        }

        .wc-bracket-card {
            position: relative;
            overflow: hidden;
            background:
                linear-gradient(180deg, rgba(255,253,247,0.97), rgba(255,253,247,0.91));
            border: 1px solid rgba(7,16,20,0.13);
            border-radius: 8px;
            padding: 1rem 0.85rem 0.85rem 0.85rem;
            margin-bottom: 0.75rem;
            box-shadow: 0 14px 38px rgba(7, 16, 20, 0.08);
        }

        .wc-bracket-card::before {
            content: "";
            position: absolute;
            inset: 0 0 auto 0;
            height: 0.35rem;
            background: linear-gradient(90deg, var(--wc-plum), var(--wc-black), var(--wc-forest), var(--wc-gold), var(--wc-blue));
        }

        .wc-match-id {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 0.5rem;
            color: var(--wc-muted);
            font-size: 0.76rem;
            font-weight: 900;
            text-transform: uppercase;
        }

        .wc-scoreline {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.65rem;
            margin-top: 0.55rem;
            font-weight: 900;
        }

        .wc-score {
            border-radius: 8px;
            padding: 0.28rem 0.6rem;
            background: var(--wc-header-gradient);
            color: var(--wc-gold);
            font-weight: 1000;
            white-space: nowrap;
        }

        .wc-winner {
            color: var(--wc-forest);
        }

        .wc-pens {
            border-radius: 999px;
            padding: 0.1rem 0.45rem;
            background: var(--wc-gold);
            color: var(--wc-black);
            font-size: 0.68rem;
            font-weight: 1000;
        }

        .wc-empty {
            border: 1px dashed rgba(7,16,20,0.22);
            border-radius: 8px;
            padding: 1rem;
            background: rgba(255,253,247,0.74);
            color: var(--wc-muted);
        }

        @media (max-width: 1100px) {
            .wc-control-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 760px) {
            .block-container {
                padding: 0.75rem 0.7rem 2rem 0.7rem;
            }

            div[data-testid="stVerticalBlock"] {
                gap: 0.55rem !important;
            }

            h3 {
                font-size: 1.08rem;
                margin-bottom: 0.55rem;
            }

            div[data-testid="stTabs"] [role="tablist"] {
                display: flex;
                gap: 0.35rem;
                overflow-x: auto;
                overflow-y: hidden;
                flex-wrap: nowrap;
                padding-bottom: 0.35rem;
                scrollbar-width: none;
            }

            div[data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar {
                display: none;
            }

            div[data-testid="stTabs"] button[role="tab"] {
                flex: 0 0 auto;
                min-height: 2.35rem;
                padding: 0.3rem 0.68rem;
                margin-right: 0;
                font-size: 0.86rem;
            }

            div[data-testid="stTabs"] [data-baseweb="tab-border"] {
                display: none;
            }

            div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap;
                gap: 0.65rem !important;
            }

            div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                flex: 1 1 100% !important;
                width: 100% !important;
                min-width: 100% !important;
            }

            .wc-header-shell {
                margin-bottom: 0.9rem;
            }

            .wc-header-image {
                height: 8.8rem !important;
                object-fit: cover !important;
                object-position: 28% center !important;
                border-radius: 12px;
                box-shadow: 0 14px 36px rgba(7, 16, 20, 0.22);
            }

            div[data-testid="stSlider"] {
                padding-bottom: 0.25rem;
            }

            div[data-testid="stSlider"] label,
            div[data-testid="stRadio"] label {
                min-height: 1.55rem;
            }

            div[data-testid="stSlider"] [data-baseweb="slider"] {
                min-height: 2.35rem;
                padding-top: 0 !important;
                padding-bottom: 0 !important;
            }

            div[data-testid="stSlider"] [role="slider"] {
                width: 1.05rem !important;
                height: 1.05rem !important;
            }

            div[data-testid="stRadio"] [role="radiogroup"] {
                transform: none;
                gap: 0.4rem;
                align-items: stretch;
                flex-wrap: wrap;
                padding-top: 0.35rem;
            }

            div[data-testid="stRadio"] [role="radio"] {
                min-height: 2.35rem;
                padding: 0.35rem 0.72rem;
            }

            .stButton > button {
                width: 100%;
                min-height: 3.1rem;
            }

            .wc-control-grid {
                grid-template-columns: 1fr;
                gap: 0.55rem;
            }

            .wc-control-tile {
                padding: 0.72rem 0.8rem;
            }

            .wc-control-value {
                font-size: 1.32rem;
            }

            .wc-card {
                padding: 0.82rem;
                margin-bottom: 0.78rem;
                box-shadow: 0 10px 26px rgba(7, 16, 20, 0.08);
            }

            .wc-card-title {
                font-size: 0.96rem;
                gap: 0.5rem;
                margin-bottom: 0.7rem;
            }

            .wc-team-row {
                grid-template-columns: minmax(0, 1fr) auto;
                row-gap: 0.22rem;
                padding: 0.42rem 0;
            }

            .wc-team-main {
                font-size: 0.88rem;
            }

            .wc-team-meta {
                font-size: 0.72rem;
            }

            .wc-rank-chip {
                min-width: 2.25rem;
                font-size: 0.7rem;
            }

            .wc-result-card {
                min-height: 0;
            }

            .wc-prob-row {
                grid-template-columns: 2.7rem minmax(0, 1fr) 3.1rem;
                gap: 0.42rem;
                font-size: 0.72rem;
                padding: 0.34rem 0;
            }

            .wc-prob-track,
            .wc-winner-track {
                height: 0.4rem;
            }

            .wc-winner-row {
                grid-template-columns: minmax(0, 1fr) auto;
                gap: 0.38rem 0.65rem;
                padding: 0.5rem 0;
            }

            .wc-winner-track {
                grid-column: 1 / -1;
                grid-row: 2;
            }

            .wc-winner-team {
                font-size: 0.86rem;
            }

            .wc-winner-pct {
                font-size: 0.82rem;
            }

            .wc-sample-row {
                grid-template-columns: auto minmax(0, 1fr) auto;
                gap: 0.42rem;
            }

            .wc-sample-row .wc-team-meta:last-child {
                grid-column: 2 / -1;
                justify-self: start;
            }

            .wc-bracket-card {
                padding: 0.95rem 0.75rem 0.75rem 0.75rem;
            }

            .wc-scoreline {
                display: grid;
                grid-template-columns: minmax(0, 1fr) auto;
                gap: 0.35rem 0.55rem;
                align-items: center;
                justify-content: start;
            }

            .wc-scoreline span:not(.wc-score) {
                overflow-wrap: anywhere;
                min-width: 0;
            }

            .wc-scoreline span:nth-child(3) {
                grid-column: 1 / -1;
            }

            .wc-score {
                padding: 0.22rem 0.5rem;
                font-size: 0.86rem;
            }
        }

        @media (max-width: 480px) {
            .block-container {
                padding-left: 0.55rem;
                padding-right: 0.55rem;
            }

            .wc-header-image {
                height: 7.6rem !important;
                object-position: 18% center !important;
            }

            div[data-testid="stTabs"] button[role="tab"] {
                min-height: 2.2rem;
                padding: 0.25rem 0.58rem;
                font-size: 0.8rem;
            }

            .wc-card {
                padding: 0.72rem;
            }

            .wc-card-title {
                align-items: flex-start;
                flex-direction: column;
            }

            .wc-prob-row {
                grid-template-columns: 2.35rem minmax(0, 1fr) 2.75rem;
                gap: 0.32rem;
                font-size: 0.68rem;
            }

            .wc-scoreline {
                grid-template-columns: 1fr;
            }

            .wc-scoreline span:nth-child(3) {
                grid-column: auto;
            }

            .wc-score {
                justify-self: start;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
