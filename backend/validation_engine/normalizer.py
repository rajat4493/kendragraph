import re, datetime as dt
from typing import Dict, Iterable

def parse_kvn_blocks(kvn_text: str) -> Iterable[Dict]:
    # Simple CDM KVN block parser (key = value)
    block, cur = [], {}
    for line in kvn_text.splitlines():
        line = line.strip()
        if not line:
            if cur: 
                yield cur; cur = {}
            continue
        if "=" in line:
            k, v = [x.strip() for x in line.split("=", 1)]
            cur[k.upper()] = v
    if cur: 
        yield cur

def normalize_cdm(block: Dict) -> Dict:
    # Field names per CDM/CSM guides
    # TCA: TIME_OF_CLOSEST_APPROACH, MISS_DISTANCE, RELATIVE_SPEED, OBJECT_DESIGNATORs/NORAD_CAT_IDs
    def to_int(x): 
        try: return int(x)
        except: return None
    def to_float(x):
        try: return float(x)
        except: return None
    def to_dt(x): 
        return dt.datetime.fromisoformat(x.replace("Z","+00:00"))

    return {
        "cdm_id": block.get("MESSAGE_ID"),
        "norad_primary": to_int(block.get("OBJECT1_OBJECT_DESIGNATOR") or block.get("OBJECT1_NORAD_CAT_ID")),
        "norad_secondary": to_int(block.get("OBJECT2_OBJECT_DESIGNATOR") or block.get("OBJECT2_NORAD_CAT_ID")),
        "tca_utc": to_dt(block["TIME_OF_CLOSEST_APPROACH"]),
        "miss_distance_km": to_float(block.get("MISS_DISTANCE")),
        "rel_speed_kms": to_float(block.get("RELATIVE_SPEED")),
        "provider": "space-track"
    }
