from pydantic import BaseModel
from datetime import date, time, datetime
from decimal import Decimal
from typing import Optional, Any

# Dynamic log model

class logbase(BaseModel):
    id: Optional[int]
    name: Optional[str]
    data: Optional[Any]
    created_at: Optional[datetime]

# สำหรับ testing.users
class lestingUserModel(BaseModel):
    id: Optional[int]
    email: Optional[str]
    username: Optional[str]

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
