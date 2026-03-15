"""Pagina de momentum de IPCA+ consolidado."""

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.mock_debentures import (
    get_debentures,
    get_consolidated_spread_history,
    calculate_momentum,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown('<p class="page-title">Momentum</p>', unsafe_allow_html=True)
st.markdown('<p class="page-subtitle">IPCA+ fechando (taxa caindo) = compra &nbsp;&bull;&nbsp; IPCA+ abrindo (taxa subindo) = venda</p>', unsafe_allow_html=True)

st.warning(
    "Dados ilustrativos para demonstracao — estrutura preparada para conexao com API real.",
    icon="⚠️",
)

# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------

df_all = get_debentures()

with st.expander("Filtros", expanded=True):
    row1 = st.columns(4)
    with row1[0]:
        setores_sel = st.multiselect(
            "Setor", options=sorted(df_all["setor"].unique()), default=[],
            key="mom_setor",
        )
    with row1[1]:
        emissores_sel = st.multiselect(
            "Emissor", options=sorted(df_all["emissor"].unique()), default=[],
            key="mom_emissor",
        )
    with row1[2]:
        ratings_sel = st.multiselect(
            "Rating", options=sorted(df_all["rating"].unique()), default=[],
            key="mom_rating",
        )
    with row1[3]:
        tickers_sel = st.multiselect(
            "Ativo", options=sorted(df_all["ticker"].unique()), default=[],
            key="mom_ticker",
        )

    row2 = st.columns(2)
    with row2[0]:
        dur_range = st.slider(
            "Duration (anos)",
            min_value=float(df_all["duration"].min()),
            max_value=float(df_all["duration"].max()),
            value=(float(df_all["duration"].min()), float(df_all["duration"].max())),
            step=0.5,
        )
    with row2[1]:
        date_range = st.date_input(
            "Periodo",
            value=(date.today() - timedelta(days=365), date.today()),
            min_value=date.today() - timedelta(days=365 * 5),
            max_value=date.today(),
            format="DD/MM/YYYY",
        )

# ---------------------------------------------------------------------------
# Historico consolidado
# ---------------------------------------------------------------------------

hist = get_consolidated_spread_history(
    setores=setores_sel or None,
    emissores=emissores_sel or None,
    ratings=ratings_sel or None,
    tickers=tickers_sel or None,
    dur_min=dur_range[0],
    dur_max=dur_range[1],
)

if hist.empty:
    st.info("Nenhum dado encontrado com os filtros selecionados.")
    st.stop()

if isinstance(date_range, tuple) and len(date_range) == 2:
    d_start, d_end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    hist = hist[(hist["data"] >= d_start) & (hist["data"] <= d_end)]

if hist.empty or len(hist) < 80:
    st.info("Periodo insuficiente para calculo de momentum (minimo ~4 meses).")
    st.stop()

# ---------------------------------------------------------------------------
# Momentum
# ---------------------------------------------------------------------------

momentum = calculate_momentum(hist["ipca_plus"])
score = momentum["score"]
sinal = momentum["sinal"]

# ---------------------------------------------------------------------------
# Score central + Componentes
# ---------------------------------------------------------------------------

col_score, col_t, col_v, col_a = st.columns([1.5, 1, 1, 1])

with col_score:
    if sinal == "COMPRA":
        color = "#16a34a"
        label = "COMPRA"
    elif sinal == "VENDA":
        color = "#dc2626"
        label = "VENDA"
    else:
        color = "#d97706"
        label = "NEUTRO"

    st.markdown(
        f'<div style="text-align:center; padding:16px 0;">'
        f'<div style="font-size:11px; color:#6b7f94; text-transform:uppercase; letter-spacing:0.1em;">Momentum Score</div>'
        f'<div style="font-size:48px; font-weight:700; color:{color}; line-height:1.1;">{score:+.0f}</div>'
        f'<div style="font-size:14px; font-weight:600; color:{color}; letter-spacing:0.05em;">{label}</div>'
        f'<div style="font-size:10px; color:#8a9ab0; margin-top:4px;">-100 venda &nbsp;&bull;&nbsp; +100 compra</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with col_t:
    st.metric(
        "Tendencia", f"{momentum['tendencia']:+.1f}",
        help="SMA 9d vs SMA 20d. Positivo = IPCA+ em queda. Peso: 45%.",
    )
with col_v:
    st.metric(
        "Velocidade", f"{momentum['velocidade']:+.1f}",
        help="Variacao do IPCA+ em 20d. Queda = positivo. Peso: 35%.",
    )
with col_a:
    st.metric(
        "Aceleracao", f"{momentum['aceleracao']:+.1f}",
        help="Mudanca na velocidade vs 20d atras. Peso: 20%.",
    )

# ---------------------------------------------------------------------------
# Grafico historico com SMAs
# ---------------------------------------------------------------------------

fig_hist = go.Figure()
fig_hist.add_trace(go.Scatter(
    x=hist["data"], y=hist["ipca_plus"], mode="lines", name="IPCA+ Medio",
    line=dict(color="#3a7fc1", width=1.5),
    hovertemplate="Data: %{x|%d/%m/%Y}<br>IPCA+: %{y:.2f}%<extra></extra>",
))

vals = hist["ipca_plus"]
if len(vals) >= 9:
    fig_hist.add_trace(go.Scatter(
        x=hist["data"], y=vals.rolling(9).mean(), mode="lines", name="SMA 9d",
        line=dict(color="#16a34a", width=1.2, dash="dash"),
        hovertemplate="SMA 9: %{y:.2f}%<extra></extra>",
    ))
if len(vals) >= 20:
    fig_hist.add_trace(go.Scatter(
        x=hist["data"], y=vals.rolling(20).mean(), mode="lines", name="SMA 20d",
        line=dict(color="#dc2626", width=1.2, dash="dot"),
        hovertemplate="SMA 20: %{y:.2f}%<extra></extra>",
    ))

fig_hist.update_layout(
    plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
    font=dict(color="#4a6a88", family="system-ui, -apple-system, sans-serif"),
    xaxis=dict(title="", gridcolor="#e8eef5"),
    yaxis=dict(title="IPCA+ (%)", gridcolor="#e8eef5", ticksuffix="%"),
    legend=dict(
        bgcolor="#ffffff", bordercolor="#e4eaf0", borderwidth=1, font=dict(color="#4a6a88"),
        orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
    ),
    height=400, margin=dict(l=50, r=20, t=10, b=40),
)
st.plotly_chart(fig_hist, use_container_width=True)
