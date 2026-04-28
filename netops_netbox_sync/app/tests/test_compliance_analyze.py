import asyncio
import unittest
from unittest.mock import patch

from app.api.main import app
from app.api.routes import compliance
from app.api.schemas_analyze import AnalyzeRequest
from app.schemas.analyze import AnalyzeResult, AppliedSummary


class ComplianceAnalyzeTests(unittest.TestCase):
    def test_openapi_includes_compliance_analyze(self):
        data = app.openapi()
        self.assertIn("/compliance/analyze", data["paths"])
        self.assertIn("/device/collect", data["paths"])
        self.assertIn("/sync", data["paths"])

    @patch("app.api.routes.compliance._do_analyze")
    @patch("app.workflow.sync_device.sync_to_netbox")
    @patch("app.workflow.sync_device.sync_bgp_plugin")
    def test_compliance_analyze_returns_expected_schema(
        self,
        mock_sync_bgp_plugin,
        mock_sync_to_netbox,
        mock_do_analyze,
    ):
        mock_do_analyze.return_value = AnalyzeResult(
            hostname="test-device",
            device_id=None,
            mode="read-only",
            netbox_loaded=False,
            compliance_enabled=False,
            applied_summary=AppliedSummary(
                interfaces=0,
                ip_addresses=0,
                vrfs=0,
                vlans=0,
                bgp_sessions=0,
                route_policies=0,
                prefix_lists=0,
                as_path_filters=0,
                communities=0,
                community_lists=0,
            ),
            documented_summary=None,
            compliance_summary=None,
            summary_diff=[],
            divergences=[],
            warnings=[],
            next_steps=[],
        )

        req = AnalyzeRequest(
            device={
                "host": "192.0.2.1",
                "username": "admin",
                "password": "secret",
                "port": 22,
            }
        )
        result = asyncio.run(compliance.analyze_device(req))

        self.assertEqual(result.hostname, "test-device")
        self.assertEqual(result.mode, "read-only")
        self.assertIsNone(result.device_id)
        self.assertFalse(result.netbox_loaded)
        self.assertEqual(result.applied_summary.interfaces, 0)
        self.assertEqual(result.summary_diff, [])
        self.assertEqual(result.divergences, [])
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.next_steps, [])
        mock_sync_to_netbox.assert_not_called()
        mock_sync_bgp_plugin.assert_not_called()
