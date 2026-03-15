"""Scraper de dados reais — Debentures IPCA+ (Mercado Secundario ANBIMA).

Fonte: www.anbima.com.br/informacoes/merc-sec-debentures/
Pagina: resultados/mdeb_DDmmmYYYY_ipca_spread.asp
~630 debentures IPCA+ por dia util. Acesso publico, sem autenticacao.
"""

import logging
import re
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.anbima.com.br/informacoes/merc-sec-debentures/resultados"
_DB_PATH = Path(__file__).parent.parent / "data" / "reune_ipca.db"

_MONTHS_PT = {
    1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun",
    7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez",
}

_COL_NAMES = [
    "codigo", "nome", "vencimento", "indice_spread",
    "taxa_compra", "taxa_venda", "taxa_indicativa", "desvio_padrao",
    "intervalo_min", "intervalo_max", "pu", "percent_pu_par",
    "duration", "percent_reune", "referencia_ntnb",
]


def _build_url(d: date) -> str:
    m = _MONTHS_PT[d.month]
    return f"{_BASE_URL}/mdeb_{d.day:02d}{m}{d.year}_ipca_spread.asp"


def fetch_day(d: date) -> pd.DataFrame:
    """Baixa debentures IPCA+ de um dia util via scraping HTML da ANBIMA."""
    url = _build_url(d)
    try:
        resp = requests.get(url, timeout=20)
        if resp.status_code != 200:
            return pd.DataFrame()

        html = resp.content.decode("latin-1")

        # Extrair todas as celulas <TD>
        cells = re.findall(r'<TD[^>]*>(.*?)</TD>', html, re.DOTALL | re.IGNORECASE)
        cells = [
            re.sub(r'<[^>]+>', '', c).strip().replace('\xa0', '').replace('\r', '').replace('&nbsp;', '')
            for c in cells
        ]

        # Encontrar inicio dos dados (primeira celula que parece codigo de deb)
        start = None
        for i, c in enumerate(cells):
            if re.match(r'^[A-Z]{3,6}\w{1,3}$', c) and i > 10:
                start = i
                break

        if start is None:
            return pd.DataFrame()

        # 15 colunas por registro
        n_cols = 15
        rows = []
        for i in range(start, len(cells) - n_cols + 1, n_cols):
            row = cells[i:i + n_cols]
            if re.match(r'^[A-Z]{3,6}\w{1,3}$', row[0]):
                rows.append(row)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows, columns=_COL_NAMES)
        df["data_referencia"] = d

        # Converter numericos (formato brasileiro: 1.234,56 → 1234.56)
        for col in ["taxa_compra", "taxa_venda", "taxa_indicativa", "desvio_padrao",
                     "intervalo_min", "intervalo_max", "pu", "percent_pu_par", "duration"]:
            df[col] = pd.to_numeric(
                df[col].str.replace(".", "", regex=False).str.replace(",", ".", regex=False).str.replace("--", "", regex=False),
                errors="coerce",
            )

        df["percent_reune"] = pd.to_numeric(
            df["percent_reune"].str.replace("%", "").str.replace(",", ".").str.strip(),
            errors="coerce",
        )

        # (*) = clausula de resgate/amortizacao antecipado
        # (**) = clausula ja em periodo de exercicio
        # NAO indica incentivada — debs IPCA+ sao tipicamente incentivadas (Lei 12.431)
        df["resgate_antecipado"] = df["nome"].str.contains(r"\(\*\)", regex=True, na=False)
        df["em_exercicio"] = df["nome"].str.contains(r"\(\*\*\)", regex=True, na=False)

        # Extrair spread do campo indice_spread (ex: "IPCA + 7,415%" → 7.415)
        df["spread_ipca"] = pd.to_numeric(
            df["indice_spread"].str.extract(r'([\d,]+)%')[0].str.replace(",", "."),
            errors="coerce",
        )

        return df

    except Exception as e:
        logger.warning("Falha ao baixar dados ANBIMA IPCA+ para %s: %s", d, e)
        return pd.DataFrame()


def _ensure_db():
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reune_ipca (
            data_referencia TEXT,
            codigo TEXT,
            nome TEXT,
            vencimento TEXT,
            indice_spread TEXT,
            spread_ipca REAL,
            taxa_compra REAL,
            taxa_venda REAL,
            taxa_indicativa REAL,
            desvio_padrao REAL,
            intervalo_min REAL,
            intervalo_max REAL,
            pu REAL,
            percent_pu_par REAL,
            duration REAL,
            percent_reune REAL,
            referencia_ntnb TEXT,
            resgate_antecipado INTEGER,
            em_exercicio INTEGER,
            PRIMARY KEY (data_referencia, codigo)
        )
    """)
    conn.commit()
    conn.close()


def sync_recent(n_days: int = 10) -> int:
    """Baixa e armazena os ultimos n_days de dados. Retorna dias novos baixados."""
    _ensure_db()
    conn = sqlite3.connect(str(_DB_PATH))

    existing = set()
    try:
        rows = conn.execute("SELECT DISTINCT data_referencia FROM reune_ipca").fetchall()
        existing = {r[0] for r in rows}
    except Exception:
        pass

    downloaded = 0
    today = date.today()

    for i in range(n_days):
        d = today - timedelta(days=i)
        if d.weekday() >= 5:
            continue
        d_str = d.isoformat()
        if d_str in existing:
            continue

        df = fetch_day(d)
        if df.empty:
            continue

        df_save = df.copy()
        df_save["data_referencia"] = d_str
        df_save["resgate_antecipado"] = df_save["resgate_antecipado"].astype(int)
        df_save["em_exercicio"] = df_save["em_exercicio"].astype(int)
        cols_to_save = [c for c in df_save.columns if c in [
            "data_referencia", "codigo", "nome", "vencimento", "indice_spread", "spread_ipca",
            "taxa_compra", "taxa_venda", "taxa_indicativa", "desvio_padrao",
            "intervalo_min", "intervalo_max", "pu", "percent_pu_par",
            "duration", "percent_reune", "referencia_ntnb",
            "resgate_antecipado", "em_exercicio",
        ]]
        df_save[cols_to_save].to_sql("reune_ipca", conn, if_exists="append", index=False)
        downloaded += 1
        logger.info("Baixado IPCA+ %s: %d debentures", d_str, len(df))

    conn.close()
    return downloaded


def get_stored_data(start_date: date = None, end_date: date = None) -> pd.DataFrame:
    """Retorna dados IPCA+ armazenados. Sync automatico se banco vazio."""
    _ensure_db()

    conn = sqlite3.connect(str(_DB_PATH))
    count = conn.execute("SELECT COUNT(*) FROM reune_ipca").fetchone()[0]
    conn.close()

    if count == 0:
        sync_recent(n_days=10)

    query = "SELECT * FROM reune_ipca"
    conditions = []
    if start_date:
        conditions.append(f"data_referencia >= '{start_date.isoformat()}'")
    if end_date:
        conditions.append(f"data_referencia <= '{end_date.isoformat()}'")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY data_referencia DESC, codigo"

    conn = sqlite3.connect(str(_DB_PATH))
    df = pd.read_sql_query(query, conn)
    conn.close()

    if not df.empty:
        df["resgate_antecipado"] = df["resgate_antecipado"].astype(bool)
        df["em_exercicio"] = df["em_exercicio"].astype(bool)
        df["data_referencia"] = pd.to_datetime(df["data_referencia"]).dt.date

    return df
