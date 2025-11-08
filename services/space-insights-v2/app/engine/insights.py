from .utils import confidence_from_quality, format_time_to_action
from ..schemas import Features, Prediction, Context, InsightBlock

def explain_root_cause(f: Features) -> str:
    parts = []
    if f.inc_deg_a is not None and f.inc_deg_b is not None:
        if abs(f.inc_deg_a - f.inc_deg_b) < 0.5:
            parts.append("shared inclination")
    if f.alt_km_a and f.alt_km_b and abs(f.alt_km_a - f.alt_km_b) < 10:
        parts.append("tight altitude band")
    if f.raan_deg_a and f.raan_deg_b and abs(f.raan_deg_a - f.raan_deg_b) < 1:
        parts.append("similar RAAN")
    return " and ".join(parts) or "nominal geometry and traffic density"

def recommended_action(pred: Prediction, ctx: Context, f: Features) -> str:
    if pred.risk_class == 1:
        if f.min_dist_km <= ctx.reg_threshold_km:
            return "Plan avoidance maneuver (lateral or radial) within next orbit."
        return "Increase tracking cadence and prepare maneuver window."
    # low risk
    return "No maneuver; monitor ephemeris freshness and covariance growth."

def impact_zone_stub(f: Features) -> str:
    # Placeholder until you wire a proper ground track mapper
    return "Polar segment (approx.), descending node"

def make_insight(f: Features, p: Prediction, ctx: Context) -> InsightBlock:
    conf = confidence_from_quality(f.tle_age_hours or 24.0, f.coverage_gaps or False, f.blackouts or 0)
    summary = (
        f"Conjunction between {f.name_a or f.norad_id_a} and {f.name_b or f.norad_id_b} "
        f"at ~{f.min_dist_km:.2f} km (TCA {f.tca_utc}); model risk={p.risk_score:.2f}."
    )
    return InsightBlock(
        insight_summary=summary,
        confidence_level=conf,
        root_cause=explain_root_cause(f),
        historical_similarity=None,  # hook for your memory layer
        recommended_action=recommended_action(p, ctx, f),
        time_to_action=format_time_to_action(ctx.alert_window_hours),
        impact_zone=impact_zone_stub(f),
    )
