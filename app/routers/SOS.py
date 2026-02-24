import os
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime
from jinja2 import Environment, FileSystemLoader
from app.service import SOS_fn
from app.service.SOS_sla import SLACalculator
from app.service.vocher_wifi import create_voucher_endpoint
from app.db.SOS_holiday import Holiday
from app.db.SOS_sla_cache import SLACache
from fastapi.responses import JSONResponse

# Jinja2 template setup
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "component")
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
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

class TicketData(BaseModel):
    voucher_code: str
    profile_name: str
    concurrent_devices: int = 1
    period: str = "1Days"
    maximum_download_rate: str = "20Mbps"

    
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


# ==========================================
# Voucher Ticket Generator
# ==========================================

@SOS.post("/generate-ticket", response_class=HTMLResponse)
async def generate_ticket(tickets: List[TicketData]):
    """
    สร้าง HTML Voucher Ticket จาก JSON
    - รับ List ของ TicketData
    - Render เป็น HTML พร้อมปริ้น
    - ไม่มีการบันทึกข้อมูล (stateless)

    Example Body:
    ```json
    [
      {"voucher_code": "abc123", "profile_name": "AAPICO_Day", "concurrent_devices": 1, "period": "1Days", "maximum_download_rate": "20Mbps"},
      {"voucher_code": "xyz789", "profile_name": "AAPICO_Day", "concurrent_devices": 1, "period": "1Days", "maximum_download_rate": "20Mbps"}
    ]
    ```
    """
    if not tickets:
        raise HTTPException(status_code=400, detail="กรุณาส่ง ticket อย่างน้อย 1 รายการ")

    try:
        template = jinja_env.get_template("voucher_template.html")
        html_content = template.render(tickets=[t.model_dump() for t in tickets])
        return HTMLResponse(content=html_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template render error: {str(e)}")


@SOS.get("/generate-ticket/preview", response_class=HTMLResponse)
async def generate_ticket_preview():
    """
    หน้า Form สำหรับทดสอบ generate-ticket
    - วาง JSON → กด Generate → เปิด HTML ใน Tab ใหม่
    """
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Voucher Generator - Preview</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #eee; min-height: 100vh; display: flex; justify-content: center; align-items: center; }
        .container { background: #16213e; border-radius: 16px; padding: 32px; width: 640px; box-shadow: 0 8px 32px rgba(0,0,0,0.3); }
        h1 { font-size: 22px; margin-bottom: 8px; background: linear-gradient(90deg, #e94560, #0f3460); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        p { font-size: 13px; color: #999; margin-bottom: 16px; }
        textarea { width: 100%; height: 260px; background: #0f3460; color: #e2e2e2; border: 1px solid #333; border-radius: 8px; padding: 12px; font-family: 'Consolas', monospace; font-size: 13px; resize: vertical; }
        textarea:focus { outline: none; border-color: #e94560; }
        button { margin-top: 12px; padding: 10px 24px; background: linear-gradient(135deg, #e94560, #c23152); color: #fff; border: none; border-radius: 8px; font-size: 15px; cursor: pointer; transition: transform 0.15s; }
        button:hover { transform: scale(1.03); }
        .status { margin-top: 12px; font-size: 13px; color: #e94560; min-height: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎫 Voucher Ticket Generator</h1>
        <p>วาง JSON Array ของ ticket แล้วกด Generate เพื่อเปิด HTML ใน Tab ใหม่</p>
        <textarea id="jsonInput">[
  {"voucher_code": "abc123", "profile_name": "AAPICO_Day", "concurrent_devices": 1, "period": "1Days", "maximum_download_rate": "20Mbps"},
  {"voucher_code": "xyz789", "profile_name": "AAPICO_Day", "concurrent_devices": 1, "period": "7Days", "maximum_download_rate": "50Mbps"}
]</textarea>
        <button onclick="generate()">🖨️ Generate & Print</button>
        <div class="status" id="status"></div>
    </div>
    <script>
        async function generate() {
            const status = document.getElementById('status');
            const input = document.getElementById('jsonInput').value;
            try {
                const data = JSON.parse(input);
                status.textContent = '⏳ Generating...';
                const res = await fetch('/SOS/generate-ticket', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (!res.ok) throw new Error(await res.text());
                const html = await res.text();
                const win = window.open('', '_blank');
                win.document.write(html);
                win.document.close();
                status.textContent = '✅ Opened in new tab!';
            } catch (e) {
                status.textContent = '❌ ' + e.message;
            }
        }
    </script>
</body>
</html>
    """)


# ==========================================
# WiFi Voucher Generator (Ruijie Cloud API)
# ==========================================

class VoucherRequest(BaseModel):
    groupname: str = "AH"
    profile_name: str = "AAPICO_Day"
    quantity: int = 1


@SOS.post("/generate-voucher")
async def generate_voucher(request: VoucherRequest):
    """
    สร้าง WiFi Voucher ผ่าน Ruijie Cloud API
    - เรียก create_voucher_endpoint เพื่อสร้าง voucher
    - แปลง response ให้เป็น TicketData format
    """
    result = create_voucher_endpoint(
        groupname=request.groupname,
        profile_name=request.profile_name,
        quantity=request.quantity,
    )
    # ดึง voucher list จาก Ruijie response
    return result
