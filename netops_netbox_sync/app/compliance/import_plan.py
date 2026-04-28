"""Build ImportPlan from compliance analysis results (read-only)."""

import re
from datetime import datetime, timezone
from typing import Optional

from app.schemas.analyze import AnalyzeResult
from app.schemas.compliance import ComplianceDivergence
from app.schemas.import_plan import (
    ImportPlan,
    ImportPlanItem,
    ImportAction,
    ConfidenceLevel,
)


def _is_base_interface_name(interface_name: str) -> bool:
    """Check if interface is base infrastructure (not subinterface/service).

    Base interfaces:
    - Physical interfaces: Ethernet, GigabitEthernet, 10GE, 100GE, etc
    - LAGs: Eth-Trunk, ae, bundle-ether
    - Management: Management, mgmt, mgt
    - Loopback: LoopBack (only as pure inventory, not service)

    NOT base:
    - Subinterfaces (contain dot): Eth-Trunk0.1580
    - Virtual: Vlan, irb, etc (service-oriented)
    - NULL/NULL0 (ignored)
    """
    if not interface_name:
        return False

    # Exclude subinterfaces (contain dot)
    if "." in interface_name:
        return False

    # Exclude virtual service interfaces
    if re.match(r"^(Vlan|Virtual|irb|lo\d|null|NULL)", interface_name, re.IGNORECASE):
        return False

    # Include base physical/management
    # Patterns: Eth-Trunk0, GigabitEthernet0/0/0, Ethernet0/0/0, etc
    base_patterns = [
        r"^(Eth-Trunk|Ethernet|GigabitEthernet|FastEthernet|TenGigabitEthernet)",
        r"^(10GE|25GE|40GE|100GE)",
        r"^(ae|bundle-ether)",
        r"^(Management|mgmt|mgt)",
        r"^LoopBack\d+$",  # LoopBack only if pure inventory (bare number)
    ]

    return any(re.match(pattern, interface_name, re.IGNORECASE) for pattern in base_patterns)


def _is_subinterface_name(interface_name: str) -> bool:
    """Check if interface is subinterface (contains dot)."""
    return bool("." in interface_name if interface_name else False)


def _is_service_interface(divergence: ComplianceDivergence) -> bool:
    """Detect if interface represents a service (not base inventory).

    Service indicators:
    - Is valid subinterface (base.number pattern)
    - Description suggests service/client/operator
    - Carries IP, VRF, VLAN tags
    """
    if divergence.object_type != "interface":
        return False

    interface_name = divergence.object_key or ""

    # Valid subinterfaces: base_name.vlan_id (e.g., Eth-Trunk0.1580)
    if "." in interface_name:
        parts = interface_name.rsplit(".", 1)
        if len(parts) == 2:
            base_name, vlan_part = parts
            # Check if base part is valid and vlan part is numeric
            if _is_base_interface_name(base_name) and vlan_part.isdigit():
                return True
        # If has dot but not valid subinterface pattern, it's suspicious
        # but we'll treat it as service and require naming validation
        return True

    # Check description for service markers
    evidence = divergence.evidence or {}
    description = (evidence.get("description") or "").lower()

    service_keywords = [
        "client", "customer", "operator", "service",
        "cdn", "peer", "tunnel", "mpls",
        "bgp", "ospf", "eigrp", "isis",
        "vpn", "vrf", "vlan",
    ]

    if any(keyword in description for keyword in service_keywords):
        return True

    # Check for IP/VRF/VLAN in evidence
    if evidence.get("ip_addresses") or evidence.get("vrf"):
        return True

    return False


def _is_naming_compliant(object_type: str, object_key: str) -> bool:
    """Check if object key follows naming convention.

    Basic rules:
    - Interface: alphanumeric, hyphens, underscores, forward slashes
    - IP address: valid IPv4/IPv6
    - VRF: alphanumeric, underscores, hyphens
    - VLAN: numeric ID
    - BGP peer: valid IP
    """
    if not object_key:
        return False

    if object_type == "interface":
        # Interface names typically contain alphanumeric, -, _, /, .
        # Allow patterns like GigabitEthernet0/0/0, ge-0/0/0, eth0, Eth-Trunk0.1580, etc
        return bool(re.match(r"^[a-zA-Z0-9/_.-]+$", object_key))

    elif object_type == "ip_address":
        # Must be valid IPv4 or IPv6
        import ipaddress
        try:
            ipaddress.ip_address(object_key.split('/')[0])
            return True
        except ValueError:
            return False

    elif object_type == "vrf":
        # VRF names: alphanumeric, underscore, hyphen
        return bool(re.match(r"^[a-zA-Z0-9_-]+$", object_key))

    elif object_type == "vlan":
        # VLAN ID must be numeric
        try:
            vid = int(object_key)
            return 1 <= vid <= 4094
        except ValueError:
            return False

    elif object_type == "bgp_peer":
        # BGP peer should be valid IP
        import ipaddress
        try:
            ipaddress.ip_address(object_key)
            return True
        except ValueError:
            return False

    # Unknown type: assume not compliant without explicit validation
    return False


def _classify_divergence(divergence: ComplianceDivergence) -> tuple[ImportAction, str, ConfidenceLevel, Optional[str]]:
    """Classify divergence into import action.

    Returns:
        (action, reason, confidence, next_step)
    """
    code = divergence.code
    object_type = divergence.object_type
    object_key = divergence.object_key

    # Rule 1: Ignore if divergence has no object context
    if not object_type or not object_key:
        if code.endswith("_MISSING_IN_NETBOX"):
            return (
                ImportAction.NEEDS_REVIEW,
                "Objeto faltando no NetBox, mas sem identificação clara",
                ConfidenceLevel.AMBIGUOUS,
                "Revisar metadados do relatório"
            )
        return (
            ImportAction.IGNORE,
            "Divergência agregada (sem objeto específico)",
            ConfidenceLevel.NONE,
            "Avaliar em contexto geral"
        )

    # Rule 2: Missing on device → needs review (device-side issue)
    if code.endswith("_MISSING_ON_DEVICE"):
        return (
            ImportAction.NEEDS_REVIEW,
            "Objeto no NetBox, faltando no equipamento (problema no device)",
            ConfidenceLevel.EXACT,
            "Sincronizar device com NetBox ou remover do NetBox"
        )

    # Rule 3: Description non-compliant → needs review
    if code == "DESCRIPTION_NON_COMPLIANT":
        return (
            ImportAction.NEEDS_REVIEW,
            "Descrição não segue naming convention",
            ConfidenceLevel.EXACT,
            "Validar e corrigir descrição"
        )

    # Rule 4: BGP peers initially → needs review (complex relationships)
    if object_type == "bgp_peer":
        return (
            ImportAction.NEEDS_REVIEW,
            "BGP peer: relacionamentos complexos, requer revisão manual",
            ConfidenceLevel.POSSIBLE,
            "Validar BGP configuration e relacionamentos"
        )

    # Rule 5: Ambiguous or insufficient metadata → blocked
    if divergence.scope in ("unknown", "ambiguous") or not object_key:
        return (
            ImportAction.BLOCKED,
            f"Metadados insuficientes ou ambíguos (scope: {divergence.scope})",
            ConfidenceLevel.AMBIGUOUS,
            "Coletar mais informações ou enriquecer divergence"
        )

    # Rule 6: Missing in NetBox candidates
    if code.endswith("_MISSING_IN_NETBOX"):
        # Rule 6.1: Interface special handling (base vs service)
        if object_type == "interface":
            # Rule 6.1a: Base infrastructure interfaces (no naming convention required)
            if _is_base_interface_name(object_key):
                return (
                    ImportAction.SAFE_CREATE_STAGED,
                    "Base interface inventory (physical/LAG/management)",
                    ConfidenceLevel.EXACT,
                    "Revisar payload sugerido e aplicar staged import"
                )

            # Rule 6.1b: Service interfaces require naming convention
            is_service = _is_service_interface(divergence)
            if is_service or _is_subinterface_name(object_key):
                # For subinterfaces, require valid pattern: base.vlan_id
                if "." in object_key:
                    parts = object_key.rsplit(".", 1)
                    if len(parts) == 2:
                        base_name, vlan_part = parts
                        if not (_is_base_interface_name(base_name) and vlan_part.isdigit()):
                            # Invalid subinterface pattern
                            return (
                                ImportAction.NEEDS_REVIEW,
                                f"Invalid subinterface pattern: {object_key} (deve ser base.vlan_id)",
                                ConfidenceLevel.EXACT,
                                "Validar padrão de subinterface antes de importar"
                            )
                    else:
                        # Multiple dots or other issue
                        return (
                            ImportAction.NEEDS_REVIEW,
                            f"Invalid interface naming: {object_key}",
                            ConfidenceLevel.EXACT,
                            "Validar naming convention antes de importar"
                        )

                # Service/subinterface must have valid naming
                is_compliant = _is_naming_compliant(object_type, object_key)
                if not is_compliant:
                    return (
                        ImportAction.NEEDS_REVIEW,
                        f"Service interface fora da naming convention: {object_key}",
                        ConfidenceLevel.EXACT,
                        "Validar naming convention antes de importar"
                    )
                # Service with valid naming → safe_create_staged
                return (
                    ImportAction.SAFE_CREATE_STAGED,
                    f"Service interface com naming válida",
                    ConfidenceLevel.EXACT,
                    "Revisar payload sugerido e aplicar staged import"
                )

            # Rule 6.1c: Unknown if base or service, require naming
            is_compliant = _is_naming_compliant(object_type, object_key)
            if not is_compliant:
                return (
                    ImportAction.NEEDS_REVIEW,
                    f"Interface fora da naming convention: {object_key}",
                    ConfidenceLevel.EXACT,
                    "Validar naming convention antes de importar"
                )
            return (
                ImportAction.SAFE_CREATE_STAGED,
                f"Interface com naming válida",
                ConfidenceLevel.EXACT,
                "Revisar payload sugerido e aplicar staged import"
            )

        # Rule 6.2: Non-interface types
        is_compliant = _is_naming_compliant(object_type, object_key)

        # Rule 6.2a: Naming convention failed → needs review (never safe_create_staged)
        if not is_compliant:
            return (
                ImportAction.NEEDS_REVIEW,
                f"Fora da naming convention ({object_type}: {object_key})",
                ConfidenceLevel.EXACT,
                "Validar naming convention antes de importar"
            )

        # Rule 6.2b: Valid naming, eligible object types → safe_create_staged
        eligible_types = {"ip_address", "vrf", "vlan"}
        if object_type in eligible_types:
            return (
                ImportAction.SAFE_CREATE_STAGED,
                f"Candidato a staged import (naming válida)",
                ConfidenceLevel.EXACT,
                "Revisar payload sugerido e aplicar staged import"
            )

        # Rule 6.2c: Other missing types → needs review
        return (
            ImportAction.NEEDS_REVIEW,
            f"Faltando no NetBox, tipo requer revisão: {object_type}",
            ConfidenceLevel.POSSIBLE,
            f"Avaliar se {object_type} deve ser importado"
        )

    # Default: needs review
    return (
        ImportAction.NEEDS_REVIEW,
        f"Divergência requer revisão: {code}",
        ConfidenceLevel.POSSIBLE,
        "Avaliar em contexto específico"
    )


def build_import_plan(result: AnalyzeResult) -> ImportPlan:
    """Build ImportPlan from AnalyzeResult (read-only, no writes).

    Classifies each divergence into import actions based on rules.
    Never generates delete or automatic update actions.
    """
    now = datetime.now(timezone.utc).isoformat() + "Z"

    items: list[ImportPlanItem] = []
    counts = {
        "safe_create_staged": 0,
        "needs_review": 0,
        "blocked": 0,
        "ignore": 0,
    }

    for divergence in result.divergences:
        action, reason, confidence, next_step = _classify_divergence(divergence)

        # Count this action
        counts[action.value] += 1

        # Determine naming compliance
        is_compliant = False
        if divergence.object_type and divergence.object_key:
            is_compliant = _is_naming_compliant(divergence.object_type, divergence.object_key)

        # Determine category for UI grouping
        category = None
        if divergence.object_type == "interface" and divergence.object_key:
            if _is_base_interface_name(divergence.object_key):
                category = "base_inventory"
            elif _is_service_interface(divergence):
                category = "service"

        # Build item
        item = ImportPlanItem(
            action=action,
            object_type=divergence.object_type or "unknown",
            object_key=divergence.object_key or "unknown",
            code=divergence.code,
            reason=reason,
            evidence=divergence.evidence,
            naming_compliant=is_compliant,
            confidence=confidence,
            preferred_next_step=next_step or "",
            category=category,
        )

        items.append(item)

    plan = ImportPlan(
        device=result.hostname,
        device_id=result.device_id,
        generated_at=now,
        source="compliance",
        total_items=len(result.divergences),
        safe_create_staged_count=counts["safe_create_staged"],
        needs_review_count=counts["needs_review"],
        blocked_count=counts["blocked"],
        ignore_count=counts["ignore"],
        items=items,
    )

    return plan
