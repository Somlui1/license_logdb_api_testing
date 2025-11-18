import io
from typing import List, Dict, Any
import base64
import requests
from urllib.parse import urlencode
from collections import defaultdict
import csv
from fastapi.responses import StreamingResponse
TENANTS = {
    "ah": {
        "Credential": "583db905e5af13cd_r_id:it@minAPI1WGant!",
        "APIKey": "FfSghSoNzPlloALCK9LN5E46rzGnAYqxJ+mgirtf",
        "Account": "WGC-3-981e96282dcc4ad0856c"
    },
    "as": {
        "Credential": "8f6543f42f463fc6_r_id:5QG+M=H+)3iL)Fw",
        "APIKey": "yujbaVOGmOi5rzxU2wBwcCJMLrkKyxU7Fbw8rQgj",
        "Account": "WGC-3-50b8aa46e31d448698c7"
    },
    "ar": {
        "Credential": "7be27fa3e7cc352a_r_id:^^K7Uc~7PYruSek",
        "APIKey": "66eMRiegSh7EhWQh6C9S5hAnQ75OScy6T9kx+VKo",
        "Account": "WGC-3-048294f7f1ed497981c8"
    }
}

def fetch_devices(tenant_name: str, segment: str, retrive: str, querystring: str | None = None):
    
    results = defaultdict(list)  # สำหรับเก็บข้อมูลรวมตาม key
    errors = {}
    
    # ---------------------------
    # 1) เตรียม TENANTS_KEYS
    # ---------------------------
    if tenant_name.lower() == 'all':
        TENANTS_KEYS = list(TENANTS.keys())
    elif tenant_name not in TENANTS:
        return {}, {tenant_name: "Tenant does not exist."}
    else:
        TENANTS_KEYS = [tenant_name]

    # ---------------------------
    # 2) Loop ทุก tenant
    # ---------------------------
    for key in TENANTS_KEYS:
        tenant = TENANTS[key]

        try:
            # --------------------- GET TOKEN ---------------------
            cred_b64 = base64.b64encode(tenant["Credential"].encode()).decode()
            token_resp = requests.post(
                "https://api.jpn.cloud.watchguard.com/oauth/token",
                headers={
                    "accept": "application/json",
                    "Authorization": f"Basic {cred_b64}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={"grant_type": "client_credentials", "scope": "api-access"}
            )
            token_resp.raise_for_status()
            token = token_resp.json().get("access_token")
            if not token:
                raise Exception("Token is null")

            # --------------------- GET DEVICES ---------------------
            url = f"https://api.jpn.cloud.watchguard.com/rest/{segment}/management/api/v1/accounts/{tenant['Account']}/{retrive}?{querystring}"
            dev_resp = requests.get(
                url,
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/json",
                    "WatchGuard-API-Key": tenant["APIKey"],
                    "Authorization": f"Bearer {token}"
                },
                timeout=120
            )

            data = dev_resp.json()

            # --------------------- MERGE DATA ---------------------
            for k, v in data.items():
                if isinstance(v, list):
                    results[k].extend(v)   # ถ้าเป็น list → extend
                else:
                    results[k].append(v)   # ถ้าเป็นค่าเดี่ยว → append

        except Exception as e:
            errors[key] = str(e)

    # ---------------------------
    # 3) Return
    # ---------------------------
    return dict(results), errors


def merge_objects(
    object1: List[Dict[str, Any]],
    object2: List[Dict[str, Any]],
    key: str = "device_id"
) -> List[Dict[str, Any]]:
    
    # 1) Convert object1 to a fast lookup dict
    index = {obj[key]: obj for obj in object1 if key in obj}

    merged = []

    # 2) Merge object2 entries
    for obj2 in object2:
        obj_key = obj2.get(key)

        if obj_key in index:  # Found matching in object1 → merge
            merged_obj = {**index[obj_key], **obj2}
            merged.append(merged_obj)
        else:  # Not found → use object2 only
            merged.append(obj2)

    return merged


#test = {
#        "tenant_name": "all",
#        "segment": "endpoint-security",
#        "retrive": "devices",
#        "querystring": urlencode({
#            "$top": 1,
#            "$count": "true"
#        })
#}
#
#object1 = fetch_devices(tenant_name ='ah',segment ="endpoint-security", retrive = "devices")
#object2 = fetch_devices(tenant_name ='ah',segment ="endpoint-security", retrive = "devicesprotectionstatus")
#
#merged = merge_objects(object1[0]['data'], object2[0]['data'])


def export_csv(data: List[Dict[str, Any]], filename: str = "output.csv"):
    if not data:
        raise ValueError("No data to export.")

    # Collect all unique CSV headers
    headers = set()
    for row in data:
        headers.update(row.keys())
    headers = list(headers)

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

    print(f"CSV exported to {filename}")


def export_csv_fastapi(data: List[Dict[str, Any]], filename: str = "output.csv") -> StreamingResponse:
    if not data:
        raise ValueError("No data to export.")

    # สร้าง CSV ใน memory
    output = io.StringIO()
    
    # รวมทุก key เป็น header
    headers = set()
    for row in data:
        headers.update(row.keys())
    headers = list(headers)

    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(data)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )