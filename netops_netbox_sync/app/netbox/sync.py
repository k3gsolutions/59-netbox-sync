import json
import time
from app.analyzers.dependency_graph import build_dependency_graph


def _retry(fn, retries=3, delay=2):
    """Executa fn() com retry em ConnectionError ou exceções transitórias."""
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as exc:
            if attempt == retries:
                raise
            if any(t in type(exc).__name__ for t in ("Connection", "Timeout", "ReadTimeout")):
                time.sleep(delay * attempt)
            else:
                raise


def _upsert_interface(nb, device_id, name, payload):
    existing = list(nb.dcim.interfaces.filter(device_id=device_id, name=name))
    if existing:
        existing[0].update(payload)
        return existing[0]
    return nb.dcim.interfaces.create(payload)


def sync_to_netbox(nb, device_id, inventory, tenant_id: int = None):
    # ── VRFs ─────────────────────────────────────────────────────────────────
    for vrf in inventory.vrfs:
        existing = list(nb.ipam.vrfs.filter(name=vrf.name))
        if not existing:
            payload = {"name": vrf.name, "rd": vrf.rd}
            if tenant_id:
                payload["tenant"] = tenant_id
            nb.ipam.vrfs.create(payload)

    # ── VLANs ────────────────────────────────────────────────────────────────
    for vlan in inventory.vlans:
        existing = list(nb.ipam.vlans.filter(vid=vlan.vlan_id))
        if not existing:
            payload = {
                "vid": vlan.vlan_id,
                "name": vlan.name or f"VLAN{vlan.vlan_id}",
            }
            if tenant_id:
                payload["tenant"] = tenant_id
            nb.ipam.vlans.create(payload)

    # ── Interfaces (1ª passagem: cria/atualiza com tipo correto) ─────────────
    iface_name_to_id = {}
    for iface in inventory.interfaces:
        payload = {
            "device": device_id,
            "name": iface.name,
            "type": iface.type or "other",
            "description": iface.description or "",
            "enabled": iface.admin_status not in ("*down", "down") if iface.admin_status else True,
        }
        obj = _retry(lambda p=payload, n=iface.name: _upsert_interface(nb, device_id, n, p))
        iface_name_to_id[iface.name] = obj.id

    # ── Interfaces (2ª passagem: vincula membros LAG ao parent) ──────────────
    for iface in inventory.interfaces:
        if iface.lag_parent and iface.lag_parent in iface_name_to_id:
            lag_id = iface_name_to_id[iface.lag_parent]
            member_id = iface_name_to_id.get(iface.name)
            if member_id:
                _retry(lambda mid=member_id, lid=lag_id:
                       nb.dcim.interfaces.get(mid).update({"lag": lid}))

    # ── Tenant e VRF do device ────────────────────────────────────────────────
    device_obj = nb.dcim.devices.get(device_id)
    tenant_name = (
        device_obj.tenant.name
        if device_obj and device_obj.tenant
        else None
    )

    # ── Resolve VRF do tenant (cria se não existir) ───────────────────────────
    ip_vrf_id = None
    if tenant_name:
        existing_vrfs = list(nb.ipam.vrfs.filter(name=tenant_name))
        if existing_vrfs:
            ip_vrf_id = existing_vrfs[0].id
            print(f"  [VRF] Tenant '{tenant_name}' → VRF id={ip_vrf_id} encontrada.")
        else:
            new_vrf = nb.ipam.vrfs.create({"name": tenant_name})
            ip_vrf_id = new_vrf.id
            print(f"  [VRF] VRF '{tenant_name}' não existia → criada (id={ip_vrf_id}).")
    else:
        print("  [VRF] Device sem tenant — IPs na tabela global.")

    # ── Migra IPs já inseridos na tabela global para a VRF correta ────────────
    if ip_vrf_id:
        print(f"  [VRF] Verificando IPs na tabela global (sem VRF) para migrar...")
        migrated = skipped_dup = deleted_global = 0
        for iface_id in iface_name_to_id.values():
            global_ips = list(nb.ipam.ip_addresses.filter(
                assigned_object_type="dcim.interface",
                assigned_object_id=iface_id,
                vrf_id="null",
            ))
            for ip_obj in global_ips:
                # Verifica se já existe esse endereço na VRF destino
                already_in_vrf = list(nb.ipam.ip_addresses.filter(
                    address=str(ip_obj.address),
                    vrf_id=ip_vrf_id,
                ))
                if already_in_vrf:
                    # Remove o duplicado da tabela global
                    _retry(lambda o=ip_obj: o.delete())
                    deleted_global += 1
                else:
                    _retry(lambda o=ip_obj: o.update({"vrf": ip_vrf_id}))
                    migrated += 1
        msgs = []
        if migrated:      msgs.append(f"{migrated} migrado(s)")
        if deleted_global: msgs.append(f"{deleted_global} duplicado(s) global removido(s)")
        if skipped_dup:   msgs.append(f"{skipped_dup} ignorado(s)")
        print(f"  [VRF] {', '.join(msgs) or 'Nenhum IP na tabela global para migrar'}.")

    # ── IPs (vinculados à interface + VRF do tenant) ──────────────────────────
    for ip in inventory.ip_addresses:
        iface_id = iface_name_to_id.get(ip.interface)

        # Busca em todas as VRFs e global para evitar duplicatas
        existing = list(nb.ipam.ip_addresses.filter(address=ip.address))
        if not existing:
            # fallback: busca pelo host (ignora prefixo) em qualquer VRF
            host = ip.address.split("/")[0]
            existing = list(nb.ipam.ip_addresses.filter(q=host))

        if not existing:
            payload = {"address": ip.address, "status": "active"}
            if ip_vrf_id:
                payload["vrf"] = ip_vrf_id
            if iface_id:
                payload["assigned_object_type"] = "dcim.interface"
                payload["assigned_object_id"] = iface_id
            _retry(lambda p=payload: nb.ipam.ip_addresses.create(p))
        else:
            # IP já existe — atualiza VRF e/ou interface se necessário
            patch = {}
            if ip_vrf_id and not existing[0].vrf:
                patch["vrf"] = ip_vrf_id
            if iface_id and not existing[0].assigned_object_id:
                patch["assigned_object_type"] = "dcim.interface"
                patch["assigned_object_id"] = iface_id
            if patch:
                _retry(lambda e=existing[0], p=patch: e.update(p))

    # ── Config Context: grafo de dependências enriquecido ─────────────────────
    graph = build_dependency_graph(inventory)

    ctx_data = {
        # Sumário para leitura rápida
        "summary": {
            "local_as":       inventory.bgp_sessions[0].local_as if inventory.bgp_sessions else None,
            "total_peers":    len(inventory.bgp_sessions),
            "total_policies": len(inventory.route_policies),
            "total_pl":       len(inventory.prefix_lists),
            "total_aspath":   len(inventory.as_path_filters),
            "total_communities": len(inventory.communities),
            "validation":     graph["validation"],
        },
        # Grafo completo peer → cadeia import/export → objetos referenciados
        "dependency_graph": {
            "peers":    graph["peers"],
            "policies": graph["policies"],
        },
        # Inventário flat (compatibilidade com versão anterior)
        "bgp_sessions": [s.model_dump() for s in inventory.bgp_sessions],
        "prefix_lists": [
            {"name": pl.name, "entries": [e.model_dump() for e in pl.entries]}
            for pl in inventory.prefix_lists
        ],
        "as_path_filters": [
            {"name": f.name, "entries": [e.model_dump() for e in f.entries]}
            for f in inventory.as_path_filters
        ],
        "community_lists": [
            {"name": cl.name, "type": cl.type,
             "entries": [e.model_dump() for e in cl.entries]}
            for cl in inventory.community_lists
        ],
    }

    device = nb.dcim.devices.get(device_id)
    ctx_name = f"bgp-routing-{device.name}"

    existing_ctx = list(nb.extras.config_contexts.filter(name=ctx_name))
    if existing_ctx:
        existing_ctx[0].update({"data": ctx_data})
    else:
        nb.extras.config_contexts.create({
            "name": ctx_name,
            "weight": 1000,
            "data": ctx_data,
            "is_active": True,
        })
        # Associa o config context ao device
        ctx = list(nb.extras.config_contexts.filter(name=ctx_name))[0]
        ctx.update({"devices": [device_id]})
