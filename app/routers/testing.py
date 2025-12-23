from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError
from app.schema import license_log_validate
import asyncio
import uuid 
from app.db import license_logsdb

Session_license_logsdb = license_logsdb.Session
#router = APIRouter(
#    prefix="/",  # ตั้ง prefix ที่นี่เลย
#    tags=["license_logs"]
#)

app = FastAPI()
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

        await asyncio.to_thread(orm_class().save, dict_objects)

        # บันทึก raw logs
        RawLogs = license_logsdb.raw_logs_table(schema_name=payload.product)
        log_entry = RawLogs.from_pydantic(payload.data, batch_id=share_uuid)
        with Session_license_logsdb() as session:
            session.add(log_entry)
            session.commit()

        if payload.raw:
            RawLogs = license_logsdb.raw_logs_table(schema_name=payload.product,table_name='raw_logs')
            log_entry = RawLogs.from_pydantic(payload.row, batch_id=share_uuid)
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

#schema_name: str,table_name: str = "raw_logs"
        # บันทึก raw logs
        RawLogs = license_logsdb.raw_logs_table(schema_name=payload.product)
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