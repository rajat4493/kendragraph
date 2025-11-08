import math
from typing import Dict

def projected_separation(min_dist_km: float, rel_vel_kms: float, orbits: int = 1) -> float:
    # very lightweight placeholder: assume separation grows modestly if tangent/diverging
    growth = max(0.0, 0.2 * orbits * (1.0 + (rel_vel_kms / 7.5)))
    return max(0.0, min_dist_km + growth)

def sigma_overlap(cov_major_km: float, cov_minor_km: float, threshold_km: float) -> bool:
    # simple ellipse “radius” check vs threshold
    # if the ellipse's equivalent radius exceeds threshold, consider potential overlap true
    equiv_radius = math.sqrt(max(cov_major_km, 1e-6) * max(cov_minor_km, 1e-6))
    return equiv_radius >= threshold_km

def rel_vel_tangent_or_diverging(rel_vel_kms: float) -> bool:
    # crude: < 2 km/s we treat as "safer profile" (often tangent/slow closing)
    return rel_vel_kms < 2.0

def dv_to_phase_align_ms() -> float:
    # tiny along-track Δv that can alter phasing meaningfully for counterfactuals
    return 0.1  # m/s
