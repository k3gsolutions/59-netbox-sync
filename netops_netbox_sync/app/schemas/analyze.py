from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.compliance import (
    ComplianceSummary,
    ComplianceDivergence,
    SummaryDiffItem,
)


class AppliedInventorySummary(BaseModel):
    interfaces: int = 0
    ip_addresses: int = 0
    vrfs: int = 0
    vlans: int = 0
    bgp_sessions: int = 0
    route_policies: int = 0
    prefix_lists: int = 0
    as_path_filters: int = 0
    communities: int = 0
    community_lists: int = 0


class AnalyzeWarning(BaseModel):
    code: str
    severity: str
    message: str


class AnalyzeResult(BaseModel):
    hostname: str
    device_id: Optional[int] = None
    mode: str = "read-only"
    netbox_loaded: bool = False
    compliance_enabled: bool = False
    applied_summary: AppliedInventorySummary
    documented_summary: Optional[AppliedInventorySummary] = None
    compliance_summary: Optional[ComplianceSummary] = None
    summary_diff: List[SummaryDiffItem] = Field(default_factory=list)
    divergences: List[ComplianceDivergence] = Field(default_factory=list)
    warnings: List[AnalyzeWarning] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)


AppliedSummary = AppliedInventorySummary
