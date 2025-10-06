from fastapi import FastAPI, HTTPException
from sqlalchemy.dialects.postgresql import insert
import uuid
from app.schema import license_log_validate
from app.schema import server_logs_validate
from app.db import license_logsdb
from app.db import server_logs
from sqlalchemy.exc import SQLAlchemyError
# ORM database setup
#engine_url_license_logsdb = "postgresql://itsupport:aapico@10.10.3.215:5432/license_logsdb"
#license_logsdb.greet(engine_url_license_logsdb)
#engine_license_logsdb = create_engine(engine_url_license_logsdb)
#Base = declarative_base()
#Base.metadata.create_all(engine_license_logsdb)
#Session_license_logsdb = sessionmaker(autocommit=False, autoflush=False, bind=engine_license_logsdb)

app = FastAPI()
#ORM session
Session_license_logsdb = license_logsdb.Session
Session_log_server = server_logs.Session
#=============================

def chunked(iterable, size):
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]

def bulk_upsert(session, orm_class, data: list[dict], chunk_size: int = 600):
    for batch in chunked(data, chunk_size):
        stmt = insert(orm_class).values(batch)
        set_dict = {field: stmt.excluded[field] for field in orm_class.UPSERT_FIELDS}
        stmt = stmt.on_conflict_do_update(
            index_elements=orm_class.UPSERT_INDEX,
            set_=set_dict
        )
        session.execute(stmt)

@app.post("/testing/")
async def get_payload_dynamic(payload: license_log_validate.LicenseInput):
    # ดึง Pydantic model และ ORM class
    ver = getattr(license_log_validate, payload.product, None)   # Pydantic model
    orm_class = getattr(license_logsdb, payload.product, None)  # ORM class

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
        with Session_license_logsdb() as session:
                try:
                    bulk_upsert(session, orm_class, dict_objects, chunk_size=600)
                    session.commit()
                except SQLAlchemyError as e:
                    session.rollback()
                    
                    
                    raise
        # บันทึก raw logs
        RawLogs = license_logsdb.raw_logs_table(payload.product)
        log_entry = RawLogs.from_pydantic(payload, batch_id=share_uuid)
        with Session_license_logsdb() as session:
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
    orm_class = getattr(license_logsdb, product, None)
    if not orm_class:
        raise HTTPException(status_code=404, detail=f"ORM '{product}' not found")

    with Session_license_logsdb() as session:
        results = session.query(orm_class).limit(100000).all()
        # แปลง ORM เป็น dict สำหรับ JSON
        return [obj.__dict__ for obj in results]
    
@app.post("/insert/testing/")
async def get_payload_dynamic_v2(payload: license_log_validate.LicenseInput):
    # ดึง Pydantic model และ ORM class
    ver = getattr(license_log_validate, payload.product, None)   # Pydantic model
    orm_class = getattr(license_logsdb, payload.product, None)  # ORM class

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
        with Session_license_logsdb() as session:
            try:
                session.bulk_save_objects([orm_class(**data) for data in dict_objects])
                session.commit()
            except SQLAlchemyError as e:
                session.rollback()
                raise

        # บันทึก raw logs
        RawLogs = license_logsdb.raw_logs_table(payload.product)
        log_entry = RawLogs.from_pydantic(payload, batch_id=share_uuid)
        with Session_license_logsdb() as session:
            session.add(log_entry)
            session.commit()

    except Exception as e:
        return {"error": str(e)}

    return {
        "ip": payload.ip,
        "product": payload.product,
        "parsed_data": validated
    }

@app.post("/server_logs/")
async def server_logs_get_payload_dynamic(payload: server_logs_validate.server_logs_Input):
    # ดึง Pydantic model และ ORM class
    ver = getattr(server_logs_validate, payload.product, None)   # Pydantic model
    orm_class = getattr(server_logs, payload.product, None)  # ORM class

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
        with Session_log_server() as session:
            try:
                session.bulk_save_objects([orm_class(**data) for data in dict_objects])
                session.commit()
            except SQLAlchemyError as e:
                session.rollback()
                raise
        # บันทึก raw logs
    except Exception as e:
        return {"error": str(e)}
    
    return {
        "ip": payload.ip,
        "product": payload.product,
        "parsed_data": validated
    }