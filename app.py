"""Entry point — Analise de Renda Fixa."""

import streamlit as st

st.set_page_config(
    page_title="Analise de Renda Fixa",
    page_icon=":material/show_chart:",
    layout="wide",
)

# ---------------------------------------------------------------------------
# CSS global — minimalista, fundo branco, dados como protagonista
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    /* Hide Streamlit chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {visibility: hidden; height: 0;}
    .block-container {padding-top: 0rem; padding-bottom: 0rem; max-width: 100%;}
    [data-testid="stSidebar"] {display: none;}
    [data-testid="stSidebarCollapsedControl"] {display: none;}

    /* Base — fundo branco limpo */
    .stApp {background-color: #ffffff; color: #2a3a4a; font-weight: 400;}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {gap: 6px;}
    .stTabs [data-baseweb="tab"] {
        background: transparent; border: 1px solid #d0dbe8; border-radius: 6px;
        color: #4a6a88; padding: 8px 20px; font-weight: 500; letter-spacing: 0.04em;
    }
    .stTabs [aria-selected="true"] {
        background: #f0f5fa; color: #1a3a6e; border-color: #3a7fc1; font-weight: 600;
    }

    /* Metric cards — sutil */
    .stMetric {
        background: #fafbfc; border: 1px solid #e4eaf0; border-radius: 8px; padding: 14px;
    }
    .stMetric label {color: #6b7f94 !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: 0.05em;}
    .stMetric [data-testid="stMetricValue"] {color: #1a3a6e !important; font-weight: 600;}

    /* Tables */
    .stDataFrame {background: #ffffff;}

    /* Headings */
    h1, h2, h3 {color: #1a3a6e !important;}

    /* Page title — inline, limpo */
    .page-title {
        font-size: 20px; font-weight: 700; color: #1a3a6e;
        letter-spacing: 0.03em; margin: 0 0 4px 0; padding: 0;
    }
    .page-subtitle {
        font-size: 12px; color: #6b7f94; margin: 0 0 12px 0;
    }
    .source-label {font-size: 10px; color: #6b7f94; font-family: monospace;}
    .demo-notice {font-size: 11px; color: #8a9ab0; font-style: italic; margin-bottom: 12px;}

    /* Navigation bar — fundo limpo, botoes outline */
    .st-key-navbar {
        background: #ffffff;
        padding: 8px 24px 8px 24px;
        margin: 0 -1rem 0.8rem -1rem;
        border-bottom: 1px solid #e4eaf0;
    }
    .st-key-navbar [data-testid="stPageLink-NavLink"] {
        background: transparent;
        border: 1.5px solid #3a7fc1;
        border-radius: 6px;
        padding: 7px 18px;
        color: #3a7fc1 !important;
        font-weight: 600; font-size: 13px; letter-spacing: 0.03em;
        text-decoration: none !important;
        transition: all 0.2s ease;
    }
    .st-key-navbar [data-testid="stPageLink-NavLink"] span {
        color: #3a7fc1 !important;
    }
    .st-key-navbar [data-testid="stPageLink-NavLink"]:hover {
        background: #f0f5fa;
        border-color: #1a6aae;
    }
    .st-key-navbar [data-testid="stPageLink-NavLink"][aria-current="page"] {
        background: #1a6aae;
        color: #ffffff !important;
        border-color: #1a6aae;
    }
    .st-key-navbar [data-testid="stPageLink-NavLink"][aria-current="page"] span {
        color: #ffffff !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

PAGE_MAP = {
    "Curvas de Juros": "pages/curvas.py",
    "Debentures": "pages/debentures.py",
    "Negocios": "pages/movimentacoes.py",
    "Momentum": "pages/momentum.py",
    "Swap IPCA→CDI": "pages/swap.py",
}

pages = {label: st.Page(path, title=label) for label, path in PAGE_MAP.items()}
pg = st.navigation(list(pages.values()), position="hidden")

with st.container(key="navbar"):
    cols = st.columns([1, 1, 1, 1, 1, 1.5])
    with cols[0]:
        st.page_link("pages/curvas.py", label="Curvas", icon=":material/show_chart:", use_container_width=True)
    with cols[1]:
        st.page_link("pages/debentures.py", label="Debentures", icon=":material/account_balance:", use_container_width=True)
    with cols[2]:
        st.page_link("pages/movimentacoes.py", label="Negocios", icon=":material/receipt_long:", use_container_width=True)
    with cols[3]:
        st.page_link("pages/momentum.py", label="Momentum", icon=":material/speed:", use_container_width=True)
    with cols[4]:
        st.page_link("pages/swap.py", label="Swap", icon=":material/swap_horiz:", use_container_width=True)

pg.run()
