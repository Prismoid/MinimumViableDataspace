from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
import httpx
from pydantic import BaseModel
from datetime import datetime, timezone
import json, base64, hashlib, requests, time

from ecdsa import VerifyingKey

app = FastAPI()

# =====================================================
# Request models
# =====================================================
class GetDataReq(BaseModel):
    data_id: str
    user_id: str
    expire_time: str
    signature: str

class RetDataReq(BaseModel):
    data_id: str
    user_id: str
    expire_time: str
    signature: str # data_id + user_id + expire_time

# =====================================================
# Helpers
# =====================================================
FC    = "http://host.docker.internal:7451"
PKR   = "http://host.docker.internal:7450"
AUTHZ = "http://host.docker.internal:7551"
FILE_SERVER = "http://host.docker.internal:7552"

def validate_expire(iso_time: str):
    t = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
    if t < datetime.now(timezone.utc):
        raise HTTPException(400, "expired")

def get_public_key(user_id: str) -> str:
    r = requests.get(f"{PKR}/pkr/get/{user_id}")
    if r.status_code != 200:
        raise HTTPException(400, "public key not found")
    return r.json()["public_key"]

def get_owner_user_id_from_fc(data_id: str) -> str:
    r = requests.get(f"{FC}/fc/get", params={"data_id": data_id})
    if r.status_code != 200:
        raise HTTPException(400, "fc access failed")
    entries = r.json()
    if not entries:
        raise HTTPException(404, "data_id not found")
    return entries[0]["user_id"]

def get_location_from_fc(data_id: str) -> str:
    r = requests.get(f"{FC}/fc/get", params={"data_id": data_id})
    if r.status_code != 200:
        raise HTTPException(400, "fc access failed")
    entries = r.json()
    if not entries:
        raise HTTPException(404, "data_id not found")
    return entries[0]["endpoint"], entries[0]["local_path"]

def check_authz(data_id: str, user_id: str):
    r = requests.get(
        f"{AUTHZ}/authz/get",
        params={"data_id": data_id, "access_grantee_id": user_id},
    )
    if r.status_code != 200:
        raise HTTPException(403, "authz denied")
    
    expired_at = datetime.fromisoformat(r.json()["expired_at"])
    expired_at = expired_at.replace(tzinfo=timezone.utc) 
    if expired_at <= datetime.now(timezone.utc):
        raise HTTPException(403, "permission expired")

def verify_signature(public_key_pem: str, data: dict, signature_b64: str) -> bool:
    try:
        vk = VerifyingKey.from_pem(public_key_pem.encode())
        msg = json.dumps(data, sort_keys=True).encode()
        sig = base64.b64decode(signature_b64)
        return vk.verify(sig, msg, hashfunc=hashlib.sha256)
    except Exception:
        return False

# リレー用関数
async def relay(req: Request, base: str, path: str):
    url = f"{base}{path}"
    if req.url.query:
        url += f"?{req.url.query}"

    async with httpx.AsyncClient() as c:
        r = await c.request(
            req.method,
            url,
            headers={k: v for k, v in req.headers.items()
                     if k.lower() not in ("host", "content-length")},
            content=await req.body(),
        )

    return Response(r.content, r.status_code, media_type=r.headers.get("content-type"))

# =====================================================
# API
# =====================================================
# FC
@app.post("/fc/add")
async def fc_add(request: Request):
    return await relay(request, FC, "/fc/add")

@app.post("/fc/upd")
async def fc_upd(request: Request):
    return await relay(request, FC, "/fc/upd")

@app.post("/fc/del")
async def fc_del(request: Request):
    return await relay(request, FC, "/fc/del")

@app.get("/fc/get")
async def fc_get(request: Request):
    return await relay(request, FC, "/fc/get")

@app.get("/fc/debug/showAll")
async def fc_debug_show_all(request: Request):
    return await relay(request, FC, "/fc/debug/showAll")

@app.delete("/fc/debug/delAll")
async def fc_debug_delete_all(request: Request):
    return await relay(request, FC, "/fc/debug/delAll")


# PKR
@app.post("/pkr/add")
async def pkr_add(request: Request):
    return await relay(request, PKR, "/pkr/add")

@app.post("/pkr/upd")
async def pkr_upd(request: Request):
    return await relay(request, PKR, "/pkr/upd")

@app.post("/pkr/del")
async def pkr_del(request: Request):
    return await relay(request, PKR, "/pkr/del")

@app.get("/pkr/get/{user_id}")
async def pkr_get(user_id: str, request: Request):
    return await relay(request, PKR, f"/pkr/get/{user_id}")

@app.get("/pkr/debug/showAllKeys")
async def pkr_debug_show_all(request: Request):
    return await relay(request, PKR, "/pkr/debug/showAllKeys")

@app.delete("/pkr/debug/delAllKeys")
async def pkr_debug_delete_all(request: Request):
    return await relay(request, PKR, "/pkr/debug/delAllKeys")


# AuthZ
@app.post("/authz/add")
async def authz_add(request: Request):
    return await relay(request, AUTHZ, "/authz/add")

@app.post("/authz/upd")
async def authz_upd(request: Request):
    return await relay(request, AUTHZ, "/authz/upd")

@app.post("/authz/del")
async def authz_del(request: Request):
    return await relay(request, AUTHZ, "/authz/del")

@app.get("/authz/get")
async def authz_get(request: Request):
    return await relay(request, AUTHZ, "/authz/get")

@app.get("/authz/debug/show_all")
async def authz_debug_show_all(request: Request):
    return await relay(request, AUTHZ, "/authz/debug/show_all")

@app.delete("/authz/debug/delete_all")
async def authz_debug_delete_all(request: Request):
    return await relay(request, AUTHZ, "/authz/debug/delete_all")

# =====================================================
# Connector Original API
# =====================================================
@app.post("/get_data")
def get_data(req: GetDataReq):
    endpoint, local_path = get_location_from_fc(req.data_id)

    ret_req = {
        "data_id": req.data_id,
        "user_id": req.user_id,
        "expire_time": req.expire_time,
        "signature": req.signature,
    }

    r = requests.post(f"{endpoint}/ret_data", json=ret_req, stream=True)
    if r.status_code != 200:
        raise HTTPException(400, "ret_data failed")

    filename = local_path.rsplit("/", 1)[-1]
    with open(f"/rcv_storage/{filename}", "wb") as f:
        for chunk in r.iter_content(8192):
            if chunk:
                f.write(chunk)

    return {"status": "ok", "saved": filename}

@app.post("/ret_data")
def ret_data(req: RetDataReq):
    pubkey = get_public_key(req.user_id)
    signed_data = {
        "data_id": req.data_id,
        "user_id": req.user_id,
        "expire_time": req.expire_time,
    }
    if not verify_signature(pubkey, signed_data, req.signature):
        raise HTTPException(400, "invalid signature")

    check_authz(req.data_id, req.user_id)

    # local_pathの取得
    endpoint, local_path = get_location_from_fc(req.data_id)
    r = requests.get(local_path, stream=True)
    if r.status_code != 200:
        raise HTTPException(404, "file fetch failed")

    filename = local_path.rsplit("/", 1)[-1]

    return StreamingResponse(
        r.iter_content(8192),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


