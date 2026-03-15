"""Pagina de analise de curvas de juros interpoladas."""

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.data_fetcher import fetch_curve, fetch_multiple_dates, HISTORICAL_OFFSETS
from src.interpolation import (
    flat_forward_interpolate,
    generate_interpolated_curve,
    calculate_implied_inflation,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown('<p class="page-title">Curvas de Juros</p>', unsafe_allow_html=True)
st.markdown('<p class="page-subtitle">Estrutura a termo — Interpolacao flat forward</p>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Curve colors & config — adjusted for light background contrast
# ---------------------------------------------------------------------------

CURVE_COLORS = {
    "Atual": {"color": "#3a7fc1", "dash": "solid", "width": 3},
    "D-1": {"color": "#5aa3e8", "dash": "dash", "width": 2},
    "D-7": {"color": "#1a6aae", "dash": "dash", "width": 1.5},
    "D-14": {"color": "#2a7ab5", "dash": "dash", "width": 1.5},
    "D-30": {"color": "#ff8c42", "dash": "dash", "width": 1.5},
    "3M": {"color": "#7a8a9a", "dash": "dot", "width": 1.5},
    "6M": {"color": "#5a6a7a", "dash": "dot", "width": 1.5},
    "1A": {"color": "#3a4a5a", "dash": "dot", "width": 1.5},
}

CURVE_TYPES = {
    "Prefixada": {"fetch_tipo": "PRE", "label": "Taxa Prefixada (DI Pre)", "suffix": "% a.a."},
    "IPCA+": {"fetch_tipo": "IPCA", "label": "Taxa Real (IPCA+)", "suffix": "% a.a."},
    "Inflacao Implicita": {"fetch_tipo": "IMPLICITA", "label": "Inflacao Implicita", "suffix": "% a.a."},
}

# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------

col_date, col_periods = st.columns([1, 3])

with col_date:
    ref_date = st.date_input(
        "Data de referencia",
        value=date.today() - timedelta(days=1),
        max_value=date.today(),
        format="DD/MM/YYYY",
    )

with col_periods:
    st.markdown("**Periodos de comparacao**")
    period_cols = st.columns(7)
    selected_periods = []
    defaults = {"D-1": True, "D-7": True, "D-14": False, "D-30": True, "3M": False, "6M": False, "1A": False}
    for i, (label, default) in enumerate(defaults.items()):
        with period_cols[i]:
            if st.checkbox(label, value=default, key=f"period_{label}"):
                selected_periods.append(label)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_pre, tab_ipca, tab_impl = st.tabs([":material/bar_chart: Prefixada", ":material/show_chart: IPCA+", ":material/trending_down: Inflacao Implicita"])


def _format_br(x, decimals=2):
    """Format number in Brazilian notation: 1.234,56"""
    if pd.isna(x):
        return "—"
    formatted = f"{x:,.{decimals}f}"
    return formatted.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def render_curve_tab(curve_key: str, container):
    """Render a full curve analysis tab."""
    config = CURVE_TYPES[curve_key]

    with container:
        # Data availability notice
        for tipo in ("PRE", "IPCA"):
            data_real = st.session_state.get(f"data_real_{tipo}_{ref_date}")
            is_fallback = st.session_state.get(f"fallback_{tipo}_{ref_date}")
            if is_fallback:
                st.info(
                    f"Dados ({tipo}) indisponiveis para {ref_date.strftime('%d/%m/%Y')}. "
                    "Usando dados de referencia (13/Mar/2026)."
                )
            elif data_real and data_real != ref_date:
                st.info(
                    f"Dados ({tipo}) indisponiveis para {ref_date.strftime('%d/%m/%Y')}. "
                    f"Usando {data_real.strftime('%d/%m/%Y')} (ultimo dia util com dados)."
                )

        with st.spinner(f"Buscando dados da curva {curve_key}..."):
            # Fetch current curve
            if config["fetch_tipo"] == "IMPLICITA":
                vertices_pre = fetch_curve("PRE", ref_date)
                vertices_ipca = fetch_curve("IPCA", ref_date)
                curve_pre_interp = generate_interpolated_curve(vertices_pre, n_points=120)
                curve_ipca_interp = generate_interpolated_curve(vertices_ipca, n_points=120)
                curve_atual = calculate_implied_inflation(curve_pre_interp, curve_ipca_interp)
            else:
                vertices_atual = fetch_curve(config["fetch_tipo"], ref_date)
                curve_atual = generate_interpolated_curve(vertices_atual, n_points=120)

            # Fetch historical curves
            hist_curves = {}
            if selected_periods:
                if config["fetch_tipo"] == "IMPLICITA":
                    hist_pre = fetch_multiple_dates("PRE", ref_date, selected_periods)
                    hist_ipca = fetch_multiple_dates("IPCA", ref_date, selected_periods)
                    for period in selected_periods:
                        if period in hist_pre and period in hist_ipca:
                            c_pre = generate_interpolated_curve(hist_pre[period], n_points=120)
                            c_ipca = generate_interpolated_curve(hist_ipca[period], n_points=120)
                            hist_curves[period] = calculate_implied_inflation(c_pre, c_ipca)
                else:
                    hist_raw = fetch_multiple_dates(config["fetch_tipo"], ref_date, selected_periods)
                    for period, verts in hist_raw.items():
                        hist_curves[period] = generate_interpolated_curve(verts, n_points=120)

        if curve_atual.empty:
            st.warning("Nao foi possivel carregar dados para esta curva.")
            return

        # ----- Metric cards -----
        mc1, mc2, mc3, mc4 = st.columns(4)

        taxa_curta = curve_atual["taxa"].iloc[0]
        taxa_longa = curve_atual["taxa"].iloc[-1]
        slope = taxa_longa - taxa_curta

        # Delta vs D-1 (robust)
        delta_d1 = None
        try:
            if "D-1" in hist_curves and not hist_curves["D-1"].empty:
                mean_atual = curve_atual["taxa"].mean()
                mean_d1 = hist_curves["D-1"]["taxa"].mean()
                delta_d1 = round((mean_atual - mean_d1) * 100, 1)
        except (KeyError, TypeError):
            delta_d1 = None

        with mc1:
            st.metric("Taxa Curta", f"{taxa_curta:.2f}%")
        with mc2:
            st.metric("Taxa Longa", f"{taxa_longa:.2f}%")
        with mc3:
            st.metric("Slope", f"{slope:+.2f}%")
        with mc4:
            if delta_d1 is not None:
                st.metric("Δ vs D-1", f"{delta_d1:+.1f} bps")
            else:
                st.metric("Δ vs D-1", "—")

        # ----- Chart -----
        fig = go.Figure()

        # Historical curves first (behind)
        for period in reversed(selected_periods):
            if period in hist_curves and not hist_curves[period].empty:
                style = CURVE_COLORS.get(period, CURVE_COLORS["D-1"])
                df_hist = hist_curves[period]
                fig.add_trace(go.Scatter(
                    x=df_hist["anos"],
                    y=df_hist["taxa"],
                    mode="lines",
                    name=period,
                    line=dict(
                        color=style["color"],
                        dash=style["dash"],
                        width=style["width"],
                    ),
                    hovertemplate=f"{period}: %{{y:.2f}}%<br>Duration: %{{x:.1f}} anos<extra></extra>",
                ))

        # Current curve (on top)
        style_atual = CURVE_COLORS["Atual"]
        fig.add_trace(go.Scatter(
            x=curve_atual["anos"],
            y=curve_atual["taxa"],
            mode="lines",
            name=f"Atual ({ref_date.strftime('%d/%m/%Y')})",
            line=dict(
                color=style_atual["color"],
                dash=style_atual["dash"],
                width=style_atual["width"],
            ),
            hovertemplate="Atual: %{y:.2f}%<br>Duration: %{x:.1f} anos<extra></extra>",
        ))

        # Add vertex markers for current curve (original vertices)
        if config["fetch_tipo"] == "IMPLICITA":
            ipca_vertices_list = list(zip(
                [int(r) for r in curve_ipca_interp["du"]] if not curve_ipca_interp.empty else [],
                curve_ipca_interp["taxa"].tolist() if not curve_ipca_interp.empty else [],
            ))
            marker_data = []
            for du, _ in vertices_ipca:
                du_min_impl = curve_atual["du"].min() if not curve_atual.empty else 0
                du_max_impl = curve_atual["du"].max() if not curve_atual.empty else 0
                if du_min_impl <= du <= du_max_impl:
                    pre_rate = flat_forward_interpolate(
                        list(zip([int(r) for r in curve_pre_interp["du"]], curve_pre_interp["taxa"])),
                        du,
                    )
                    ipca_rate = flat_forward_interpolate(ipca_vertices_list, du)
                    denom = 1 + ipca_rate / 100
                    if abs(denom) > 1e-10:
                        implied = ((1 + pre_rate / 100) / denom - 1) * 100
                        marker_data.append((du / 252, round(implied, 4), du))
            if marker_data:
                fig.add_trace(go.Scatter(
                    x=[m[0] for m in marker_data],
                    y=[m[1] for m in marker_data],
                    mode="markers",
                    name="Vertices",
                    marker=dict(color="#3a7fc1", size=7, line=dict(color="#1a3a6e", width=1.5)),
                    hovertemplate="Vertice: %{y:.2f}%<br>DU: %{customdata}<br>Anos: %{x:.1f}<extra></extra>",
                    customdata=[m[2] for m in marker_data],
                ))
        else:
            marker_anos = [du / 252 for du, _ in vertices_atual]
            marker_taxas = [taxa for _, taxa in vertices_atual]
            fig.add_trace(go.Scatter(
                x=marker_anos,
                y=marker_taxas,
                mode="markers",
                name="Vertices",
                marker=dict(color="#3a7fc1", size=7, line=dict(color="#1a3a6e", width=1.5)),
                hovertemplate="Vertice: %{y:.2f}%<br>DU: %{customdata}<br>Anos: %{x:.1f}<extra></extra>",
                customdata=[du for du, _ in vertices_atual],
            ))

        # Light mode chart layout
        fig.update_layout(
            title=dict(
                text=config["label"],
                font=dict(color="#1a3a6e", size=18),
            ),
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            font=dict(color="#4a6a88", family="system-ui, -apple-system, sans-serif"),
            xaxis=dict(
                title="Duration (anos)",
                gridcolor="#e8eef5",
                zerolinecolor="#8fc4f0",
                tickformat=".1f",
                rangeslider=dict(visible=True, bgcolor="#e8eef5"),
            ),
            yaxis=dict(
                title=f"Taxa ({config['suffix']})",
                gridcolor="#e8eef5",
                zerolinecolor="#8fc4f0",
                tickformat=".2f",
                ticksuffix="%",
            ),
            legend=dict(
                bgcolor="#fafbfc",
                bordercolor="#c8dff5",
                borderwidth=1,
                font=dict(color="#4a6a88"),
            ),
            hovermode="x unified",
            height=500,
            margin=dict(l=60, r=20, t=50, b=40),
        )

        st.plotly_chart(fig, use_container_width=True)

        # ----- Data table -----
        with st.expander("Tabela de vertices interpolados", expanded=False):
            display_df = curve_atual.copy()
            display_df.columns = ["DU", "Anos", "Taxa Atual (%)"]

            if "D-1" in hist_curves and not hist_curves["D-1"].empty:
                d1_df = hist_curves["D-1"]
                merged = pd.merge_asof(
                    display_df.sort_values("DU"),
                    d1_df[["du", "taxa"]].rename(columns={"du": "DU", "taxa": "Taxa D-1 (%)"}),
                    on="DU",
                    direction="nearest",
                )
                merged["Δ (bps)"] = ((merged["Taxa Atual (%)"] - merged["Taxa D-1 (%)"]) * 100).round(1)
                display_df = merged

            for col in display_df.select_dtypes(include="float").columns:
                display_df[col] = display_df[col].apply(
                    lambda x: _format_br(x) if pd.notna(x) else "—"
                )

            st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.markdown(
            '<p class="source-label">Fonte: ANBIMA / B3 / Tesouro Direto &nbsp;|&nbsp; '
            f'Data ref: {ref_date.strftime("%d/%m/%Y")} &nbsp;|&nbsp; '
            "Interpolacao: Flat Forward</p>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Render tabs
# ---------------------------------------------------------------------------

render_curve_tab("Prefixada", tab_pre)
render_curve_tab("IPCA+", tab_ipca)
render_curve_tab("Inflacao Implicita", tab_impl)
