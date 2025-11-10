"""
KendraGraph — Unified Web API
Purpose: expose risks + validation under one FastAPI app.
"""

from fastapi import FastAPI, Query
import pandas as pd
import pathlib, hashlib
from api.routers import validation

app = FastAPI(title="KendraGraph API", version="v1")


# -------- Health --------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/data")
def data_health():
    p = pathlib.Path("data/processed/top_pairs.parquet")
    if not p.exists():
        return {"exists": False, "rows": 0}
    df = pd.read_parquet(p)
    b = p.read_bytes()
    return {
        "exists": True,
        "rows": int(len(df)),
        "size": p.stat().st_size,
        "mtime": int(p.stat().st_mtime),
        "md5": hashlib.md5(b).hexdigest(),
    }


# -------- Top risks (single source of truth) --------
@app.get("/top-risks")
def top_risks(n: int = Query(50, ge=1, le=1000)):
    p = pathlib.Path("data/processed/top_pairs.parquet")
    if not p.exists():
        return []

    df = pd.read_parquet(p)

    # Normalize to a stable schema the UI expects
    col_map = {
        "norad_a": "norad_id_a",
        "norad_b": "norad_id_b",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    needed = [
        "norad_id_a", "name_a",
        "norad_id_b", "name_b",
        "min_dist_km", "tca_utc",
        "risk_score", "risk_class",
    ]
    have = [c for c in needed if c in df.columns]
    df = df[have].copy()

    # Sort by risk score (desc) so UI order matches
    if "risk_score" in df.columns:
        df = df.sort_values("risk_score", ascending=False)

    # Safety: ensure ISO for datetimes
    if "tca_utc" in df.columns:
        df["tca_utc"] = pd.to_datetime(df["tca_utc"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%S%z")

    return df.head(n).to_dict(orient="records")

app.include_router(validation.router)