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

class veeambackupjob(BaseModel):
    veeamserver = Optional[str] = [str]
    backupjob: Optional[str] = [str]
    server: Optional[str] = [str]
    starttime: Optional[datetime] = [datetime] 
    endtime: Optional[datetime] = [datetime] 
    duration: Optional[str] = [str]
    status: Optional[str] = [str]
    progress: Optional[float] = None
    info: Optional[str] = None
    encrypted: Optional[bool] = None
    transferedsize_byte: Optional[int] = None
    transferedsize: Optional[float] = None
    percents: Optional[float] = None
    
    # ข้อมูลเชิงตัวเลข
    totalobjects: Optional[int] = None
    processedsize: Optional[int] = None
    processedusedsize: Optional[int] = None
    readsize: Optional[int] = None
    readedaveragesize: Optional[int] = None
    # เวลาที่เกี่ยวข้อง
    starttimelocal: Optional[datetime] = None
    stoptimelocal: Optional[datetime] = None
    starttimeutc: Optional[datetime] = None
    stoptimeutc: Optional[datetime] = None
    # ข้อมูลเชิง performance
    avgspeed: Optional[int] = None
    totalsize: Optional[int] = None
    totalusedsize: Optional[int] = None
    usedspaceration: Optional[float] = None
    totalsizedelta: Optional[int] = None
    totalusedsizedelta: Optional[int] = None
    hash_id: Optional[str] = None


  # backupjob
  # server
  # starttime
  # endtime
  # duration
  # status
  # progress
  # info
  # encrypted
  # transferedsize_byte
  # transferedsize
  # percents
  # totalobjects
  # processedsize
  # processedusedsize
  # readsize
  # readedaveragesize
  # starttimelocal
  # stoptimelocal
  # starttimeutc
  # stoptimeutc
  # avgspeed
  # totalsize
  # totalusedsize
  # usedspaceration
  # totalsizedelta
  # totalusedsizedelta
  # hash_id

