"""Flat forward interpolation for Brazilian yield curves."""

import numpy as np
import pandas as pd


def flat_forward_interpolate(vertices: list[tuple[int, float]], du_target: int) -> float:
    """Interpolate yield curve using flat forward method.

    Args:
        vertices: sorted list of (du, rate%) tuples — rate as percentage (e.g. 14.90)
        du_target: business days to interpolate for

    Returns:
        Interpolated rate as percentage.
    """
    if not vertices:
        raise ValueError("vertices must not be empty")
    if du_target <= 0:
        raise ValueError(f"du_target must be positive, got {du_target}")

    vertices = sorted(vertices)

    # Edge cases: flat extrapolation
    if du_target <= vertices[0][0]:
        return vertices[0][1]
    if du_target >= vertices[-1][0]:
        return vertices[-1][1]

    # Exact vertex match — return directly for clarity & performance
    for du_v, rate_v in vertices:
        if du_target == du_v:
            return rate_v

    # Find surrounding vertices
    for i in range(len(vertices) - 1):
        du_short, r_short_pct = vertices[i]
        du_long, r_long_pct = vertices[i + 1]

        if du_short < du_target <= du_long:
            r_short = r_short_pct / 100.0
            r_long = r_long_pct / 100.0

            # Accumulation factors
            acc_short = (1 + r_short) ** (du_short / 252.0)
            acc_long = (1 + r_long) ** (du_long / 252.0)

            # Forward rate between short and long
            fwd = (acc_long / acc_short) ** (252.0 / (du_long - du_short)) - 1

            # Accumulate from start to du_target
            acc_target = acc_short * (1 + fwd) ** ((du_target - du_short) / 252.0)

            # Convert back to annualized rate
            rate = acc_target ** (252.0 / du_target) - 1

            return rate * 100.0

    return vertices[-1][1]


def generate_interpolated_curve(
    vertices: list[tuple[int, float]], n_points: int = 100
) -> pd.DataFrame:
    """Generate N interpolated points across the curve.

    Args:
        vertices: sorted list of (du, rate%) tuples
        n_points: number of points to generate

    Returns:
        DataFrame with columns: du, anos, taxa
    """
    if not vertices:
        return pd.DataFrame(columns=["du", "anos", "taxa"])

    vertices = sorted(vertices)
    du_min = vertices[0][0]
    du_max = vertices[-1][0]

    dus = np.unique(np.round(np.linspace(du_min, du_max, n_points)).astype(int))

    rows = []
    for du in dus:
        taxa = flat_forward_interpolate(vertices, du)
        rows.append({"du": int(du), "anos": round(du / 252, 2), "taxa": round(taxa, 4)})

    return pd.DataFrame(rows)


def calculate_implied_inflation(
    curve_pre: pd.DataFrame, curve_ipca: pd.DataFrame
) -> pd.DataFrame:
    """Calculate implied inflation curve via Fisher equation.

    implied_inflation = (1 + pre/100) / (1 + ipca/100) - 1

    Both DataFrames must have 'du' and 'taxa' columns.
    Interpolates to common DU points from the prefixada curve.
    """
    # Use pre curve DU points as reference
    pre_vertices = list(zip(curve_pre["du"], curve_pre["taxa"]))
    ipca_vertices = list(zip(curve_ipca["du"], curve_ipca["taxa"]))

    if not pre_vertices or not ipca_vertices:
        return pd.DataFrame(columns=["du", "anos", "taxa"])

    # Determine common range
    du_min = max(pre_vertices[0][0], ipca_vertices[0][0])
    du_max = min(pre_vertices[-1][0], ipca_vertices[-1][0])

    rows = []
    for _, row in curve_pre.iterrows():
        du = int(row["du"])
        if du < du_min or du > du_max:
            continue

        pre_rate = row["taxa"]
        ipca_rate = flat_forward_interpolate(ipca_vertices, du)

        denominator = 1 + ipca_rate / 100
        if abs(denominator) < 1e-10:
            continue
        implied = ((1 + pre_rate / 100) / denominator - 1) * 100

        rows.append({"du": du, "anos": round(du / 252, 2), "taxa": round(implied, 4)})

    return pd.DataFrame(rows)
