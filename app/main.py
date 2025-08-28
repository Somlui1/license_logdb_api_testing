from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import Any
from sqlalchemy import create_engine, text

app = FastAPI()

# Dynamic payload handler
@app.post("/testing/")
async def get_payload_dynamic(payload: Any = Body(...)):
    return {"received_payload": payload}
