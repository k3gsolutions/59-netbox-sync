import pynetbox
from app.collectors.huawei_ne8000 import HuaweiNE8000Collector
from app.normalizers.netbox_mapper import build_inventory
from app.netbox.planner import build_plan
from app.netbox.sync import sync_to_netbox
from app.netbox.bgp_sync import sync_bgp_plugin
from app.analyzers.dependency_graph import build_dependency_graph
from app.analyzers.backup import save_backup


def run_collection(driver):
    collector = HuaweiNE8000Collector(driver)
    raw = collector.collect_all()
    vrf_bgp = collector.collect_bgp_all_vrfs(raw.get("vrfs", ""))
    inventory = build_inventory(raw, vrf_bgp=vrf_bgp)
    plan = build_plan(inventory)
    return raw, inventory, plan


def _normalize_nb_url(url: str) -> str:
    """Remove /api do final, caso o usuário tenha incluído na URL base."""
    url = url.rstrip("/")
    if url.endswith("/api"):
        url = url[:-4]
    return url


def run_update(driver, nb_url: str, nb_token: str, device_id: int,
               verify_ssl: bool = False) -> dict:
    """
    Coleta dados do dispositivo e sincroniza com o NetBox.
    Retorna dict com changelogs de DCIM e BGP.
    """
    collector = HuaweiNE8000Collector(driver)
    raw = collector.collect_all()
    vrf_bgp = collector.collect_bgp_all_vrfs(raw.get("vrfs", ""))
    inventory = build_inventory(raw, vrf_bgp=vrf_bgp)

    nb_base = _normalize_nb_url(nb_url)
    nb = pynetbox.api(nb_base, token=nb_token)
    nb.http_session.verify = verify_ssl

    # ── Resolve tenant e hostname do device ───────────────────────────────────
    tenant_id   = None
    tenant_name = None
    device_obj  = nb.dcim.devices.get(device_id)
    hostname    = device_obj.name if device_obj else f"device-{device_id}"
    if device_obj and device_obj.tenant:
        tenant_id   = device_obj.tenant.id
        tenant_name = device_obj.tenant.name

    # ── Backup versionado do running-config ───────────────────────────────────
    backup_info = {}
    running_config = raw.get("running_config", "")
    if running_config.strip():
        try:
            backup_info = save_backup(hostname, running_config)
            changed_msg = (
                f"+{backup_info['lines_added']}/-{backup_info['lines_removed']} linhas"
                if backup_info["changed"] else "sem alterações"
            )
            print(f"  [backup] {hostname} → {backup_info['file']} ({changed_msg})")
        except Exception as exc:
            print(f"  [backup] Aviso: não foi possível salvar backup — {exc}")

    # ── Grafo de dependências ─────────────────────────────────────────────────
    graph = build_dependency_graph(inventory)
    validation = graph["validation"]
    if validation["total_issues"]:
        print(f"  [grafo] {validation['total_issues']} referência(s) quebrada(s) detectada(s)!")
        for issue in validation["broken_refs"][:5]:
            print(f"    → {issue}")
    if validation["unused_prefix_lists"]:
        print(f"  [grafo] {len(validation['unused_prefix_lists'])} prefix-list(s) não utilizadas")
    if validation["unused_aspath_filters"]:
        print(f"  [grafo] {len(validation['unused_aspath_filters'])} as-path-filter(s) não utilizados")

    sync_to_netbox(nb, device_id, inventory, tenant_id=tenant_id)

    changelog = sync_bgp_plugin(
        base_url=nb_base,
        token=nb_token,
        device_id=device_id,
        inventory=inventory,
        verify_ssl=verify_ssl,
        verbose=False,
        tenant_id=tenant_id,
        tenant_name=tenant_name,
    )

    return {
        "inventory_summary": {
            "interfaces":     len(inventory.interfaces),
            "ip_addresses":   len(inventory.ip_addresses),
            "vrfs":           len(inventory.vrfs),
            "vlans":          len(inventory.vlans),
            "bgp_sessions":   len(inventory.bgp_sessions),
            "route_policies": len(inventory.route_policies),
            "prefix_lists":   len(inventory.prefix_lists),
            "as_path_filters":  len(inventory.as_path_filters),
            "communities":      len(inventory.communities),
            "community_lists":  len(inventory.community_lists),
        },
        "bgp_changelog": changelog.to_dict(),
        "backup": {
            "file":          backup_info.get("file"),
            "changed":       backup_info.get("changed", False),
            "lines_added":   backup_info.get("lines_added", 0),
            "lines_removed": backup_info.get("lines_removed", 0),
        },
        "validation": validation,
    }


def ask_confirmation(plan):
    print("\nResumo detectado:")
    for k, v in plan.items():
        print(f"- {k}: {v}")

    answer = input("\nConfirma a inserção no NetBox? [sim/nao]: ").strip().lower()
    return answer == "sim"