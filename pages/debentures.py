"""Pagina de analise de debentures incentivadas (IPCA+)."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.mock_debentures import get_debentures, get_spread_history, get_emissor_debentures

# ---------------------------------------------------------------------------
# Cores por setor
# ---------------------------------------------------------------------------

SETOR_COLORS = {
    "Energia Eletrica": "#3a7fc1", "Transmissao": "#1a6aae", "Rodovias": "#ff8c42",
    "Saneamento": "#2ecc71", "Portos": "#8e44ad", "Telecom": "#e74c3c",
    "Petroquimico": "#f39c12", "Siderurgia": "#95a5a6", "Papel e Celulose": "#27ae60",
    "Mineracao": "#d35400", "Oleo e Gas": "#2c3e50", "Holding": "#7f8c8d",
    "Financeiro": "#1abc9c",
}

RATING_ORDER = ["AAA", "AA+", "AA", "AA-", "A+"]

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown('<p class="page-title">Debentures Incentivadas</p>', unsafe_allow_html=True)
st.markdown('<p class="page-subtitle">Taxas IPCA+, duration e valor relativo</p>', unsafe_allow_html=True)

st.warning(
    "Dados ilustrativos para demonstracao — estrutura preparada para conexao com API real.",
    icon="⚠️",
)

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

df_all = get_debentures()

# ---------------------------------------------------------------------------
# Graficos: Scatter + Heatmap (TOPO)
# ---------------------------------------------------------------------------

col_scatter, col_heat = st.columns(2)

with col_scatter:
    fig_scatter = go.Figure()
    for setor in sorted(df_all["setor"].unique()):
        mask = df_all["setor"] == setor
        fig_scatter.add_trace(go.Scatter(
            x=df_all.loc[mask, "duration"], y=df_all.loc[mask, "ipca_plus"],
            mode="markers", name=setor,
            marker=dict(color=SETOR_COLORS.get(setor, "#7a8a9a"), size=7, line=dict(color="#ffffff", width=0.5)),
            text=df_all.loc[mask, "ticker"],
            hovertemplate="%{text}<br>Duration: %{x:.1f}<br>IPCA+: %{y:.2f}%<extra></extra>",
        ))

    if len(df_all) >= 2:
        coeffs = np.polyfit(df_all["duration"].values, df_all["ipca_plus"].values, 1)
        x_reg = np.linspace(df_all["duration"].min() * 0.9, df_all["duration"].max() * 1.1, 50)
        fig_scatter.add_trace(go.Scatter(
            x=x_reg, y=np.polyval(coeffs, x_reg), mode="lines", name="Regressao",
            line=dict(color="#1a3a6e", width=2, dash="dash"), hoverinfo="skip",
        ))

    fig_scatter.update_layout(
        title=dict(text="IPCA+ vs Duration", font=dict(color="#1a3a6e", size=14)),
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(color="#4a6a88", family="system-ui, -apple-system, sans-serif", size=11),
        xaxis=dict(title="Duration (anos)", gridcolor="#e8eef5"),
        yaxis=dict(title="IPCA+ (%)", gridcolor="#e8eef5", ticksuffix="%"),
        legend=dict(bgcolor="#ffffff", bordercolor="#e4eaf0", borderwidth=1, font=dict(size=9)),
        height=380, margin=dict(l=50, r=10, t=35, b=40),
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

with col_heat:
    # Heatmap: Setor x Rating — IPCA+ medio
    pivot = df_all.pivot_table(values="ipca_plus", index="setor", columns="rating", aggfunc="mean")
    # Reorder columns by rating quality
    ordered_cols = [r for r in RATING_ORDER if r in pivot.columns]
    pivot = pivot[ordered_cols]
    pivot = pivot.sort_index()

    # Annotations (values in cells)
    annotations = []
    for i, setor in enumerate(pivot.index):
        for j, rating in enumerate(pivot.columns):
            val = pivot.loc[setor, rating]
            if pd.notna(val):
                annotations.append(dict(
                    x=rating, y=setor, text=f"{val:.1f}",
                    font=dict(size=10, color="#1a3a6e"),
                    showarrow=False,
                ))

    fig_heat = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=[[0, "#e8f5e9"], [0.5, "#fff8e1"], [1, "#fce4e4"]],
        hovertemplate="Setor: %{y}<br>Rating: %{x}<br>IPCA+ medio: %{z:.2f}%<extra></extra>",
        showscale=False,
    ))
    fig_heat.update_layout(
        title=dict(text="IPCA+ medio: Setor x Rating", font=dict(color="#1a3a6e", size=14)),
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(color="#4a6a88", family="system-ui, -apple-system, sans-serif", size=11),
        xaxis=dict(title="", side="top"),
        yaxis=dict(title="", autorange="reversed"),
        annotations=annotations,
        height=380, margin=dict(l=120, r=10, t=55, b=10),
    )
    st.plotly_chart(fig_heat, use_container_width=True)

# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    setores_sel = st.multiselect("Setor", options=sorted(df_all["setor"].unique()), default=[])
with col_f2:
    emissores_sel = st.multiselect("Emissor", options=sorted(df_all["emissor"].unique()), default=[])
with col_f3:
    ratings_sel = st.multiselect("Rating", options=sorted(df_all["rating"].unique()), default=[])

df = df_all.copy()
if setores_sel:
    df = df[df["setor"].isin(setores_sel)]
if emissores_sel:
    df = df[df["emissor"].isin(emissores_sel)]
if ratings_sel:
    df = df[df["rating"].isin(ratings_sel)]

if df.empty:
    st.info("Nenhuma debenture encontrada com os filtros selecionados.")
    st.stop()

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------

kpi1, kpi2, kpi3 = st.columns(3)
with kpi1:
    st.metric("Total", len(df), help="Debentures no universo filtrado.")
with kpi2:
    st.metric("Atrativos (z < 0)", len(df[df["z_score"] < 0]),
              help="Taxa acima da media historica = maior rentabilidade relativa.")
with kpi3:
    st.metric("IPCA+ Medio", f"{df['ipca_plus'].mean():.2f}%",
              help="Media das taxas IPCA+ filtradas.")

# ---------------------------------------------------------------------------
# Tabela
# ---------------------------------------------------------------------------

st.caption("Selecione uma debenture para detalhes")

display_df = df[["ticker", "emissor", "setor", "rating",
                  "duration", "ipca_plus", "cdi_plus", "delta_med_bps", "z_score"]].copy()
display_df.columns = ["TICKER", "EMISSOR", "SETOR", "RATING", "DURATION", "IPCA+", "CDI+", "Δ MED (bps)", "Z-SCORE"]

event = st.dataframe(
    display_df, use_container_width=True, hide_index=True,
    on_select="rerun", selection_mode="single-row",
    column_config={
        "DURATION": st.column_config.NumberColumn(format="%.1f", help="Duration modificada (anos)."),
        "IPCA+": st.column_config.NumberColumn(format="%.2f%%", help="Taxa real acima do IPCA."),
        "CDI+": st.column_config.NumberColumn(format="%.2f%%", help="Spread equivalente sobre CDI (tipicamente negativo para incentivadas)."),
        "Δ MED (bps)": st.column_config.NumberColumn(format="%+d", help="Positivo = taxa acima da mediana (barato). Negativo = abaixo (caro)."),
        "Z-SCORE": st.column_config.NumberColumn(format="%.2f", help="Negativo = taxa acima da media (barato). Positivo = abaixo (caro)."),
    },
)

# ---------------------------------------------------------------------------
# Detalhe da deb selecionada
# ---------------------------------------------------------------------------

selected_rows = event.selection.rows if event.selection else []
if not selected_rows:
    selected_rows = [0]

idx = selected_rows[0]
selected = df.iloc[idx]
ticker = selected["ticker"]
emissor = selected["emissor"]
setor = selected["setor"]

st.markdown("---")

hist = get_spread_history(ticker)
if not hist.empty:
    taxa_atual = hist["ipca_plus"].iloc[-1]
    mediana = hist["ipca_plus"].median()
    z = selected["z_score"]

    fig_hist = go.Figure()
    fig_hist.add_trace(go.Scatter(
        x=hist["data"], y=hist["ipca_plus"], mode="lines", name="IPCA+",
        line=dict(color="#3a7fc1", width=2),
        hovertemplate="Data: %{x|%d/%m/%Y}<br>IPCA+: %{y:.2f}%<extra></extra>",
    ))
    fig_hist.add_hline(y=mediana, line_dash="dash", line_color="#ff8c42",
                        annotation_text=f"Mediana: {mediana:.2f}%", annotation_position="top right")
    fig_hist.update_layout(
        title=dict(text=f"Historico IPCA+ — {ticker}", font=dict(color="#1a3a6e", size=14)),
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(color="#4a6a88", family="system-ui, -apple-system, sans-serif"),
        xaxis=dict(title="", gridcolor="#e8eef5"),
        yaxis=dict(title="IPCA+ (%)", gridcolor="#e8eef5", ticksuffix="%"),
        height=350, margin=dict(l=50, r=20, t=35, b=40), showlegend=False,
    )
    st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown(
        f'<p class="source-label">'
        f"Setor: {setor} &nbsp;&bull;&nbsp; "
        f"IPCA+: {taxa_atual:.2f}% &nbsp;&bull;&nbsp; "
        f"Mediana 5a: {mediana:.2f}% &nbsp;&bull;&nbsp; "
        f"Z-Score: {z:+.2f}</p>",
        unsafe_allow_html=True,
    )

emissor_debs = get_emissor_debentures(emissor)
if len(emissor_debs) > 1:
    st.markdown(f"### Curva do Emissor — {emissor}")
    fig_e = go.Figure()
    other = emissor_debs[emissor_debs["ticker"] != ticker]
    fig_e.add_trace(go.Scatter(
        x=other["duration"], y=other["ipca_plus"], mode="markers+text", name="Outras",
        marker=dict(color="#7a8a9a", size=10, line=dict(color="#ffffff", width=1)),
        text=other["ticker"], textposition="top center", textfont=dict(size=9, color="#4a6a88"),
        hovertemplate="%{text}<br>Dur: %{x:.1f}<br>IPCA+: %{y:.2f}%<extra></extra>",
    ))
    sel_r = emissor_debs[emissor_debs["ticker"] == ticker]
    fig_e.add_trace(go.Scatter(
        x=sel_r["duration"], y=sel_r["ipca_plus"], mode="markers+text", name=ticker,
        marker=dict(color="#e74c3c", size=14, line=dict(color="#ffffff", width=2)),
        text=[ticker], textposition="top center", textfont=dict(size=10, color="#e74c3c"),
        hovertemplate="%{text}<br>Dur: %{x:.1f}<br>IPCA+: %{y:.2f}%<extra></extra>",
    ))
    xv, yv = emissor_debs["duration"].values, emissor_debs["ipca_plus"].values
    if len(xv) >= 2:
        c = np.polyfit(xv, yv, 1)
        xl = np.linspace(xv.min() * 0.9, xv.max() * 1.1, 50)
        fig_e.add_trace(go.Scatter(x=xl, y=np.polyval(c, xl), mode="lines", name="Regressao",
                                    line=dict(color="#3a7fc1", width=2, dash="dash"), hoverinfo="skip"))
    fig_e.update_layout(
        title=dict(text=f"IPCA+ vs Duration — {emissor}", font=dict(color="#1a3a6e", size=14)),
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(color="#4a6a88", family="system-ui, -apple-system, sans-serif"),
        xaxis=dict(title="Duration (anos)", gridcolor="#e8eef5"),
        yaxis=dict(title="IPCA+ (%)", gridcolor="#e8eef5", ticksuffix="%"),
        legend=dict(bgcolor="#ffffff", bordercolor="#e4eaf0", borderwidth=1, font=dict(color="#4a6a88")),
        height=350, margin=dict(l=50, r=20, t=35, b=40),
    )
    st.plotly_chart(fig_e, use_container_width=True)
