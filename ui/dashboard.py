import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
import streamlit as st
import pandas as pd
import numpy as np
import pathlib
from datetime import datetime, timezone

# Optional: allow quick recompute for a small batch without leaving the UI.
# (Uses your existing pipeline code.)
from engine.data_refresh import fetch_active_tles
from adapters.space_adapter import load_tle_txt
from engine.fast_pairs import min_distance_over_window
from engine.score_baseline import apply_baseline

st.set_page_config(page_title="KendraGraph", layout="wide")

# ---------- Helpers ----------
DATA_PARQUET = pathlib.Path("data/processed/top_pairs.parquet")
LAST_FETCH = pathlib.Path("data/raw/last_fetch.txt")
TLE_FILE = pathlib.Path("data/raw/active.txt")

@st.cache_data(show_spinner=False)
def load_results() -> pd.DataFrame:
    if DATA_PARQUET.exists():
        return pd.read_parquet(DATA_PARQUET)
    return pd.DataFrame(columns=["norad_id_a","norad_id_b","min_dist_km","tca_utc","risk_score","risk_class","name_a","name_b"])

def fmt_dt(dt_str: str) -> str:
    try:
        return datetime.fromisoformat(dt_str.replace("Z","")).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return dt_str

def badge(value, color="green"):
    st.markdown(f"<span style='background:{color};padding:2px 8px;border-radius:12px;color:white;font-weight:600'>{value}</span>", unsafe_allow_html=True)

# ---------- Sidebar ----------
st.sidebar.title("Controls")
top_n = st.sidebar.slider("Rows to show", 20, 500, 100, 10)
radius_km = st.sidebar.slider("Proximity radius (km)", 20, 200, 100, 10)
hours = st.sidebar.slider("Look-ahead window (hours)", 3, 24, 12, 3)
risk_scale = st.sidebar.slider("Risk decay scale (km)", 20, 100, 50, 5)

st.sidebar.markdown("---")
with st.sidebar.expander("Quick Recompute (demo-safe)"):
    st.caption("Runs a small batch so it stays fast on laptop.")
    recalc_count = st.number_input("Satellites to include", 50, 1000, 300, 50)
    if st.button("Refresh TLEs + Recompute"):
        with st.spinner("Fetching live TLEs and recomputing…"):
            fetch_active_tles()
            df_tle = load_tle_txt(str(TLE_FILE)).head(int(recalc_count))
            df_pairs = min_distance_over_window(df_tle, hours=int(hours), step_min=60, radius_km=float(radius_km))
            scored = apply_baseline(df_pairs, risk_threshold_km=float(risk_scale))
            name_map = {int(r.norad_id): str(r.name) for r in df_tle.itertuples()}
            scored["name_a"] = scored["norad_id_a"].map(name_map)
            scored["name_b"] = scored["norad_id_b"].map(name_map)
            DATA_PARQUET.parent.mkdir(parents=True, exist_ok=True)
            scored.to_parquet(DATA_PARQUET)
            st.success(f"Recomputed {len(scored)} pairs.")
            st.session_state["_force_rerun"] = True

# ---------- Header ----------
st.title("KendraGraph — Risk Radar")

cols = st.columns([2,2,2,3])
with cols[0]:
    if LAST_FETCH.exists():
        st.caption("Last TLE refresh")
        badge(fmt_dt(LAST_FETCH.read_text()), "#0E7C66")
    else:
        st.caption("Last TLE refresh")
        badge("Unknown", "#7c0e0e")
with cols[1]:
    df = load_results()
    st.caption("Pairs evaluated")
    badge(f"{len(df):,}", "#1F4B99")
with cols[2]:
    st.caption("Top risk score")
    top_score = float(df["risk_score"].max()) if not df.empty else 0.0
    badge(f"{top_score:.3f}", "#B35C00")
with cols[3]:
    st.caption("Download")
    st.download_button("CSV (Top N)", df.head(top_n).to_csv(index=False).encode("utf-8"), file_name="kendragraph_top_pairs.csv")

st.markdown("---")

# ---------- Tabs ----------
tab_overview, tab_explorer, tab_3d, tab_about = st.tabs(["Overview", "Explorer", "3D View", "About"])

# -------- Overview --------
with tab_overview:
    st.subheader("Top Risky Pairs")
    if df.empty:
        st.info("No data yet. Use the sidebar ‘Refresh TLEs + Recompute’.")
    else:
        view = df.head(top_n)[["norad_id_a","name_a","norad_id_b","name_b","min_dist_km","tca_utc","risk_score","risk_class"]]
        st.dataframe(view, use_container_width=True, height=480)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Avg min distance (km)", f"{df['min_dist_km'].mean():.1f}")
        with c2:
            st.metric("Closest observed (km)", f"{df['min_dist_km'].min():.2f}")
        with c3:
            st.metric("Very-close pairs (<10km est.)", int((df['min_dist_km'] < 10).sum()))

# -------- Explorer --------
with tab_explorer:
    st.subheader("Filter & Inspect")
    if df.empty:
        st.info("No data yet.")
    else:
        # simple filters
        max_dist = st.slider("Max distance to keep (km)", 5, 500, 150, 5)
        q = st.text_input("Search by NORAD ID or Name")
        dff = df[df["min_dist_km"] <= max_dist].copy()
        if q:
            ql = q.lower()
            mask = (
                dff["name_a"].fillna("").str.lower().str.contains(ql) |
                dff["name_b"].fillna("").str.lower().str.contains(ql) |
                dff["norad_id_a"].astype(str).str.contains(q) |
                dff["norad_id_b"].astype(str).str.contains(q)
            )
            dff = dff[mask]
        st.dataframe(dff.head(top_n), use_container_width=True, height=520)

# -------- 3D View --------
with tab_3d:
    st.subheader("Approx 3D Positions (closest pairs only)")
    if df.empty:
        st.info("No data yet.")
    else:
        # For a lightweight 3D view, approximate positions by placing pairs along axes
        # (True ECI positions are available in engine.fast_pairs; for speed, we pseudo-plot here)
        import plotly.express as px
        top_close = df.nsmallest(min(200, len(df)), "min_dist_km").copy()
        # Fake small offset so nodes don't overlap in the scatter
        rng = np.random.default_rng(42)
        top_close["x"] = rng.normal(0, 1, len(top_close)) * 10 + top_close["min_dist_km"] * 0.2
        top_close["y"] = rng.normal(0, 1, len(top_close)) * 10
        top_close["z"] = rng.normal(0, 1, len(top_close)) * 10
        top_close["label"] = top_close["name_a"].fillna(top_close["norad_id_a"].astype(str)) + " ↔ " + \
                              top_close["name_b"].fillna(top_close["norad_id_b"].astype(str))
        fig = px.scatter_3d(
            top_close, x="x", y="y", z="z",
            color="risk_score",
            size=np.maximum(6 - (top_close["min_dist_km"]/50), 2),
            hover_name="label",
            hover_data={"min_dist_km":":.2f","tca_utc":True,"risk_score":":.3f","x":False,"y":False,"z":False},
            title="Not-to-scale preview (use for intuitive clustering only)"
        )
        fig.update_traces(marker=dict(opacity=0.8))
        fig.update_layout(height=640)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Note: This is a lightweight illustrative view. For true ECI coordinates, we can wire real positions from the propagation step (heavier).")
# -------- Globe --------
tab_globe = st.tabs(["Globe"])[0]
with tab_globe:
    st.subheader("Live Earth View (sub-points of Top-N satellites)")

    try:
        import plotly.graph_objects as go
        from skyfield.api import EarthSatellite, load, wgs84
        from adapters.space_adapter import load_tle_txt

        # 1) Take the Top-N pairs currently shown
        shown = df.head(top_n).copy()
        ids = set(shown["norad_id_a"].tolist() + shown["norad_id_b"].tolist())

        # 2) Load TLEs and build quick lookup
        df_tle = load_tle_txt(str(TLE_FILE))
        tle_map = {int(r.norad_id): (str(r.l1), str(r.l2), str(r.name)) for r in df_tle.itertuples() if int(r.norad_id) in ids}

        if not tle_map:
            st.info("No TLEs found for current selection. Try recalculating.")
        else:
            # 3) Compute current sub-point (lat/lon/alt) for each satellite
            ts = load.timescale()
            t_now = ts.from_datetime(datetime.now(timezone.utc))
            points = []
            for nid, (l1, l2, nm) in tle_map.items():
                sat = EarthSatellite(l1, l2, nm, ts)
                geo = sat.at(t_now)
                sp = wgs84.subpoint(geo)
                points.append({
                    "norad_id": nid,
                    "name": nm,
                    "lat": sp.latitude.degrees,
                    "lon": sp.longitude.degrees,
                    "alt_km": sp.elevation.km
                })
            dfg = pd.DataFrame(points)

            # 4) Plot globe with points + pair lines
            fig = go.Figure()

            # Base Earth (orthographic globe)
            fig.update_geos(
                projection_type="orthographic",
                showcountries=True,
                showcoastlines=True,
                showland=True,
                landcolor="rgb(230,230,230)",
            )

            # Points: satellites’ sub-points
            fig.add_trace(go.Scattergeo(
                lat=dfg["lat"], lon=dfg["lon"],
                text=dfg["name"],
                hovertemplate="<b>%{text}</b><br>lat: %{lat:.2f}°, lon: %{lon:.2f}°<br>alt: %{customdata:.0f} km<extra></extra>",
                customdata=np.stack([dfg["alt_km"]], axis=1),
                mode="markers",
                marker=dict(size=6, opacity=0.9),
                name="Satellites"
            ))

            # Lines: connect each pair (approx on surface great-circle)
            # (This is illustrative; it connects ground sub-points.)
            lines = []
            for _, r in shown.iterrows():
                a = dfg[dfg["norad_id"] == r["norad_id_a"]]
                b = dfg[dfg["norad_id"] == r["norad_id_b"]]
                if len(a) and len(b):
                    lines.append(go.Scattergeo(
                        lat=[float(a["lat"]), float(b["lat"])],
                        lon=[float(a["lon"]), float(b["lon"])],
                        mode="lines",
                        line=dict(width=1),
                        opacity=0.5,
                        hoverinfo="skip",
                        showlegend=False
                    ))
            for ln in lines: fig.add_trace(ln)

            fig.update_layout(height=650, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Note: Points are current sub-points (ground tracks). Lines connect sub-points for the shown pairs. For full orbit arcs we can add propagated tracks next.")
    except Exception as e:
        st.warning(f"Globe view unavailable: {e}")


# -------- About --------
with tab_about:
    st.subheader("What am I seeing?")
    st.markdown("""
**KendraGraph** finds the closest satellite pairs in a short time window and assigns a *smooth risk score*:

- Positions predicted with SGP4 at hourly steps.
- Pairs within a radius (sidebar) found with a fast spatial index.
- Risk = `exp(-distance/scale)` so closer pairs get higher scores.
- This UI is a demo shell; the real product exposes a clean API for operators and insurers.

**Tips**
- Use “Refresh TLEs + Recompute” for a quick live update.
- Tweak *radius* and *risk scale* to change sensitivity.
- Download CSV to share results.
    """)

# Rerun after recompute
if st.session_state.get("_force_rerun"):
    st.session_state["_force_rerun"] = False
    st.experimental_rerun()
