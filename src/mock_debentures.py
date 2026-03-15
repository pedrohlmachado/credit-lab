"""Dados mock realistas de debentures incentivadas (IPCA+).

IMPORTANTE: Estes dados sao ficticios, gerados para demonstrar
funcionalidades e potenciais da plataforma. Nao representam
dados reais de mercado.

Interface preparada para substituicao por API real no futuro.
Basta reimplementar as funcoes com a mesma assinatura.
"""

import hashlib

import numpy as np
import pandas as pd

# Proxies para conversao IPCA+ -> CDI+ equivalente
_INFLACAO_IMPLICITA = 5.0  # % a.a. — substituir por dado real via API
_CDI_PROXY = 14.75  # % a.a. — proxy Selic/CDI atual, substituir por dado real

# ---------------------------------------------------------------------------
# Dados base — tickers e emissores realistas
# Formato: (ticker, emissor, setor, rating, duration, ipca_plus)
# ---------------------------------------------------------------------------

_DEBENTURES_RAW = [
    # Energia Eletrica
    ("ENBR31", "Energias do Brasil", "Energia Eletrica", "AA+", 4.8, 5.20),
    ("ELET14", "Eletrobras", "Energia Eletrica", "AAA", 4.8, 5.25),
    ("CPFL21", "CPFL Energia", "Energia Eletrica", "AAA", 4.3, 5.10),
    ("EQTL11", "Equatorial", "Energia Eletrica", "AA+", 5.2, 5.30),
    ("CPLE11", "Copel", "Energia Eletrica", "AA+", 4.5, 5.15),
    ("CMIG11", "CEMIG", "Energia Eletrica", "AA", 5.7, 5.60),
    ("NEOE11", "Neoenergia", "Energia Eletrica", "AA+", 4.4, 5.35),
    ("ENGP11", "Energisa", "Energia Eletrica", "AA+", 5.0, 5.40),
    ("ENBR41", "Energias do Brasil", "Energia Eletrica", "AA+", 6.5, 5.45),
    ("ELET24", "Eletrobras", "Energia Eletrica", "AAA", 6.0, 5.00),
    ("CPFL31", "CPFL Energia", "Energia Eletrica", "AAA", 5.9, 5.20),
    ("EQTL21", "Equatorial", "Energia Eletrica", "AA+", 7.0, 5.50),
    ("CPLE21", "Copel", "Energia Eletrica", "AA+", 6.3, 5.30),
    ("CMIG21", "CEMIG", "Energia Eletrica", "AA", 7.5, 5.75),
    ("NEOE21", "Neoenergia", "Energia Eletrica", "AA+", 5.8, 5.50),
    ("ENGP21", "Energisa", "Energia Eletrica", "AA+", 6.6, 5.55),
    ("ENGI11", "Engie Brasil", "Energia Eletrica", "AAA", 4.2, 4.80),
    ("ENGI21", "Engie Brasil", "Energia Eletrica", "AAA", 5.8, 5.00),
    ("LIGT11", "Light", "Energia Eletrica", "A+", 3.5, 7.50),
    ("LIGT21", "Light", "Energia Eletrica", "A+", 5.0, 7.80),
    ("TIET11", "AES Tiete", "Energia Eletrica", "AA", 4.0, 5.80),
    ("TIET21", "AES Tiete", "Energia Eletrica", "AA", 5.5, 6.00),
    ("AESB11", "AES Brasil", "Energia Eletrica", "AA", 4.3, 5.90),
    ("AESB21", "AES Brasil", "Energia Eletrica", "AA", 5.9, 6.10),
    ("CESP11", "CESP", "Energia Eletrica", "AA+", 3.7, 5.25),
    ("CESP21", "CESP", "Energia Eletrica", "AA+", 5.3, 5.45),
    ("CPFL41", "CPFL Energia", "Energia Eletrica", "AAA", 7.2, 5.30),
    ("EQTL31", "Equatorial", "Energia Eletrica", "AA+", 8.5, 5.60),
    ("CGAS11", "Comgas", "Energia Eletrica", "AAA", 3.4, 4.60),
    ("CGAS21", "Comgas", "Energia Eletrica", "AAA", 5.0, 4.80),
    # Transmissao
    ("TAEE31", "TAESA", "Transmissao", "AAA", 3.9, 4.80),
    ("ISAE11", "ISA CTEEP", "Transmissao", "AAA", 3.5, 4.70),
    ("TRPL11", "Transmissao Paulista", "Transmissao", "AAA", 3.2, 4.60),
    ("TAEE41", "TAESA", "Transmissao", "AAA", 5.5, 4.90),
    ("ISAE21", "ISA CTEEP", "Transmissao", "AAA", 5.0, 4.85),
    ("TRPL21", "Transmissao Paulista", "Transmissao", "AAA", 4.8, 4.75),
    ("TAEE51", "TAESA", "Transmissao", "AAA", 7.0, 5.00),
    ("ISAE31", "ISA CTEEP", "Transmissao", "AAA", 6.5, 4.95),
    ("TRPL31", "Transmissao Paulista", "Transmissao", "AAA", 6.2, 4.85),
    # Rodovias e Concessoes
    ("CCRN31", "CCR", "Rodovias", "AA+", 4.6, 6.20),
    ("ECOV11", "EcoRodovias", "Rodovias", "AA", 5.3, 6.40),
    ("ARTR11", "Arteris", "Rodovias", "AA+", 4.9, 6.10),
    ("RENT11", "Localiza", "Rodovias", "AA+", 4.1, 5.80),
    ("CCRN41", "CCR", "Rodovias", "AA+", 6.8, 6.30),
    ("ECOV21", "EcoRodovias", "Rodovias", "AA", 7.2, 6.55),
    ("ARTR21", "Arteris", "Rodovias", "AA+", 6.5, 6.20),
    ("RENT21", "Localiza", "Rodovias", "AA+", 5.5, 5.90),
    ("RLOG11", "Rumo Logistica", "Rodovias", "AA", 4.8, 6.30),
    ("RLOG21", "Rumo Logistica", "Rodovias", "AA", 6.5, 6.50),
    ("BRML11", "BR Malls", "Rodovias", "AA", 4.0, 6.10),
    ("BRML21", "BR Malls", "Rodovias", "AA", 5.5, 6.30),
    ("ECOV31", "EcoRodovias", "Rodovias", "AA", 8.5, 6.70),
    ("IGTA11", "Iguatemi", "Rodovias", "AA", 3.9, 6.00),
    ("IGTA21", "Iguatemi", "Rodovias", "AA", 5.4, 6.20),
    # Saneamento
    ("AEGP31", "Aegea Saneamento", "Saneamento", "AA+", 5.4, 5.50),
    ("SBSP11", "Sabesp", "Saneamento", "AAA", 4.0, 4.90),
    ("AEGP41", "Aegea Saneamento", "Saneamento", "AA+", 7.1, 5.70),
    ("SBSP21", "Sabesp", "Saneamento", "AAA", 5.8, 5.10),
    ("SBSP31", "Sabesp", "Saneamento", "AAA", 7.5, 5.30),
    ("AEGP51", "Aegea Saneamento", "Saneamento", "AA+", 8.5, 5.90),
    ("MRVE11", "MRV Engenharia", "Saneamento", "AA-", 4.2, 6.20),
    ("MRVE21", "MRV Engenharia", "Saneamento", "AA-", 5.8, 6.40),
    # Portos e Logistica
    ("PRTB11", "Portonave", "Portos", "AA+", 4.8, 4.90),
    ("SNAT11", "Santos Brasil", "Portos", "AA", 3.6, 6.80),
    ("WILS11", "Wilson Sons", "Portos", "AA", 4.6, 6.50),
    ("PRTB21", "Portonave", "Portos", "AA+", 3.2, 7.00),
    ("SNAT21", "Santos Brasil", "Portos", "AA", 5.2, 6.90),
    ("WILS21", "Wilson Sons", "Portos", "AA", 6.0, 6.70),
    # Telecom
    ("TELB41", "Telefonica Brasil", "Telecom", "AA-", 6.0, 6.00),
    ("ALGA21", "Algar Telecom", "Telecom", "AA", 5.1, 5.50),
    ("TELB51", "Telefonica Brasil", "Telecom", "AA-", 3.8, 6.60),
    ("ALGA31", "Algar Telecom", "Telecom", "AA", 6.8, 5.65),
    ("VIVO11", "Vivo", "Telecom", "AAA", 3.6, 4.80),
    ("VIVO21", "Vivo", "Telecom", "AAA", 5.2, 5.00),
    ("TIMS11", "TIM", "Telecom", "AA+", 3.8, 5.20),
    ("TIMS21", "TIM", "Telecom", "AA+", 5.4, 5.40),
    ("OIBR11", "Oi", "Telecom", "A+", 3.0, 8.50),
    ("OIBR21", "Oi", "Telecom", "A+", 4.5, 8.80),
    # Petroquimico e Industria
    ("BRKM11", "Braskem", "Petroquimico", "AA+", 6.6, 5.20),
    ("BRKM21", "Braskem", "Petroquimico", "AA+", 8.0, 5.40),
    ("BRKM31", "Braskem", "Petroquimico", "AA+", 9.2, 5.60),
    ("CSNA11", "CSN", "Siderurgia", "AA-", 4.5, 6.80),
    ("CSNA21", "CSN", "Siderurgia", "AA-", 6.2, 7.00),
    ("GGBR11", "Gerdau", "Siderurgia", "AA+", 3.9, 5.20),
    ("GGBR21", "Gerdau", "Siderurgia", "AA+", 5.6, 5.40),
    # Papel e Celulose
    ("SUZB11", "Suzano", "Papel e Celulose", "AA+", 4.3, 5.10),
    ("SUZB21", "Suzano", "Papel e Celulose", "AA+", 6.0, 5.30),
    ("KLBN11", "Klabin", "Papel e Celulose", "AA", 4.7, 5.60),
    ("KLBN21", "Klabin", "Papel e Celulose", "AA", 6.3, 5.80),
    # Mineracao e O&G
    ("VALE11", "Vale", "Mineracao", "AAA", 3.8, 4.50),
    ("VALE21", "Vale", "Mineracao", "AAA", 5.5, 4.70),
    ("PETR11", "Petrobras", "Oleo e Gas", "AAA", 3.5, 4.40),
    ("PETR21", "Petrobras", "Oleo e Gas", "AAA", 5.0, 4.60),
    # Holding e Financeiro
    ("ITSA11", "Itausa", "Holding", "AAA", 3.2, 4.30),
    ("ITSA21", "Itausa", "Holding", "AAA", 4.8, 4.50),
    ("CSAN11", "Cosan", "Holding", "AA", 6.2, 6.00),
    ("CSAN21", "Cosan", "Holding", "AA", 7.8, 6.15),
    ("BBDC11", "Bradesco", "Financeiro", "AAA", 3.0, 4.20),
    ("BBDC21", "Bradesco", "Financeiro", "AAA", 4.5, 4.40),
    ("SANB11", "Santander", "Financeiro", "AAA", 3.3, 4.35),
    ("SANB21", "Santander", "Financeiro", "AAA", 4.9, 4.55),
]


def _seed_from_ticker(ticker: str) -> int:
    """Deterministic seed from ticker name."""
    return int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)


def get_debentures() -> pd.DataFrame:
    """Retorna DataFrame com ~100 debentures incentivadas (dados mock).

    Colunas: ticker, emissor, setor, rating, duration, ipca_plus, cdi_plus,
             delta_med_bps, z_score
    """
    rows = []
    for ticker, emissor, setor, rating, duration, ipca_plus in _DEBENTURES_RAW:
        rng = np.random.RandomState(_seed_from_ticker(ticker))
        delta = rng.randint(-40, 30)
        z = round(rng.uniform(-1.5, 1.5), 2)
        # CDI+ equivalente: taxa nominal via Fisher menos CDI
        # Nominal = (1+IPCA+)*(1+inflacao)-1, CDI+ = nominal - CDI
        # Resultado tipicamente negativo (deb incentivada paga CDI - X%)
        nominal = ((1 + ipca_plus / 100) * (1 + _INFLACAO_IMPLICITA / 100) - 1) * 100
        cdi_plus = round(nominal - _CDI_PROXY, 2)
        rows.append({
            "ticker": ticker,
            "emissor": emissor,
            "setor": setor,
            "rating": rating,
            "duration": duration,
            "ipca_plus": ipca_plus,
            "cdi_plus": cdi_plus,
            "delta_med_bps": delta,
            "z_score": z,
        })
    return pd.DataFrame(rows)


def get_spread_history(ticker: str) -> pd.DataFrame:
    """Retorna historico diario de taxa IPCA+ para 5 anos (dados mock).

    Colunas: data, ipca_plus
    """
    df_all = get_debentures()
    row = df_all[df_all["ticker"] == ticker]
    if row.empty:
        return pd.DataFrame(columns=["data", "ipca_plus"])

    base = row.iloc[0]["ipca_plus"]
    rng = np.random.RandomState(_seed_from_ticker(ticker))

    end_date = pd.Timestamp.today().normalize()
    start_date = end_date - pd.DateOffset(years=5)
    dates = pd.bdate_range(start=start_date, end=end_date)

    n = len(dates)
    noise = rng.normal(0, 0.02, n)
    trend = np.linspace(-0.3, 0.3, n) * rng.choice([-1, 1])
    walk = np.cumsum(noise) * 0.15
    series = base + walk + trend
    series = series - (series.mean() - base)
    series = np.clip(series, base * 0.6, base * 1.5)

    return pd.DataFrame({"data": dates[:n], "ipca_plus": np.round(series, 2)})


def get_emissor_debentures(emissor: str) -> pd.DataFrame:
    """Retorna todas as debentures de um emissor (dados mock)."""
    df = get_debentures()
    return df[df["emissor"] == emissor][["ticker", "duration", "ipca_plus", "setor"]].copy()


def get_consolidated_spread_history(
    setores=None, emissores=None, ratings=None, tickers=None,
    dur_min=None, dur_max=None,
) -> pd.DataFrame:
    """Retorna historico consolidado (media) de IPCA+ filtrado.

    Colunas: data, ipca_plus
    """
    df = get_debentures()
    if setores:
        df = df[df["setor"].isin(setores)]
    if emissores:
        df = df[df["emissor"].isin(emissores)]
    if ratings:
        df = df[df["rating"].isin(ratings)]
    if tickers:
        df = df[df["ticker"].isin(tickers)]
    if dur_min is not None:
        df = df[df["duration"] >= dur_min]
    if dur_max is not None:
        df = df[df["duration"] <= dur_max]

    if df.empty:
        return pd.DataFrame(columns=["data", "ipca_plus"])

    histories = []
    for ticker in df["ticker"]:
        h = get_spread_history(ticker)
        if not h.empty:
            histories.append(h.set_index("data")["ipca_plus"])

    if not histories:
        return pd.DataFrame(columns=["data", "ipca_plus"])

    combined = pd.concat(histories, axis=1)
    mean_val = combined.mean(axis=1)
    return pd.DataFrame({"data": mean_val.index, "ipca_plus": mean_val.values})


def calculate_momentum(ipca_series: pd.Series) -> dict:
    """Calcula momentum de taxa IPCA+.

    Logica de mercado:
    - IPCA+ fechando (taxa caindo) = precos subindo = COMPRA
    - IPCA+ abrindo (taxa subindo) = precos caindo = VENDA

    Componentes (pesos):
    - Tendencia (45%): SMA9 vs SMA20
    - Velocidade (35%): taxa de variacao 20d
    - Aceleracao (20%): variacao da velocidade

    Retorna dict com score [-100, +100], componentes e sinal.
    """
    if len(ipca_series) < 80:
        return {"score": 0, "tendencia": 0, "velocidade": 0,
                "aceleracao": 0, "sinal": "NEUTRO"}

    s = ipca_series.values

    # Tendencia: SMA9 vs SMA20 (invertida — IPCA+ caindo = positivo)
    sma9 = np.mean(s[-9:])
    sma20 = np.mean(s[-20:])
    sma_diff = (sma9 - sma20) / sma20 * 100 if sma20 != 0 else 0
    # Multiplicadores calibrados para credito (movimentos de 1-5 bps/dia)
    tendencia = np.clip(-sma_diff * 30, -100, 100)

    # Velocidade: variacao percentual 20d (invertida — queda = positivo)
    if s[-21] != 0:
        vel_pct = (s[-1] - s[-21]) / s[-21] * 100
    else:
        vel_pct = 0
    velocidade = np.clip(-vel_pct * 18, -100, 100)

    # Aceleracao: variacao da velocidade (invertida)
    if len(s) >= 41 and s[-41] != 0:
        vel_anterior = (s[-21] - s[-41]) / s[-41] * 100
    else:
        vel_anterior = 0
    acel = vel_pct - vel_anterior
    aceleracao = np.clip(-acel * 30, -100, 100)

    # Score ponderado
    score = tendencia * 0.45 + velocidade * 0.35 + aceleracao * 0.20
    score = np.clip(score, -100, 100)

    if score > 20:
        sinal = "COMPRA"
    elif score < -20:
        sinal = "VENDA"
    else:
        sinal = "NEUTRO"

    return {
        "score": round(float(score), 1),
        "tendencia": round(float(tendencia), 1),
        "velocidade": round(float(velocidade), 1),
        "aceleracao": round(float(aceleracao), 1),
        "sinal": sinal,
    }


def get_top_trades(n: int = 5) -> pd.DataFrame:
    """Retorna top N compra + top N venda baseado em momentum individual.

    Colunas: ticker, emissor, setor, ipca_plus, score, sinal
    """
    df = get_debentures()
    rows = []
    for _, deb in df.iterrows():
        hist = get_spread_history(deb["ticker"])
        if hist.empty or len(hist) < 80:
            continue
        mom = calculate_momentum(hist["ipca_plus"])
        rows.append({
            "ticker": deb["ticker"],
            "emissor": deb["emissor"],
            "setor": deb["setor"],
            "ipca_plus": deb["ipca_plus"],
            "score": mom["score"],
            "sinal": mom["sinal"],
        })

    result = pd.DataFrame(rows)
    if result.empty:
        return result

    top_buy = result.nlargest(n, "score")
    top_sell = result.nsmallest(n, "score")
    return pd.concat([top_buy, top_sell]).drop_duplicates(subset="ticker")
