import os
import pynetbox


def get_netbox():
    url = os.getenv("NETBOX_URL")
    token = os.getenv("NETBOX_TOKEN") or os.getenv("API_TOKEN")
    verify_ssl = os.getenv("NETBOX_VERIFY_SSL", "true").lower() == "true"

    nb = pynetbox.api(url, token=token)
    nb.http_session.verify = verify_ssl
    return nb