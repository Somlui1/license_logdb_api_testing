import os
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime
from jinja2 import Environment, FileSystemLoader
from app.service import SOS_fn
from app.service.SOS_sla import SLACalculator
from app.service.vocher_wifi import (
    create_voucher_endpoint,
    get_access_token,
    get_network_group_id,
    get_all_network_groups,
    get_all_profiles,
)
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


@SOS.get(
    "/generate-ticket/print",
    response_class=HTMLResponse,
    summary="🖨️ Generate & Print Voucher via Query Parameters",
    description="""
## Quick Print — One-Click Voucher via URL

ทำงานเหมือนหน้า `/generate-ticket/preview` แต่ทำอัตโนมัติทั้งหมดผ่าน query parameter
ไม่ต้องกรอกฟอร์ม — เปิด URL แล้วระบบจะ generate voucher และ redirect ไปหน้า print ให้เลย

### ตัวอย่างการใช้งาน

```
GET /SOS/generate-ticket/print?groupname=AH&profile_name=AAPICO_Day&quantity=5
```

### Query Parameters
| Parameter | Required | Default | Description |
|---|:---:|---|---|
| `groupname` | ✅ | `AH` | ชื่อ Network Group (เช่น AH, FT) |
| `profile_name` | ✅ | `AAPICO_Day` | ชื่อ Profile ของ Voucher |
| `quantity` | ✅ | `1` | จำนวน Voucher ที่ต้องการสร้าง |

### ขั้นตอนการทำงาน (อัตโนมัติ)
1. เปิดหน้า loading ใน browser
2. เรียก Ruijie Cloud API สร้าง Voucher (`POST /generate-voucher`)
3. ส่งข้อมูล voucher ไปยัง `POST /generate-ticket` เพื่อ render HTML
4. redirect ไปหน้า print voucher อัตโนมัติ (เหมือนกด Generate ใน preview)

### หมายเหตุ
- **Refresh ไม่ได้** — URL จะถูกลบ query params ออกหลัง generate เพื่อป้องกันการสร้าง voucher ซ้ำ
- ใช้ Ruijie Cloud API ตัวเดียวกับ `POST /generate-voucher`
""",
)
async def print_voucher_via_query(
    groupname: str = "AH",
    profile_name: str = "AAPICO_Day",
    quantity: int = 1,
):
    """
    Serve หน้า voucher_auto_print.html ที่จะทำงานอัตโนมัติ:
    1. อ่าน query params จาก URL
    2. เรียก POST /generate-voucher (Ruijie Cloud API)
    3. เรียก POST /generate-ticket (render HTML)
    4. Replace หน้าปัจจุบันด้วย voucher print layout
    5. ลบ query params ออกจาก URL เพื่อป้องกัน refresh ซ้ำ
    """
    try:
        template = jinja_env.get_template("voucher_auto_print.html")
        html_content = template.render()
        return HTMLResponse(content=html_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template render error: {str(e)}")


@SOS.get("/generate-ticket/preview", response_class=HTMLResponse)
async def generate_ticket_preview():
    """
    หน้า Form สำหรับทดสอบ generate-ticket
    - วาง JSON → กด Generate → เปิด HTML ใน Tab ใหม่
    """
    try:
        template = jinja_env.get_template("new_vocher_portal.html")
        html_content = template.render()
        return HTMLResponse(content=html_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template render error: {str(e)}")


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


@SOS.get(
    "/wifi/groups",
    summary="📡 List all Ruijie Network Groups",
    description="""
ดึงรายการ Network Groups ทั้งหมดจาก Ruijie Cloud API

ใช้เพื่อดูว่ามี group อะไรบ้าง ก่อนเรียก `/wifi/groups/{groupname}/profiles`

### Response
```json
{
  "status": "success",
  "data": [
    { "name": "AH", "groupId": 12345 },
    { "name": "FT", "groupId": 67890 }
  ]
}
```
""",
)
async def list_wifi_groups():
    """
    ดึง Network Groups ทั้งหมดจาก Ruijie Cloud
    """
    access_token = get_access_token()
    groups = get_all_network_groups(access_token)
    return {
        "status": "success",
        "count": len(groups),
        "data": groups,
    }


@SOS.get(
    "/wifi/groups/{groupname}/profiles",
    summary="📋 List WiFi Profiles of a Group",
    description="""
ดึงรายการ WiFi Profile ทั้งหมดของ Network Group ที่ระบุ

### ตัวอย่าง
```
GET /SOS/wifi/groups/AH/profiles
```

### Response
```json
{
  "status": "success",
  "groupname": "AH",
  "data": [
    {
      "name": "AAPICO_Day",
      "id": 123,
      "authProfileId": "456",
      "concurrent_devices": 1,
      "period": "1.0Day",
      "maximum_download_rate": "20.0Mbps"
    }
  ]
}
```
""",
)
async def list_wifi_profiles(groupname: str):
    """
    ดึง WiFi Profile ทั้งหมดของ Group ที่ระบุ
    1. ดึง Access Token
    2. หา Group ID จากชื่อ
    3. ดึง Profile List ทั้งหมด
    """
    access_token = get_access_token()
    group_id = get_network_group_id(access_token=access_token, name=groupname)
    profiles = get_all_profiles(access_token=access_token, group_id=group_id)
    return {
        "status": "success",
        "groupname": groupname.upper(),
        "count": len(profiles),
        "data": profiles,
    }
