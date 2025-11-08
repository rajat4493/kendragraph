# adapters/insight_client.py
import requests

def build_insight(features: dict, prediction: dict, context: dict) -> dict:
    r = requests.post(
        "http://localhost:8000/conjunctions/insight",
        json={"features": features, "prediction": prediction, "context": context},
        timeout=5,
    )
    r.raise_for_status()
    return r.json()
