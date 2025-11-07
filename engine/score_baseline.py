import pandas as pd

def apply_baseline(df_pairs: pd.DataFrame, risk_threshold_km: float) -> pd.DataFrame:
    df = df_pairs.copy()
    df["risk_score"] = (df["min_dist_km"].clip(upper=risk_threshold_km) / risk_threshold_km).rsub(1.0)
    # => 1.0 when 0km, 0.0 when >= threshold
    df["risk_class"] = (df["min_dist_km"] < risk_threshold_km).astype(int)
    return df.sort_values(["risk_score"], ascending=False)
