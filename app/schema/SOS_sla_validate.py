from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SLAResult(BaseModel):
    """ผลคำนวณ SLA ของแต่ละ Ticket"""
    ticket_id: str
    it_empno: Optional[str] = None
    req_user: Optional[str] = None
    req_des: Optional[str] = None
    created_at_ticket: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    working_minutes: Optional[int] = None
    sla_met: Optional[bool] = None
    from_cache: bool = False


class SLABatchResponse(BaseModel):
    """Response สำหรับ SLA หลาย Ticket พร้อมสรุป"""
    total_tickets: int = 0
    calculated_tickets: int = 0
    skipped_tickets: int = Field(0, description="Tickets ที่ยังไม่ถูก Accept")
    sla_met_count: int = 0
    sla_missed_count: int = 0
    results: List[SLAResult] = []


class SLACacheItem(BaseModel):
    """Item จาก Cache สำหรับ GET /sla/cache"""
    ticket_id: str
    it_empno: Optional[str] = None
    req_user: Optional[str] = None
    req_des: Optional[str] = None
    created_at_ticket: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    working_minutes: Optional[int] = None
    sla_met: Optional[bool] = None
    cached_at: Optional[datetime] = None
