"""
KendraGraph — Baseline Risk Scoring
Purpose: Turn "how close did they get?" into a 0–1 risk score.
Why: Even if nothing is <1 km, we still want a ranking: closer = riskier.
"""

import numpy as np
import pandas as pd

def apply_baseline(df_pairs: pd.DataFrame, risk_threshold_km: float = 50.0) -> pd.DataFrame:
    """
    Soft scoring: exponential decay so we avoid 'all zeros'.
    - 0 km → 1.0
    - 50 km → ~0.37
    - 100 km → ~0.14, etc.
    Also produce a simple 0/1 class for "very close" pairs (< 20% of threshold).
    """
    if df_pairs.empty:
        return df_pairs.assign(risk_score=[], risk_class=[])

    df = df_pairs.copy()
    scale = risk_threshold_km
    df["risk_score"] = np.exp(-df["min_dist_km"] / scale)
    df["risk_class"] = (df["min_dist_km"] < (0.2 * scale)).astype(int)  # e.g., <10 km if scale=50
    return df.sort_values("risk_score", ascending=False)
