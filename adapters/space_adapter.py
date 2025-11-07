"""
KendraGraph — Space Adapter
Purpose: Turn the raw TLE text file into a simple table (DataFrame).
Why: Everything downstream expects 'rows' of satellites with IDs and TLE lines.
"""

from pathlib import Path
import pandas as pd

def load_tle_txt(tle_path: str) -> pd.DataFrame:
    """
    TLE files are in 3-line groups: NAME, LINE1, LINE2.
    We parse those into columns: name, norad_id, l1, l2.
    norad_id is extracted from line 1 (columns 3–7 in standard TLEs).
    """
    lines = Path(tle_path).read_text().strip().splitlines()
    recs = []
    for i in range(0, len(lines), 3):
        name = lines[i].strip()
        l1 = lines[i + 1].strip()
        l2 = lines[i + 2].strip()
        # Extract the NORAD catalog number. TLE format guarantees this position.
        norad = int(l1[2:7])
        recs.append({"name": name, "norad_id": norad, "l1": l1, "l2": l2})
    return pd.DataFrame(recs)

def load_gp_json(json_path: str) -> pd.DataFrame:
    data = json.loads(Path(json_path).read_text())
    df = pd.json_normalize(data)   # flattens OMM fields
    # Standardize names to your schema
    # OBJECT_NAME, NORAD_CAT_ID, EPOCH, INCLINATION, ECCENTRICITY, RA_OF_ASC_NODE, ARG_OF_PERICENTER, MEAN_ANOMALY, MEAN_MOTION, BSTAR, etc.
    df = df.rename(columns={
        "OBJECT_NAME": "name",
        "NORAD_CAT_ID": "norad_id"
    })
    return df