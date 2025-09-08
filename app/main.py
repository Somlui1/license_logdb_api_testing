from fastapi import FastAPI ,HTTPException
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

def chunked(iterable, size):
      for i in range(0, len(iterable), size):
        yield iterable[i:i+size]

@app.post("/testing/")
async def get_payload_dynamic(payload: valid.LicenseInput):
    # ดึง Pydantic model และ ORM class
    ver = getattr(valid, payload.product, None)   # Pydantic model
    orm_class = getattr(db, payload.product, None)  # ORM class
    if not ver :
        return {"error": f"Model '{payload.product}' not found"}
    if not orm_class :
        return {"error": f"ORM '{payload.product}' not found"}
    try:
        # 1) validate ข้อมูลด้วย Pydantic
        validated = [ver(**item) for item in payload.data]
       
        # 2) แปลงเป็น ORM objects
        #orm_objects = [orm_class(**item.dict()) for item in validated]
       
        #for item in payload.data:
        #    item['batch_id'] = share_uuid
        share_uuid = uuid.uuid4()
        
        #RawLogs = db.raw_logs_table(payload.product)
        validated = [ver(**item) for item in payload.data]
        dict_objects = []
        for item in validated:
            d = item.dict()
            d['batch_id'] = share_uuid
            dict_objects.append(d)
 
        with Session() as session:
     
            for batch in chunked(dict_objects, 600):
                stmt = insert(orm_class).values(batch)
                session.execute(stmt)
 
            session.commit()  # commit ทั้งหมดใน transaction เดียวกัน
 
        RawLogs = db.raw_logs_table(payload.product)
        log_entry = RawLogs.from_pydantic(payload, batch_id=share_uuid)

        with Session() as session:
            session.add(log_entry)
            session.commit()

# เพิ่มเข้า DB
                       # commit ทีละ batch
    except Exception as e:
        return {"error": str(e)}
        
    return {
        "ip": payload.ip,
        "product": payload.product,
        "parsed_data": validated
    }

@app.get("/logs/{product}/")
def read_logs(product: str):
    ver = getattr(db, product, None)   # Pydantic model
    if not ver:
        raise HTTPException(status_code=404, detail=f"ORM '{product}' not found")

    with Session() as session:
        results = session.query(ver).limit(100000).all()
        # Convert ORM to dict for JSON serialization

        
        return results
        #print([obj.__dict__ for obj in results])