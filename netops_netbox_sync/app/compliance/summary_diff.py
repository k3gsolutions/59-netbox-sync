from typing import List, Tuple

from app.schemas.analyze import AppliedInventorySummary
from app.schemas.compliance import (
    ComplianceSummary,
    ComplianceDivergence,
    SummaryDiffItem,
)

METRICS = [
    ("interfaces", "high"),
    ("ip_addresses", "high"),
    ("vrfs", "medium"),
    ("vlans", "medium"),
    ("bgp_sessions", "high"),
    ("route_policies", "medium"),
    ("prefix_lists", "medium"),
    ("as_path_filters", "medium"),
    ("communities", "medium"),
    ("community_lists", "medium"),
]


def build_summary_diff(
    applied: AppliedInventorySummary,
    documented: AppliedInventorySummary,
) -> Tuple[ComplianceSummary, List[SummaryDiffItem], List[ComplianceDivergence]]:
    diff_items: List[SummaryDiffItem] = []
    divergences: List[ComplianceDivergence] = []

    matching = 0
    mismatching = 0

    for metric, severity in METRICS:
        applied_value = getattr(applied, metric)
        documented_value = getattr(documented, metric)
        delta = applied_value - documented_value
        status = "match" if delta == 0 else "mismatch"
        if status == "match":
            matching += 1
        else:
            mismatching += 1
            if delta > 0:
                code = "MISSING_IN_NETBOX"
                preferred_action = "fix_netbox"
                message = (
                    "Existem objetos aplicados no dispositivo que não estão documentados no NetBox."
                )
            else:
                code = "MISSING_ON_DEVICE"
                preferred_action = "review"
                message = (
                    "Existem objetos documentados no NetBox que não aparecem no dispositivo."
                )

            divergences.append(
                ComplianceDivergence(
                    code=code,
                    severity=severity,
                    scope=metric,
                    message=message,
                    evidence={
                        "applied": applied_value,
                        "documented": documented_value,
                        "delta": delta,
                    },
                    recommendation="Investigar diferença de contagem antes de ações corretivas.",
                    preferred_action=preferred_action,
                )
            )

        diff_items.append(
            SummaryDiffItem(
                metric=metric,
                applied=applied_value,
                documented=documented_value,
                delta=delta,
                status=status,
            )
        )

    summary = ComplianceSummary(
        total_metrics=len(METRICS),
        matching_metrics=matching,
        mismatching_metrics=mismatching,
        status="ok" if mismatching == 0 else "drift_detected",
    )

    return summary, diff_items, divergences
