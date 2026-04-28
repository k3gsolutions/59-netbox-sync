from typing import Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field


class ImportAction(str, Enum):
    """Classification of proposed import action."""
    SAFE_CREATE_STAGED = "safe_create_staged"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"
    IGNORE = "ignore"


class ConfidenceLevel(str, Enum):
    """Confidence level for import proposal."""
    EXACT = "exact"
    NORMALIZED = "normalized"
    POSSIBLE = "possible"
    AMBIGUOUS = "ambiguous"
    NONE = "none"


class ImportPlanItem(BaseModel):
    """Single import proposal item from divergence."""
    action: ImportAction
    object_type: str  # interface, ip_address, vrf, vlan, bgp_peer, etc
    object_key: str  # interface name, IP, VRF name, etc
    code: str  # INTERFACE_MISSING_IN_NETBOX, etc
    reason: str  # Classification reason
    evidence: Dict[str, object]  # From divergence evidence
    recommended_payload: Optional[Dict[str, object]] = None  # Suggested object data
    required_fields_missing: List[str] = Field(default_factory=list)
    naming_compliant: bool = False  # Does name follow convention
    confidence: ConfidenceLevel = ConfidenceLevel.NONE
    preferred_next_step: str  # Action for human reviewer
    category: Optional[str] = None  # "base_inventory", "service", etc (for UI grouping)


class ImportPlan(BaseModel):
    """Complete import plan from compliance analysis."""
    device: str  # Hostname or device name
    device_id: Optional[int] = None
    generated_at: str  # ISO8601 timestamp
    source: str = "compliance"  # Where plan comes from

    total_items: int
    safe_create_staged_count: int = 0
    needs_review_count: int = 0
    blocked_count: int = 0
    ignore_count: int = 0

    items: List[ImportPlanItem] = Field(default_factory=list)
