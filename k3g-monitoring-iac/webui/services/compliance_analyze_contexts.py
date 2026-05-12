"""Compliance analysis engine — check device against standards by context."""

import re
from typing import Any, Dict, List, Optional, TypedDict

from .compliance_snmp import collect_interfaces_snmp

try:
    from netmiko import ConnectHandler
except ImportError:
    ConnectHandler = None


class HuaweiNetmikoDriver:
    """Minimal local Netmiko driver for read-only Huawei commands."""

    def __init__(self, host: str, username: str, password: str, port: int = 22):
        self.params = {
            "device_type": "huawei",
            "host": host,
            "username": username,
            "password": password,
            "port": port,
            "fast_cli": False,
        }
        self.conn = None

    def open(self):
        if ConnectHandler is None:
            raise RuntimeError("netmiko não instalado")
        self.conn = ConnectHandler(**self.params)

    def close(self):
        if self.conn:
            self.conn.disconnect()

    def send_command(self, command: str, read_timeout: int = 90) -> str:
        if not self.conn:
            raise RuntimeError("Conexão SSH não iniciada")
        return self.conn.send_command(command, read_timeout=read_timeout)


class ComplianceFinding(TypedDict):
    """Single compliance issue."""
    severity: str  # blocker|error|warning|info
    context: str
    object: str  # Interface name, peer address, etc.
    message: str
    details: Dict[str, Any]


CONTEXTS = [
    "interfaces",    # SNMP
    "bgp",           # SSH
    "seguranca",     # SSH
    "nomenclaturas", # SSH
    "ntp_snmp",      # SSH
    "sysname",       # SSH
]


def _extract_display_output(output: str, search_pattern: str) -> str:
    """Extract section from Huawei device output."""
    pattern = re.compile(search_pattern, re.MULTILINE | re.IGNORECASE)
    match = pattern.search(output)
    return match.group(1) if match else output


def _analyze_interfaces(
    interfaces: List[Dict[str, Any]]
) -> List[ComplianceFinding]:
    """Check interface compliance via SNMP data."""
    findings: List[ComplianceFinding] = []

    for iface in interfaces:
        name = iface.get("name", "unknown")
        admin_status = iface.get("admin_status", "")
        oper_status = iface.get("oper_status", "")
        description = iface.get("description", "").strip()

        # Rule: admin up but no description
        if admin_status == "up" and not description:
            findings.append(ComplianceFinding(
                severity="warning",
                context="interfaces",
                object=name,
                message="Interface habilitada sem descrição",
                details={"admin_status": admin_status}
            ))

        # Rule: oper down with admin up (possible problem)
        if admin_status == "up" and oper_status == "down":
            findings.append(ComplianceFinding(
                severity="error",
                context="interfaces",
                object=name,
                message="Interface administrativamente ativa mas operacionalmente inativa",
                details={"admin_status": admin_status, "oper_status": oper_status}
            ))

    return findings


def _analyze_bgp(output: str) -> List[ComplianceFinding]:
    """Check BGP peer status from SSH display bgp peer."""
    findings: List[ComplianceFinding] = []

    if not output or ("display bgp" in output.lower() and "error" in output.lower()):
        return findings  # Device may not have BGP configured

    # Look for BGP Peer is X.X.X.X format
    peer_blocks = re.findall(
        r"BGP Peer is\s+(\d+\.\d+\.\d+\.\d+)[^\n]*\n.*?BGP current state:\s+(\w+)",
        output,
        re.IGNORECASE | re.DOTALL
    )

    bad_states = {"idle", "connect", "active", "opensent", "openconfirm"}
    for peer_ip, state in peer_blocks:
        state_lower = state.lower()
        if state_lower in bad_states:
            findings.append(ComplianceFinding(
                severity="error",
                context="bgp",
                object=peer_ip,
                message=f"Peer em estado {state}",
                details={"peer": peer_ip, "state": state}
            ))

    return findings


def _analyze_security(output: str) -> List[ComplianceFinding]:
    """Check security config (SSH/Stelnet/users)."""
    findings: List[ComplianceFinding] = []

    # Check STelnet is not preferred
    if re.search(r"stelnet\s+(?:server\s+)?enable", output, re.IGNORECASE):
        findings.append(ComplianceFinding(
            severity="error",
            context="seguranca",
            object="stelnet",
            message="Stelnet habilitado — SSH recomendado",
            details={"service": "stelnet"}
        ))

    # Check users have privilege level
    user_lines = re.findall(r"local-user\s+(\w+)", output, re.IGNORECASE)
    if user_lines and "privilege" not in output.lower():
        findings.append(ComplianceFinding(
            severity="warning",
            context="seguranca",
            object="users",
            message="Usuários locais sem configuração de privilégio verificada",
            details={"users_found": len(user_lines)}
        ))

    return findings


def _analyze_nomenclaturas(output: str) -> List[ComplianceFinding]:
    """Check interface naming conventions."""
    findings: List[ComplianceFinding] = []

    # Pattern: SVC|CID|HOST|PORTA|BANDA|COMMENT
    pattern = r"(SVC|CLI|OP|PTP|PTMP|EN)\|([^|]+)\|([^|]+)\|([^|]+)\|(\d+[MGT])\|"
    valid_descs = re.findall(pattern, output, re.IGNORECASE)

    # Check for descriptions that don't match pattern
    desc_lines = re.findall(r"description\s+(.+?)(?:\n|$)", output, re.IGNORECASE)
    for desc in desc_lines:
        desc = desc.strip()
        if desc and not re.match(pattern, desc, re.IGNORECASE):
            # Ignore short/auto-generated descriptions
            if len(desc) > 10 and "|" in desc:
                findings.append(ComplianceFinding(
                    severity="warning",
                    context="nomenclaturas",
                    object="description",
                    message=f"Descrição não segue padrão SVC|CID|... : {desc[:50]}",
                    details={"description": desc}
                ))

    return findings


def _analyze_ntp_snmp(output: str) -> List[ComplianceFinding]:
    """Check NTP and SNMP configuration."""
    findings: List[ComplianceFinding] = []

    # Check NTP
    if not re.search(r"ntp\s+(?:source|server)", output, re.IGNORECASE):
        findings.append(ComplianceFinding(
            severity="warning",
            context="ntp_snmp",
            object="ntp",
            message="NTP não configurado ou fonte não definida",
            details={"service": "ntp"}
        ))

    # Check SNMP community
    if re.search(r"snmp-agent\s+community\s+(?:read|write)\s+(?:public|private)", output, re.IGNORECASE):
        findings.append(ComplianceFinding(
            severity="error",
            context="ntp_snmp",
            object="snmp",
            message="SNMP community padrão configurado",
            details={"service": "snmp"}
        ))

    return findings


def _analyze_sysname(device: Dict[str, Any], output: str) -> List[ComplianceFinding]:
    """Check device sysname matches NetBox name."""
    findings: List[ComplianceFinding] = []

    device_name = device.get("name", "unknown")
    sysname_match = re.search(r"sysname\s+(\S+)", output, re.IGNORECASE)

    if sysname_match:
        sysname = sysname_match.group(1).strip()
        if sysname.lower() != device_name.lower():
            findings.append(ComplianceFinding(
                severity="warning",
                context="sysname",
                object="sysname",
                message=f"Sysname no dispositivo ({sysname}) não corresponde ao NetBox ({device_name})",
                details={"device_name": device_name, "sysname": sysname}
            ))
    else:
        findings.append(ComplianceFinding(
            severity="warning",
            context="sysname",
            object="sysname",
            message="Sysname não encontrado na saída do dispositivo",
            details={}
        ))

    return findings


def analyze_device(
    device: Dict[str, Any],
    contexts: List[str],
    ssh_credentials: Dict[str, Any],
    snmp_community: Optional[str] = None,
) -> tuple[List[ComplianceFinding], Dict[str, Any]]:
    """
    Analyze device compliance across selected contexts.

    Args:
        device: Device dict from NetBox (name, primary_ip4, etc.)
        contexts: List of context names to check
        ssh_credentials: Dict with {host, port, username, password}
        snmp_community: SNMP community string (optional)

    Returns:
        (findings: list of ComplianceFinding, summary: dict with counts)
    """
    findings: List[ComplianceFinding] = []
    ssh_output = {}

    # Resolve host
    host = ssh_credentials.get("host") or device.get("primary_ip4", "").split("/")[0]
    if not host:
        return [ComplianceFinding(
            severity="blocker",
            context="common",
            object="device",
            message="Nenhum IP primário disponível",
            details={}
        )], {}

    # SSH collection for non-SNMP contexts
    ssh_contexts_needed = [c for c in contexts if c != "interfaces"]
    if ssh_contexts_needed:
        try:
            driver = HuaweiNetmikoDriver(
                host=host,
                username=ssh_credentials.get("username", "admin"),
                password=ssh_credentials.get("password", ""),
                port=ssh_credentials.get("port", 22),
            )
            driver.open()

            if "bgp" in ssh_contexts_needed:
                ssh_output["bgp"] = driver.send_command("display bgp peer verbose")

            if "seguranca" in ssh_contexts_needed:
                ssh_output["security"] = driver.send_command("display current-configuration | include ssh|stelnet|user")

            if "nomenclaturas" in ssh_contexts_needed:
                ssh_output["nomenclaturas"] = driver.send_command("display interface description")

            if "ntp_snmp" in ssh_contexts_needed:
                ntp_out = driver.send_command("display ntp status")
                snmp_out = driver.send_command("display current-configuration | include snmp-agent")
                ssh_output["ntp_snmp"] = f"{ntp_out}\n{snmp_out}"

            if "sysname" in ssh_contexts_needed:
                ssh_output["sysname"] = driver.send_command("display sysname")

            driver.close()
        except Exception as e:
            findings.append(ComplianceFinding(
                severity="blocker",
                context="common",
                object="ssh",
                message=f"Falha na conexão SSH: {str(e)}",
                details={"error": str(e)}
            ))

    # Analyze each context
    if "interfaces" in contexts:
        success, interfaces, err = collect_interfaces_snmp(host, snmp_community)
        if success:
            findings.extend(_analyze_interfaces(interfaces))
        elif err:
            findings.append(ComplianceFinding(
                severity="warning",
                context="interfaces",
                object="snmp",
                message=f"Coleta SNMP não disponível: {err}",
                details={}
            ))

    if "bgp" in contexts and "bgp" in ssh_output:
        findings.extend(_analyze_bgp(ssh_output["bgp"]))

    if "seguranca" in contexts and "security" in ssh_output:
        findings.extend(_analyze_security(ssh_output["security"]))

    if "nomenclaturas" in contexts and "nomenclaturas" in ssh_output:
        findings.extend(_analyze_nomenclaturas(ssh_output["nomenclaturas"]))

    if "ntp_snmp" in contexts and "ntp_snmp" in ssh_output:
        findings.extend(_analyze_ntp_snmp(ssh_output["ntp_snmp"]))

    if "sysname" in contexts:
        sysname_out = ssh_output.get("sysname", "")
        findings.extend(_analyze_sysname(device, sysname_out))

    # Summary
    summary = {
        "total": len(findings),
        "blocker": sum(1 for f in findings if f["severity"] == "blocker"),
        "error": sum(1 for f in findings if f["severity"] == "error"),
        "warning": sum(1 for f in findings if f["severity"] == "warning"),
        "info": sum(1 for f in findings if f["severity"] == "info"),
    }

    return findings, summary
