# backend/validation_engine/validator_service.py

from __future__ import annotations

import os
import json
import datetime as dt
from datetime import timezone
from pathlib import Path
from typing import Dict, List

from .cdm_fetcher import SpaceTrackClient, has_spacetrack_creds
from .pair_matcher import match
from .metrics_calculator import compute_metrics

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
LOG_DIR = Path("logs/validation")
RUNS_DIR = LOG_DIR / "runs"
SUMMARY_DIR = LOG_DIR / "summary"
PRED_DIR = Path("logs/predictions")  # your engine should write *.jsonl here


# -----------------------------------------------------------------------------
# Small helpers
# -----------------------------------------------------------------------------
def _iter_jsonl(p: Path):
    with p.open() as f:
        for line in f:
            s = line.strip()
            if s:
                yield json.loads(s)


def _to_int(x):
    try:
        return int(x)
    except Exception:
        return None


def _to_float(x):
    try:
        return float(x)
    except Exception:
        return None


def _to_dt(x):
    if not x:
        return None
    # Normalize to timezone-aware UTC
    return dt.datetime.fromisoformat(str(x).replace("Z", "+00:00")).astimezone(timezone.utc)


# -----------------------------------------------------------------------------
# Predictions loader (by time window)
# -----------------------------------------------------------------------------
def load_predictions_by_window(start: dt.datetime, end: dt.datetime) -> List[Dict]:
    """
    Scan logs/predictions/*.jsonl and collect records whose tca_utc falls within [start, end].
    Expected fields in each record (at minimum):
      - norad_id_a, norad_id_b (or norad_a/norad_b if your writer used those)
      - tca_utc (ISO string)
      - min_dist_km, risk_score, risk_class (optional but useful)
    """
    preds: List[Dict] = []
    if not PRED_DIR.exists():
        return preds

    for file in sorted(PRED_DIR.glob("*.jsonl")):
        for rec in _iter_jsonl(file):
            t = rec.get("tca_utc")
            if not t:
                continue
            t_dt = _to_dt(t)
            if not t_dt:
                continue
            if start <= t_dt <= end:
                # Standardize field names if needed
                if "norad_id_a" not in rec and "norad_a" in rec:
                    rec["norad_id_a"] = rec["norad_a"]
                if "norad_id_b" not in rec and "norad_b" in rec:
                    rec["norad_id_b"] = rec["norad_b"]
                rec["tca_utc"] = t_dt
                preds.append(rec)
    return preds


# -----------------------------------------------------------------------------
# Core runner
# -----------------------------------------------------------------------------
def run_validation(
    start: dt.datetime,
    end: dt.datetime,
    tca_window_s: int = 300,
    dist_window_km: float = 1.0,
) -> Dict:
    """
    Main validation entrypoint.
    - Loads predictions from disk for [start, end]
    - Fetches Space-Track CDMs (if creds available), otherwise offline mode
    - Matches predictions↔CDMs and computes metrics
    - Writes per-run matches JSONL and summary/latest.json
    """
    # Ensure inputs are timezone-aware UTC
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    else:
        start = start.astimezone(timezone.utc)

    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    else:
        end = end.astimezone(timezone.utc)

    # 1) Load predictions
    preds = load_predictions_by_window(start, end)

    # 2) Fetch CDMs (online if creds; else offline)
    cdms: List[Dict] = []
    note: str | None = None

    if has_spacetrack_creds():
        try:
            st = SpaceTrackClient(os.environ["ST_USERNAME"], os.environ["ST_PASSWORD"])
            items = st.fetch_cdm_public_json(start, end, orderby="TCA asc")
            # Normalize JSON items to our internal schema
            for it in items or []:
                cdms.append(
                    {
                        "cdm_id": it.get("MESSAGE_ID"),
                        "norad_primary": _to_int(
                            it.get("OBJECT1_NORAD_CAT_ID") or it.get("OBJECT1_OBJECT_DESIGNATOR")
                        ),
                        "norad_secondary": _to_int(
                            it.get("OBJECT2_NORAD_CAT_ID") or it.get("OBJECT2_OBJECT_DESIGNATOR")
                        ),
                        "tca_utc": _to_dt(it.get("TCA")),
                        "miss_distance_km": _to_float(it.get("MISS_DISTANCE")),
                        "rel_speed_kms": _to_float(it.get("RELATIVE_SPEED")),
                        "provider": "space-track",
                    }
                )
        except Exception as e:
            note = f"Space-Track fetch failed; running offline. error={e!s}"
    else:
        note = "No Space-Track credentials; running offline (no CDMs)."

    # 3) Match + metrics
    # pair_matcher.match expects:
    #   preds: [{'norad_id_a','norad_id_b','tca_utc','min_dist_km','closing_velocity_kms',...}]
    #   cdms : [{'norad_primary','norad_secondary','tca_utc','miss_distance_km','rel_speed_kms',...}]
    matches = match(preds, cdms, tca_window_s=tca_window_s, dist_window_km=dist_window_km)
    metrics = compute_metrics(matches)

    # 4) Persist artifacts
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

    run_file = RUNS_DIR / f"{dt.datetime.utcnow():%Y%m%dT%H%M%SZ}.jsonl"
    with run_file.open("a") as f:
        for m in matches:
            # JSON-serialize datetimes to ISO strings
            m_ser = json.loads(json.dumps(m, default=_serialize_dt))
            f.write(json.dumps(m_ser) + "\n")

    summary_payload = {
        "window": [start.isoformat(), end.isoformat()],
        "metrics": metrics,
    }
    if note:
        summary_payload["note"] = note

    with (SUMMARY_DIR / "latest.json").open("w") as f:
        json.dump(summary_payload, f)

    # 5) Return response
    return summary_payload


# -----------------------------------------------------------------------------
# Misc
# -----------------------------------------------------------------------------
def _serialize_dt(o):
    if isinstance(o, dt.datetime):
        # Always ISO with Z
        return o.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return o
