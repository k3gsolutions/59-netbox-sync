"""SNMP collection for compliance — interface discovery and verification."""

import os
import asyncio
from typing import Any, Dict, List, Optional

try:
    from pysnmp.hlapi.asyncio import (
        SnmpEngine, CommunityData, UdpTransportTarget, ContextData,
        bulkCmd, ObjectType, ObjectIdentity
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
        from pysnmp.hlapi.asyncio import walkCmd

        async def _walk_oid(oid_str):
            results = {}
            async for errorIndication, errorStatus, errorIndex, varBinds in walkCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=0),
                UdpTransportTarget((host, port), timeout=timeout, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(oid_str)),
            ):
                if errorIndication:
                    continue
                for varBind in varBinds:
                    oid = str(varBind[0])
                    value = varBind[1]
                    if oid.startswith(oid_str + "."):
                        idx = oid.split(".")[-1]
                        results[idx] = value
            return results

        # Walk each OID
        names = asyncio.run(_walk_oid("1.3.6.1.2.1.2.2.1.2"))
        aliases = asyncio.run(_walk_oid("1.3.6.1.2.1.31.1.1.1.18"))
        admin_statuses = asyncio.run(_walk_oid("1.3.6.1.2.1.2.2.1.7"))
        oper_statuses = asyncio.run(_walk_oid("1.3.6.1.2.1.2.2.1.8"))
        speeds = asyncio.run(_walk_oid("1.3.6.1.2.1.2.2.1.5"))
        types_oids = asyncio.run(_walk_oid("1.3.6.1.2.1.2.2.1.3"))

        if not names:
            return False, [], "No interfaces found via SNMP"

        # Merge all results
        status_map = {1: "up", 2: "down", 3: "testing"}
        type_map = {
            1: "other", 6: "ethernetCsmacd", 23: "ppp", 24: "softwareLoopback",
            53: "propVirtual", 135: "l2vlan", 161: "lag",
        }

        ifaces_by_idx = {}
        for idx, name in names.items():
            ifaces_by_idx[idx] = {
                "index": int(idx),
                "name": str(name),
                "description": str(aliases.get(idx, "")),
                "admin_status": status_map.get(int(admin_statuses.get(idx, 1)), "unknown"),
                "oper_status": status_map.get(int(oper_statuses.get(idx, 1)), "unknown"),
                "speed": int(speeds.get(idx, 0)) if idx in speeds else 0,
                "type": type_map.get(int(types_oids.get(idx, 0)), f"type_{int(types_oids.get(idx, 0))}") if idx in types_oids else "unknown",
            }

        interfaces = sorted(ifaces_by_idx.values(), key=lambda x: x["index"])
        return True, interfaces, ""

    except Exception as e:
        return False, [], f"SNMP collection failed: {str(e)}"
