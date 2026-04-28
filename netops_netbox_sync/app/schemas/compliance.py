from typing import Dict, List, Optional

from pydantic import BaseModel


class SummaryDiffItem(BaseModel):
    metric: str
    applied: int
    documented: int
    delta: int
    status: str  # match | mismatch


class ComplianceDivergence(BaseModel):
    code: str
    severity: str
    scope: str
    message: str
    evidence: Dict[str, object]
    recommendation: str
    preferred_action: str  # fix_netbox | fix_device | review
    object_type: Optional[str] = None
    object_key: Optional[str] = None


class ComplianceSummary(BaseModel):
    total_metrics: int
    matching_metrics: int
    mismatching_metrics: int
    status: str  # ok | drift_detected

