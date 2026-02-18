from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime
from app.service import SOS_fn
from app.service.SOS_sla import SLACalculator
from app.db.SOS_holiday import Holiday
from app.db.SOS_sla_cache import SLACache
# สร้าง Router
SOS  = APIRouter(
    prefix="/SOS",  # ตั้ง prefix ที่นี่เลย
    tags=["SOS"]
)
# เตรียม Service ไว้ใช้งาน
intranet_service = SOS_fn.IntranetService()
sla_calculator = SLACalculator()

# --- Data Model (Pydantic) ---
class SOSRequest(BaseModel):

    sos_message: str = "test SOS massage via API"
    # Optional Fields (มีค่า Default)
    requestor_name: str = "Wajeepradit Prompan"
    email: str = "wajeepradit.p@aapico.com"
    dept: str = "IT"
    location: str = "office AH"
    tel: str = "1234"
    company: str = "AH"
    ips: str = "10.10.20.93(API_AGENT)"

class HolidayItem(BaseModel):
    date: date
    name: str

# --- API Endpoint ---
@SOS.post("/report-issue")
async def report_issue(ticket: SOSRequest):
    try:
        # เรียกใช้ Logic จาก server.py
        result = intranet_service.submit_ticket(
            sos_message=ticket.sos_message,
            requestor_name=ticket.requestor_name,
            email=ticket.email,
            dept=ticket.dept,
            tel=ticket.tel,
            location=ticket.location,
            company=ticket.company,
            ips=ticket.ips
        )
        return result

    except Exception as e:
        # แปลง Error จาก server เป็น HTTP Error ส่งกลับไป
        error_msg = str(e)
        if "Login" in error_msg:
            raise HTTPException(status_code=401, detail=error_msg)
        else:
            raise HTTPException(status_code=500, detail=error_msg)



@SOS.patch("/holidays")
async def upsert_holidays(holidays: List[HolidayItem]):
    try:
        # Convert Pydantic models to dicts
        data = [h.dict() for h in holidays]
        result = Holiday.save(data)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class HolidayDeleteRequest(BaseModel):
    dates: List[date]

@SOS.delete("/holidays")
async def delete_holidays(item: HolidayDeleteRequest):
    try:
        result = Holiday.delete(item.dates)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@SOS.get("/holidays")
async def get_holidays(start_date: date = None, end_date: date = None):
    try:
        return Holiday.get_by_range(start_date, end_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# SLA Calculation Endpoints
# ==========================================

@SOS.get("/sla/calculate")
async def calculate_sla(
    background_tasks: BackgroundTasks,
    id: str = None,
    year: int = None,
):
    """
    คำนวณ SLA ของ Ticket ทั้งหมดของ IT Staff
    - ดึงข้อมูลจาก Express.js Microservice
    - ตรวจ Cache → ถ้ามีให้คืนค่าเลย
    - ถ้าไม่มี → คำนวณ Working Minutes แล้ว Cache ไว้

    Query Params:
        id: รหัสพนักงาน IT (IT_EMPNO)
        year: ปี (เช่น 2026)
    """
    if not id or not year:
        raise HTTPException(
            status_code=400,
            detail="กรุณาระบุ id (IT_EMPNO) และ year"
        )

    try:
        # 1. ดึง Ticket จาก Express.js
        tickets = sla_calculator.fetch_tickets(emp_id=id, year=year)

        # 2. คำนวณ SLA (ตรวจ cache ภายในอัตโนมัติ)
        result = sla_calculator.calculate_all(tickets)

        # 3. บันทึก Cache แบบ Background (ไม่ block response)
        to_cache = result.pop("_to_cache", [])
        if to_cache:
            background_tasks.add_task(sla_calculator.save_to_cache, to_cache)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@SOS.get("/sla/cache")
async def get_sla_cache(
    start_date: date = None,
    end_date: date = None,
):
    """
    ค้นหาผล SLA ที่ Cache ไว้ ตามช่วงวันที่
    """
    try:
        return SLACache.get_by_range(start_date, end_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

            