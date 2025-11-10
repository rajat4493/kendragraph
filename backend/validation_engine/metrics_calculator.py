from typing import Dict, List
from statistics import mean

def compute_metrics(matches: List[Dict]) -> Dict:
    tp = [m for m in matches if m["type"]=="TP"]
    fp = [m for m in matches if m["type"]=="FP"]
    fn = [m for m in matches if m["type"]=="FN"]
    P = len(tp) / max(1, (len(tp)+len(fp)))
    R = len(tp) / max(1, (len(tp)+len(fn)))
    F1 = 0 if P+R==0 else (2*P*R)/(P+R)
    # errors
    def errs():
        out=[]
        for m in tp:
            p, c = m["pred"], m["cdm"]
            t_err = (p["tca_utc"] - c["tca_utc"]).total_seconds()
            d_err = (p.get("min_dist_km") or 0) - (c.get("miss_distance_km") or 0)
            v_err = (p.get("closing_velocity_kms") or 0) - (c.get("rel_speed_kms") or 0)
            out.append((abs(t_err), abs(d_err), abs(v_err)))
        return out
    terr, derr, verr = zip(*errs()) if tp else ([0],[0],[0])
    return {
        "counts": {"tp": len(tp), "fp": len(fp), "fn": len(fn)},
        "precision": P, "recall": R, "f1": F1,
        "mae_seconds_tca": mean(terr), "mae_km_distance": mean(derr), "mae_kms_velocity": mean(verr)
    }
