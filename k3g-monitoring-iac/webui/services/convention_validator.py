"""Convention validator for Huawei VRP configuration policies."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Try to load yaml; fallback to inline dicts if unavailable
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# Rule ID explanations
RULE_EXPLANATIONS = {
    "IFACE-001": "Base interface name does not match expected pattern (Eth-Trunk\\d+, GigabitEthernet\\d+/\\d+/\\d+, etc.)",
    "IFACE-002": "Service subinterface name does not match expected pattern (Eth-Trunk\\d+\\.\\d+, GigabitEthernet\\d+/\\d+/\\d+\\.\\d+)",
    "IFACE-003": "Service interface missing required fields (description, tenant, service_type, criticality, owner)",
    "VRF-001": "VRF name does not match expected pattern (alphanumeric, hyphen, underscore)",
    "RTPOL-001": "Route-policy name does not conform to convention (AS<ASN>-<SITE>-<CONTEXT>-<SERVICE>-IPv[46]-<Import|Export>)",
    "PREFIX-001": "IP prefix name does not conform to convention (BOGONS|CUSTOMER|CDN|IX|TRANSIT|INFRA)-<NAME>-IPv[46]",
    "COMM-001": "Community value not in ASN:VALUE format",
    "COMM-002": "Community filter reference not found",
    "ASPATH-001": "AS-path filter regex invalid or not found",
    "SNMP-001": "SNMP community string is blocked (public, private, secret, admin, cisco, snmp)",
    "SNMP-002": "SNMP version below v3 without exception",
    "BGP-001": "BGP peer missing required field: remote_asn",
    "BGP-002": "BGP peer missing required field: owner",
    "BGP-003": "BGP peer missing required field: policy_intent",
    "BGP-004": "BGP peer criticality missing for service type",
    "IPMAP-001": "IP address mapping relation_type=service but service_relation missing",
    "IPMAP-002": "IP address mapping relation_type=unknown but notes missing",
    "COMMENT-001": "Comment contains blocked keyword (token, password, secret, etc.)",
    "COMMENT-002": "Comment exceeds maximum length",
}

# Inline policy registry (fallback if YAML not available)
INLINE_POLICIES = {
    "interface": {
        "base_inventory_patterns": [
            r"^Eth-Trunk\d+$",
            r"^GigabitEthernet\d+/\d+/\d+$",
            r"^10GE\d+/\d+/\d+$",
            r"^LoopBack\d+$",
            r"^NULL\d+$",
            r"^Vlanif\d+$",
            r"^Vlan\d+$",
        ],
        "service_interface_patterns": [
            r"^Eth-Trunk\d+\.\d+$",
            r"^GigabitEthernet\d+/\d+/\d+\.\d+$",
            r"^10GE\d+/\d+/\d+\.\d+$",
        ],
    },
    "vrf": {
        "pattern": r"^[a-zA-Z0-9_\-]+$",
        "max_length": 100,
    },
    "route_policy": {
        "pattern": r"^AS\d+-[A-Z0-9]+-[A-Z0-9]+-\w+-IPv[46]-(Import|Export)$",
    },
    "ip_prefix": {
        "patterns": [
            r"^BOGONS-(IPv4|IPv6)$",
            r"^CUSTOMER-[A-Z0-9_\-]+-IPv[46]$",
            r"^CDN-[A-Z0-9_\-]+-IPv[46]$",
            r"^IX-[A-Z0-9_\-]+-IPv[46]$",
            r"^TRANSIT-[A-Z0-9_\-]+-IPv[46]$",
            r"^INFRA-[A-Z0-9_\-]+-IPv[46]$",
        ],
    },
    "community": {
        "pattern": r"^\d+:\d+$",
    },
    "snmp": {
        "blocked_communities": ["public", "private", "secret", "admin", "cisco", "snmp"],
    },
    "comment": {
        "blocked_keywords": ["token", "password", "secret", "private key", "bearer", "api_key", "ssh_key"],
        "max_length_short": 255,
        "max_length_evidence": 1024,
    },
}


def _load_policies() -> Dict[str, Any]:
    """Load policy registry from YAML or inline."""
    policies_dir = Path(__file__).parent.parent.parent / "policies" / "compliance"

    # Always start with inline policies
    policies = {k: v.copy() if isinstance(v, dict) else v for k, v in INLINE_POLICIES.items()}

    if not HAS_YAML or not policies_dir.exists():
        return policies

    # Try to load from YAML files and merge
    yaml_files = {
        "interface": "naming-conventions.yaml",
        "vrf": "naming-conventions.yaml",
        "route_policy": "naming-conventions.yaml",
        "ip_prefix": "naming-conventions.yaml",
        "community": "naming-conventions.yaml",
        "snmp": "snmp-policy.yaml",
        "comment": "comments-policy.yaml",
    }

    for key, filename in yaml_files.items():
        filepath = policies_dir / filename
        if filepath.exists():
            try:
                with filepath.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    if key in data:
                        # Merge YAML data with inline, YAML takes precedence
                        if isinstance(policies[key], dict) and isinstance(data[key], dict):
                            policies[key].update(data[key])
                        else:
                            policies[key] = data[key]
            except Exception:
                pass  # Keep inline version

    return policies


# Global registry cache
_POLICY_CACHE: Optional[Dict[str, Any]] = None


def load_policy_registry() -> Dict[str, Any]:
    """Load and cache policy registry."""
    global _POLICY_CACHE
    if _POLICY_CACHE is None:
        _POLICY_CACHE = _load_policies()
    return _POLICY_CACHE


def classify_interface(name: str) -> str:
    """Classify interface as base_inventory, service_interface, or invalid."""
    if not name:
        return "invalid"

    policies = load_policy_registry()
    iface_policy = policies.get("interface", INLINE_POLICIES["interface"])

    # Check service patterns first
    service_patterns = iface_policy.get("service_interface_patterns", [])
    for pattern in service_patterns:
        if re.match(pattern, name):
            return "service_interface"

    # Check base patterns
    base_patterns = iface_policy.get("base_inventory_patterns", [])
    for pattern in base_patterns:
        if re.match(pattern, name):
            return "base_inventory"

    return "invalid"


def validate_interface_name(name: str) -> Dict[str, Any]:
    """Validate interface base naming."""
    if not name:
        return {
            "valid": False,
            "rule_id": "IFACE-001",
            "message": "Interface name required",
            "message_pt": "Nome de interface obrigatório",
            "severity": "error",
            "details": {},
        }

    classification = classify_interface(name)
    if classification in ("base_inventory", "service_interface"):
        return {
            "valid": True,
            "rule_id": "IFACE-001",
            "message": f"Interface name valid ({classification})",
            "message_pt": f"Nome de interface válido ({classification})",
            "severity": "info",
            "details": {"classification": classification},
        }

    return {
        "valid": False,
        "rule_id": "IFACE-001",
        "message": f"Interface name does not match pattern",
        "message_pt": "Nome de interface não corresponde ao padrão esperado",
        "severity": "error",
        "details": {"name": name},
    }


def validate_vrf_name(name: str) -> Dict[str, Any]:
    """Validate VRF naming."""
    if not name:
        return {
            "valid": False,
            "rule_id": "VRF-001",
            "message": "VRF name required",
            "message_pt": "Nome VRF obrigatório",
            "severity": "error",
            "details": {},
        }

    policies = load_policy_registry()
    vrf_policy = policies.get("vrf", INLINE_POLICIES["vrf"])
    pattern = vrf_policy.get("pattern", r"^[a-zA-Z0-9_\-]+$")
    max_length = vrf_policy.get("max_length", 100)

    if len(name) > max_length:
        return {
            "valid": False,
            "rule_id": "VRF-001",
            "message": f"VRF name too long (max {max_length} chars)",
            "message_pt": f"Nome VRF muito longo (máx {max_length} caracteres)",
            "severity": "error",
            "details": {"name": name, "length": len(name)},
        }

    if re.match(pattern, name):
        return {
            "valid": True,
            "rule_id": "VRF-001",
            "message": "VRF name valid",
            "message_pt": "Nome VRF válido",
            "severity": "info",
            "details": {"name": name},
        }

    return {
        "valid": False,
        "rule_id": "VRF-001",
        "message": "VRF name pattern invalid",
        "message_pt": "Padrão de nome VRF inválido",
        "severity": "error",
        "details": {"name": name},
    }


def validate_route_policy_name(name: str, direction: Optional[str] = None) -> Dict[str, Any]:
    """Validate route-policy naming convention."""
    if not name:
        return {
            "valid": False,
            "rule_id": "RTPOL-001",
            "message": "Route-policy name required",
            "message_pt": "Nome da route-policy obrigatório",
            "severity": "error",
            "details": {},
        }

    policies = load_policy_registry()
    rtpol_policy = policies.get("route_policy", INLINE_POLICIES.get("route_policy", {}))
    pattern = rtpol_policy.get("pattern", r"^AS\d+-[A-Z0-9]+-[A-Z0-9]+-\w+-IPv[46]-(Import|Export)$")

    if re.match(pattern, name):
        return {
            "valid": True,
            "rule_id": "RTPOL-001",
            "message": "Route-policy name valid",
            "message_pt": "Nome de route-policy válido",
            "severity": "info",
            "details": {"name": name},
        }

    return {
        "valid": False,
        "rule_id": "RTPOL-001",
        "message": "Route-policy name does not conform to convention",
        "message_pt": "Nome de route-policy não conforma à convenção esperada",
        "severity": "error",
        "details": {"name": name},
    }


def parse_route_policy_name(name: str) -> Dict[str, Optional[str]]:
    """Parse route-policy name into components."""
    result = {
        "asn": None,
        "site": None,
        "context": None,
        "service": None,
        "afi": None,
        "direction": None,
    }

    pattern = r"^AS(\d+)-([A-Z0-9]+)-([A-Z0-9]+)-(\w+)-(IPv[46])-(Import|Export)$"
    match = re.match(pattern, name)
    if match:
        result["asn"] = match.group(1)
        result["site"] = match.group(2)
        result["context"] = match.group(3)
        result["service"] = match.group(4)
        result["afi"] = match.group(5)
        result["direction"] = match.group(6)

    return result


def validate_ip_prefix_name(name: str) -> Dict[str, Any]:
    """Validate IP prefix naming."""
    if not name:
        return {
            "valid": False,
            "rule_id": "PREFIX-001",
            "message": "IP prefix name required",
            "message_pt": "Nome do prefix obrigatório",
            "severity": "error",
            "details": {},
        }

    policies = load_policy_registry()
    prefix_policy = policies.get("ip_prefix", INLINE_POLICIES.get("ip_prefix", {}))
    patterns = prefix_policy.get("patterns", [])

    for pattern in patterns:
        if re.match(pattern, name):
            return {
                "valid": True,
                "rule_id": "PREFIX-001",
                "message": "IP prefix name valid",
                "message_pt": "Nome do prefix válido",
                "severity": "info",
                "details": {"name": name},
            }

    return {
        "valid": False,
        "rule_id": "PREFIX-001",
        "message": "IP prefix name does not conform to convention",
        "message_pt": "Nome do prefix não conforma à convenção esperada",
        "severity": "error",
        "details": {"name": name},
    }


def validate_community(value: str) -> Dict[str, Any]:
    """Validate BGP community format."""
    if not value:
        return {
            "valid": False,
            "rule_id": "COMM-001",
            "message": "Community value required",
            "message_pt": "Valor de community obrigatório",
            "severity": "error",
            "details": {},
        }

    policies = load_policy_registry()
    comm_policy = policies.get("community", INLINE_POLICIES.get("community", {}))
    pattern = comm_policy.get("pattern", r"^\d+:\d+$")

    if re.match(pattern, value):
        parts = value.split(":")
        try:
            asn = int(parts[0])
            val = int(parts[1])
            if 1 <= asn <= 4294967295 and 0 <= val <= 65535:
                return {
                    "valid": True,
                    "rule_id": "COMM-001",
                    "message": "Community value valid",
                    "message_pt": "Valor de community válido",
                    "severity": "info",
                    "details": {"value": value},
                }
        except (ValueError, IndexError):
            pass

    return {
        "valid": False,
        "rule_id": "COMM-001",
        "message": "Community not in ASN:VALUE format",
        "message_pt": "Community não está no formato ASN:VALOR",
        "severity": "error",
        "details": {"value": value},
    }


def validate_comment(value: str, max_len: int = 255) -> Dict[str, Any]:
    """Validate comment field."""
    if not value:
        return {
            "valid": True,
            "rule_id": "COMMENT-001",
            "message": "Comment field empty (optional)",
            "message_pt": "Campo comentário vazio (opcional)",
            "severity": "info",
            "details": {},
        }

    policies = load_policy_registry()
    comment_policy = policies.get("comment", INLINE_POLICIES.get("comment", {}))
    blocked_keywords = comment_policy.get("blocked_keywords", [])

    # Check for blocked keywords
    value_lower = value.lower()
    for keyword in blocked_keywords:
        if keyword in value_lower:
            return {
                "valid": False,
                "rule_id": "COMMENT-001",
                "message": f"Comment contains blocked keyword: {keyword}",
                "message_pt": f"Comentário contém palavra-chave bloqueada: {keyword}",
                "severity": "blocker",
                "details": {"keyword": keyword},
            }

    # Check length
    if len(value) > max_len:
        return {
            "valid": False,
            "rule_id": "COMMENT-002",
            "message": f"Comment too long (max {max_len} chars)",
            "message_pt": f"Comentário muito longo (máx {max_len} caracteres)",
            "severity": "error",
            "details": {"length": len(value), "max_length": max_len},
        }

    return {
        "valid": True,
        "rule_id": "COMMENT-001",
        "message": "Comment valid",
        "message_pt": "Comentário válido",
        "severity": "info",
        "details": {},
    }


def validate_bgp_metadata(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Validate BGP peer metadata."""
    errors = []

    # Check remote_asn
    if not data.get("remote_asn"):
        errors.append({
            "valid": False,
            "rule_id": "BGP-001",
            "message": "BGP peer missing remote_asn",
            "message_pt": "Peer BGP faltando remote_asn",
            "severity": "error",
            "details": {},
        })

    # Check owner
    if not data.get("owner"):
        errors.append({
            "valid": False,
            "rule_id": "BGP-002",
            "message": "BGP peer missing owner",
            "message_pt": "Peer BGP faltando owner",
            "severity": "error",
            "details": {},
        })

    # Check policy_intent
    if not data.get("policy_intent"):
        errors.append({
            "valid": False,
            "rule_id": "BGP-003",
            "message": "BGP peer missing policy_intent",
            "message_pt": "Peer BGP faltando policy_intent",
            "severity": "error",
            "details": {},
        })

    # Check criticality for service peers
    if data.get("service_type") and not data.get("criticality"):
        errors.append({
            "valid": False,
            "rule_id": "BGP-004",
            "message": "Service peer missing criticality",
            "message_pt": "Peer de serviço faltando criticality",
            "severity": "error",
            "details": {},
        })

    # Check comments
    notes = data.get("notes") or ""
    if notes:
        result = validate_comment(notes, max_len=1024)
        if not result["valid"]:
            errors.append(result)

    return errors


def validate_ip_address_relation(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Validate IP address relation mapping."""
    errors = []

    # Check relation_type=service requires service_relation
    if data.get("relation_type") == "service" and not data.get("service_relation"):
        errors.append({
            "valid": False,
            "rule_id": "IPMAP-001",
            "message": "relation_type=service requires service_relation",
            "message_pt": "relation_type=service requer service_relation",
            "severity": "error",
            "details": {},
        })

    # Check relation_type=unknown requires notes
    if data.get("relation_type") == "unknown" and not data.get("notes"):
        errors.append({
            "valid": False,
            "rule_id": "IPMAP-002",
            "message": "relation_type=unknown requires notes",
            "message_pt": "relation_type=unknown requer notes",
            "severity": "error",
            "details": {},
        })

    return errors


def explain_violation(rule_id: str) -> str:
    """Return explanation for a violation rule."""
    return RULE_EXPLANATIONS.get(rule_id, "Unknown rule")
