from fastapi import APIRouter
from sqlalchemy.dialects.postgresql import insert
import uuid
from app.schema import server_logs_validate
from app.db import server_logsdb
import asyncio

router = APIRouter(
    prefix="/server_logs",  # ตั้ง prefix ที่นี่เลย
    tags=["server_logs"]
)
#ORM session
Session_log_server = server_logsdb.Session
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

@router.post("/")
async def server_logs_get_payload_dynamic(payload: server_logs_validate.server_logs_Input):
    # ดึง Pydantic model และ ORM class
    ver = getattr(server_logs_validate, payload.product, None)   # Pydantic model
    orm_class = getattr(server_logsdb, payload.product, None)  # ORM class
    
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
        await asyncio.to_thread(orm_class().save,dict_objects)
        # บันทึก raw logs
    except Exception as e:
        return {"error": str(e)}
    return {
        "ip": payload.ip,
        "product": payload.product,
        "parsed_data": validated
    }

