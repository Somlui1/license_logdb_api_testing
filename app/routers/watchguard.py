import asyncio
from datetime import datetime, timedelta
from fastapi import APIRouter,Request,Query,HTTPException
from app.service import watchguard_fn
from urllib.parse import urlencode
from app.db import watchguarddb
from app.schema import watchguard_validate
import aiohttp
from typing import List, Dict, Any
import base64

session = watchguarddb.Session()

router = APIRouter(
    prefix="/watchguard",  # ตั้ง prefix ที่นี่เลย
    tags=["watchguard"]
)

@router.get("/{tenant}/{segment}/{retrive}",description = "Include query parameters for filtering data")
async def watchguard_Endpoint_Security(tenant :str,segment: str,retrive : str,request : Request,
                                    Query_parameter : str | None = Query(default=None, description="Optional search query")
                                       ):  
    if Query_parameter is None:
         query_string = urlencode(request.query_params)
    else:
         query_string = Query_parameter
    
    devices, error = watchguard_fn.fetch_devices(tenant_name=tenant,segment=segment, retrive=retrive,querystring =query_string)
    if error:
        return {"error": error}
    return {"devices": devices}

@router.get("/export/devices&devicesprotectionstatus/{tenant}/",description = "Include query parameters for filtering data")
async def devices_and_devicesprotectionstatus(tenant :str,csv :bool = Query(default=False, description="Export to CSV file")):
   
    object1 = watchguard_fn.fetch_devices(tenant_name ='ah',segment ="endpoint-security", retrive = "devices")
    object2 = watchguard_fn.fetch_devices(tenant_name ='ah',segment ="endpoint-security", retrive = "devicesprotectionstatus")
    merged = watchguard_fn.merge_objects(object1[0]['data'], object2[0]['data'])
    if csv:
        return watchguard_fn.export_csv_fastapi(merged, filename="devices_merged.csv")
    
    return {"data": merged}

@router.post("/patch", description="Dynamic table data insertion")
async def get_payload_dynamic(payload: watchguard_validate.Input):
    # --- Resolve models ---
    ver = getattr(watchguard_validate, payload.table, None)
    orm_class = getattr(watchguarddb, payload.table, None)
    if not ver:
        return {
            "success": False,
            "error": f"Pydantic model '{payload.table}' not found"
        }
    if not orm_class:
        return {
            "success": False,
            "error": f"ORM class '{payload.table}' not found"
        }
    try:
        # --- Validate payload ---
        validated = [ver(**item) for item in payload.data]
        dict_objects = [item.dict() for item in validated]
        # --- Call ORM.save() and get result ---
        result = await asyncio.to_thread(
            orm_class().save,
            dict_objects
        )
        # --- Ensure consistent response ---
        return {
            "success": result.get("success", False),
            "table": payload.table,
            "received": len(payload.data),
            "inserted": result.get("inserted", 0),
            "skipped": result.get("skipped", 0),
            "error": result.get("error")
        }
    except Exception as e:
        return {
        "success": False,
        "table": payload.table,
        "error": str(e),
        "details": getattr(e, "errors", lambda: None)()
    }

@router.post(
    "/truncate/{schema_name}/{table_name}",
    description="Dynamic table truncate"
)
async def truncate(schema_name: str, table_name: str):
    try:
        watchguarddb.tuncate_table(
            table_name=table_name,
            schema_name=schema_name
        )
        return {"status": "truncate called"}
    except Exception as e:
        return {"error": str(e)}

# =========================
# 🚀 Router endpoint
# =========================

# เก็บเวลาที่เรียก API ล่าสุด
last_called: datetime | None = None
lock = asyncio.Lock()  # เพื่อให้ thread-safe ใน async
last_total_patches: int = 0
@router.get("/patches")
async def get_watchguard_patches(tenant_id: str = "ah"):
    insert_table = 'AvailablePatch'
    ver = getattr(watchguard_validate, insert_table, None)
    orm_class = getattr(watchguarddb, insert_table, None)
    global last_called, last_total_patches
    async with lock:
        now = datetime.utcnow()
        if last_called and now - last_called < timedelta(minutes=5):
            # ยังไม่ครบ 5 นาที
            remaining = timedelta(minutes=5) - (now - last_called)
            return{
                "table": orm_class.__tablename__ ,
                "detail": f"Too soon! Please wait {int(remaining.total_seconds())} seconds.",
                "cached_total_patches": last_total_patches
            }
            raise HTTPException(
                status_code=429, 
                detail=f"Too soon! Please wait {int(remaining.total_seconds())} seconds."
            )
        # อัปเดตเวลาเรียกครั้งล่าสุด
        last_called = now
    print(f"DEBUG: Request received for tenant_id: {tenant_id}") # เพิ่มบรรทัดนี้

    if tenant_id not in watchguard_fn.TENANTS:
        raise HTTPException(status_code=404, detail="Tenant not found")
    t_start = watchguard_fn.now()
    tenant = watchguard_fn.TENANTS[tenant_id]
    print()
    segment = "endpoint-security"
    retrieve = "patchavailability"
    top = 900
    max_concurrent = 4
    sem = asyncio.Semaphore(max_concurrent)
    patches: List[dict] = []
    timeout = aiohttp.ClientTimeout(total=600)
    connector = aiohttp.TCPConnector(limit=50, limit_per_host=20)
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        try:
            token = await watchguard_fn.get_token(session, tenant["Credential"])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Token error: {e}")
            
        # First page
        first = await watchguard_fn.fetch_devices_async(
            session, tenant, token, segment, retrieve, f"$top={top}&$skip=0&$count=true", sem
        )
        total = first["total_items"]
        patches.extend(first["data"])
        print(f"Fetched first page: {len(first['data'])}/{total}")
    
        skips = list(range(top, total, top))
        tasks = [
            watchguard_fn.fetch_devices_async(session, tenant, token, segment, retrieve, f"$top={top}&$skip={skip}", sem)
            for skip in skips
        ]
        completed = 0
        for coro in asyncio.as_completed(tasks):
            result = await coro
            patches.extend(result.get("data", []))
            completed += 1
            print(f"Progress {completed}/{len(tasks)} → {len(patches)}/{total}")

    print("\n==========================")
    print(f"⏱ Total time : {watchguard_fn.now() - t_start:.2f}s")
    print(f"✔ Total patches: {len(patches)}")
    last_total_patches = len(patches)
    #truncate table & insert


    # --- เริ่มต้นส่วนการจัดการ Database ---
    try:
        validated = [ver(**item) for item in patches]
        dict_objects = [item.dict() for item in validated]
        # เตรียมตาราง
        orm_class.setup_table()
        orm_class.truncate()

        # ฟังก์ชันที่จะรันใน Thread แยก
        def process_and_save():
            # สร้าง instance เปล่าๆ
            instance = orm_class()
            # เรียก save_bulk_simple ที่แก้ใหม่ (ส่ง list[dict] เข้าไปได้เลย)
            return instance.save(dict_objects)

        # สั่งรัน (await เพื่อรอผลลัพธ์)
        print("DEBUG: Sending data to DB thread...")
        result = await asyncio.to_thread(process_and_save)

        return {
            "success": result.get("success", False),
            "table": orm_class.__tablename__ ,
            "received": len(dict_objects),
            "inserted": result.get("inserted", 0),
            "error": result.get("error")
        }

    except Exception as e:
        print(f"❌ API Error: {e}")
        return {
            "success": False,
            "error": str(e)
        }