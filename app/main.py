from fastapi import FastAPI, Request, Body, HTTPException
from pydantic import BaseModel
from typing import Any

app = FastAPI()

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
    return item.model_dump()   # Pydantic v2

@app.post("/payload-dynamic/")
async def get_payload_dynamic(payload: Any = Body(...)):
    return {"received": payload}
