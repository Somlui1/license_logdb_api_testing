from fastapi import FastAPI, HTTPException
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import uuid
from app import validate
from app import db
from sqlalchemy.exc import SQLAlchemyError
# ORM database setup
engine_url = "postgresql://itsupport:aapico@10.10.3.215:5432/license_logsdb"
db.greet(engine_url)
engine = create_engine(engine_url)
Base = declarative_base()
Base.metadata.create_all(engine)
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

def chunked(iterable, size):
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]

@app.post("/testing/")
async def get_payload_dynamic(payload: validate.LicenseInput):
    # ดึง Pydantic model และ ORM class
    ver = getattr(validate, payload.product, None)   # Pydantic model
    orm_class = getattr(db, payload.product, None)  # ORM class

    if not ver:
        return {"error": f"Model '{payload.product}' not found"}
    if not orm_class:
        return {"error": f"ORM '{payload.product}' not found"}

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

        # Bulk upsert batch 600 row
   


        with Session() as session:
            try:
                for batch in chunked(dict_objects, 600):
                    stmt = insert(orm_class).values(batch)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['hash_id'],
                        set_={
                            "start_datetime": stmt.excluded.start_datetime,
                            "start_action": stmt.excluded.start_action,
                            "end_datetime": stmt.excluded.end_datetime,
                            "end_action": stmt.excluded.end_action,
                            "duration_minutes": stmt.excluded.duration_minutes,
                            "host": stmt.excluded.host,
                            "module": stmt.excluded.module,
                            "username": stmt.excluded.username,
                            "version": stmt.excluded.version,
                            "batch_id": stmt.excluded.batch_id
                        }
                    )
                    session.execute(stmt)
                session.commit()
            except SQLAlchemyError as e:
                session.rollback()  # ย้อนกลับทุกอย่างที่ยังไม่ได้ commit
                print("Upsert failed:", e)  # แสดง error
                # หรือ raise ใหม่เพื่อให้ caller รับรู้
                raise

        # บันทึก raw logs
        RawLogs = db.raw_logs_table(payload.product)
        log_entry = RawLogs.from_pydantic(payload, batch_id=share_uuid)
        with Session() as session:
            session.add(log_entry)
            session.commit()

    except Exception as e:
        return {"error": str(e)}

    return {
        "ip": payload.ip,
        "product": payload.product,
        "parsed_data": validated
    }

@app.get("/logs/{product}/")
def read_logs(product: str):
    orm_class = getattr(db, product, None)
    if not orm_class:
        raise HTTPException(status_code=404, detail=f"ORM '{product}' not found")

    with Session() as session:
        results = session.query(orm_class).limit(100000).all()
        # แปลง ORM เป็น dict สำหรับ JSON
        return [obj.__dict__ for obj in results]
