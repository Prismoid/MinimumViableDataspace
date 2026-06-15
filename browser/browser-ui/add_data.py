import requests
import json
import base64
import hashlib
from datetime import datetime, timezone, timedelta
from ecdsa import SigningKey, NIST256p

PKR_URL = "http://localhost:7450"
CAT_URL = "http://localhost:7451"


def iso_now_plus(mins=60):
    return (
        datetime.now(timezone.utc) + timedelta(minutes=mins)
    ).isoformat().replace("+00:00", "Z")


def sign(sk: SigningKey, data: dict) -> str:
    msg = json.dumps(data, sort_keys=True).encode()
    sig = sk.sign(msg, hashfunc=hashlib.sha256)
    return base64.b64encode(sig).decode()


def show(title, res):
    print(f"\n=== {title} ===")
    print(res.status_code)
    print(res.text)


users = {}

for user_id in ["userA", "userB", "userC"]:
    sk = SigningKey.generate(curve=NIST256p)
    vk = sk.get_verifying_key()
    public_key = vk.to_pem().decode()
    users[user_id] = {
        "sk": sk,
        "public_key": public_key,
    }


# =====================================================
# reset
# =====================================================
show("PKR: delete all", requests.delete(f"{PKR_URL}/pkr/debug/delAllKeys"))
show("CAT: delete all", requests.delete(f"{CAT_URL}/fc/debug/delAll"))


# =====================================================
# add public keys
# =====================================================
for user_id, key_info in users.items():
    payload = {
        "user_id": user_id,
        "public_key": key_info["public_key"],
        "expire_time": iso_now_plus(),
    }

    res = requests.post(
        f"{PKR_URL}/pkr/add",
        json={**payload, "signature": sign(key_info["sk"], payload)},
    )

    show(f"PKR: add {user_id}", res)


# =====================================================
# add catalog entries
# =====================================================
catalog_entries = [
    {
        "resource_id": "resource-001",
        "user_id": "userA",
        "description": "sample climate dataset for PoC",
        "endpoint": "https://example.com/connector-a",
        "resource_path": "/resource/climate",
    },
    {
        "resource_id": "resource-002",
        "user_id": "userA",
        "description": "sample temperature sensor API",
        "endpoint": "https://example.com/connector-a",
        "resource_path": "/api/v1/sensors/temperature",
    },
    {
        "resource_id": "resource-003",
        "user_id": "userB",
        "description": "sample air conditioner metadata",
        "endpoint": "https://example.com/connector-b",
        "resource_path": "/api/v1/hvac/airconditioner/metadata",
    },
    {
        "resource_id": "resource-004",
        "user_id": "userB",
        "description": "sample factory energy management data",
        "endpoint": "https://example.com/connector-b",
        "resource_path": "/resource/fems/energy",
    },
    {
        "resource_id": "resource-005",
        "user_id": "userC",
        "description": "sample asset administration shell data",
        "endpoint": "https://example.com/connector-c",
        "resource_path": "/aas/submodels/001",
    },
]

for entry in catalog_entries:
    payload = {
        **entry,
        "expire_time": iso_now_plus(),
    }

    sk = users[entry["user_id"]]["sk"]

    res = requests.post(
        f"{CAT_URL}/fc/add",
        json={**payload, "signature": sign(sk, payload)},
    )

    show(f"CAT: add {entry['resource_id']}", res)


# =====================================================
# check
# =====================================================
show("CAT: get all", requests.get(f"{CAT_URL}/fc/get"))

for user_id in users.keys():
    show(f"PKR: get {user_id}", requests.get(f"{PKR_URL}/pkr/get/{user_id}"))
