"""
KendraGraph — Baseline Risk Scoring
Purpose: Turn "how close did they get?" into a 0–1 risk score.
Why: Even if nothing is <1 km, we still want a ranking: closer = riskier.
"""

import numpy as np
import pandas as pd
from pathlib import Path
import json, datetime as dt

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

    # normalize columns
    if "norad_id_a" not in df_top.columns and "norad_a" in df_top.columns:
        df_top["norad_id_a"] = df_top["norad_a"]
    if "norad_id_b" not in df_top.columns and "norad_b" in df_top.columns:
        df_top["norad_id_b"] = df_top["norad_b"]

    # ensure datetime ISO Z
    if "tca_utc" in df_top.columns:
        df_top["tca_utc"] = pd.to_datetime(df_top["tca_utc"], utc=True, errors="coerce")
        df_top = df_top[df_top["tca_utc"].notna()]
        df_top["tca_utc"] = df_top["tca_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    pred_cols = ["norad_id_a","norad_id_b","tca_utc","min_dist_km","risk_score","risk_class","name_a","name_b"]
    pred_cols = [c for c in pred_cols if c in df_top.columns]
    preds = df_top[pred_cols].copy()

    # write predictions JSONL
    out_dir = Path("logs/predictions"); out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{dt.datetime.utcnow():%Y%m%dT%H%M%SZ}.jsonl"
    with out_file.open("w") as f:
        for rec in preds.to_dict(orient="records"):
            f.write(json.dumps(rec) + "\n")
    print(f"✅ Wrote {len(preds)} predictions → {out_file}")