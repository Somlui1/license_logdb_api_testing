
from datetime import datetime, date, time
from decimal import Decimal
from typing import Any

class LogBase:
    id: int
    name: str
    data: Any
    created_at: datetime


# สำหรับ testing.users

class LestingUserModel:
    id: int
    email: str
    username: str


# NX session_logs

class NX:
    id: int
    start_date: date
    start_time: time
    end_date: date
    end_time: time
    duration_minutes: Decimal
    hostname: str
    module: str
    username: str


# Autoform session_logs

class AutoForm:
    id: int
    start_date: date
    start_time: time
    start_hours: int
    start_action: str
    end_date: date
    end_time: time
    end_hours: int
    end_action: str
    duration_minutes: Decimal
    host: str
    module: str
    username: str
    version: str


# Solidworks session_logs

class SolidWork:
    id: int
    start_date: date
    start_time: time
    end_date: date
    end_time: time
    duration_minutes: Decimal
    feature: str
    username: str
    computer: str
