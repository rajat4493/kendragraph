#!/usr/bin/env python3
"""
run_space_baseline.py
---------------------
Kendragraph v1 baseline runner + Insight Layer V2 enrichment.

Features:
- Works with a single example or a batch input file (JSON/JSONL)
- Calls the Insight + Why-Not FastAPI service to enrich outputs
- Writes raw and enriched results to disk (JSONL)
- Graceful fallback if the service is unavailable

Usage:
  python run_space_baseline.py                           # demo sample
  python run_space_baseline.py --in data/pairs.jsonl     # batch
  python run_space_baseline.py --raw-out logs/raw.jsonl --enriched-out logs/enriched.jsonl
  INSIGHT_URL=http://localhost:8000/conjunctions/insight python run_space_baseline.py
"""

from __future__ import annotations

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import Dict, Iterable, Iterator, List, Optional, Tuple, Any

# ------------------------------------------------------------
# Optional dependency: adapters/insight_client.py
# If not present, we fall back to a tiny inline client.
# ------------------------------------------------------------
INSIGHT_URL = os.environ.get("INSIGHT_URL", "http://localhost:8000/conjunctions/insight")

def _inline_build_insight(features: dict, prediction: dict, context: dict) -> dict:
    """Fallback HTTP client used if adapters.insight_client is not available."""
    import requests
    payload = {"features": features, "prediction": prediction, "context": context}
    r = requests.post(INSIGHT_URL, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()

try:
    from adapters.insight_client import build_insight as _client_build_insight  # type: ignore
    build_insight = _client_build_insight
except Exception:
    build_insight = _inline_build_insight


# ============================================================
# 1) Baseline model (placeholder) — replace with your real v1
# ============================================================

def mock_baseline_infer(pair: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Placeholder inference.
    Replace this with calls into your actual GNN / baseline engine.
    Returns (features_dict, prediction_dict)
    """
    # Input can already contain many of these fields; we just map safely.
    norad_id_a = int(pair.get("norad_id_a", 31698))
    norad_id_b = int(pair.get("norad_id_b", 36605))

    features = {
        "norad_id_a": norad_id_a,
        "norad_id_b": norad_id_b,
        "name_a": pair.get("name_a", "TERRASAR-X"),
        "name_b": pair.get("name_b", "TANDEM-X"),
        "tca_utc": pair.get("tca_utc", "2025-11-08T06:38:48Z"),
        "min_dist_km": float(pair.get("min_dist_km", 0.29)),
        "rel_vel_kms": float(pair.get("rel_vel_kms", 1.2)),
        "raan_deg_a": _to_float(pair.get("raan_deg_a", 123.1)),
        "raan_deg_b": _to_float(pair.get("raan_deg_b", 123.6)),
        "inc_deg_a": _to_float(pair.get("inc_deg_a", 97.44)),
        "inc_deg_b": _to_float(pair.get("inc_deg_b", 97.41)),
        "alt_km_a": _to_float(pair.get("alt_km_a", 514.0)),
        "alt_km_b": _to_float(pair.get("alt_km_b", 514.6)),
        "tle_age_hours": _to_float(pair.get("tle_age_hours", 6.0)),
        "cov_major_km": _to_float(pair.get("cov_major_km", 0.5)),
        "cov_minor_km": _to_float(pair.get("cov_minor_km", 0.2)),
        # Optional telemetry quality flags if you have them:
        "coverage_gaps": bool(pair.get("coverage_gaps", False)),
        "blackouts": int(pair.get("blackouts", 0)),
    }

    # Risk model output — replace with your real scorer
    risk_score = float(pair.get("risk_score", 0.9942))
    risk_class = int(pair.get("risk_class", 1))  # 1 = high-risk

    prediction = {
        "risk_score": risk_score,
        "risk_class": risk_class,
    }
    return features, prediction


# ============================================================
# 2) Insight context & enrichment wrapper
# ============================================================

def insight_context_from_args(args: argparse.Namespace, pair: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the context payload used by the Insight Layer service.
    You can customize thresholds/operator policy here.
    """
    ctx = {
        "reg_threshold_km": args.reg_threshold_km,
        "alert_window_hours": args.alert_window_hours,
    }
    # Optional operator info if present in input
    if "operator_a" in pair:
        ctx["operator_a"] = pair["operator_a"]
    if "operator_b" in pair:
        ctx["operator_b"] = pair["operator_b"]
    return ctx


def enrich_with_insight(features: Dict[str, Any], prediction: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calls the Insight + Why-Not service and returns the enriched JSON.
    If the service is unavailable, raises an exception.
    """
    return build_insight(features, prediction, context)


# ============================================================
# 3) I/O helpers (files, JSONL, etc.)
# ============================================================

def read_pairs_stream(path: Optional[str]) -> Iterator[Dict[str, Any]]:
    """
    Yields dicts. Supports:
      - None (no file): yields a single demo pair
      - .json  : expects a list[dict]
      - .jsonl : one JSON object per line
    """
    if not path:
        yield {}  # demo/defaults in mock_baseline_infer()
        return

    ext = os.path.splitext(path)[1].lower()
    if ext == ".jsonl":
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)
    elif ext == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                for obj in data:
                    yield obj
            elif isinstance(data, dict):
                yield data
            else:
                raise ValueError("Unsupported JSON structure (expect object or list of objects).")
    else:
        raise ValueError(f"Unsupported input extension: {ext}")


def append_jsonl(path: str, obj: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _to_float(x: Any) -> Optional[float]:
    try:
        return None if x is None else float(x)
    except Exception:
        return None


# ============================================================
# 4) Main pipeline
# ============================================================

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Kendragraph baseline runner with Insight + Why-Not enrichment")
    parser.add_argument("--in", dest="in_path", default=None, help="Input file (.json or .jsonl) of candidate pairs")
    parser.add_argument("--raw-out", default="logs/raw.jsonl", help="Where to append raw baseline results (JSONL)")
    parser.add_argument("--enriched-out", default="logs/enriched.jsonl", help="Where to append enriched outputs (JSONL)")
    parser.add_argument("--reg-threshold-km", type=float, default=0.5, help="Regulatory/ops min-distance threshold (km)")
    parser.add_argument("--alert-window-hours", type=int, default=24, help="Ops alert window (hours)")
    parser.add_argument("--print", dest="do_print", action="store_true", help="Print enriched insight blocks to console")
    args = parser.parse_args(argv)

    started = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"🚀 Kendragraph v1 → Insight V2 | start: {started}")
    print(f"• Insight service: {INSIGHT_URL}")
    if args.in_path:
        print(f"• Input: {args.in_path}")
    print(f"• Raw out: {args.raw_out}")
    print(f"• Enriched out: {args.enriched_out}\n")

    count = 0
    enriched_ok = 0

    for pair in read_pairs_stream(args.in_path):
        count += 1

        # 1) Baseline inference (replace with your real pipeline)
        features, prediction = mock_baseline_infer(pair)
        raw_out = {
            "features": features,
            "prediction": prediction,
            "meta": {
                "ts_utc": datetime.utcnow().isoformat().replace("+00:00", "Z")
            }
        }
        append_jsonl(args.raw_out, raw_out)

        # 2) Build context
        context = insight_context_from_args(args, pair)

        # 3) Enrich with Insight + Why-Not
        try:
            enriched = enrich_with_insight(features, prediction, context)
            enriched["meta"] = raw_out["meta"]
            append_jsonl(args.enriched_out, enriched)
            enriched_ok += 1

            if args.do_print:
                print("=== INSIGHT LAYER ===")
                print(json.dumps(enriched.get("insight", {}), indent=2))
                print("\n=== WHY-NOT LAYER ===")
                print(json.dumps(enriched.get("why_not", {}), indent=2))
                print("-" * 60)

        except Exception as e:
            # Service unavailable — continue without blocking the baseline run
            warn = {
                "warning": f"Insight service failed: {e.__class__.__name__}: {e}",
                "pair": {
                    "norad_id_a": features.get("norad_id_a"),
                    "norad_id_b": features.get("norad_id_b"),
                    "tca_utc": features.get("tca_utc"),
                },
                "ts_utc": datetime.utcnow().isoformat().replace("+00:00", "Z")
            }
            append_jsonl(args.enriched_out, warn)
            if args.do_print:
                print(f"[warn] {warn['warning']} for pair {warn['pair']}")

        # (optional) small sleep if you’re hitting a live service
        time.sleep(0.01)

    finished = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"\n✅ Done. processed={count}, enriched_ok={enriched_ok}, start={started}, end={finished}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
