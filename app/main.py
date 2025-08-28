from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import Any
from fastapi.encoders import jsonable_encoder
from typing import List

app = FastAPI()

class data(BaseModel):
    username: str
    email: str

class license_input(BaseModel):
    ip : int
    hostname: str
    data : List[data] 

# Dynamic payload handler
@app.post("/testing/")
async def get_payload_dynamic(payload : license_input):
    payload = jsonable_encoder(payload)
    return payload
