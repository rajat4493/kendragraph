import requests

INSIGHT_URL = "http://localhost:8000/conjunctions/insight"

def build_insight(features: dict, prediction: dict, context: dict) -> dict:
    payload = {"features": features, "prediction": prediction, "context": context}
    r = requests.post(INSIGHT_URL, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()
