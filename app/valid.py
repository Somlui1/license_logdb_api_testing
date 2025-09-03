from pydantic import BaseModel
from typing import Optional, Any
from datetime import date, time, datetime
from decimal import Decimal

# Dynamic log model
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

# NX session_logs
class nx(BaseModel):
    start_date: Optional[date] = None
    start_time: Optional[time] = None
    end_date: Optional[date] = None
    end_time: Optional[time] = None
    duration_minutes: Optional[Decimal] = None
    hostname: Optional[str] = None
    module: Optional[str] = None
    username: Optional[str] = None
    class Config:
        extra = "ignore"

# Autoform session_logs
class autoform(BaseModel):
    start_date: Optional[date] = None
    start_time: Optional[time] = None
    start_hours: Optional[int] = None
    start_action: Optional[str] = None
    end_date: Optional[date] = None
    end_time: Optional[time] = None
    end_hours: Optional[int] = None
    end_action: Optional[str] = None
    duration_minutes: Optional[Decimal] = None
    host: Optional[str] = None
    module: Optional[str] = None
    username: Optional[str] = None
    version: Optional[str] = None
    class Config:
        extra = "ignore"

# Solidworks session_logs
class solidwork(BaseModel):
    start_date: Optional[date] = None
    start_time: Optional[time] = None
    end_date: Optional[date] = None
    end_time: Optional[time] = None
    duration_minutes: Optional[Decimal] = None
    feature: Optional[str] = None
    username: Optional[str] = None
    computer: Optional[str] = None
    class Config:
        extra = "ignore"