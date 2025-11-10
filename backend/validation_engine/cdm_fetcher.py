import os
import datetime as dt
import requests

BASE = "https://www.space-track.org"

def has_spacetrack_creds() -> bool:
    return bool(os.getenv("ST_USERNAME")) and bool(os.getenv("ST_PASSWORD"))

class SpaceTrackClient:
    def __init__(self, user: str, pwd: str):
        self.s = requests.Session()
        self.user, self.pwd = user, pwd
        self._login()

    def _login(self):
        r = self.s.post(
            f"{BASE}/ajaxauth/login",
            data={"identity": self.user, "password": self.pwd},
            timeout=30,
        )
        r.raise_for_status()

    def fetch_cdm_public_json(
        self,
        start: dt.datetime,
        end: dt.datetime,
        limit: int | None = None,
        orderby: str | None = "TCA asc",
    ) -> list[dict]:
        """
        Fetch public CDMs from Space-Track in JSON.
        Uses /basicspacedata/query/class/cdm_public with TCA window.
        """
        # Build path segments. Space-Track uses slash-separated params.
        path = [
            "basicspacedata", "query",
            "class", "cdm_public",
            "TCA", f"{start:%Y-%m-%d}--{end:%Y-%m-%d}",
            "format", "json",
        ]
        if orderby:
            path += ["orderby", orderby.replace(" ", "%20")]
        if limit:
            path += ["limit", str(limit)]
        url = f"{BASE}/" + "/".join(path)

        r = self.s.get(url, timeout=60)
        r.raise_for_status()
        return r.json()
