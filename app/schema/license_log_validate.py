from pydantic import BaseModel
from typing import Optional, Any, List, Union
from datetime import date, time, datetime
from decimal import Decimal
from pydantic import BaseModel

# Dynamic log model
class LicenseInput(BaseModel):
    ip: int                          # ต้องเป็นตัวเลข
    product: str                      # ใช้เป็น key เลือก model
    data: List[Any]                   # เป็น array ของ object / dict
    raw: Optional[bool] = False       # default = False
    row: Optional[List[Any]] = None   # array ของ object หรือ empty list

    class Config:
        extra = "ignore"     

class logbase(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    data: Optional[Any] = None
    created_at: Optional[datetime] = None
    class Config:
        extra = "ignore"

# สำหรับ testing.users
class  lestingUserModel(BaseModel):
    id: Optional[int] = None
    email: Optional[str] = None
    username: Optional[str] = None
    class Config:
        extra = "ignore"
    
class CatiaBaseModel(BaseModel):
    username: Optional[str] = None
    hostname: Optional[str] = None
    feature : Optional[str] = None
    start_datetime: Optional[datetime] = None
    start_action : Optional[str] = None 
    end_datetime: Optional[datetime] = None
    duration_min: Optional[float] = None
    end_action: Optional[str] = None
    product: Optional[str] = None
    customer: Optional[str] = None
    license_type: Optional[str] = None
    count: Optional[int] = None
    level: Optional[str] = None
    hash_id: Optional[str] = None
    #batch_id: Optional[str] = None

    class Config:
        extra = "ignore"

class AA_catia(CatiaBaseModel):
    pass

class AHA_catia(CatiaBaseModel):
    pass

# Autoform session_logs
class autoform(BaseModel):
    start_datetime: Optional[datetime] = None
    start_action: Optional[str] = None
    end_datetime: Optional[datetime] = None
    end_action: Optional[str] = None
    duration_minutes: Optional[Decimal] = None
    host: Optional[str] = None
    module: Optional[str] = None
    username: Optional[str] = None
    version: Optional[str] = None
    hash_id: Optional[str] = None
    hash   :Optional[str] = None
    #batch_id: Optional[str] = None
    class Config:
        extra = "ignore"

#class autodesk(BaseModel):
#    start_date: Optional[date] = None
#    start_time: Optional[date] = None
#    start_hours: Optional[int] = None
#    start_action: Optional[str] = None
#    end_date: Optional[date] = None
#    end_time: Optional[date] = None
#    end_hours: Optional[int] = None
#    end_action: Optional[str] = None
#    duration_minutes: Optional[Decimal] = None
#    host: Optional[str] = None
#    module: Optional[str] = None
#    username: Optional[str] = None
#    version: Optional[str] = None
#    batch_id: Optional[str] = None
#    class Config:
#        extra = "ignore"
#        
#
## NX session_logs
class nx(BaseModel):
    start_datetime: Optional[datetime] = None
    start_action: Optional[str] = None
    end_datetime: Optional[datetime] = None
    end_action: Optional[str] = None
    duration_minutes: Optional[Decimal] = None
    hostname: Optional[str] = None
    module: Optional[str] = None
    username: Optional[str] = None
    hash_id: Optional[str] = None
    #batch_id: Optional[str] = None
    #keyword: Optional[str] = None
    class Config:
        extra = "ignore"
    

class solidwork(BaseModel):
    start_datetime: Optional[datetime] = None
    start_action: Optional[str] = None
    end_datetime: Optional[datetime] = None
    end_action: Optional[str] = None
    duration_minutes: Optional[Decimal] = None
    hostname: Optional[str] = None
    module: Optional[str] = None
    username: Optional[str] = None
    hash_id: Optional[str] = None
    #batch_id: Optional[str] = None
    #keyword: Optional[str] = None
    class Config:
        extra = "ignore"

# Solidworks session_logs
#lass solidwork(BaseModel):
#   start_date: Optional[date] = None
#   start_time: Optional[time] = None
#   end_date: Optional[date] = None
#   end_time: Optional[time] = None
#   duration_minutes: Optional[Decimal] = None
#   feature: Optional[str] = None
#   username: Optional[str] = None
#   computer: Optional[str] = None
#   batch_id: Optional[str]
#   class Config:
#       extra = "ignore"
    


