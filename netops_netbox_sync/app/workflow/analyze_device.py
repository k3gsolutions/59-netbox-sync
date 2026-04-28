from app.collectors.huawei_ne8000 import HuaweiNE8000Collector
from app.normalizers.netbox_mapper import build_inventory
from app.netbox.inventory import load_netbox_inventory, resolve_netbox_device_id
from app.compliance.object_diff import build_object_diff
from app.compliance.summary_diff import build_summary_diff
from app.schemas.analyze import (
    AnalyzeResult,
    AppliedInventorySummary,
    AnalyzeWarning,
)


def run_analyze_device(
    driver,
    device_id: int | None = None,
    device_name: str | None = None,
    netbox=None,
) -> AnalyzeResult:
    collector = HuaweiNE8000Collector(driver)
    raw = collector.collect_all()
    vrf_bgp = collector.collect_bgp_all_vrfs(raw.get("vrfs", ""))
    inventory = build_inventory(raw, vrf_bgp=vrf_bgp)

    # hostname: prefer device name from inventory, fallback to SSH host
    hostname = inventory.hostname or getattr(driver, "host", None) or "unknown"

    warnings: list[AnalyzeWarning] = []
    netbox_loaded = False
    documented_summary: AppliedInventorySummary | None = None
    compliance_summary = None
    summary_diff = []
    divergences = []
    compliance_enabled = False

    applied_summary = AppliedInventorySummary(
        interfaces=len(inventory.interfaces),
        ip_addresses=len(inventory.ip_addresses),
        vrfs=len(inventory.vrfs),
        vlans=len(inventory.vlans),
        bgp_sessions=len(inventory.bgp_sessions),
        route_policies=len(inventory.route_policies),
        prefix_lists=len(inventory.prefix_lists),
        as_path_filters=len(inventory.as_path_filters),
        communities=len(inventory.communities),
        community_lists=len(inventory.community_lists),
    )

    resolved_device_id = device_id

    if netbox is not None:
        # Resolve device_id if not provided
        if resolved_device_id is None:
            resolved_device_id, resolve_warnings = resolve_netbox_device_id(
                netbox,
                device_id=None,
                device_name=device_name,
                device_host=getattr(driver, "host", None),
            )
            warnings.extend(resolve_warnings)

        if resolved_device_id is not None:
            try:
                netbox_inventory, load_warnings = load_netbox_inventory(netbox, resolved_device_id)
                warnings.extend(load_warnings)
                netbox_loaded = True
                documented_summary = netbox_inventory.summary
                # Update hostname if still unknown and NetBox device has name
                if hostname == "unknown" and netbox_inventory.device.name:
                    hostname = netbox_inventory.device.name
                if documented_summary is not None:
                    compliance_summary, summary_diff, divergences = build_summary_diff(
                        applied_summary,
                        documented_summary,
                    )
                    try:
                        object_divergences = build_object_diff(inventory, netbox_inventory)
                        divergences.extend(object_divergences)
                    except Exception as diff_exc:
                        warnings.append(
                            AnalyzeWarning(
                                code="COMPLIANCE_DIFF_FAILED",
                                severity="medium",
                                message=f"Erro no diff de objetos: {diff_exc}",
                            )
                        )
                    compliance_enabled = True
            except Exception as exc:
                warnings.append(
                    AnalyzeWarning(
                        code="NETBOX_LOAD_FAILED",
                        severity="medium",
                        message=f"Não foi possível carregar inventário do NetBox: {exc}",
                    )
                )
        # else: resolve_warnings already contain NOT_FOUND/AMBIGUOUS/FAILED
    else:
        warnings.append(
            AnalyzeWarning(
                code="NO_NETBOX_PARAMS",
                severity="low",
                message="Parâmetros do NetBox não foram fornecidos para carregar o inventário.",
            )
        )
        if device_id is None:
            warnings.append(
                AnalyzeWarning(
                    code="NO_NETBOX_DEVICE_ID",
                    severity="low",
                    message="Nenhum device_id foi fornecido para análise comparativa.",
                )
            )

    return AnalyzeResult(
        hostname=hostname,
        device_id=resolved_device_id,
        mode="read-only",
        netbox_loaded=netbox_loaded,
        compliance_enabled=compliance_enabled,
        applied_summary=applied_summary,
        documented_summary=documented_summary,
        compliance_summary=compliance_summary,
        summary_diff=summary_diff,
        divergences=divergences,
        warnings=warnings,
        next_steps=[
            "Analisar divergências agregadas e priorizar ações.",
            "Gerar relatório de compliance agregado.",
        ],
    )


run_analyze = run_analyze_device
