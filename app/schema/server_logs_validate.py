from pydantic import BaseModel
from typing import Optional, Any, List
from datetime import date, time, datetime
from decimal import Decimal
from pydantic import BaseModel

# Dynamic log model
class server_logs_Input(BaseModel):
    ip: int
    product: str   # ใช้เป็น key เลือก model
    data: List[Any]

class ibm_spectrum(BaseModel):
    object_id : Optional[str] = None
    consistency_group : Optional[str] = None
    name : Optional[str] = None
    source_target_host : Optional[str] = None
    source_target_pool : Optional[str] = None
    source_target_storage : Optional[str] = None
    source_target_tier : Optional[str] = None
    source_target_volume : Optional[str] = None
    status : Optional[str] = None
    type : Optional[str] = None 
    class Config:
        extra = "ignore"
