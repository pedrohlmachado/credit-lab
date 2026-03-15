"""Fetch real yield curve data from Brazilian market sources via pyield."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# pyield — Primary data source (ANBIMA + B3)
# ---------------------------------------------------------------------------

def _fetch_pre_pyield(ref_date: date) -> Optional[list[tuple[int, float]]]:
    """Fetch prefixada spot rates via pyield (B3/ANBIMA data)."""
    try:
        import pyield as yd

        df = yd.pre.spot_rates(ref_date)
        if df is None or len(df) == 0:
            return None

        vertices = []
        for row in df.iter_rows(named=True):
            du = row["BDToMat"]
            rate = row["SpotRate"] * 100  # Convert decimal to percentage
            if du > 0 and -1 < rate < 100:
                vertices.append((int(du), round(rate, 4)))

        return sorted(vertices) if vertices else None
    except Exception as e:
        logger.warning("Failed to fetch PRE spot rates for %s: %s", ref_date, e)
        return None


def _fetch_ntnb_pyield(ref_date: date) -> Optional[list[tuple[int, float]]]:
    """Fetch NTN-B (IPCA+) indicative rates via pyield (ANBIMA data)."""
    try:
        import pyield as yd

        df = yd.ntnb.data(ref_date)
        if df is None or len(df) == 0:
            return None

        vertices = []
        for row in df.iter_rows(named=True):
            du = row["BDToMat"]
            rate = row["IndicativeRate"] * 100  # Convert decimal to percentage
            # Filtrar titulos com menos de 1 ano (252 DU) — taxas reais
            # de NTN-Bs curtas sao sistematicamente distorcidas e nao
            # representam a estrutura a termo relevante para credito
            if du >= 252 and -10 < rate < 50:
                vertices.append((int(du), round(rate, 4)))

        return sorted(vertices) if vertices else None
    except Exception as e:
        logger.warning("Failed to fetch NTN-B data for %s: %s", ref_date, e)
        return None


def _fetch_di1_pyield(ref_date: date) -> Optional[list[tuple[int, float]]]:
    """Fetch DI1 futures settlement rates via pyield (B3 data).
    Fallback for when pre.spot_rates fails.
    """
    try:
        import pyield as yd

        df = yd.di1.data(ref_date)
        if df is None or len(df) == 0:
            return None

        vertices = []
        for row in df.iter_rows(named=True):
            du = row["BDaysToExp"]
            rate = row["SettlementRate"] * 100  # Convert decimal to percentage
            if du > 0 and -1 < rate < 100:
                vertices.append((int(du), round(rate, 4)))

        return sorted(vertices) if vertices else None
    except Exception as e:
        logger.warning("Failed to fetch DI1 data for %s: %s", ref_date, e)
        return None


# ---------------------------------------------------------------------------
# Fallback — Hardcoded data (13/Mar/2026, fonte: pyield/ANBIMA)
# ---------------------------------------------------------------------------

FALLBACK_DI_PRE = [
    (13, 14.75), (74, 14.41), (139, 14.24), (201, 14.16),
    (261, 14.12), (324, 13.98), (389, 13.95), (452, 13.85),
    (515, 13.86), (576, 13.87), (700, 13.95), (824, 14.05),
    (949, 14.11), (1201, 14.23), (1453, 14.30), (1705, 14.34),
    (2204, 14.32), (2706, 14.36),
]

FALLBACK_NTNB = [
    (292, 8.53), (607, 8.43), (791, 8.30), (1105, 8.31),
    (1291, 8.22), (1609, 8.09), (1796, 8.07), (2295, 7.86),
    (2796, 7.77), (3614, 7.61), (4801, 7.50), (6116, 7.43),
    (7305, 7.39), (8622, 7.40),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _try_fetch(tipo: str, d: date):
    """Tenta buscar dados para um tipo e data especificos."""
    if tipo == "PRE":
        v = _fetch_pre_pyield(d)
        if not v:
            v = _fetch_di1_pyield(d)
        return v
    elif tipo == "IPCA":
        return _fetch_ntnb_pyield(d)
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_curve(tipo: str, ref_date: date) -> list[tuple[int, float]]:
    """Fetch yield curve vertices for a given type and date.

    Se a data solicitada nao tem dados, tenta ate 5 dias uteis anteriores.
    Armazena a data real usada em session_state para exibicao na UI.

    Args:
        tipo: "PRE" (prefixada/DI) or "IPCA" (NTN-B real rates)
        ref_date: reference date

    Returns:
        Sorted list of (du, rate%) tuples.
    """
    if tipo not in ("PRE", "IPCA"):
        raise ValueError(f"tipo must be 'PRE' or 'IPCA', got '{tipo}'")

    # Tentar a data solicitada
    vertices = _try_fetch(tipo, ref_date)
    if vertices:
        st.session_state[f"data_real_{tipo}_{ref_date}"] = ref_date
        st.session_state.pop(f"fallback_{tipo}_{ref_date}", None)
        return sorted(vertices)

    # Tentar ate 5 dias uteis anteriores
    for attempt in range(1, 8):
        alt_date = get_business_date_offset(ref_date, attempt)
        vertices = _try_fetch(tipo, alt_date)
        if vertices:
            logger.info("Data %s sem dados para %s, usando %s", ref_date, tipo, alt_date)
            st.session_state[f"data_real_{tipo}_{ref_date}"] = alt_date
            st.session_state[f"fallback_{tipo}_{ref_date}"] = False
            return sorted(vertices)

    # Fallback hardcoded
    logger.warning("Using fallback data for %s on %s", tipo, ref_date)
    st.session_state[f"fallback_{tipo}_{ref_date}"] = True
    st.session_state[f"data_real_{tipo}_{ref_date}"] = None
    fallback = FALLBACK_DI_PRE if tipo == "PRE" else FALLBACK_NTNB
    return sorted(fallback)


def get_business_date_offset(ref_date: date, offset_days: int) -> date:
    """Approximate business date by subtracting calendar days (adjusted for weekends).

    Note: Does not account for Brazilian holidays — weekend-only approximation.
    """
    target = ref_date - timedelta(days=offset_days)
    while target.weekday() >= 5:
        target -= timedelta(days=1)
    return target


HISTORICAL_OFFSETS = {
    "D-1": 1,
    "D-7": 7,
    "D-14": 14,
    "D-30": 30,
    "3M": 90,
    "6M": 180,
    "1A": 365,
}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_multiple_dates(
    tipo: str, ref_date: date, periods: list[str]
) -> dict[str, list[tuple[int, float]]]:
    """Fetch curves for multiple historical periods."""
    result = {}
    for period in periods:
        offset = HISTORICAL_OFFSETS.get(period, 0)
        if offset == 0:
            continue
        hist_date = get_business_date_offset(ref_date, offset)
        result[period] = fetch_curve(tipo, hist_date)
    return result
