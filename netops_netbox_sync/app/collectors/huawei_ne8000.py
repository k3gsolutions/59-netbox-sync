import re


class HuaweiNE8000Collector:
    COMMANDS = {
        "version":              "display version",
        "running_config":       "display current-configuration",
        "interfaces_brief":     "display interface brief",
        "interfaces_desc":      "display interface description",
        "ip_interfaces":        "display ip interface brief",
        "vlans":                "display vlan",
        "vrfs":                 "display ip vpn-instance",
        "bgp_summary":          "display bgp all summary",
        "bgp_peers":            "display bgp peer",
        "bgp_peers_verbose":    "display bgp peer verbose",
        "bgp_ipv6_verbose":     "display bgp ipv6 peer verbose",
        "route_policy":         "display route-policy",
        "ip_prefix":            "display ip ip-prefix",
        "as_path_filter":       "display ip as-path-filter",
    }

    # Comandos por VRF — {placeholder} será substituído pelo nome da VRF
    VRF_BGP_COMMANDS = {
        "vpnv4": "display bgp vpnv4 vpn-instance {vrf} peer verbose",
        "vpnv6": "display bgp vpnv6 vpn-instance {vrf} peer verbose",
    }

    def __init__(self, driver):
        self.driver = driver

    def _cmd(self, cmd: str, timeout: int = 90) -> str:
        return self.driver.send_command(cmd, read_timeout=timeout)

    def _is_valid(self, output: str) -> bool:
        """Retorna False se o output for erro ou vazio."""
        if not output or not output.strip():
            return False
        if "Unrecognized command" in output or ("^" in output[:80] and "Error" in output):
            return False
        if output.strip() in ("Info: No peer exists.", "Info: No VPN peer exists."):
            return False
        return True

    def _parse_vrf_names(self, vrfs_output: str) -> list[str]:
        """Extrai nomes de VRFs do output de 'display ip vpn-instance'."""
        vrfs = set()
        for line in vrfs_output.splitlines():
            m = re.match(r"\s+(\S+)\s+\S*\s+(IPv4|IPv6)", line)
            if m:
                name = m.group(1)
                if name not in ("VPN-Instance", "Name"):
                    vrfs.add(name)
        return list(vrfs)

    def collect_all(self) -> dict:
        """Coleta todos os comandos estáticos."""
        raw = {}
        for name, cmd in self.COMMANDS.items():
            raw[name] = self._cmd(cmd)
        return raw

    def collect_bgp_all_vrfs(self, vrfs_output: str) -> dict:
        """
        Coleta peers BGP de todas as VRFs (VPNv4 e VPNv6).
        Retorna dict: { "<af>:<vrf>": "<output_verbose>" }
        """
        vrf_names = self._parse_vrf_names(vrfs_output)
        results = {}

        for vrf in vrf_names:
            for af, tmpl in self.VRF_BGP_COMMANDS.items():
                cmd = tmpl.format(vrf=vrf)
                out = self._cmd(cmd)
                if self._is_valid(out):
                    results[f"{af}:{vrf}"] = out

        return results
