from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime, date, time
from decimal import Decimal

class logbase(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    data: Optional[Any] = None
    created_at: Optional[datetime] = None

    class Config:
        extra = "ignore"


class lestingUserModel(BaseModel):
    id: Optional[int] = None
    email: Optional[str] = None
    username: Optional[str] = None

    class Config:
        extra = "ignore"


class nx(BaseModel):
    id: Optional[int] = None
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


class autofrom(BaseModel): 
    id: Optional[int] = None
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


class solidwork(BaseModel): 
    id: Optional[int] = None
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
