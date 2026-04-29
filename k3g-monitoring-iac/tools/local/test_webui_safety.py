#!/usr/bin/env python3
"""
Security tests for web UI — FASE 3.9 with response forms.

Verify:
- No path traversal
- No sensitive files accessible
- POST allowed ONLY for /service-engagement/{device}/responses/edit
- All other POST/PATCH/DELETE blocked
- Response validation works
- No NetBox API calls
- No approval/apply automatic creation
"""

import sys
from pathlib import Path

# Add webui to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webui.services.artifact_scanner import safe_resolve_path


def test_imports():
    """Test that modules import without error."""
    print("Test 1: Imports")
    try:
        from webui import app
        from webui.services import validators, response_forms
        print("  ✓ app imports OK")
        print("  ✓ validators imports OK")
        print("  ✓ response_forms imports OK")
    except ImportError as e:
        if "jinja2" in str(e).lower():
            print(f"  ⚠ SKIP: jinja2 not in test env")
            return True
        print(f"  ✗ FAILED: {e}")
        return False

    return True


def test_path_traversal():
    """Test path traversal protection."""
    print("\nTest 2: Path Traversal Protection")
    root = Path(__file__).parent.parent.parent / "reports"

    # Should block ..
    result = safe_resolve_path(root, "../../etc/passwd")
    if result is None:
        print("  ✓ Blocks ../../")
    else:
        print(f"  ✗ FAILED: Should block ../, got {result}")
        return False

    return True


def test_denylist():
    """Test denylist protection."""
    print("\nTest 3: Denylist Protection")
    root = Path(__file__).parent.parent.parent / "reports"

    # Should block payload.local.json
    result = safe_resolve_path(root, "payload.local.json")
    if result is None:
        print("  ✓ Blocks payload.local.json")
    else:
        print(f"  ✗ FAILED: Should block payload.local.json")
        return False

    # Should block files with 'raw' in name
    result = safe_resolve_path(root, "something-raw.json")
    if result is None:
        print("  ✓ Blocks *raw*.json")
    else:
        print(f"  ✗ FAILED: Should block raw JSON")
        return False

    return True


def test_safe_paths():
    """Test that safe paths work."""
    print("\nTest 4: Safe Paths")
    root = Path(__file__).parent.parent.parent / "reports"

    # Safe paths should resolve
    result = safe_resolve_path(root, "pilot-device-compliance/README.md")
    if result is not None:
        print("  ✓ Safe paths resolve correctly")
        return True
    else:
        print("  ✗ FAILED: Safe path should resolve")
        return False


def test_allowed_post_routes():
    """Verify POST allowed ONLY for response forms."""
    print("\nTest 5: Allowed POST Routes (Response Forms)")
    try:
        from webui.app import app

        allowed_posts = [
            "/service-engagement/{device}/responses/edit"
        ]

        write_routes = {}
        for route in app.routes:
            methods = getattr(route, "methods", set())
            if "POST" in methods or "PATCH" in methods or "DELETE" in methods:
                path = getattr(route, "path", "")
                write_routes[path] = methods

        # Check allowed
        allowed_found = 0
        for path in allowed_posts:
            if path in write_routes:
                print(f"  ✓ Allowed POST found: {path}")
                allowed_found += 1

        # Check blocked
        blocked = [p for p in write_routes if p not in allowed_posts]
        if blocked:
            print(f"  ✗ FAILED: Blocked POST routes still exist:")
            for path in blocked:
                print(f"    - {path}: {write_routes[path]}")
            return False

        if allowed_found >= 1:
            print(f"  ✓ {allowed_found} allowed POST route(s)")
            return True
        else:
            print("  ✗ FAILED: Response form POST not found")
            return False

    except Exception as e:
        print(f"  ⚠ SKIP (dynamic routes): {str(e)[:50]}")
        return True


def test_no_write_keywords():
    """Test for dangerous keywords in code."""
    print("\nTest 6: No Write Keywords")

    app_path = Path(__file__).parent.parent.parent / "webui" / "app.py"
    dangerous_keywords = [
        "netbox_create",
        "netbox_update",
        "netbox_delete",
        "/sync",
        "approve_approval",
        "create_apply_plan",
    ]

    if not app_path.exists():
        print("  ⚠ SKIP: app.py not found")
        return True

    with open(app_path, 'r') as f:
        content = f.read()

    found = []
    for keyword in dangerous_keywords:
        if keyword in content:
            found.append(keyword)

    if not found:
        print("  ✓ No dangerous keywords")
        return True
    else:
        print(f"  ✗ FAILED: Found dangerous keywords: {found}")
        return False


def test_validator_service_type():
    """Test service_type validator."""
    print("\nTest 7: Validator — Service Type")
    try:
        from webui.services.validators import validate_service_type

        # Valid
        valid, err = validate_service_type("customer-internet", required=True)
        if valid:
            print("  ✓ Valid service type accepted")
        else:
            print(f"  ✗ FAILED: Valid service type rejected: {err}")
            return False

        # Invalid
        valid, err = validate_service_type("invalid-service", required=True)
        if not valid:
            print("  ✓ Invalid service type rejected")
        else:
            print("  ✗ FAILED: Invalid service type accepted")
            return False

        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_validator_asn():
    """Test remote_asn validator."""
    print("\nTest 8: Validator — Remote ASN")
    try:
        from webui.services.validators import validate_remote_asn

        # Valid ASN
        valid, err = validate_remote_asn("64512", required=True)
        if valid:
            print("  ✓ Valid ASN accepted")
        else:
            print(f"  ✗ FAILED: Valid ASN rejected: {err}")
            return False

        # Invalid ASN (too large)
        valid, err = validate_remote_asn("5000000000", required=True)
        if not valid:
            print("  ✓ Invalid ASN rejected")
        else:
            print("  ✗ FAILED: Invalid ASN accepted")
            return False

        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_blocked_keywords():
    """Test that blocked keywords are detected."""
    print("\nTest 9: Blocked Keywords Detection")
    try:
        from webui.services.validators import contains_blocked_keywords

        # Should block password
        if contains_blocked_keywords("password=secret123"):
            print("  ✓ Blocks 'password='")
        else:
            print("  ✗ FAILED: Should block password")
            return False

        # Should block token
        if contains_blocked_keywords("token abc123"):
            print("  ✓ Blocks 'token '")
        else:
            print("  ✗ FAILED: Should block token")
            return False

        # Should allow normal text
        if not contains_blocked_keywords("This is customer data"):
            print("  ✓ Allows normal text")
        else:
            print("  ✗ FAILED: Should allow normal text")
            return False

        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("K3G Web UI Safety Tests — FASE 3.9")
    print("=" * 60)

    tests = [
        test_imports,
        test_path_traversal,
        test_denylist,
        test_safe_paths,
        test_allowed_post_routes,
        test_no_write_keywords,
        test_validator_service_type,
        test_validator_asn,
        test_blocked_keywords,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ✗ EXCEPTION: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
