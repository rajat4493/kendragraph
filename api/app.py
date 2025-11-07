"""
KendraGraph — Tiny Web API
Purpose: Let other tools (or your UI) fetch results as JSON.
Why: Treat your analytics like a service from day one.
"""

from fastapi import FastAPI
import pandas as pd

app = FastAPI(title="KendraGraph API")

@app.get("/top-risks")
def top_risks(n: int = 50):
    """
    Return the top N risk pairs as plain JSON.
    Downstream clients can call: /top-risks?n=100
    """
    df = pd.read_parquet("data/processed/top_pairs.parquet")
    return df.head(n).to_dict(orient="records")
