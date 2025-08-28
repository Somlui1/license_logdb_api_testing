from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, List

app = FastAPI()

class LicenseInput(BaseModel):
    ip: int
    hostname: str   # ใช้เป็น key เลือก model
    data: List[Any]

class nx(BaseModel):
    hostname: str
    module: str

@app.post("/testing/")
async def get_payload_dynamic(payload: LicenseInput):
    # ✅ ดึง class โดยตรงจากชื่อ (เช่น "nx")
    cls = globals().get(payload.hostname)
    if not cls:
        return {"error": f"Model '{payload.hostname}' not found"}

    try:
        parsed_data = [cls(**item) for item in payload.data]
    except Exception as e:
        return {"error": str(e)}

    return {
        "ip": payload.ip,
        "hostname": payload.hostname,
        "parsed_data": [d.dict() for d in parsed_data]
    }
