from app.compliance.summary_diff import build_summary_diff
from app.schemas.analyze import AppliedInventorySummary


def test_summary_diff_all_match():
    applied = AppliedInventorySummary(interfaces=2, ip_addresses=2)
    documented = AppliedInventorySummary(interfaces=2, ip_addresses=2)

    summary, items, divergences = build_summary_diff(applied, documented)

    assert summary.status == "ok"
    assert summary.mismatching_metrics == 0
    assert all(item.status == "match" for item in items)
    assert divergences == []


def test_summary_diff_detects_missing_in_netbox():
    applied = AppliedInventorySummary(interfaces=5)
    documented = AppliedInventorySummary(interfaces=3)

    summary, items, divergences = build_summary_diff(applied, documented)

    assert summary.status == "drift_detected"
    interface_item = next(item for item in items if item.metric == "interfaces")
    assert interface_item.delta == 2
    assert divergences[0].code == "MISSING_IN_NETBOX"
    assert divergences[0].preferred_action == "fix_netbox"
    assert divergences[0].severity == "high"


def test_summary_diff_detects_missing_on_device():
    applied = AppliedInventorySummary(bgp_sessions=2)
    documented = AppliedInventorySummary(bgp_sessions=4)

    summary, items, divergences = build_summary_diff(applied, documented)

    assert summary.status == "drift_detected"
    diff_item = next(item for item in items if item.metric == "bgp_sessions")
    assert diff_item.delta == -2
    assert divergences[0].code == "MISSING_ON_DEVICE"
    assert divergences[0].preferred_action == "review"
    assert divergences[0].severity == "high"
