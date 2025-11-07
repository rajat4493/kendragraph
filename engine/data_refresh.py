"""
KendraGraph — Data Refresh
Purpose: Download the latest public orbit data (TLEs) from CelesTrak.
Why: Keeps your pipeline "live" so results change as the sky changes.
"""

import pathlib, requests, datetime as dt

# New GP endpoint (recommended)
GP_ACTIVE_TLE = "https://celestrak.org/NORAD/elements/gp.php?GROUP=ACTIVE&FORMAT=TLE"
RAW = pathlib.Path("data/raw"); RAW.mkdir(parents=True, exist_ok=True)

GP_ACTIVE_JSON = "https://celestrak.org/NORAD/elements/gp.php?GROUP=ACTIVE&FORMAT=JSON"

def fetch_active_json(path=RAW/"active.json") -> str:
    r = requests.get(GP_ACTIVE_JSON, timeout=30)
    r.raise_for_status()
    path.write_text(r.text)
    return str(path)

def fetch_active_tles(path=RAW/"active.txt") -> str:
    """Fetch latest GP data in TLE format (works with existing SGP4 code)."""
    r = requests.get(GP_ACTIVE_TLE, timeout=30)
    r.raise_for_status()
    path.write_text(r.text)
    (RAW/"last_fetch.txt").write_text(dt.datetime.utcnow().isoformat()+"Z")
    return str(path)


if __name__ == "__main__":
    # Running this file directly lets you refresh data on demand.
    print("Saved:", fetch_active_tles())
