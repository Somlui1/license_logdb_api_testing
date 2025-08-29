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

#ORM database setup
engine_url = "postgresql://itsupport:aapico@10.10.3.215:5432/license_logsdb"
db.greet(engine_url)
engine = create_engine(engine_url)
Base = declarative_base()
Base.metadata.create_all(engine)

#insert data to database
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#FastAPI app
app = FastAPI()
class LicenseInput(BaseModel):
    ip: int
    product: str   # ใช้เป็น key เลือก model
    data: List[Any]

def chunked(iterable, size):
      for i in range(0, len(iterable), size):
        yield iterable[i:i+size]

@app.post("/testing/")
async def get_payload_dynamic(payload: LicenseInput):
    # ดึง Pydantic model และ ORM class
    ver = getattr(valid, payload.product, None)   # Pydantic model
    orm_class = getattr(db, payload.product, None)  # ORM class
    if not ver or not orm_class:
        return {"error": f"Model '{payload.product}' not found"}
    if not orm_class:
        return {"error": f"ORM '{payload.product}' not found"}
    try:
        # 1) validate ข้อมูลด้วย Pydantic
        validated = [ver(**item) for item in payload.data]

        # 2) แปลงเป็น ORM objects
        orm_objects = [orm_class(**item.dict()) for item in validated]

        # 3) insert batch 100 record
        for batch in chunked(orm_objects, 200):
            with Session() as session:
                session.add_all(batch)   # add ORM objects
                session.commit()         # commit ทีละ batch
    except Exception as e:
        return {"error": str(e)}

    return {
        "ip": payload.ip,
        "product": payload.product,
        "parsed_data": [d.dict() for d in validated]
    }