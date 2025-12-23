import asyncio
from fastapi import APIRouter, FastAPI,Request,Query,HTTPException
from urllib.parse import urlencode
import aiohttp
from typing import List, Dict, Any
import base64
app = FastAPI()
TENANTS = {
    "ah": {
        "credential": "583db905e5af13cd_r_id:it@minAPI1WGant!",
        "api_key": "FfSghSoNzPlloALCK9LN5E46rzGnAYqxJ+mgirtf",
        "account": "WGC-3-981e96282dcc4ad0856c",
    }
}
BASE_URL = "https://api.jpn.cloud.watchguard.com"
TOKEN_URL = f"{BASE_URL}/oauth/token"

# =========================
# Timer helper
# =========================
def now():
    import time
    return time.perf_counter()

# =========================
# 🔑 Token (once)
# =========================
async def get_token(session: aiohttp.ClientSession, credential: str) -> str:
    cred_b64 = base64.b64encode(credential.encode()).decode()
    async with session.post(
        TOKEN_URL,
        headers={
            "Authorization": f"Basic {cred_b64}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials", "scope": "api-access"},
        timeout=60,
    ) as resp:
        resp.raise_for_status()
        return (await resp.json())["access_token"]

# =========================
# 🌐 Fetch with retry
# =========================
async def fetch_devices(
    session: aiohttp.ClientSession,
    tenant: dict,
    token: str,
    segment: str,
    retrieve: str,
    query: str,
    sem: asyncio.Semaphore,
    retries: int = 2,
) -> Dict[str, Any]:
    url = f"{BASE_URL}/rest/{segment}/management/api/v1/accounts/{tenant['account']}/{retrieve}?{query}"
    headers = {
        "WatchGuard-API-Key": tenant["api_key"],
        "Authorization": f"Bearer {token}",
    }

    async with sem:
        for attempt in range(1, retries + 2):
            try:
                async with session.get(url, headers=headers) as resp:
                    resp.raise_for_status()
                    return await resp.json()
            except asyncio.TimeoutError:
                if attempt > retries:
                    raise
                print(f"⚠️ timeout retry {attempt} → {query}")

# =========================
# 🚀 Router endpoint
# =========================
@app.get("/patches")
async def get_watchguard_patches(tenant_id: str = "ah"):
    if tenant_id not in TENANTS:
        raise HTTPException(status_code=404, detail="Tenant not found")
    t_start = now()
    tenant = TENANTS[tenant_id]
    segment = "endpoint-security"
    retrieve = "patchavailability"
    top = 900
    max_concurrent = 6
    sem = asyncio.Semaphore(max_concurrent)
    patches: List[dict] = []

    timeout = aiohttp.ClientTimeout(total=600)
    connector = aiohttp.TCPConnector(limit=50, limit_per_host=20)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        try:
            token = await get_token(session, tenant["credential"])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Token error: {e}")

        # First page
        first = await fetch_devices(
            session, tenant, token, segment, retrieve, f"$top={top}&$skip=0&$count=true", sem
        )
        total = first["total_items"]
        patches.extend(first["data"])
        print(f"Fetched first page: {len(first['data'])}/{total}")


        skips = list(range(top, total, top))
        tasks = [
            fetch_devices(session, tenant, token, segment, retrieve, f"$top={top}&$skip={skip}", sem)
            for skip in skips
        ]
        completed = 0
        for coro in asyncio.as_completed(tasks):
            result = await coro
            patches.extend(result.get("data", []))
            completed += 1
            print(f"Progress {completed}/{len(tasks)} → {len(patches)}/{total}")

    print("\n==========================")
    print(f"⏱ Total time : {now() - t_start:.2f}s")
    print(f"✔ Total patches: {len(patches)}")

    return {
        "total_items": total,
        "fetched_items": len(patches),
        "patches": patches,
        "elapsed_seconds": round(now() - t_start, 2)
    }