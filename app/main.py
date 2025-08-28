from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import Any
from sqlalchemy import create_engine, text
from fastapi.encoders import jsonable_encoder
from datetime import date, time
from decimal import Decimal
from typing import Optional
app = FastAPI()

class NXSessionCreate(BaseModel):
    start_date: Optional[date]
    start_time: Optional[time]
    end_date: Optional[date]
    end_time: Optional[time]
    duration_minutes: Optional[Decimal]
    hostname: Optional[str]
    module: Optional[str]
    username: Optional[str]

# Dynamic payload handler
@app.post("/testing/{parameter}")
async def get_payload_dynamic(parameter: str, payload: Any = Body(...)):
    # แปลง payload เป็น dict
    json_payload = jsonable_encoder(payload)

    # ดึงค่าจาก dict ตาม parameter
    value = json_payload.get(parameter, None)
    
    return {"message": "Session received", "field": parameter, "value": value}
