import os, requests, time

url = os.environ.get("NETBOX_URL")
token = os.environ.get("NETBOX_TOKEN")

t0 = time.time()
r = requests.get(
    f"{url}/api/dcim/devices/",
    headers={"Authorization": f"Token {token}", "Accept": "application/json"},
    params={"status": "active", "tenant_group": "k3g-solutions"}
)
print("Query active + tenant_group time:", time.time() - t0, "Count:", r.json().get("count"))

t0 = time.time()
r = requests.get(
    f"{url}/api/dcim/devices/",
    headers={"Authorization": f"Token {token}", "Accept": "application/json"},
    params={"status": "active", "tenant_group": "k3g-solutions", "cf_compliance": "true"}
)
print("Query active + tenant_group + cf_compliance time:", time.time() - t0, "Count:", r.json().get("count"))
