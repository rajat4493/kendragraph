# backend/validation_engine/metrics_calculator.py
from typing import Dict, List
from statistics import mean

def _counts(matches: List[Dict]):
    tp = [m for m in matches if m["type"]=="TP"]
    fp = [m for m in matches if m["type"]=="FP"]
    fn = [m for m in matches if m["type"]=="FN"]
    return tp, fp, fn

def compute_metrics(matches: List[Dict]) -> Dict:
    tp, fp, fn = _counts(matches)
    P = len(tp) / max(1, (len(tp)+len(fp)))
    R = len(tp) / max(1, (len(tp)+len(fn)))
    F1 = 0 if P+R==0 else (2*P*R)/(P+R)

    # errors on TPs
    terr, derr, verr = [], [], []
    for m in tp:
        p, c = m["pred"], m["cdm"]
        t_err = (p["tca_utc"] - c["tca_utc"]).total_seconds()
        d_err = (p.get("min_dist_km") or 0) - (c.get("miss_distance_km") or 0)
        v_err = (p.get("closing_velocity_kms") or 0) - (c.get("rel_speed_kms") or 0)
        terr.append(abs(t_err)); derr.append(abs(d_err)); verr.append(abs(v_err))

    metrics = {
        "counts": {"tp": len(tp), "fp": len(fp), "fn": len(fn)},
        "precision": P, "recall": R, "f1": F1,
        "mae_seconds_tca": (sum(terr)/len(terr)) if terr else 0,
        "mae_km_distance": (sum(derr)/len(derr)) if derr else 0,
        "mae_kms_velocity": (sum(verr)/len(verr)) if verr else 0,
    }

    # PR curve over risk threshold if risk_score available
    preds = [m["pred"] for m in (tp+fp) if "risk_score" in (m.get("pred") or {})]
    if preds:
        thresholds = [round(x/100, 2) for x in range(0, 101, 5)]
        curve = []
        for t in thresholds:
            t_tp = [m for m in tp if (m["pred"].get("risk_score", 0) >= t)]
            t_fp = [m for m in fp if (m["pred"].get("risk_score", 0) >= t)]
            # FNs are independent of threshold (events you missed entirely)
            P_t = len(t_tp) / max(1, (len(t_tp)+len(t_fp)))
            R_t = len(t_tp) / max(1, (len(tp)+len(fn)))
            curve.append({"thr": t, "precision": P_t, "recall": R_t})
        metrics["pr_curve"] = curve

    return metrics
