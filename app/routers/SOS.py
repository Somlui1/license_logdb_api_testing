from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.service import SOS_fn
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