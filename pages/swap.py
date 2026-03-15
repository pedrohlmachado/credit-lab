"""Simulador de Swap IPCA+ → CDI+ via DAP."""

import pandas as pd
import streamlit as st

from src.mock_debentures import get_debentures

# Proxies de mercado — substituir por dados reais via API
_CDI_PROXY = 14.75  # % a.a. (Selic/CDI)
_INFLACAO_BASE = 5.0  # % a.a. (inflacao implicita projetada)
_CUSTO_SWAP_BPS = 15  # bps — custo estimado de execucao do swap

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown('<p class="page-title">Simulador de Swap IPCA+ → CDI+</p>', unsafe_allow_html=True)
st.markdown('<p class="page-subtitle">Conversao via DAP (Futuro de Cupom de IPCA)</p>', unsafe_allow_html=True)

st.warning(
    "Dados ilustrativos para demonstracao — estrutura preparada para conexao com API real.",
    icon="⚠️",
)

with st.expander("Como funciona o swap via DAP"):
    st.markdown("""
O **DAP** (Futuro de Cupom de IPCA) da B3 permite converter uma posicao IPCA+ em CDI+.
Um gestor que detem uma debenture incentivada pagando IPCA + X% pode "trocar" esse indexador
para CDI + Y% usando este derivativo.

**Mecanica simplificada:**
1. O gestor possui a deb pagando **IPCA + X%**
2. Entra em um swap: paga IPCA + cupom DAP, recebe DI (100% CDI)
3. O resultado liquido e: **CDI + (X% - cupom_DAP) - custo**

**Fonte:** Manual de Curvas B3 — Cupom de IPCA (DAP).
""")

# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

df_all = get_debentures()

st.markdown("### Parametros da operacao")

col_ticker, col_ipca, col_nocional = st.columns(3)

with col_ticker:
    ticker_options = ["-- Manual --"] + sorted(df_all["ticker"].tolist())
    ticker_sel = st.selectbox("Ticker", options=ticker_options, help="Selecione um ativo ou insira taxa manualmente.")

with col_ipca:
    if ticker_sel != "-- Manual --":
        row = df_all[df_all["ticker"] == ticker_sel].iloc[0]
        default_ipca = float(row["ipca_plus"])
        default_dur = float(row["duration"])
    else:
        default_ipca = 6.00
        default_dur = 5.0

    ipca_input = st.number_input(
        "IPCA+ (% a.a.)", value=default_ipca, min_value=0.0, max_value=20.0, step=0.05, format="%.2f",
        help="Taxa IPCA+ da debenture.",
    )

with col_nocional:
    nocional = st.number_input(
        "Nocional (R$)", value=10_000_000, min_value=100_000, step=1_000_000, format="%d",
        help="Valor nocional da operacao.",
    )

col_di, col_infl, col_custo = st.columns(3)

with col_di:
    cdi_rate = st.number_input(
        "CDI (% a.a.)", value=_CDI_PROXY, min_value=0.0, max_value=30.0, step=0.25, format="%.2f",
        help="Taxa CDI/Selic atual.",
    )
with col_infl:
    inflacao = st.number_input(
        "Inflacao implicita (% a.a.)", value=_INFLACAO_BASE, min_value=0.0, max_value=20.0, step=0.25, format="%.2f",
        help="Inflacao implicita projetada (Pre vs IPCA+).",
    )
with col_custo:
    custo_bps = st.number_input(
        "Custo do swap (bps)", value=_CUSTO_SWAP_BPS, min_value=0, max_value=100, step=5,
        help="Custo estimado de execucao do swap (bid-ask + corretagem).",
    )

# ---------------------------------------------------------------------------
# Calculo
# ---------------------------------------------------------------------------

# Fisher: taxa nominal = (1 + real) * (1 + inflacao) - 1
nominal_equiv = ((1 + ipca_input / 100) * (1 + inflacao / 100) - 1) * 100

# CDI+ = nominal - CDI
cdi_plus_bruto = nominal_equiv - cdi_rate

# CDI+ liquido (descontando custo do swap)
custo_pct = custo_bps / 100  # bps -> %
cdi_plus_liquido = cdi_plus_bruto - custo_pct

# P&L anual estimado do swap (carry)
carry_anual = nocional * cdi_plus_liquido / 100

# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------

st.markdown("### Resultado do swap")

r1, r2, r3, r4 = st.columns(4)
with r1:
    st.metric(
        "Taxa nominal equiv.", f"{nominal_equiv:.2f}%",
        help="Taxa nominal equivalente via Fisher: (1+IPCA+) x (1+inflacao) - 1.",
    )
with r2:
    st.metric(
        "CDI+ bruto", f"{cdi_plus_bruto:+.2f}%",
        help="Spread sobre CDI antes do custo do swap. Nominal equiv. menos CDI.",
    )
with r3:
    st.metric(
        "CDI+ liquido", f"{cdi_plus_liquido:+.2f}%",
        help=f"Spread sobre CDI apos custo do swap ({custo_bps}bps).",
    )
with r4:
    st.metric(
        "Carry anual", f"R$ {carry_anual:,.0f}",
        help="P&L anual estimado do swap (nocional x CDI+ liquido). Positivo = custo, negativo = receita.",
    )

# ---------------------------------------------------------------------------
# Cenarios de inflacao
# ---------------------------------------------------------------------------

st.markdown("### Analise de cenarios")
st.caption("Como o CDI+ equivalente muda conforme a inflacao implicita varia.")

cenarios = [-2.0, -1.0, -0.5, 0.0, +0.5, +1.0, +2.0]
rows = []
for delta in cenarios:
    infl_c = inflacao + delta
    nom_c = ((1 + ipca_input / 100) * (1 + infl_c / 100) - 1) * 100
    cdi_c = nom_c - cdi_rate - custo_pct
    rows.append({
        "Cenario": f"{'Base' if delta == 0 else f'{delta:+.1f}%'}",
        "Inflacao (%)": round(infl_c, 2),
        "Nominal (%)": round(nom_c, 2),
        "CDI+ liq. (%)": round(cdi_c, 2),
        "Carry anual (R$)": round(nocional * cdi_c / 100),
    })

cenarios_df = pd.DataFrame(rows)
st.dataframe(
    cenarios_df, hide_index=True, use_container_width=True,
    column_config={
        "Cenario": st.column_config.TextColumn(help="Variacao da inflacao implicita em relacao ao cenario base."),
        "Inflacao (%)": st.column_config.NumberColumn(format="%.2f%%", help="Inflacao implicita projetada neste cenario."),
        "Nominal (%)": st.column_config.NumberColumn(format="%.2f%%", help="Taxa nominal equivalente: (1+IPCA+) x (1+inflacao) - 1."),
        "CDI+ liq. (%)": st.column_config.NumberColumn(format="%+.2f%%", help="Spread sobre CDI apos custo do swap. Negativo = paga menos que CDI."),
        "Carry anual (R$)": st.column_config.NumberColumn(format="R$ %,.0f", help="P&L anual estimado: nocional x CDI+ liquido."),
    },
)

st.markdown(
    '<p class="source-label">'
    "Fonte metodologica: Manual de Curvas B3 — Cupom de IPCA (DAP)</p>",
    unsafe_allow_html=True,
)
