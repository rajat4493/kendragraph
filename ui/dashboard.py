# KendraGraph — Risk Radar (Streamlit thin client)
# Reads ONLY from the API; no direct file access.

import os
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="KendraGraph — Risk Radar", layout="wide")

API = os.getenv("KENDRAGRAPH_API_BASE", "http://127.0.0.1:8000")

# ------------- Data access -------------
@st.cache_data(ttl=30)
def load_top_risks(n: int = 100) -> pd.DataFrame:
    r = requests.get(f"{API}/top-risks", params={"n": n}, timeout=30)
    r.raise_for_status()
    items = r.json()
    df = pd.DataFrame(items)
    if df.empty:
        return df
    # Enforce dtypes
    if "tca_utc" in df.columns:
        df["tca_utc"] = pd.to_datetime(df["tca_utc"], errors="coerce", utc=True)
    for c in ("risk_score", "min_dist_km"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    # Sort to match API (defensive)
    if "risk_score" in df.columns:
        df = df.sort_values("risk_score", ascending=False)
    return df


@st.cache_data(ttl=15)
def health_data() -> dict:
    try:
        r = requests.get(f"{API}/health/data", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# ------------- Sidebar -------------
st.sidebar.header("Controls")
top_n = st.sidebar.slider("Top N pairs", min_value=10, max_value=200, value=50, step=10)
if st.sidebar.button("Clear cache"):
    st.cache_data.clear()

# ------------- Header -------------
st.title("KendraGraph — Risk Radar")

hd = health_data()
cols = st.columns(3)
with cols[0]:
    st.metric("API", API)
with cols[1]:
    if isinstance(hd, dict) and hd.get("exists"):
        st.metric("Pairs evaluated", hd.get("rows", 0))
    else:
        st.metric("Pairs evaluated", 0)
with cols[2]:
    # Will fill after we load df
    st.metric("Top risk score", "—")

st.divider()

# ------------- Top risks table -------------
df = load_top_risks(top_n)

if df.empty:
    st.info("No data yet. Use your recompute step, then refresh.")
else:
    # Update top metric if available
    try:
        top_score = float(df["risk_score"].iloc[0])
        cols[2].metric("Top risk score", f"{top_score:.3f}")
    except Exception:
        pass

    st.subheader("Top Risky Pairs")
    show_cols = [c for c in [
        "norad_id_a", "name_a", "norad_id_b", "name_b",
        "min_dist_km", "tca_utc", "risk_score", "risk_class"
    ] if c in df.columns]

    st.dataframe(df[show_cols], use_container_width=True)

# ------------- Debug -------------
with st.expander("Debug · Data source"):
    st.write({"API": API, "health_data": hd})
    st.write("Preview:", df.head(3) if not df.empty else df)
