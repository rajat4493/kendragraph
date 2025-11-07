import pandas as pd
from pathlib import Path

def load_tle_txt(tle_path: str) -> pd.DataFrame:
    """Assumes standard 3-line groups: name, L1, L2."""
    lines = Path(tle_path).read_text().strip().splitlines()
    recs = []
    for i in range(0, len(lines), 3):
        name = lines[i].strip()
        l1 = lines[i+1].strip()
        l2 = lines[i+2].strip()
        norad = int(l1[2:7])
        recs.append({"name": name, "norad_id": norad, "l1": l1, "l2": l2})
    return pd.DataFrame(recs)
