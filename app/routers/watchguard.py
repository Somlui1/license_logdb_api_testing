from fastapi import APIRouter,Request,Query
from fastapi.responses import StreamingResponse
from app.service import watchguard_fn
from urllib.parse import urlencode
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