from typing import List, Dict
from .physics import projected_separation, sigma_overlap, rel_vel_tangent_or_diverging, dv_to_phase_align_ms
from .utils import REASON_TEXT, confidence_from_quality
from ..schemas import Features, Prediction, Context, WhyNotBlock, WhyNotReason, Counterfactual

def derive_reasons(f: Features, ctx: Context) -> List[WhyNotReason]:
    reasons = []
    d_next = projected_separation(f.min_dist_km, f.rel_vel_kms, orbits=1)
    if d_next > f.min_dist_km:
        reasons.append(WhyNotReason(code="GEOM_SEP_GROWING", summary=REASON_TEXT["GEOM_SEP_GROWING"]))
    if not sigma_overlap(f.cov_major_km or 0.5, f.cov_minor_km or 0.2, threshold_km=ctx.reg_threshold_km):
        reasons.append(WhyNotReason(code="COV_SMALL", summary=REASON_TEXT["COV_SMALL"]))
    if rel_vel_tangent_or_diverging(f.rel_vel_kms):
        reasons.append(WhyNotReason(code="REL_VEL_PROFILE_SAFE", summary=REASON_TEXT["REL_VEL_PROFILE_SAFE"]))
    if f.min_dist_km > ctx.reg_threshold_km:
        reasons.append(WhyNotReason(code="REG_BUFFER_OK", summary=REASON_TEXT["REG_BUFFER_OK"]))
    return reasons[:3] if reasons else [WhyNotReason(code="PRED_AGREEMENT", summary="Models agree on low risk")]

def counterfactuals(f: Features, ctx: Context) -> List[Counterfactual]:
    cfs: List[Counterfactual] = []

    # CF1: geometric minimum distance reduction
    delta_needed = max(0.0, f.min_dist_km - ctx.reg_threshold_km + 0.01)
    if delta_needed > 0:
        cfs.append(Counterfactual(
            description=f"Would become high risk if min distance < {ctx.reg_threshold_km:.2f} km",
            minimal_change={"delta_min_dist_km": -delta_needed},
            plausibility="low" if delta_needed > 1.0 else "medium",
            path="phase shift + RAAN precession anomaly"
        ))

    # CF2: covariance inflation due to stale TLEs
    cfs.append(Counterfactual(
        description="High risk if covariance grows 3× (e.g., TLE age > 72h or solar activity spike)",
        minimal_change={"covariance_scale": 3.0},
        plausibility="medium",
        monitor="Refresh ephemeris before next two orbits"
    ))

    # CF3: slight along-track Δv alignment by the counterpart
    cfs.append(Counterfactual(
        description="High risk if small along-track Δv aligns phasing",
        minimal_change={"dv_ms": dv_to_phase_align_ms()},
        plausibility="low",
        path="opponent executes uncoordinated 0.1 m/s along-track burn"
    ))
    return cfs[:3]

def monitors(facts: Dict[str, float | bool | str]) -> List[Dict[str, str]]:
    items = []
    if float(facts.get("tle_age_hours", 0)) > 48:
        items.append({"condition": "tle_age_hours > 48", "action": "force ephemeris refresh"})
    if facts.get("sigma_overlap") is True:
        items.append({"condition": "sigma_overlap == true", "action": "escalate to analyst"})
    return items

def make_why_not(f: Features, p: Prediction, ctx: Context) -> WhyNotBlock:
    facts = {
        "min_dist_km": f.min_dist_km,
        "rel_velocity_kms": f.rel_vel_kms,
        "sigma_overlap": sigma_overlap(f.cov_major_km or 0.5, f.cov_minor_km or 0.2, threshold_km=ctx.reg_threshold_km),
        "d_sep_next_orbit_km": projected_separation(f.min_dist_km, f.rel_vel_kms, 1),
        "tle_age_hours": f.tle_age_hours or 24.0,
        "ephemeris_quality": "good" if (f.tle_age_hours or 24.0) <= 48 else "stale"
    }
    conf = confidence_from_quality(float(facts["tle_age_hours"]), False, int(f.blackouts or 0))

    reasons = derive_reasons(f, ctx)
    cfs = counterfactuals(f, ctx)
    watch = monitors(facts)

    return WhyNotBlock(
        verdict="High risk" if p.risk_class == 1 else "Low risk",
        primary_reasons=reasons,
        supporting_facts=facts,
        counterfactual=cfs,
        assumptions=[
            "No unplanned maneuvers before TCA",
            "Ephemeris within historical error bounds for both operators"
        ],
        data_quality={
            "ephemeris_age_hours": facts["tle_age_hours"],
            "coverage_gaps": f.coverage_gaps or False,
            "downlink_blackouts": f.blackouts or 0,
            "confidence": round(conf, 2)
        },
        watch_items=watch,
        audit_tags=["exoneration", "explainability"] + (["data_quality_ok"] if conf > 0.8 else ["needs_review"])
    )
