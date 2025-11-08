from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field

RiskClass = Literal[0, 1]  # 0=low, 1=high

class Features(BaseModel):
    norad_id_a: int
    norad_id_b: int
    name_a: Optional[str] = None
    name_b: Optional[str] = None
    tca_utc: str
    min_dist_km: float
    rel_vel_kms: float
    raan_deg_a: Optional[float] = None
    raan_deg_b: Optional[float] = None
    inc_deg_a: Optional[float] = None
    inc_deg_b: Optional[float] = None
    alt_km_a: Optional[float] = None
    alt_km_b: Optional[float] = None

    # Uncertainty / data quality
    tle_age_hours: Optional[float] = 24.0
    cov_major_km: Optional[float] = 0.5
    cov_minor_km: Optional[float] = 0.2
    cov_angle_deg: Optional[float] = 0.0
    coverage_gaps: Optional[bool] = False
    blackouts: Optional[int] = 0

class Prediction(BaseModel):
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_class: RiskClass

class Context(BaseModel):
    reg_threshold_km: float = 0.5
    alert_window_hours: int = 48
    operator_a: Optional[str] = None
    operator_b: Optional[str] = None

class InsightBlock(BaseModel):
    insight_summary: str
    confidence_level: float
    root_cause: Optional[str] = None
    historical_similarity: Optional[str] = None
    recommended_action: Optional[str] = None
    time_to_action: Optional[str] = None
    impact_zone: Optional[str] = None

class WhyNotReason(BaseModel):
    code: str
    summary: str

class Counterfactual(BaseModel):
    description: str
    minimal_change: Dict[str, float]
    plausibility: Literal["low", "medium", "high"]
    path: Optional[str] = None
    monitor: Optional[str] = None

class WhyNotBlock(BaseModel):
    verdict: Literal["Low risk", "High risk"]
    primary_reasons: List[WhyNotReason]
    supporting_facts: Dict[str, float | bool | str]
    counterfactual: List[Counterfactual]
    assumptions: List[str]
    data_quality: Dict[str, float | bool | str]
    watch_items: List[Dict[str, str]]
    audit_tags: List[str]

class AugmentedResponse(BaseModel):
    features: Features
    prediction: Prediction
    context: Context
    insight: InsightBlock
    why_not: WhyNotBlock
