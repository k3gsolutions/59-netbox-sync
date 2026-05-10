"""SNMP collection for compliance — interface discovery and verification."""

import os
from typing import Any, Dict, List, Optional

try:
    from pysnmp.hlapi import (
        SnmpEngine, CommunityData, UdpTransportTarget, ContextData,
        getCmd, ObjectType, ObjectIdentity, SnmpErrorIndication
    )
except ImportError:
    SnmpEngine = None


def collect_interfaces_snmp(
    host: str,
    community: Optional[str] = None,
    version: int = 2,
    port: int = 161,
    timeout: int = 5,
) -> tuple[bool, List[Dict[str, Any]], str]:
    """
    Collect interfaces via SNMP IF-MIB (SNMPv2c).

    Args:
        host: Device IP/hostname
        community: SNMP community string (default from env SNMP_COMMUNITY)
        version: SNMP version (default 2 for v2c)
        port: UDP port (default 161)
        timeout: Connection timeout in seconds

    Returns:
        (success: bool, interfaces: list, error_msg: str)
        interfaces = [{
            'index': int,
            'name': str,
            'description': str,
            'admin_status': str (up|down|testing),
            'oper_status': str (up|down|testing),
            'speed': int (bytes/sec, 0 if unknown),
            'type': str (e.g. ethernetCsmacd),
        }]
    """
    if SnmpEngine is None:
        return False, [], "pysnmp not installed. Install: pip install pysnmp>=6.2.5"

    community = community or os.getenv("SNMP_COMMUNITY", "public")
    if not community or community == "":
        return False, [], "SNMP_COMMUNITY not configured"

    try:
        engine = SnmpEngine()
        target = UdpTransportTarget((host, port), timeout=timeout, retries=1)
        community_data = CommunityData(community, mpModel=0)
        context = ContextData()

        interfaces = []
        # OID base for IF-MIB::ifTable
        oid_ifName = ObjectType(ObjectIdentity("1.3.6.1.2.1.2.2.1.2"))
        oid_ifAlias = ObjectType(ObjectIdentity("1.3.6.1.2.1.31.1.1.1.18"))
        oid_ifAdminStatus = ObjectType(ObjectIdentity("1.3.6.1.2.1.2.2.1.7"))
        oid_ifOperStatus = ObjectType(ObjectIdentity("1.3.6.1.2.1.2.2.1.8"))
        oid_ifSpeed = ObjectType(ObjectIdentity("1.3.6.1.2.1.2.2.1.5"))
        oid_ifType = ObjectType(ObjectIdentity("1.3.6.1.2.1.2.2.1.3"))

        # Walk ifTable
        error_indication, error_status, error_index, var_binds = next(
            engine.bulkCmd(
                community_data, target, context, 0, 25,
                oid_ifName, oid_ifAlias, oid_ifAdminStatus, oid_ifOperStatus,
                oid_ifSpeed, oid_ifType,
                maxRepetitions=10
            )
        )

        if error_indication:
            return False, [], f"SNMP error: {error_indication}"

        # Parse results
        status_map = {1: "up", 2: "down", 3: "testing"}
        type_map = {
            1: "other", 6: "ethernetCsmacd", 23: "ppp", 24: "softwareLoopback",
            53: "propVirtual", 135: "l2vlan", 161: "lag",
        }

        ifaces_by_idx = {}
        for var_bind in var_binds:
            oid_str = str(var_bind[0])
            value = var_bind[1]

            if not value:
                continue

            if ".1.3.6.1.2.1.2.2.1.2." in oid_str:  # ifName
                idx = oid_str.split(".")[-1]
                if idx not in ifaces_by_idx:
                    ifaces_by_idx[idx] = {}
                ifaces_by_idx[idx]["name"] = str(value)
                ifaces_by_idx[idx]["index"] = int(idx)

            elif ".1.3.6.1.2.1.31.1.1.1.18." in oid_str:  # ifAlias
                idx = oid_str.split(".")[-1]
                if idx not in ifaces_by_idx:
                    ifaces_by_idx[idx] = {}
                ifaces_by_idx[idx]["description"] = str(value)

            elif ".1.3.6.1.2.1.2.2.1.7." in oid_str:  # ifAdminStatus
                idx = oid_str.split(".")[-1]
                if idx not in ifaces_by_idx:
                    ifaces_by_idx[idx] = {}
                ifaces_by_idx[idx]["admin_status"] = status_map.get(int(value), "unknown")

            elif ".1.3.6.1.2.1.2.2.1.8." in oid_str:  # ifOperStatus
                idx = oid_str.split(".")[-1]
                if idx not in ifaces_by_idx:
                    ifaces_by_idx[idx] = {}
                ifaces_by_idx[idx]["oper_status"] = status_map.get(int(value), "unknown")

            elif ".1.3.6.1.2.1.2.2.1.5." in oid_str:  # ifSpeed
                idx = oid_str.split(".")[-1]
                if idx not in ifaces_by_idx:
                    ifaces_by_idx[idx] = {}
                ifaces_by_idx[idx]["speed"] = int(value)

            elif ".1.3.6.1.2.1.2.2.1.3." in oid_str:  # ifType
                idx = oid_str.split(".")[-1]
                if idx not in ifaces_by_idx:
                    ifaces_by_idx[idx] = {}
                ifaces_by_idx[idx]["type"] = type_map.get(int(value), f"type_{int(value)}")

        # Build final list
        for iface in ifaces_by_idx.values():
            interfaces.append({
                "index": iface.get("index", 0),
                "name": iface.get("name", "unknown"),
                "description": iface.get("description", ""),
                "admin_status": iface.get("admin_status", "unknown"),
                "oper_status": iface.get("oper_status", "unknown"),
                "speed": iface.get("speed", 0),
                "type": iface.get("type", "unknown"),
            })

        return True, sorted(interfaces, key=lambda x: x["index"]), ""

    except Exception as e:
        return False, [], f"SNMP collection failed: {str(e)}"
