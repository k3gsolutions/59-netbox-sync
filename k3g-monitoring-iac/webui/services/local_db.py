"""Local SQLite database for compliance inventory cache."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple


DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "local.db"


def init_db() -> None:
    """Create database and schema if it doesn't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT,
            group_name TEXT,
            snmp_community TEXT,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            tenant_id INTEGER REFERENCES tenants(id),
            platform TEXT,
            manufacturer TEXT,
            model TEXT,
            primary_ip TEXT,
            site TEXT,
            role TEXT,
            status TEXT,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_credentials (
            device_id INTEGER PRIMARY KEY REFERENCES devices(id),
            snmp_community TEXT,
            ssh_host TEXT,
            ssh_port INTEGER DEFAULT 22,
            username TEXT,
            password TEXT,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compliance_runs (
            id TEXT PRIMARY KEY,
            device_id INTEGER,
            mode TEXT NOT NULL,
            platform TEXT,
            contexts TEXT,
            status TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP,
            raw_file_path TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compliance_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT REFERENCES compliance_runs(id),
            context TEXT,
            severity TEXT,
            object TEXT,
            message TEXT,
            expected TEXT,
            found TEXT,
            recommendation TEXT
        )
    """)

    conn.commit()
    conn.close()


def get_conn() -> sqlite3.Connection:
    """Get database connection with row factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def upsert_tenant(id: int, name: str, slug: str, group_name: str, snmp_community: Optional[str] = None) -> None:
    """Upsert tenant record."""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO tenants (id, name, slug, group_name, snmp_community, synced_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (id, name, slug, group_name, snmp_community))

    conn.commit()
    conn.close()


def upsert_device(
    id: int,
    name: str,
    tenant_id: int,
    platform: Optional[str] = None,
    manufacturer: Optional[str] = None,
    model: Optional[str] = None,
    primary_ip: Optional[str] = None,
    site: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None
) -> None:
    """Upsert device record."""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO devices
        (id, name, tenant_id, platform, manufacturer, model, primary_ip, site, role, status, synced_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (id, name, tenant_id, platform, manufacturer, model, primary_ip, site, role, status))

    conn.commit()
    conn.close()


def upsert_credentials(
    device_id: int,
    snmp_community: Optional[str] = None,
    ssh_host: Optional[str] = None,
    ssh_port: int = 22,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> None:
    """Upsert device credentials record."""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO device_credentials
        (device_id, snmp_community, ssh_host, ssh_port, username, password, synced_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (device_id, snmp_community, ssh_host, ssh_port, username, password))

    conn.commit()
    conn.close()


def get_tenants() -> List[Dict]:
    """Get all tenants from local DB."""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tenants ORDER BY name")
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_tenant(tenant_id: int) -> Optional[Dict]:
    """Get single tenant by ID."""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tenants WHERE id = ?", (tenant_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_devices(tenant_id: Optional[int] = None) -> List[Dict]:
    """Get devices, optionally filtered by tenant."""
    conn = get_conn()
    cursor = conn.cursor()

    if tenant_id:
        cursor.execute("SELECT * FROM devices WHERE tenant_id = ? ORDER BY name", (tenant_id,))
    else:
        cursor.execute("SELECT * FROM devices ORDER BY name")

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_device(device_id: int) -> Optional[Dict]:
    """Get single device by ID."""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_credentials(device_id: int) -> Optional[Dict]:
    """Get device credentials by device ID."""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM device_credentials WHERE device_id = ?", (device_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def resolve_snmp_community(device_id: int) -> Optional[str]:
    """Resolve SNMP community: device > tenant > env fallback."""
    # Device-level override
    creds = get_credentials(device_id)
    if creds and creds.get("snmp_community"):
        return creds["snmp_community"]

    # Tenant-level
    device = get_device(device_id)
    if device and device.get("tenant_id"):
        tenant = get_tenant(device["tenant_id"])
        if tenant and tenant.get("snmp_community"):
            return tenant["snmp_community"]

    # Env fallback
    import os
    return os.getenv("SNMP_COMMUNITY", None)


def save_run(run_id: str, device_id: Optional[int], mode: str, platform: str, contexts: List[str], raw_file_path: Optional[str] = None) -> None:
    """Save compliance run record."""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO compliance_runs
        (id, device_id, mode, platform, contexts, status, raw_file_path)
        VALUES (?, ?, ?, ?, ?, 'done', ?)
    """, (run_id, device_id, mode, platform, json.dumps(contexts), raw_file_path))

    conn.commit()
    conn.close()


def save_findings(run_id: str, findings: List[Dict]) -> None:
    """Save compliance findings for a run."""
    conn = get_conn()
    cursor = conn.cursor()

    for finding in findings:
        cursor.execute("""
            INSERT INTO compliance_findings
            (run_id, context, severity, object, message, expected, found, recommendation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            finding.get("context"),
            finding.get("severity"),
            finding.get("object"),
            finding.get("message"),
            finding.get("expected"),
            finding.get("found"),
            finding.get("recommendation")
        ))

    conn.commit()
    conn.close()


def get_run_findings(run_id: str) -> List[Dict]:
    """Get all findings for a compliance run."""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM compliance_findings WHERE run_id = ? ORDER BY severity DESC, context", (run_id,))
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def clear_all() -> None:
    """DANGER: Clear entire database. Use for testing only."""
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_db()
