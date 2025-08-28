from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import Any
from sqlalchemy import create_engine, text
from fastapi.encoders import jsonable_encoder
app = FastAPI()

# Dynamic payload handler
@app.post("/testing/{parameter}")
async def get_payload_dynamic(parameter : int,payload: Any = Body(...)):
    json_payload = jsonable_encoder(payload)
    return {"received_payload": json_payload,
            "parameter" : parameter 
            }
