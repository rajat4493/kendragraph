import numpy as np, pandas as pd
from datetime import datetime, timedelta, timezone
from sgp4.api import Satrec, jday

def _eci_position_km(rec, when):
    # returns ECI position (km) at datetime `when`
    jd, fr = jday(when.year, when.month, when.day, when.hour, when.minute, when.second + when.microsecond/1e6)
    e, r, v = rec.sgp4(jd, fr)
    if e != 0:  # propagation error
        return None
    return np.array(r)  # km

def propagate_positions(df_tle: pd.DataFrame, when: datetime):
    sats = {}
    for _, row in df_tle.iterrows():
        sat = Satrec.twoline2rv(row["l1"], row["l2"])
        pos = _eci_position_km(sat, when)
        if pos is not None:
            sats[row["norad_id"]] = pos
    return sats

def pairwise_min_distance_over_window(df_tle: pd.DataFrame, hours=24, step_min=30):
    now = datetime.now(timezone.utc)
    times = [now + timedelta(minutes=m) for m in range(0, hours*60, step_min)]
    # pre-propagate all times to avoid repeated SGP4 object creation
    sat_objs = {row["norad_id"]: Satrec.twoline2rv(row["l1"], row["l2"]) for _, row in df_tle.iterrows()}
    def pos_at(sat, when):
        jd, fr = jday(when.year, when.month, when.day, when.hour, when.minute, when.second + when.microsecond/1e6)
        e, r, v = sat.sgp4(jd, fr)
        return None if e!=0 else np.array(r)
    # collect min distances
    ids = list(sat_objs.keys())
    out = []
    for i in range(len(ids)):
        for j in range(i+1, len(ids)):
            id_a, id_b = ids[i], ids[j]
            min_d = None
            min_t = None
            for t in times:
                ra = pos_at(sat_objs[id_a], t); rb = pos_at(sat_objs[id_b], t)
                if ra is None or rb is None: continue
                d = np.linalg.norm(ra - rb)  # km
                if (min_d is None) or (d < min_d):
                    min_d, min_t = d, t
            if min_d is not None:
                out.append({"norad_id_a": id_a, "norad_id_b": id_b, "min_dist_km": float(min_d), "tca_utc": min_t})
    return pd.DataFrame(out)
