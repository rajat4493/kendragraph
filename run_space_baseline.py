# run_space_baseline.py
import pandas as pd
from adapters.space_adapter import load_tle_txt
from engine.build_graph import pairwise_min_distance_over_window
from engine.score_baseline import apply_baseline
from pathlib import Path

RISK_THRESHOLD_KM = 1.0
TLE_FILE = "data/raw/active.txt"   # put a small TLE file here (e.g., active satellites)

df_tle = load_tle_txt(TLE_FILE).head(80)   # start small for speed
df_pairs = pairwise_min_distance_over_window(df_tle, hours=24, step_min=60)
scored = apply_baseline(df_pairs, RISK_THRESHOLD_KM)
Path("data/processed").mkdir(parents=True, exist_ok=True)
scored.to_parquet("data/processed/top_pairs.parquet")
print(scored.head(10))
