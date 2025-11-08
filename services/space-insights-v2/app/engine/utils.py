from typing import List, Tuple

def reason(code: str, summary: str) -> Tuple[str, str]:
    return code, summary

def confidence_from_quality(tle_age_hours: float, coverage_gaps: bool, blackouts: int) -> float:
    base = 0.95
    if tle_age_hours > 48: base -= 0.1
    if tle_age_hours > 72: base -= 0.15
    if coverage_gaps: base -= 0.05
    base -= min(blackouts * 0.02, 0.1)
    return max(0.2, min(0.99, base))

def format_time_to_action(alert_window_hours: int) -> str:
    return f"{alert_window_hours - 1} hours" if alert_window_hours > 1 else "now"

REASON_TEXT = {
    "GEOM_SEP_GROWING": "Separation increasing after next orbit",
    "COV_SMALL": "Covariance ellipsoids do not overlap (1–3σ)",
    "REL_VEL_PROFILE_SAFE": "Relative velocity profile is tangent/diverging",
    "REG_BUFFER_OK": "Above regulatory keep-out threshold",
}
