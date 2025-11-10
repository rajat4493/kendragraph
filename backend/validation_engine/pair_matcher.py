from typing import List, Dict, Tuple
from datetime import datetime, timedelta

def _key(a: int, b: int) -> Tuple[int,int]:
    return tuple(sorted((a,b)))

def match(preds: List[Dict], cdms: List[Dict], tca_window_s=300, dist_window_km=1.0):
    twin = timedelta(seconds=tca_window_s)
    # index CDMs by pair
    by_pair = {}
    for c in cdms:
        by_pair.setdefault(_key(c["norad_primary"], c["norad_secondary"]), []).append(c)
    # greedy time-nearest match
    results, matched_cdm_ids = [], set()
    for p in preds:
        k = _key(p["norad_a"], p["norad_b"])
        candidates = by_pair.get(k, [])
        best, best_dt = None, None
        for c in candidates:
            dt_err = abs(p["tca_utc"] - c["tca_utc"])
            if dt_err <= twin:
                if best is None or dt_err < best_dt:
                    best, best_dt = c, dt_err
        if best:
            if (p.get("min_dist_km") is not None and best.get("miss_distance_km") is not None):
                if abs(p["min_dist_km"] - best["miss_distance_km"]) > dist_window_km:
                    best = None
        if best:
            matched_cdm_ids.add(best["cdm_id"])
            results.append({"type": "TP", "pred": p, "cdm": best})
        else:
            results.append({"type": "FP", "pred": p, "cdm": None})
    # FNs
    pred_keys = { _key(p["norad_a"], p["norad_b"]) for p in preds }
    for c in cdms:
        if c["cdm_id"] not in matched_cdm_ids and _key(c["norad_primary"], c["norad_secondary"]) in pred_keys:
            results.append({"type": "FN", "pred": None, "cdm": c})
    return results
