"""Negocios do Dia — Debentures IPCA+ (ANBIMA)."""

import streamlit as st
import pandas as pd

from src.anbima_reune import get_stored_data, sync_recent

# ---------------------------------------------------------------------------
# Funcao para buscar taxa NTN-B de referencia
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def _get_ntnb_rates():
    """Busca taxas NTN-B atuais via pyield. Retorna dict com chave DD/MM/YYYY."""
    try:
        import pyield as yd
        from datetime import date, timedelta
        for offset in range(0, 7):
            d = date.today() - timedelta(days=offset)
            if d.weekday() >= 5:
                continue
            df = yd.ntnb.data(d)
            if df is not None and len(df) > 0:
                rates = {}
                for row in df.iter_rows(named=True):
                    mat = row["MaturityDate"]  # datetime.date
                    # Chave em DD/MM/YYYY para casar com formato ANBIMA
                    key = mat.strftime("%d/%m/%Y")
                    rates[key] = round(row["IndicativeRate"] * 100, 4)
                return rates
    except Exception:
        pass
    return {}


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown('<p class="page-title">Negocios do Dia</p>', unsafe_allow_html=True)
st.markdown('<p class="page-subtitle">Debentures IPCA+ — mercado secundario (dados reais ANBIMA)</p>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sync automatico + carregamento (5 dias uteis mais recentes)
# ---------------------------------------------------------------------------

with st.spinner("Sincronizando com ANBIMA..."):
    sync_recent(n_days=10)
    df_all = get_stored_data()
    ntnb_rates = _get_ntnb_rates()

# Limitar a 5 dias uteis mais recentes
if not df_all.empty:
    available_dates = sorted(df_all["data_referencia"].unique(), reverse=True)[:5]
    df_all = df_all[df_all["data_referencia"].isin(available_dates)]
    st.caption(
        f"{len(available_dates)} dias | {len(df_all)} ativos | "
        f"Fonte: ANBIMA — Mercado Secundario (IPCA+ Spread)"
    )
else:
    st.warning("Nao foi possivel carregar dados da ANBIMA.")
    st.stop()

# ---------------------------------------------------------------------------
# Coluna vs NTN-B
# ---------------------------------------------------------------------------

def _calc_vs_ntnb(row):
    """Calcula diferenca entre taxa indicativa e NTN-B de referencia."""
    ref = row.get("referencia_ntnb", "")
    taxa = row.get("taxa_indicativa")
    if pd.isna(taxa) or not ref or not ntnb_rates:
        return None
    # Match direto (ambos DD/MM/YYYY)
    ntnb_rate = ntnb_rates.get(ref.strip())
    if ntnb_rate is None:
        return None
    return round(taxa - ntnb_rate, 4)

df_all["vs_ntnb"] = df_all.apply(_calc_vs_ntnb, axis=1)

# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------

available_dates = sorted(df_all["data_referencia"].unique(), reverse=True)

col_date, col_search = st.columns([1, 1])
with col_date:
    selected_date = st.selectbox(
        "Data de referencia", options=available_dates, index=0,
        format_func=lambda d: d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d),
    )
with col_search:
    search = st.text_input("Buscar por codigo ou emissor", value="", key="neg_search")

col_f1, _ = st.columns(2)
with col_f1:
    dur_filter = st.slider(
        "Duration (DU)", min_value=0, max_value=5000,
        value=(0, 5000), step=100, key="neg_dur",
    )

# Aplicar filtros
df = df_all[df_all["data_referencia"] == selected_date].copy()
if search:
    mask = (
        df["codigo"].str.contains(search, case=False, na=False)
        | df["nome"].str.contains(search, case=False, na=False)
    )
    df = df[mask]
df = df[df["duration"].between(dur_filter[0], dur_filter[1], inclusive="both") | df["duration"].isna()]

if df.empty:
    st.info("Nenhuma movimentacao encontrada com os filtros selecionados.")
    st.stop()

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Total de ativos", len(df))
with k2:
    tx = df["taxa_indicativa"].dropna().mean()
    st.metric("Taxa indicativa media", f"{tx:.2f}%" if tx == tx else "--")
with k3:
    spread = df["spread_ipca"].dropna().mean()
    st.metric("Spread IPCA+ medio", f"{spread:.2f}%" if spread == spread else "--",
              help="Spread medio sobre IPCA (taxa de emissao).")
with k4:
    vs = df["vs_ntnb"].dropna()
    if len(vs) > 0:
        st.metric("vs NTN-B medio", f"{vs.mean():+.2f}%",
                  help="Diferenca media entre taxa indicativa da deb e NTN-B de referencia. Positivo = deb paga mais que NTN-B (premio de credito).")
    else:
        st.metric("vs NTN-B medio", "--")

# ---------------------------------------------------------------------------
# Tabela
# ---------------------------------------------------------------------------

display = df[[
    "codigo", "nome", "vencimento", "indice_spread", "resgate_antecipado",
    "taxa_compra", "taxa_venda", "taxa_indicativa",
    "vs_ntnb",
    "desvio_padrao", "pu", "percent_pu_par", "duration",
    "percent_reune", "referencia_ntnb",
]].copy()

display.columns = [
    "CODIGO", "EMISSOR", "VENC.", "INDICE", "RESGATE ANT.",
    "TX COMPRA", "TX VENDA", "TX INDIC.",
    "vs NTN-B",
    "DESVIO", "PU", "% PU PAR", "DURATION (DU)",
    "% REUNE", "REF. NTN-B",
]

st.dataframe(
    display, use_container_width=True, hide_index=True,
    column_config={
        "RESGATE ANT.": st.column_config.CheckboxColumn(
            help="(*) Clausula de resgate ou amortizacao antecipado. (**) Clausula em periodo de exercicio.",
        ),
        "TX COMPRA": st.column_config.NumberColumn(format="%.4f", help="Taxa de compra (bid)."),
        "TX VENDA": st.column_config.NumberColumn(format="%.4f", help="Taxa de venda (ask)."),
        "TX INDIC.": st.column_config.NumberColumn(format="%.4f", help="Taxa indicativa ANBIMA."),
        "vs NTN-B": st.column_config.ProgressColumn(
            label="vs NTN-B",
            format="%.2f%%",
            min_value=-2.0,
            max_value=4.0,
            help="Diferenca entre taxa indicativa e NTN-B de referencia. Maior = maior premio de credito (potencial oportunidade).",
        ),
        "DESVIO": st.column_config.NumberColumn(format="%.4f", help="Desvio padrao."),
        "PU": st.column_config.NumberColumn(format="%.6f", help="Preco unitario."),
        "% PU PAR": st.column_config.NumberColumn(format="%.2f", help="% PU par / VNE."),
        "DURATION (DU)": st.column_config.NumberColumn(format="%.0f", help="Duration em dias uteis."),
        "% REUNE": st.column_config.NumberColumn(format="%.0f%%", help="Contribuicao REUNE."),
    },
)

st.markdown(
    f'<p class="source-label">'
    f"Data: {selected_date} &nbsp;&bull;&nbsp; "
    f"{len(df)} ativos IPCA+ &nbsp;&bull;&nbsp; "
    f"(*) Resgate antecipado &nbsp;&bull;&nbsp; "
    f"Fonte: ANBIMA</p>",
    unsafe_allow_html=True,
)
