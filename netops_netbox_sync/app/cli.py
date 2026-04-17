import os
from dotenv import load_dotenv

from app.drivers.huawei_netmiko import HuaweiNetmikoDriver
from app.workflow.sync_device import run_collection, ask_confirmation
from app.netbox.client import get_netbox
from app.netbox.sync import sync_to_netbox
from app.netbox.bgp_sync import sync_bgp_plugin


def main():
    load_dotenv()

    driver = HuaweiNetmikoDriver(
        host=os.getenv("DEVICE_HOST"),
        username=os.getenv("DEVICE_USERNAME"),
        password=os.getenv("DEVICE_PASSWORD"),
        port=int(os.getenv("DEVICE_PORT", "22")),
    )

    driver.open()
    try:
        _, inventory, plan = run_collection(driver)
    finally:
        driver.close()

    # Sumário de peers por address family
    af_counts: dict[str, int] = {}
    for s in inventory.bgp_sessions:
        key = s.address_family or "ipv4"
        if s.vrf:
            key = f"{key}:{s.vrf}"
        af_counts[key] = af_counts.get(key, 0) + 1
    if af_counts:
        print("\nPeers BGP coletados por address-family:")
        for af, cnt in sorted(af_counts.items()):
            print(f"  {af:<20} {cnt} peers")

    confirmed = ask_confirmation(plan)
    if not confirmed:
        print("Inserção cancelada. Apenas coleta e parsing executados.")
        return

    nb = get_netbox()
    base_url = os.getenv("NETBOX_URL", "").rstrip("/")
    token = os.getenv("NETBOX_TOKEN", "")

    device_id = int(input("Informe o device_id do NetBox para associar as interfaces: ").strip())

    # ── Sync DCIM/IPAM (interfaces, IPs, VRFs...) ───────────────────────────
    print("\n[DCIM/IPAM] Sincronizando interfaces, IPs e VRFs...")
    sync_to_netbox(nb, device_id, inventory)

    # ── Sync BGP plugin ──────────────────────────────────────────────────────
    print("\n[BGP Plugin] Sincronizando sessões BGP, políticas e filtros...")
    changelog = sync_bgp_plugin(
        base_url=base_url,
        token=token,
        device_id=device_id,
        inventory=inventory,
        verify_ssl=False,
        verbose=True,
    )
    print(changelog.summary())

    print("Sincronização concluída.")


if __name__ == "__main__":
    main()