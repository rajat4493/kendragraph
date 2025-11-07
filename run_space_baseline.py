"""
KendraGraph — End-to-End Runner (Baseline)
Purpose: Glue everything together:
  1) Fetch latest TLEs
  2) Parse satellites
  3) Predict close pairs (fast)
  4) Score risk
  5) Save for API/UI
"""

from pathlib import Path
import pandas as pd

from engine.data_refresh import fetch_active_tles
from adapters.space_adapter import load_tle_txt
from engine.fast_pairs import min_distance_over_window
from engine.score_baseline import apply_baseline

# 1) Always start with fresh data (live feel).
fetch_active_tles()

# 2) Read satellites; limit count at first so it's fast on a laptop.
TLE_FILE = "data/raw/active.txt"
df_tle = load_tle_txt(TLE_FILE).head(500)  # try 300–1000; increase later

# 3) Find near neighbors over the next 12 hours.
#    Larger radius (e.g., 100 km) gives you more signal to rank.
df_pairs = min_distance_over_window(df_tle, hours=12, step_min=60, radius_km=100.0)

# 4) Convert distances → risk score. Use a soft threshold so results aren't all zero.
scored = apply_baseline(df_pairs, risk_threshold_km=50.0)

# Optional: include human-readable names for each NORAD id.
name_map = {int(r.norad_id): str(r.name) for r in df_tle.itertuples()}
scored["name_a"] = scored["norad_id_a"].map(name_map)
scored["name_b"] = scored["norad_id_b"].map(name_map)

# 5) Save for API/UI.
Path("data/processed").mkdir(parents=True, exist_ok=True)
scored.to_parquet("data/processed/top_pairs.parquet")
print("Saved top_pairs.parquet with", len(scored), "rows.")
print(scored.head(10))
