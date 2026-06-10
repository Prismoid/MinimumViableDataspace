import requests
import json
import base64
import hashlib
from datetime import datetime, timezone, timedelta
from ecdsa import SigningKey, NIST256p
import time

# =====================================================
# config
# =====================================================
CONNECTOR_URL = "http://localhost:7550"

USER_A = "userA"
USER_B = "userB"
DATA_ID = "data-001"

# =====================================================
# utils
# =====================================================
def iso_now_plus(mins=5, hours=0):
    return (
        datetime.now(timezone.utc) + timedelta(minutes=mins, hours=hours)
    ).isoformat().replace("+00:00", "Z")

def sign(sk: SigningKey, data: dict) -> str:
    msg = json.dumps(data, sort_keys=True).encode()
    sig = sk.sign(msg, hashfunc=hashlib.sha256)
    return base64.b64encode(sig).decode()

def show(label, res: requests.Response):
    print(f"{label} -> {res.status_code}")
    try:
        print(json.dumps(res.json(), indent=2))
    except Exception:
        print(res.text)
    print("-" * 60)

# =====================================================
# keys (PoC)
# =====================================================
sk_a = SigningKey.generate(curve=NIST256p)
pub_a = sk_a.get_verifying_key().to_pem().decode()

# =====================================================
# 0. DEBUG delete_all
# =====================================================
show(
    "PKR delete_all",
    requests.delete(f"{CONNECTOR_URL}/pkr/debug/delAllKeys"),
)

show(
    "FC delete_all",
    requests.delete(f"{CONNECTOR_URL}/fc/debug/delAll"),
)

show(
    "AuthZ delete_all",
    requests.delete(f"{CONNECTOR_URL}/authz/debug/delete_all"),
)

# =====================================================
# 1. PKR: register userA
# =====================================================
payload = {
    "user_id": USER_A,
    "public_key": pub_a,
    "expire_time": iso_now_plus(),
}
payload["signature"] = sign(sk_a, payload)

show(
    "PKR add userA",
    requests.post(f"{CONNECTOR_URL}/pkr/add", json=payload),
)

# =====================================================
# 2. FC: add data-001 (owner=userA)
# =====================================================
payload = {
    "data_id": DATA_ID,
    "user_id": USER_A,
    "description": "minimal PoC data",
    "endpoint": "http://host.docker.internal:7550",
    "local_path": "http://host.docker.internal:7552/hello_world.txt", 
    "expire_time": iso_now_plus(),
}
payload["signature"] = sign(sk_a, payload)

show(
    "FC add data-001",
    requests.post(f"{CONNECTOR_URL}/fc/add", json=payload),
)

time.sleep(0.5)

# =====================================================
# 3. AuthZ: grant userB (signed by userA)
# =====================================================
payload = {
    "data_id": DATA_ID,
    "access_grantee_id": USER_B,
    "expired_at": iso_now_plus(hours=1),
    "expire_time": iso_now_plus(),
}
payload["signature"] = sign(sk_a, payload)

show(
    "AuthZ add (grant userB)",
    requests.post(f"{CONNECTOR_URL}/authz/add", json=payload),
)

# =====================================================
# 4. AuthZ: get (確認)
# =====================================================
r = requests.get(
    f"{CONNECTOR_URL}/authz/get",
    params={
        "data_id": DATA_ID,
        "access_grantee_id": USER_B,
    },
)

show("AuthZ get", r)

# =====================================================
# 5. PKR: register userB
# =====================================================
sk_b = SigningKey.generate(curve=NIST256p)
pub_b = sk_b.get_verifying_key().to_pem().decode()

payload = {
    "user_id": USER_B,
    "public_key": pub_b,
    "expire_time": iso_now_plus(),
}
payload["signature"] = sign(sk_b, payload)

show(
    "PKR add userB",
    requests.post(f"{CONNECTOR_URL}/pkr/add", json=payload),
)

# =====================================================
# 6. get_data (signed by userB)
# =====================================================
payload = {
    "data_id": DATA_ID,
    "user_id": USER_B,
    "expire_time": iso_now_plus(),
}
payload["signature"] = sign(sk_b, payload)

r = requests.post(
    f"{CONNECTOR_URL}/get_data",
    json=payload,
    stream=True,   # ★重要
)

print("get_data ->", r.status_code)
if r.status_code != 200:
    print(r.text)
    raise SystemExit(1)
