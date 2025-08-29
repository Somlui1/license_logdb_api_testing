from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, List
from app import valid # Import models from valid.py
from app import db
from sqlalchemy import Column, Integer, String, Date, Time, Numeric, DateTime, create_engine, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from faker import Faker
from sqlalchemy import create_engine       # สร้าง connection engine
from sqlalchemy.orm import sessionmaker    # สร้าง session สำหรับ insert/query

#ORM setup
engine_url = "postgresql://itsupport:aapico@10.10.3.215:5432/license_logsdb"
engine = create_engine(engine_url)
Base = declarative_base()
Base.metadata.create_all(engine)

#FastAPI app
app = FastAPI()
class LicenseInput(BaseModel):
    ip: int
    product: str   # ใช้เป็น key เลือก model
    data: List[Any]

@app.post("/testing/")
async def get_payload_dynamic(payload: LicenseInput):
    # ✅ ดึง class โดยตรงจากชื่อ (เช่น "nx")
    cls = getattr(valid, payload.product, None)
    #cls = None
    if not cls:
        return {"error": f"Model '{payload.product}' not found"}

    try:
        parsed_data = [cls(**item) for item in payload.data]
    
    except Exception as e:
        return {"error": str(e)}
    return {
        "ip": payload.ip,
        "product": payload.product,
        "parsed_data": [d.dict() for d in parsed_data]
    }