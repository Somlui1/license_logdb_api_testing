from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List
from datetime import date
from app.service import SOS_fn
from app.db.SOS_holiday import Holiday
# สร้าง Router
SOS  = APIRouter(
    prefix="/SOS",  # ตั้ง prefix ที่นี่เลย
    tags=["SOS"]
)
# เตรียม Service ไว้ใช้งาน
intranet_service = SOS_fn.IntranetService()

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
            