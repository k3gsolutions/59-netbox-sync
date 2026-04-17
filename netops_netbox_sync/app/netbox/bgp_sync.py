"""
Sincronização com o plugin netbox-bgp (v0.18+).
Endpoints base: /api/plugins/bgp/
"""
import re
import time
import requests


BGP_STATUS_MAP = {
    "Established": "active",
    "Idle":        "offline",
    "Idle(Admin)": "planned",
    "Active":      "offline",
    "Connect":     "offline",
    "OpenSent":    "offline",
    "OpenConfirm": "offline",
}


# ─────────────────────────────────────────────────────────────────────────────
# ChangeLog — rastreia todas as alterações para o resumo final
# ─────────────────────────────────────────────────────────────────────────────

class ChangeLog:
    def __init__(self):
        self._log: list[dict] = []

    def record(self, obj_type: str, name: str, action: str, detail: str = ""):
        self._log.append({"type": obj_type, "name": name, "action": action, "detail": detail})

    def summary(self) -> str:
        from collections import defaultdict
        counts = defaultdict(lambda: {"created": 0, "updated": 0, "skipped": 0})
        for entry in self._log:
            counts[entry["type"]][entry["action"]] += 1

        lines = ["\n══════════════════════════════════════════════════════════"]
        lines.append("  RESUMO DA SINCRONIZAÇÃO BGP")
        lines.append("══════════════════════════════════════════════════════════")
        lines.append(f"  {'Objeto':<28} {'Criados':>8} {'Atualizados':>12} {'Já existia':>12}")
        lines.append("  " + "─" * 64)
        for obj_type, cnt in sorted(counts.items()):
            lines.append(
                f"  {obj_type:<28} {cnt['created']:>8} {cnt['updated']:>12} {cnt['skipped']:>12}"
            )
        total_c = sum(v["created"] for v in counts.values())
        total_u = sum(v["updated"] for v in counts.values())
        total_s = sum(v["skipped"] for v in counts.values())
        lines.append("  " + "─" * 64)
        lines.append(f"  {'TOTAL':<28} {total_c:>8} {total_u:>12} {total_s:>12}")
        lines.append("══════════════════════════════════════════════════════════\n")
        return "\n".join(lines)

    def detail_lines(self) -> list[str]:
        return [
            f"  [{e['action'].upper():<8}] {e['type']:<28} {e['name']}"
            + (f"  ({e['detail']})" if e["detail"] else "")
            for e in self._log
        ]

    def to_dict(self) -> dict:
        from collections import defaultdict
        counts = defaultdict(lambda: {"created": 0, "updated": 0, "skipped": 0})
        for entry in self._log:
            counts[entry["type"]][entry["action"]] += 1
        return {
            "totals": {
                "created": sum(v["created"] for v in counts.values()),
                "updated": sum(v["updated"] for v in counts.values()),
                "skipped": sum(v["skipped"] for v in counts.values()),
            },
            "by_type": {k: dict(v) for k, v in sorted(counts.items())},
            "detail": self._log,
        }


# ─────────────────────────────────────────────────────────────────────────────
# BGPPluginClient — cliente HTTP alinhado com o schema real do plugin
# ─────────────────────────────────────────────────────────────────────────────

class BGPPluginClient:
    def __init__(self, base_url: str, token: str, verify_ssl: bool = True,
                 tenant_id: int = None, tenant_name: str = None):
        self.base = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.verify = verify_ssl
        self.tenant_id   = tenant_id
        self.tenant_name = tenant_name
        self.tag_slug    = None   # preenchido em get_or_create_tenant_tag()
        self._capabilities = self._detect_capabilities()

    def _detect_capabilities(self) -> dict:
        """Detecta endpoints disponíveis no plugin instalado."""
        try:
            r = requests.get(
                f"{self.base}/api/plugins/bgp/",
                headers=self.headers, verify=self.verify, timeout=10
            )
            endpoints = set(r.json().keys()) if r.ok else set()
        except Exception:
            endpoints = set()
        return {
            "aspath_list":      "aspath-list" in endpoints,
            "match_aspath_list": "aspath-list" in endpoints,
        }

    @property
    def has_aspath(self) -> bool:
        return self._capabilities["aspath_list"]

    def _url(self, path: str) -> str:
        return f"{self.base}/api/plugins/bgp/{path}/"

    def _ipam(self, path: str) -> str:
        return f"{self.base}/api/ipam/{path}/"

    def _get(self, url: str, params: dict = None, retries: int = 3) -> list:
        for attempt in range(1, retries + 1):
            r = requests.get(url, headers=self.headers, params=params or {},
                             verify=self.verify, timeout=30)
            if r.ok:
                return r.json().get("results", [])
            if r.status_code in (502, 503, 504) and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
        return []

    def _post(self, url: str, payload: dict, retries: int = 3) -> dict:
        for attempt in range(1, retries + 1):
            r = requests.post(url, headers=self.headers, json=payload,
                              verify=self.verify, timeout=30)
            if r.ok:
                return r.json()
            if r.status_code in (502, 503, 504) and attempt < retries:
                time.sleep(2 ** attempt)   # backoff: 2s, 4s
                continue
            raise RuntimeError(f"POST {url} falhou [{r.status_code}]: {r.text[:300]}")
        raise RuntimeError(f"POST {url} falhou após {retries} tentativas")

    def _patch(self, url: str, payload: dict, retries: int = 3) -> dict:
        for attempt in range(1, retries + 1):
            r = requests.patch(url, headers=self.headers, json=payload,
                               verify=self.verify, timeout=30)
            if r.ok:
                return r.json()
            if r.status_code in (502, 503, 504) and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"PATCH {url} falhou [{r.status_code}]: {r.text[:300]}")
        raise RuntimeError(f"PATCH {url} falhou após {retries} tentativas")

    def _get_or_create(self, url: str, filter_params: dict, create_payload: dict,
                       changelog: ChangeLog, obj_type: str, name: str):
        existing = self._get(url, filter_params)
        if existing:
            changelog.record(obj_type, name, "skipped")
            return existing[0], False
        obj = self._post(url, create_payload)
        changelog.record(obj_type, name, "created")
        return obj, True

    # ── Tag de tenant (para objetos sem campo tenant nativo) ─────────────────
    def get_or_create_tenant_tag(self) -> str | None:
        """Cria/retorna a tag slug do tenant para uso em objetos que não têm campo tenant."""
        if not self.tenant_name:
            return None
        if self.tag_slug:
            return self.tag_slug
        slug = re.sub(r"[^a-z0-9-]", "-", self.tenant_name.lower()).strip("-")
        results = self._get(f"{self.base}/api/extras/tags/", {"slug": slug})
        if not results:
            color = "0275d8"   # azul padrão
            try:
                tag = self._post(f"{self.base}/api/extras/tags/",
                                 {"name": self.tenant_name, "slug": slug, "color": color})
            except RuntimeError:
                return None
        self.tag_slug = slug
        return slug

    def _with_tag(self, payload: dict) -> dict:
        """Injeta tag do tenant no payload se disponível."""
        if self.tag_slug:
            payload.setdefault("tags", [])
            if not any(t.get("slug") == self.tag_slug for t in payload["tags"]):
                payload["tags"].append({"slug": self.tag_slug})
        return payload

    def _with_tenant(self, payload: dict) -> dict:
        """Injeta tenant_id no payload se disponível."""
        if self.tenant_id:
            payload["tenant"] = self.tenant_id
        return payload

    # ── ASN ──────────────────────────────────────────────────────────────────
    def _get_or_create_rir(self) -> int:
        """Garante que existe um RIR padrão e retorna seu ID."""
        results = self._get(self._ipam("rirs"), {"slug": "unknown"})
        if results:
            return results[0]["id"]
        obj = self._post(self._ipam("rirs"), {"name": "Unknown", "slug": "unknown"})
        return obj["id"]

    def get_or_create_asn(self, asn: int, changelog: ChangeLog) -> dict:
        results = self._get(self._ipam("asns"), {"asn": asn})
        if results:
            changelog.record("ASN", str(asn), "skipped")
            return results[0]
        rir_id = self._get_or_create_rir()
        obj = self._post(self._ipam("asns"), {"asn": asn, "rir": rir_id})
        changelog.record("ASN", str(asn), "created")
        return obj

    # ── IP Address ───────────────────────────────────────────────────────────
    @staticmethod
    def _normalize_ip(address: str) -> str:
        """Acrescenta prefixo /32 (IPv4) ou /128 (IPv6) se não houver máscara."""
        if "/" in address:
            return address
        return f"{address}/128" if ":" in address else f"{address}/32"

    def get_or_create_ip(self, address: str, changelog: ChangeLog) -> dict:
        address = self._normalize_ip(address)
        host = address.split("/")[0]

        # 1. busca match exato na tabela global
        results = self._get(self._ipam("ip-addresses"), {"address": address})
        if results:
            changelog.record("IPAddress", address, "skipped")
            return results[0]

        # 2. busca em todas as VRFs pelo host (evita duplicata em qualquer VRF)
        results = self._get(self._ipam("ip-addresses"), {"q": host})
        if results:
            changelog.record("IPAddress", address, "skipped")
            return results[0]

        # 3. cria novo na tabela global
        obj = self._post(self._ipam("ip-addresses"), {"address": address, "status": "active"})
        changelog.record("IPAddress", address, "created")
        return obj

    # ── Prefix List ──────────────────────────────────────────────────────────
    def get_or_create_prefix_list(self, name: str, family: str,
                                   changelog: ChangeLog) -> dict:
        existing = self._get(self._url("prefix-list"), {"name": name})
        if existing:
            obj = existing[0]
            if self.tag_slug and not any(t.get("slug") == self.tag_slug for t in obj.get("tags", [])):
                obj = self._patch(
                    f"{self.base}/api/plugins/bgp/prefix-list/{obj['id']}/",
                    {"tags": [{"slug": self.tag_slug}]}
                )
                changelog.record("PrefixList", name, "updated", "tag linked")
            else:
                changelog.record("PrefixList", name, "skipped")
            return obj
        payload = self._with_tag({"name": name, "family": family})
        obj = self._post(self._url("prefix-list"), payload)
        changelog.record("PrefixList", name, "created")
        return obj

    def get_or_create_prefix_list_rule(
        self, pl_id: int, index: int, action: str,
        prefix: str, ge: int, le: int, changelog: ChangeLog
    ) -> dict:
        existing = self._get(self._url("prefix-list-rule"),
                             {"prefix_list_id": pl_id, "index": index})
        name = f"pl:{pl_id}#{index}"
        if existing:
            changelog.record("PrefixListRule", name, "skipped")
            return existing[0]
        payload = {
            "prefix_list": pl_id,
            "index": index,
            "action": action,
            "prefix_custom": prefix,
        }
        if ge is not None:
            payload["ge"] = ge
        if le is not None:
            payload["le"] = le
        obj = self._post(self._url("prefix-list-rule"), payload)
        changelog.record("PrefixListRule", name, "created", f"{action} {prefix}")
        return obj

    # ── Community ─────────────────────────────────────────────────────────────
    def get_or_create_community(self, value: str, changelog: ChangeLog) -> dict:
        results = self._get(self._url("community"), {"value": value})
        if results:
            obj = results[0]
            # Atualiza tenant se ainda não estiver setado
            if self.tenant_id and not obj.get("tenant"):
                obj = self._patch(
                    f"{self.base}/api/plugins/bgp/community/{obj['id']}/",
                    {"tenant": self.tenant_id}
                )
                changelog.record("Community", value, "updated", "tenant linked")
            else:
                changelog.record("Community", value, "skipped")
            return obj
        payload = self._with_tenant({"value": value, "status": "active"})
        obj = self._post(self._url("community"), payload)
        changelog.record("Community", value, "created")
        return obj

    def get_or_create_community_list(self, name: str, changelog: ChangeLog) -> dict:
        existing = self._get(self._url("community-list"), {"name": name})
        if existing:
            obj = existing[0]
            if self.tag_slug and not any(t.get("slug") == self.tag_slug for t in obj.get("tags", [])):
                obj = self._patch(
                    f"{self.base}/api/plugins/bgp/community-list/{obj['id']}/",
                    {"tags": [{"slug": self.tag_slug}]}
                )
                changelog.record("CommunityList", name, "updated", "tag linked")
            else:
                changelog.record("CommunityList", name, "skipped")
            return obj
        payload = self._with_tag({"name": name})
        obj = self._post(self._url("community-list"), payload)
        changelog.record("CommunityList", name, "created")
        return obj

    def get_or_create_community_list_rule(
        self, cl_id: int, index: int, action: str,
        community_id: int, changelog: ChangeLog
    ) -> dict:
        existing = self._get(self._url("community-list-rule"),
                             {"community_list_id": cl_id, "index": index})
        name = f"cl:{cl_id}#{index}"
        if existing:
            changelog.record("CommunityListRule", name, "skipped")
            return existing[0]
        obj = self._post(self._url("community-list-rule"), {
            "community_list": cl_id,
            "index":          index,
            "action":         action,
            "community":      community_id,
        })
        changelog.record("CommunityListRule", name, "created", f"{action}")
        return obj

    # ── AS-Path List ─────────────────────────────────────────────────────────
    def get_or_create_aspath_list(self, name: str, changelog: ChangeLog) -> dict:
        existing = self._get(self._url("aspath-list"), {"name": name})
        if existing:
            obj = existing[0]
            if self.tag_slug and not any(t.get("slug") == self.tag_slug for t in obj.get("tags", [])):
                obj = self._patch(
                    f"{self.base}/api/plugins/bgp/aspath-list/{obj['id']}/",
                    {"tags": [{"slug": self.tag_slug}]}
                )
                changelog.record("ASPathList", name, "updated", "tag linked")
            else:
                changelog.record("ASPathList", name, "skipped")
            return obj
        payload = self._with_tag({"name": name})
        obj = self._post(self._url("aspath-list"), payload)
        changelog.record("ASPathList", name, "created")
        return obj

    def get_or_create_aspath_list_rule(
        self, aspath_id: int, index: int, action: str,
        pattern: str, changelog: ChangeLog
    ) -> dict:
        existing = self._get(self._url("aspath-list-rule"),
                             {"aspath_list_id": aspath_id, "index": index})
        name = f"aspath:{aspath_id}#{index}"
        if existing:
            changelog.record("ASPathListRule", name, "skipped")
            return existing[0]
        obj = self._post(self._url("aspath-list-rule"), {
            "aspath_list": aspath_id,
            "index": index,
            "action": action,
            "pattern": pattern,
        })
        changelog.record("ASPathListRule", name, "created", f"{action} {pattern}")
        return obj

    # ── Routing Policy ───────────────────────────────────────────────────────
    def get_or_create_routing_policy(self, name: str, changelog: ChangeLog) -> dict:
        existing = self._get(self._url("routing-policy"), {"name": name})
        if existing:
            obj = existing[0]
            if self.tag_slug and not any(t.get("slug") == self.tag_slug for t in obj.get("tags", [])):
                obj = self._patch(
                    f"{self.base}/api/plugins/bgp/routing-policy/{obj['id']}/",
                    {"tags": [{"slug": self.tag_slug}]}
                )
                changelog.record("RoutingPolicy", name, "updated", "tag linked")
            else:
                changelog.record("RoutingPolicy", name, "skipped")
            return obj
        payload = self._with_tag({"name": name})
        obj = self._post(self._url("routing-policy"), payload)
        changelog.record("RoutingPolicy", name, "created")
        return obj

    def get_or_create_routing_policy_rule(
        self, policy_id: int, index: int, action: str,
        match_clauses: list, apply_clauses: list,
        pl_name_to_id: dict, aspath_name_to_id: dict,
        cl_name_to_id: dict,
        changelog: ChangeLog,
    ) -> dict:
        existing = self._get(self._url("routing-policy-rule"),
                             {"routing_policy_id": policy_id, "index": index})
        name = f"rp:{policy_id}#{index}"
        if existing:
            changelog.record("RoutingPolicyRule", name, "skipped")
            return existing[0]

        payload = {
            "routing_policy": policy_id,
            "index": index,
            "action": action,
            "match_ip_address": [],
            "match_ipv6_address": [],
            "match_community_list": [],
            "match_custom": {},
            "set_actions": {},
        }
        if self.has_aspath:
            payload["match_aspath_list"] = []

        custom_match = []
        for clause in match_clauses:
            # ip-prefix → match_ip_address
            m = re.match(r"ip-prefix\s+(\S+)", clause)
            if m and m.group(1) in pl_name_to_id:
                payload["match_ip_address"].append(pl_name_to_id[m.group(1)])
                continue
            # ipv6 address prefix-list → match_ipv6_address
            m = re.match(r"ipv6 address prefix-list\s+(\S+)", clause)
            if m and m.group(1) in pl_name_to_id:
                payload["match_ipv6_address"].append(pl_name_to_id[m.group(1)])
                continue
            # as-path-filter → match_aspath_list (somente se suportado)
            m = re.match(r"as-path-filter\s+(\S+)", clause)
            if m:
                if self.has_aspath and m.group(1) in aspath_name_to_id:
                    payload["match_aspath_list"].append(aspath_name_to_id[m.group(1)])
                else:
                    custom_match.append(clause)
                continue
            # community-filter → match_community_list
            m = re.match(r"community-filter\s+(\S+)", clause)
            if m:
                if m.group(1) in cl_name_to_id:
                    payload["match_community_list"].append(cl_name_to_id[m.group(1)])
                else:
                    custom_match.append(clause)
                continue
            # tudo mais → custom
            custom_match.append(clause)

        if custom_match:
            payload["match_custom"] = {"clauses": custom_match}

        if apply_clauses:
            payload["set_actions"] = {"actions": apply_clauses}

        obj = self._post(self._url("routing-policy-rule"), payload)
        changelog.record("RoutingPolicyRule", name, "created",
                         f"{action} seq={index}")
        return obj

    # ── BGP Session ──────────────────────────────────────────────────────────
    def get_or_create_session(
        self, local_addr_id: int, remote_addr_id: int, payload: dict,
        changelog: ChangeLog
    ) -> tuple:
        existing = self._get(self._url("session"), {
            "local_address_id": local_addr_id,
            "remote_address_id": remote_addr_id,
        })
        name = payload.get("name", f"session:{remote_addr_id}")
        if existing:
            # Atualiza campos que podem ter mudado (status, description, tenant)
            sess = existing[0]
            patch = {}
            if sess.get("status", {}).get("value") != payload.get("status"):
                patch["status"] = payload["status"]
            if sess.get("description", "") != payload.get("description", ""):
                patch["description"] = payload.get("description", "")
            if self.tenant_id and not sess.get("tenant"):
                patch["tenant"] = self.tenant_id
            if patch:
                updated = self._patch(
                    f"{self.base}/api/plugins/bgp/session/{sess['id']}/", patch
                )
                changelog.record("BGPSession", name, "updated",
                                 ", ".join(patch.keys()))
                return updated, False
            changelog.record("BGPSession", name, "skipped")
            return sess, False
        obj = self._post(self._url("session"), payload)
        changelog.record("BGPSession", name, "created")
        return obj, True

    def link_session_policies(
        self, session_id: int,
        import_pol_id: int = None, export_pol_id: int = None,
        pl_in_id: int = None, pl_out_id: int = None,
        changelog: ChangeLog = None,
    ):
        patch = {}
        if import_pol_id:
            patch["import_policies"] = [import_pol_id]
        if export_pol_id:
            patch["export_policies"] = [export_pol_id]
        if pl_in_id:
            patch["prefix_list_in"] = pl_in_id
        if pl_out_id:
            patch["prefix_list_out"] = pl_out_id
        if patch:
            self._patch(
                f"{self.base}/api/plugins/bgp/session/{session_id}/", patch
            )
            if changelog:
                changelog.record("BGPSession", f"id:{session_id}", "updated",
                                 "policies linked")


# ─────────────────────────────────────────────────────────────────────────────
# Função principal de sync BGP
# ─────────────────────────────────────────────────────────────────────────────

def sync_bgp_plugin(
    base_url: str, token: str, device_id: int, inventory,
    verify_ssl: bool = True, verbose: bool = True,
    tenant_id: int = None, tenant_name: str = None,
) -> ChangeLog:

    client = BGPPluginClient(base_url, token, verify_ssl,
                             tenant_id=tenant_id, tenant_name=tenant_name)
    changelog = ChangeLog()

    def log(msg):
        if verbose:
            print(msg)

    # Cria tag do tenant (para objetos que não suportam campo tenant nativo)
    if tenant_name:
        client.get_or_create_tenant_tag()
        log(f"  [tenant] Tag '{tenant_name}' (slug={client.tag_slug}) pronta.")

    # ── 0a. Community Values individuais (de apply community + community-filter) ─
    log("  [0/6] Communities (valores individuais)...")
    comm_value_to_id: dict[str, int] = {}
    for value in inventory.communities:
        try:
            obj = client.get_or_create_community(value, changelog)
            comm_value_to_id[value] = obj["id"]
        except RuntimeError as exc:
            changelog.record("Community", value, "skipped", str(exc)[:80])

    # ── 0b. Community Lists + Rules ───────────────────────────────────────────
    log("  [0b/6] Community Lists...")
    cl_name_to_id: dict[str, int] = {}
    for cl in inventory.community_lists:
        cl_obj = client.get_or_create_community_list(cl.name, changelog)
        cl_name_to_id[cl.name] = cl_obj["id"]
        for entry in cl.entries:
            # Reutiliza community já criado ou cria novo
            try:
                if entry.community in comm_value_to_id:
                    comm_id = comm_value_to_id[entry.community]
                else:
                    comm_obj = client.get_or_create_community(entry.community, changelog)
                    comm_id = comm_obj["id"]
                    comm_value_to_id[entry.community] = comm_id
                client.get_or_create_community_list_rule(
                    cl_obj["id"], entry.index, entry.action,
                    comm_id, changelog
                )
            except RuntimeError as exc:
                changelog.record("CommunityListRule",
                                 f"{cl.name}#{entry.index}", "skipped", str(exc)[:80])

    # ── 1. Prefix Lists + Rules ───────────────────────────────────────────────
    log("  [1/6] Prefix Lists...")
    pl_name_to_id: dict[str, int] = {}
    for pl in inventory.prefix_lists:
        family = "ipv6" if "v6" in pl.name.lower() or "ipv6" in pl.name.lower() else "ipv4"
        pl_obj = client.get_or_create_prefix_list(pl.name, family, changelog)
        pl_name_to_id[pl.name] = pl_obj["id"]

        for entry in pl.entries:
            ge = le = None
            if entry.options:
                m_ge = re.search(r"ge\s+(\d+)", entry.options)
                m_le = re.search(r"le\s+(\d+)", entry.options)
                ge = int(m_ge.group(1)) if m_ge else None
                le = int(m_le.group(1)) if m_le else None
            client.get_or_create_prefix_list_rule(
                pl_obj["id"], entry.index, entry.action,
                entry.prefix, ge, le, changelog
            )

    # ── 2. AS-Path Lists + Rules ─────────────────────────────────────────────
    aspath_name_to_id: dict[str, int] = {}
    if client.has_aspath:
        log("  [2/6] AS-Path Lists...")
        for aspath in inventory.as_path_filters:
            as_obj = client.get_or_create_aspath_list(aspath.name, changelog)
            aspath_name_to_id[aspath.name] = as_obj["id"]
            for entry in aspath.entries:
                client.get_or_create_aspath_list_rule(
                    as_obj["id"], entry.index, entry.action, entry.regex, changelog
                )
    else:
        log("  [2/6] AS-Path Lists... IGNORADO (plugin v0.15 não suporta — atualize para v0.18+)")

    # ── 3. Routing Policies + Rules ───────────────────────────────────────────
    log("  [3/6] Routing Policies...")
    policy_name_to_id: dict[str, int] = {}
    for rp in inventory.route_policies:
        rp_obj = client.get_or_create_routing_policy(rp.name, changelog)
        policy_name_to_id[rp.name] = rp_obj["id"]
        for node in rp.nodes:
            try:
                client.get_or_create_routing_policy_rule(
                    rp_obj["id"], node.sequence, node.action,
                    node.match, node.apply,
                    pl_name_to_id, aspath_name_to_id, cl_name_to_id,
                    changelog,
                )
            except RuntimeError as exc:
                changelog.record("RoutingPolicyRule",
                                 f"{rp.name}#{node.sequence}", "skipped", str(exc)[:80])

    # ── 4. ASNs e IPs dos peers ───────────────────────────────────────────────
    log("  [4/6] ASNs e IPs de peers...")
    asn_cache: dict[int, int] = {}
    for session in inventory.bgp_sessions:
        for asn_val in {session.local_as, session.peer_as}:
            if asn_val and asn_val not in asn_cache:
                obj = client.get_or_create_asn(asn_val, changelog)
                asn_cache[asn_val] = obj["id"]

    # ── 5. BGP Sessions ───────────────────────────────────────────────────────
    log("  [5/6] BGP Sessions...")
    for session in inventory.bgp_sessions:
        if not session.local_as or not session.peer_as:
            changelog.record("BGPSession", session.peer_ip, "skipped", "ASN ausente")
            continue

        local_as_id  = asn_cache.get(session.local_as)
        remote_as_id = asn_cache.get(session.peer_as)
        if not local_as_id or not remote_as_id:
            continue

        # local_address = router-id do dispositivo (IPv6 sessions usam IPv6 router-id se disponível)
        router_id = session.router_id or ""
        local_ip = client.get_or_create_ip(router_id, changelog) if router_id else None

        # remote_address = IP do peer (auto-detect /32 vs /128)
        remote_ip = client.get_or_create_ip(session.peer_ip, changelog)

        if not local_ip:
            changelog.record("BGPSession", session.peer_ip, "skipped", "local_address não resolvido")
            continue

        # Nome inclui AF e VRF para unicidade quando há múltiplas AFs
        af = session.address_family or "ipv4"
        vrf_label = f"/{session.vrf}" if session.vrf else ""
        session_name = f"{session.peer_type or 'BGP'}-{session.peer_ip}-{af}{vrf_label}"

        status = BGP_STATUS_MAP.get(session.state or "", "offline")
        payload = client._with_tenant({
            "name": session_name,
            "local_address": local_ip["id"],
            "remote_address": remote_ip["id"],
            "local_as": local_as_id,
            "remote_as": remote_as_id,
            "status": status,
            "device": device_id,
            "description": session.description or "",
        })

        sess_obj, _ = client.get_or_create_session(
            local_ip["id"], remote_ip["id"], payload, changelog
        )

        # Vincula políticas e prefix-lists
        client.link_session_policies(
            sess_obj["id"],
            import_pol_id  = policy_name_to_id.get(session.import_policy),
            export_pol_id  = policy_name_to_id.get(session.export_policy),
            pl_in_id       = pl_name_to_id.get(session.import_prefix_list),
            pl_out_id      = pl_name_to_id.get(session.export_prefix_list),
            changelog      = changelog,
        )

        log(
            f"    {'✓' if status == 'active' else '○'} {session.peer_ip:<40}"
            f" AS={session.peer_as:<8} [{status:<8}]"
            f" {session.peer_type or '?':<5} [{af}{vrf_label}]"
            f" import={session.import_policy or '-':<30}"
            f" export={session.export_policy or '-'}"
        )

    return changelog
