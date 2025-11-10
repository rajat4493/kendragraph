from fastapi import APIRouter
from pydantic import BaseModel
import datetime as dt
from backend.validation_engine.validator_service import run_validation

router = APIRouter(prefix="/v1/validation", tags=["validation"])

class RunReq(BaseModel):
    start: dt.datetime
    end: dt.datetime
    tca_window_s: int = 300
    dist_window_km: float = 1.0
    # For now pass predictions in body or load from your existing store/logs
    predictions: list

@router.post("/run")
def run(body: RunReq):
    res = run_validation(body.start, body.end, body.predictions, body.tca_window_s, body.dist_window_km)
    return res

@router.get("/metrics")
def metrics():
    import json
    with open("logs/validation/summary/latest.json") as f:
        return json.load(f)
