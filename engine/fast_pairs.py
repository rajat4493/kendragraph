"""
KendraGraph — Fast Close-Pair Finder
Purpose: Find satellites that are near each other without O(N^2) brute force.
Idea: 1) Predict positions in 3D space at a few timestamps (SGP4).
      2) Use a BallTree to query "who is within R km of me?" quickly.
Why: BallTree avoids comparing every satellite with every other one.
"""

from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
from sgp4.api import Satrec, jday
from sklearn.neighbors import BallTree  # acts like a 3D "nearby objects" index

def _eci_pos_km(sat: Satrec, when: datetime):
    """
    Use the SGP4 physics model to convert a TLE + time → a 3D position (x,y,z) in km (ECI frame).
    If the propagation fails (bad TLE), return None and skip.
    """
    jd, fr = jday(
        when.year, when.month, when.day,
        when.hour, when.minute, when.second + when.microsecond / 1e6
    )
    err, r, _v = sat.sgp4(jd, fr)
    if err != 0:
        return None
    return np.array(r, dtype=np.float64)

def positions_table(df_tle: pd.DataFrame, times: list[datetime]) -> pd.DataFrame:
    """
    Build a simple table of positions for all satellites at the given times.
    Output columns: time, norad_id, x_km, y_km, z_km
    """
    sats = {row.norad_id: Satrec.twoline2rv(row.l1, row.l2) for row in df_tle.itertuples()}
    rows = []
    for t in times:
        for nid, sat in sats.items():
            p = _eci_pos_km(sat, t)
            if p is None:
                continue
            rows.append((t, nid, p[0], p[1], p[2]))
    return pd.DataFrame(rows, columns=["time", "norad_id", "x_km", "y_km", "z_km"])

def close_pairs_at_time(df_pos: pd.DataFrame, radius_km: float = 50.0) -> pd.DataFrame:
    """
    Given positions at a single timestamp, find all pairs closer than 'radius_km'.
    BallTree makes neighbor search fast even for thousands of satellites.
    """
    P = df_pos[["x_km", "y_km", "z_km"]].to_numpy()
    tree = BallTree(P, metric="euclidean")
    # For each point, get indices of neighbors within radius and their distances.
    (indices, distances) = tree.query_radius(P, r=radius_km, return_distance=True, sort_results=True)

    out = []
    ids = df_pos["norad_id"].to_numpy()
    for i, (nbrs, dists) in enumerate(zip(indices, distances)):
        for j, d in zip(nbrs, dists):
            # Skip self-pair and duplicates (i,j) vs (j,i)
            if j <= i:
                continue
            out.append((df_pos["time"].iat[i], int(ids[i]), int(ids[j]), float(d)))
    return pd.DataFrame(out, columns=["time", "norad_id_a", "norad_id_b", "dist_km"])

def min_distance_over_window(
    df_tle: pd.DataFrame,
    hours: int = 12,
    step_min: int = 60,
    radius_km: float = 100.0
) -> pd.DataFrame:
    """
    Slide across a time window (e.g., next 12 hours).
    At each step: compute positions → find close pairs → keep the minimum distance per pair.
    Output: one row per pair with their best (closest) approach.
    """
    now = datetime.now(timezone.utc)
    times = [now + timedelta(minutes=m) for m in range(0, hours * 60, step_min)]
    mins = []

    for t in times:
        dfp = positions_table(df_tle, [t])
        if dfp.empty:
            continue
        pairs = close_pairs_at_time(dfp, radius_km=radius_km)
        if pairs.empty:
            continue

        # For this timestamp, get the closest distance per pair.
        g = pairs.groupby(["norad_id_a", "norad_id_b"], as_index=False)["dist_km"].min()
        g["tca_utc"] = t  # time-of-closest-approach at this step
        mins.append(g)

    if not mins:
        return pd.DataFrame(columns=["norad_id_a", "norad_id_b", "min_dist_km", "tca_utc"])

    # Across all steps, keep the single closest encounter per pair.
    df = pd.concat(mins, ignore_index=True)
    df = (df.sort_values("dist_km")
            .groupby(["norad_id_a", "norad_id_b"], as_index=False)
            .first()
            .rename(columns={"dist_km": "min_dist_km"}))
    return df
