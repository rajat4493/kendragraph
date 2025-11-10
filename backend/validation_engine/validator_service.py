import os, json, datetime as dt
from pathlib import Path
from typing import Dict, List
from .cdm_fetcher import SpaceTrackClient
from .normalizer import parse_kvn_blocks, normalize_cdm
from .pair_matcher import match
from .metrics_calculator import compute_metrics
from datetime import datetime, timezone

LOG_DIR = Path("logs/validation")

def run_validation(start: dt.datetime, end: dt.datetime, preds: List[Dict], tca_window_s=300, dist_window_km=1.0) -> Dict:
    st = SpaceTrackClient(os.environ["ST_USERNAME"], os.environ["ST_PASSWORD"])
    raw = st.fetch_cdm_public(start, end)
    blocks = list(parse_kvn_blocks(raw))
    cdms = [normalize_cdm(b) for b in blocks]
    # parse ISO tca in preds to datetime if needed
    for p in preds:
        if isinstance(p["tca_utc"], str):
            p["tca_utc"] = dt.datetime.fromisoformat(p["tca_utc"].replace("Z","+00:00"))
    matches = match(preds, cdms, tca_window_s, dist_window_km)
    metrics = compute_metrics(matches)
    # persist
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    run_file = LOG_DIR / f"runs/{dt.datetime.utcnow():%Y%m%dT%H%M%SZ}.jsonl"
    run_file.parent.mkdir(parents=True, exist_ok=True)
    with run_file.open("a") as f:
        for m in matches:
            f.write(json.dumps(m, default=str) + "\n")
    (LOG_DIR/"summary").mkdir(exist_ok=True)
    with (LOG_DIR/"summary/latest.json").open("w") as f:
        json.dump({"window": [start.isoformat(), end.isoformat()], "metrics": metrics}, f)
    return {"window": [start.isoformat(), end.isoformat()], "metrics": metrics}
