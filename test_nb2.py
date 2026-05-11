import os, requests, time

url = os.environ.get("NETBOX_URL")
token = os.environ.get("NETBOX_TOKEN")

t0 = time.time()
r = requests.get(
    f"{url}/api/dcim/devices/",
    headers={"Authorization": f"Token {token}", "Accept": "application/json"},
    params={"status": "active", "tenant_group": "k3g-solutions", "limit": 1000}
)
print("Time:", time.time() - t0, "Status:", r.status_code)
