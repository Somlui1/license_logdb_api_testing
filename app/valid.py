from pydantic import BaseModel
from typing import Any, List

class nx(BaseModel):
    hostname: str
    module: str

class solidworks(BaseModel):
    hostname: str
    feature: str
