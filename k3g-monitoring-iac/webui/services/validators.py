"""Response form validators for FASE 3.9."""

import re
from typing import Dict, List, Tuple, Optional

BLOCKED_KEYWORDS = {'password', 'token', 'secret', 'api_key', 'ssh_key', 'private_key'}
SERVICE_TYPES = {
    'customer-internet', 'customer-l2vpn', 'customer-l3vpn', 'customer-transport',
    'carrier-transit', 'carrier-peering', 'ix-public', 'cdn-cache',
    'infra-backbone', 'infra-management'
}
CRITICALITIES = {'platinum', 'gold', 'silver', 'bronze'}
STATUSES = {'pending', 'answered', 'needs_clarification', 'blocked', 'rejected'}

def contains_blocked_keywords(text: str) -> bool:
    """Check if text contains blocked keywords."""
    text_lower = text.lower()
    return any(f"{kw}=" in text_lower or f"{kw} " in text_lower for kw in BLOCKED_KEYWORDS)

def validate_tenant(value: str, required: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate tenant field."""
    if not value and required:
        return False, "Tenant required"
    if value and contains_blocked_keywords(value):
        return False, "Tenant contains blocked keywords"
    if value and len(value) > 100:
        return False, "Tenant too long (max 100 chars)"
    return True, None

def validate_service_type(value: str, required: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate service_type field."""
    if not value and required:
        return False, "Service type required"
    if value and value not in SERVICE_TYPES:
        return False, f"Invalid service type: {value}"
    return True, None

def validate_criticality(value: str, required: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate criticality field."""
    if not value and required:
        return False, "Criticality required"
    if value and value not in CRITICALITIES:
        return False, f"Invalid criticality: {value}"
    return True, None

def validate_owner(value: str, required: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate owner field."""
    if not value and required:
        return False, "Owner required"
    if value and len(value) < 3:
        return False, "Owner too short (min 3 chars)"
    if value and len(value) > 100:
        return False, "Owner too long (max 100 chars)"
    if value and contains_blocked_keywords(value):
        return False, "Owner contains blocked keywords"
    return True, None

def validate_evidence(value: str, required: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate evidence field."""
    if not value and required:
        return False, "Evidence required"
    if value and len(value) < 5:
        return False, "Evidence too short (min 5 chars)"
    if value and len(value) > 500:
        return False, "Evidence too long (max 500 chars)"
    if value and contains_blocked_keywords(value):
        return False, "Evidence contains blocked keywords"
    return True, None

def validate_remote_asn(value: str, required: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate BGP remote_asn field."""
    if not value and required:
        return False, "Remote ASN required"
    if value:
        try:
            asn = int(value)
            if asn < 1 or asn > 4294967295:
                return False, "ASN must be 1-4294967295"
        except ValueError:
            return False, "Remote ASN must be numeric"
    return True, None

def validate_remote_bgp_group(value: str, required: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate BGP remote_bgp_group field."""
    if not value and required:
        return False, "Remote BGP group required"
    if value:
        # Alphanumeric, hyphen, underscore, dot
        if not re.match(r'^[a-zA-Z0-9\-_.]+$', value):
            return False, "BGP group must contain only alphanumeric, hyphen, underscore, dot"
        if len(value) > 100:
            return False, "BGP group too long (max 100 chars)"
    return True, None

def validate_interface(value: str, required: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate interface field."""
    if not value and required:
        return False, "Interface required"
    if value:
        # Common interface patterns
        patterns = [
            r'^Eth-Trunk\d+(\.\d+)?$',
            r'^GigabitEthernet\d+/\d+/\d+(\.\d+)?$',
            r'^LoopBack\d+$',
            r'^Vlanif\d+$',
            r'^10GE\d+/\d+/\d+$',
        ]
        if not any(re.match(p, value) for p in patterns):
            return False, f"Interface format invalid: {value}"
    return True, None

def validate_vrf(value: str, required: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate VRF field."""
    if not value and required:
        return False, "VRF required"
    if value:
        if value.lower() == '_public_':
            return True, None
        # Alphanumeric, hyphen, underscore
        if not re.match(r'^[a-zA-Z0-9\-_]+$', value):
            return False, "VRF must contain only alphanumeric, hyphen, underscore"
        if len(value) > 100:
            return False, "VRF too long (max 100 chars)"
    return True, None

def validate_notes(value: str) -> Tuple[bool, Optional[str]]:
    """Validate optional notes field."""
    if value:
        if contains_blocked_keywords(value):
            return False, "Notes contain blocked keywords"
        if len(value) > 1000:
            return False, "Notes too long (max 1000 chars)"
    return True, None

def validate_status(value: str) -> Tuple[bool, Optional[str]]:
    """Validate status field."""
    if not value:
        return False, "Status required"
    if value not in STATUSES:
        return False, f"Invalid status: {value}"
    return True, None

def validate_subinterface_response(data: Dict) -> Tuple[bool, List[str]]:
    """Validate subinterface form response."""
    errors = []

    status = data.get('status')
    valid, err = validate_status(status)
    if not valid:
        errors.append(f"status: {err}")
        return False, errors

    # Required if answered
    if status == 'answered':
        required_fields = ['tenant', 'service_type', 'criticality', 'owner', 'evidence']
        for field in required_fields:
            value = data.get(field, '').strip()
            if field == 'tenant':
                valid, err = validate_tenant(value, required=True)
            elif field == 'service_type':
                valid, err = validate_service_type(value, required=True)
            elif field == 'criticality':
                valid, err = validate_criticality(value, required=True)
            elif field == 'owner':
                valid, err = validate_owner(value, required=True)
            elif field == 'evidence':
                valid, err = validate_evidence(value, required=True)
            if not valid:
                errors.append(f"{field}: {err}")

    # Optional validation
    notes = data.get('notes', '').strip()
    valid, err = validate_notes(notes)
    if not valid:
        errors.append(f"notes: {err}")

    return len(errors) == 0, errors

def validate_bgp_response(data: Dict) -> Tuple[bool, List[str]]:
    """Validate BGP peer form response."""
    errors = []

    status = data.get('status')
    valid, err = validate_status(status)
    if not valid:
        errors.append(f"status: {err}")
        return False, errors

    if status == 'answered':
        required_fields = ['remote_asn', 'remote_bgp_group', 'policy_intent', 'owner', 'criticality']

        for field in required_fields:
            value = data.get(field, '').strip()
            if field == 'remote_asn':
                valid, err = validate_remote_asn(value, required=True)
            elif field == 'remote_bgp_group':
                valid, err = validate_remote_bgp_group(value, required=True)
            elif field == 'policy_intent':
                valid, err = validate_evidence(value, required=True)  # Same as evidence
            elif field == 'owner':
                valid, err = validate_owner(value, required=True)
            elif field == 'criticality':
                valid, err = validate_criticality(value, required=True)
            if not valid:
                errors.append(f"{field}: {err}")

    notes = data.get('notes', '').strip()
    valid, err = validate_notes(notes)
    if not valid:
        errors.append(f"notes: {err}")

    return len(errors) == 0, errors

def validate_ip_response(data: Dict) -> Tuple[bool, List[str]]:
    """Validate IP address form response."""
    errors = []

    status = data.get('status')
    valid, err = validate_status(status)
    if not valid:
        errors.append(f"status: {err}")
        return False, errors

    if status == 'answered':
        required_fields = ['interface', 'vrf', 'owner']

        for field in required_fields:
            value = data.get(field, '').strip()
            if field == 'interface':
                valid, err = validate_interface(value, required=True)
            elif field == 'vrf':
                valid, err = validate_vrf(value, required=True)
            elif field == 'owner':
                valid, err = validate_owner(value, required=True)
            if not valid:
                errors.append(f"{field}: {err}")

    notes = data.get('notes', '').strip()
    valid, err = validate_notes(notes)
    if not valid:
        errors.append(f"notes: {err}")

    return len(errors) == 0, errors
