from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime, date, time
from decimal import Decimal


class logbase(BaseModel):
    id: Optional[int]
    name: Optional[str]
    data: Optional[Any]
    created_at: Optional[datetime]
    class Config:
        extra = "ignore"


# สำหรับ testing.users
class lestingUserModel(BaseModel):
    id: Optional[int]
    email: Optional[str]
    username: Optional[str]
    class Config:
        extra = "ignore"

# NX session_logs
class nx(BaseModel):
    id: Optional[int]
    start_date: Optional[date]
    start_time: Optional[time]
    end_date: Optional[date]
    end_time: Optional[time]
    duration_minutes: Optional[Decimal]
    hostname: Optional[str]
    module: Optional[str]
    username: Optional[str]
    class Config:
        extra = "ignore"

# Autoform session_logs
class autofrom(BaseModel):
    id: Optional[int]
    start_date: Optional[date]
    start_time: Optional[time]
    start_hours: Optional[int]
    start_action: Optional[str]
    end_date: Optional[date]
    end_time: Optional[time]
    end_hours: Optional[int]
    end_action: Optional[str]
    duration_minutes: Optional[Decimal]
    host: Optional[str]
    module: Optional[str]
    username: Optional[str]
    version: Optional[str]
    class Config:
        extra = "ignore"
# Solidworks session_logs
class solidwork(BaseModel):
    id: Optional[int]
    start_date: Optional[date]
    start_time: Optional[time]
    end_date: Optional[date]
    end_time: Optional[time]
    duration_minutes: Optional[Decimal]
    feature: Optional[str]
    username: Optional[str]
    computer: Optional[str]
    class Config:
        extra = "ignore"