import os, datetime as dt
from typing import List, Dict, Any
import requests

SPACE_TRACK = "https://www.space-track.org"
# Use the 'spacetrack' Python client if you prefer; both are fine.

class SpaceTrackClient:
    def __init__(self, user: str, pwd: str):
        self.s = requests.Session()
        self.user, self.pwd = user, pwd
        self._login()

    def _login(self):
        r = self.s.post(f"{SPACE_TRACK}/ajaxauth/login", data={"identity": self.user, "password": self.pwd})
        r.raise_for_status()

    def fetch_cdm_public(self, start: dt.datetime, end: dt.datetime, limit: int = 10000) -> str:
        # KVN is compact; JSON is also available depending on controller.
        # Example CDM public controller (subject to account privileges/rate limits).
        # See Space-Track docs for query forms and rate limits.
        qs = (
          f"/expandedspacedata/query/class/cdm_public/"
          f"epoch/{start:%Y-%m-%d}--{end:%Y-%m-%d}/"
          f"format/kvn/emptyresult/show"
        )
        r = self.s.get(SPACE_TRACK + qs, timeout=60)
        r.raise_for_status()
        return r.text  # raw KVN
