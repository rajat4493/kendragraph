"""

KendraGraph — Unified Web API
Purpose:
Expose multiple services (risks, validation, insights) under one FastAPI app.
"""

from fastapi import FastAPI
import pandas as pd

# Import routers
from api.routers import validation  # new validation endpoints

app = FastAPI(title="KendraGraph API", version="v1")

# --------------- Existing Endpoint ---------------
@app.get("/top-risks")
def top_risks(n: int = 50):
    """
    Return the top N risk pairs as JSON.
    Downstream clients can call: /top-risks?n=100
    """
    df = pd.read_parquet("data/processed/top_pairs.parquet")
    return df.head(n).to_dict(orient="records")

# --------------- New Validation API ---------------
app.include_router(validation.router)
