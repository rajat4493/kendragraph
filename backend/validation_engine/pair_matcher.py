from typing import List, Dict, Tuple
from datetime import datetime, timedelta

def _as_int(x):
    try:
        return int(x)
    except Exception:
        return None

def _valid_pair(a, b):
    return isinstance(a, int) and isinstance(b, int)

def _key(a: int, b: int) -> Tuple[int, int]:
    # assumes validated ints
    return (a, b) if a <= b else (b, a)

def match(preds: List[Dict], cdms: List[Dict], tca_window_s=300, dist_window_km=1.0):
    twin = timedelta(seconds=tca_window_s)

    # ---- sanitize inputs ----
    clean_preds = []
    for p in preds:
        a = _as_int(p.get("norad_id_a") or p.get("norad_a"))
        b = _as_int(p.get("norad_id_b") or p.get("norad_b"))
        t = p.get("tca_utc")
        if not _valid_pair(a, b) or t is None:
            continue
        p = dict(p)  # shallow copy
        p["norad_id_a"], p["norad_id_b"] = a, b
        clean_preds.append(p)

    clean_cdms = []
    for c in cdms:
        a = _as_int(c.get("norad_primary"))
        b = _as_int(c.get("norad_secondary"))
        t = c.get("tca_utc")
        if not _valid_pair(a, b) or t is None:
            continue
        c = dict(c)
        c["norad_primary"], c["norad_secondary"] = a, b
        clean_cdms.append(c)

    # ---- index CDMs by pair ----
    by_pair: Dict[Tuple[int,int], List[Dict]] = {}
    for c in clean_cdms:
        k = _key(c["norad_primary"], c["norad_secondary"])
        by_pair.setdefault(k, []).append(c)

    # ---- greedy nearest-time match ----
    results, matched_cdm_ids = [], set()
    for p in clean_preds:
        k = _key(p["norad_id_a"], p["norad_id_b"])
        candidates = by_pair.get(k, [])
        best, best_dt = None, None
        for c in candidates:
            dt_err = abs(p["tca_utc"] - c["tca_utc"])
            if dt_err <= twin and (best is None or dt_err < best_dt):
                best, best_dt = c, dt_err

        # optional distance filter
        if best and p.get("min_dist_km") is not None and best.get("miss_distance_km") is not None:
            if abs(float(p["min_dist_km"]) - float(best["miss_distance_km"])) > float(dist_window_km):
                best = None

        if best:
            matched_cdm_ids.add(best.get("cdm_id"))
            results.append({"type": "TP", "pred": p, "cdm": best})
        else:
            results.append({"type": "FP", "pred": p, "cdm": None})

    # ---- FNs: cdms with a matching pair but no pred matched ----
    pred_pairs = { _key(p["norad_id_a"], p["norad_id_b"]) for p in clean_preds }
    for c in clean_cdms:
        if (c.get("cdm_id") not in matched_cdm_ids) and (_key(c["norad_primary"], c["norad_secondary"]) in pred_pairs):
            results.append({"type": "FN", "pred": None, "cdm": c})

    # optional: attach simple diagnostics
    results_meta = {
        "diag": {
            "preds_in": len(preds), "preds_clean": len(clean_preds),
            "cdms_in": len(cdms),   "cdms_clean": len(clean_cdms)
        }
    }
    # You can return meta elsewhere if you want; keeping results list for now.
    return results
