import asyncio
import uuid
from fastapi import APIRouter,Request,Query
from fastapi.responses import StreamingResponse
from app.service import watchguard_fn
from urllib.parse import urlencode
from app.db import watchguarddb
from app.schema import watchguard_validate
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


@router.post("/table/data/",description = "Dynamic table data insertion")
async def get_payload_dynamic(payload: watchguard_validate.LicenseInput):
    # ดึง Pydantic model และ ORM class
    ver = getattr(watchguard_validate, payload.table, None)   # Pydantic model
    orm_class = getattr(watchguarddb, payload.table, None)  # ORM class
    if not ver:
        return {"error": f"Model '{payload.table}' not found"}
    if not orm_class:
        return {"error": f"ORM '{payload.table}' not found"}
    try:
        share_uuid = uuid.uuid4()
        # Validate payload
        validated = [ver(**item) for item in payload.data]
        # แปลงเป็น list ของ dict พร้อม batch_id
        dict_objects = []
        for item in validated:
            d = item.dict()
            d['batch_id'] = share_uuid
            dict_objects.append(d)

        await asyncio.to_thread(orm_class().save, dict_objects)
        # บันทึก raw logs
        #RawLogs = watchguarddb.raw_logs_table(schema_name=payload.table)
        #log_entry = RawLogs.from_pydantic(payload.data, batch_id=share_uuid)
        #with Session_license_logsdb() as session:
        #    session.add(log_entry)
        #    session.commit()
    except Exception as e:
        return {"error": str(e)}

    return {
        "ip": payload.ip,
        "table": payload.table,
        "parsed_data": validated
    }