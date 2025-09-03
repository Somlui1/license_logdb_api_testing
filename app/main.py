from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, List
from sqlalchemy import insert
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine       # สร้าง connection engine
from sqlalchemy.orm import sessionmaker    # สร้าง session สำหรับ insert/query
import uuid

from app import valid 
from app import db

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
    if not ver :
        return {"error": f"Model '{payload.product}' not found"}
    if not orm_class :
        return {"error": f"ORM '{payload.product}' not found"}
    try:
        
        # 1) validate ข้อมูลด้วย Pydantic
#        validated = [ver(**item) for item in payload.data]
#
#        # 2) แปลงเป็น ORM objects
#        orm_objects = [orm_class(**item.dict()) for item in validated]

        
        validated = [ver(**item) for item in payload.data]

        # 2) แปลงเป็น dict (เพราะ Core insert ใช้ dict)
        dict_objects = [item.dict() for item in validated]


        # 3) insert batch 100 record
        #for batch in chunked(orm_objects, 400):
        for batch in chunked(dict_objects, 600):
             with Session() as session:
                stmt = insert(orm_class).values(batch)   # Core bulk insert
                session.execute(stmt)
                session.commit()        # commit ทีละ batch
    except Exception as e:
        return {"error": str(e)}
        
    return {
        "ip": payload.ip,
        "product": payload.product,
        "parsed_data": validated
    }