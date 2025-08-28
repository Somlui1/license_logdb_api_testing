from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import Any
from sqlalchemy import create_engine, text
from db import Base, create_log_model, TestingUser, NXSession, AutoformSession, SolidworkSession

app = FastAPI()

# Database connection
engine = create_engine("postgresql://admin:it%40apico4U@10.10.10.181:5432/license_logsdb")

# สร้าง schemas
schemas = ["testing", "nx", "autoform", "solidworks"]
with engine.connect() as conn:
    for schema_name in schemas:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
    conn.commit()

# สร้าง tables
Base.metadata.create_all(bind=engine)

# Pydantic models
class Supplier(BaseModel):
    name: str
    contact: str

class Item(BaseModel):
    name: str
    price: float
    quantity: int
    supplier: Supplier

@app.post("/testing/items/")
async def create_item(item: Item):
    return item.model_dump()  # Pydantic v2

# Dynamic payload handler
@app.post("/logs/")
async def get_payload_dynamic(log_type: str, payload: Any = Body(...)):
    return {payload}
