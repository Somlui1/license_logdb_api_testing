import requests
import os
from collections import defaultdict
from datetime import datetime, timedelta, time, date
from app.db.SOS_holiday import Holiday
from app.db.SOS_sla_cache import SLACache

# ========== Config ==========
SOS_MICROSERVICE_URL = os.getenv("SOS_MICROSERVICE_URL", "http://10.10.3.215:3434")

# ========== SLA Constants ==========
WORK_START = time(8, 0)    # 08:00
WORK_END = time(17, 0)     # 17:00
BREAK_START = time(12, 0)  # 12:00
BREAK_END = time(13, 0)    # 13:00
SLA_THRESHOLD_MINUTES = 480  # 8 ชั่วโมงทำงาน

class SLACalculator:
    """
    Service สำหรับคำนวณ SLA ของ SOS Ticket
    - ดึงข้อมูลจาก Express.js Microservice
    - ตรวจ Cache ก่อนคำนวณ
    - คำนวณ Working Minutes (08:00-17:00, พัก 12:00-13:00, หยุดวันอาทิตย์/วันหยุด)
    """

    def __init__(self):
        self.base_url = SOS_MICROSERVICE_URL

    # ==========================================
    # 1. ดึงข้อมูลจาก Express.js Microservice
    # ==========================================
    def fetch_tickets(self, emp_id: str, year: int, count: bool = True) -> list[dict]:
        """
        เรียก Express.js API เพื่อดึง Ticket ของ IT Staff
        URL: GET /sos/log?id={emp_id}&year={year}&$count=true
        """
        try:
            params = {
                "id": emp_id,
                "year": year,
            }
            if count:
                params["$count"] = "true"

            url = f"{self.base_url}/sos/log"
            print(f"📡 Fetching tickets from: {url} params={params}")

            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()

            json_data = response.json()

            # รองรับทั้ง format { "data": [...] } และ [...]
            if isinstance(json_data, dict) and "data" in json_data:
                tickets = json_data["data"]
            elif isinstance(json_data, list):
                tickets = json_data
            else:
                tickets = []

            print(f"✅ Received {len(tickets)} tickets")
            return tickets

        except requests.RequestException as e:
            print(f"❌ Error fetching tickets from microservice: {e}")
            raise Exception(f"ไม่สามารถเชื่อมต่อ Express.js Microservice: {e}")

    # ==========================================
    # 2. คำนวณ SLA สำหรับ Ticket ทั้งหมด
    # ==========================================
    def calculate_all(self, tickets: list[dict]) -> dict:
        """
        คำนวณ SLA ของ Ticket ทั้งหมดที่ได้จาก Microservice
        - ตรวจ Cache ก่อน
        - ถ้าไม่มี Cache → คำนวณใหม่
        Returns: dict พร้อมสรุปผล + monthly_summary
        """
        results = []
        sla_met_count = 0
        sla_missed_count = 0
        skipped = 0
        to_cache = []  # เก็บรายการที่ต้อง save cache

        # สถิติรายเดือน: key = เดือน (str)
        monthly_stats = defaultdict(lambda: {
            "total": 0,
            "sla_met": 0,
            "sla_missed": 0,
            "eval_total_score": 0.0,
            "eval_count": 0,
        })

        # โหลด Holidays ทั้งหมดไว้ใช้ (ป้องกัน query ซ้ำ)
        holidays_set = self._load_holidays_set()

        for ticket in tickets:
            ticket_id = str(ticket.get("REQ_NO", ""))
            acept_date_raw = ticket.get("ACEPT_DATE")

            # ข้ามถ้ายังไม่ถูก Accept
            if not acept_date_raw or acept_date_raw in ("", "null", None):
                skipped += 1
                continue

            # --- Parse ข้อมูลจาก live data (ทำก่อน cache check) ---
            req_date_for_month = self._parse_req_date(ticket.get("REQ_DATE", ""))
            month_key = str(req_date_for_month.month) if req_date_for_month else None

            # Parse Eval Score
            eval_raw = ticket.get("EVAL_SCRORE", "") or ""
            eval_score_str = eval_raw.split(",")[0].strip() if eval_raw else "0"
            try:
                eval_score_val = float(eval_score_str)
            except (ValueError, TypeError):
                eval_score_val = 0.0

            # สะสม Eval Score ตามเดือน (เฉพาะที่มีค่า > 0)
            if eval_score_val > 0 and month_key:
                monthly_stats[month_key]["eval_total_score"] += eval_score_val
                monthly_stats[month_key]["eval_count"] += 1

            # --- Step 1: ตรวจ Cache ---
            cached = SLACache.get_by_ticket_id(ticket_id)
            if cached:
                cached["from_cache"] = True
                cached["EVAL_SCRORE"] = eval_score_val
                results.append(cached)

                is_met = cached.get("sla_met", False)
                if is_met:
                    sla_met_count += 1
                else:
                    sla_missed_count += 1

                # สะสมสถิติรายเดือน (cache hit)
                if month_key:
                    monthly_stats[month_key]["total"] += 1
                    if is_met:
                        monthly_stats[month_key]["sla_met"] += 1
                    else:
                        monthly_stats[month_key]["sla_missed"] += 1
                continue

            # --- Step 2: Parse Dates ---
            req_date = self._parse_req_date(ticket.get("REQ_DATE", ""))
            acept_date = self._parse_acept_date(acept_date_raw)

            if not req_date or not acept_date:
                skipped += 1
                continue

            # --- Step 3: คำนวณ Working Minutes ---
            working_mins = self._calculate_working_minutes(req_date, acept_date, holidays_set)
            sla_met = working_mins <= SLA_THRESHOLD_MINUTES

            if sla_met:
                sla_met_count += 1
            else:
                sla_missed_count += 1

            # สะสมสถิติรายเดือน (fresh calculation)
            if month_key:
                monthly_stats[month_key]["total"] += 1
                if sla_met:
                    monthly_stats[month_key]["sla_met"] += 1
                else:
                    monthly_stats[month_key]["sla_missed"] += 1

            result_item = {
                "ticket_id": ticket_id,
                "it_empno": str(ticket.get("IT_EMPNO", "")),
                "req_user": ticket.get("REQ_USER", ""),
                "req_des": ticket.get("REQ_DES", ""),
                "created_at_ticket": req_date,
                "accepted_at": acept_date,
                "working_minutes": working_mins,
                "sla_met": sla_met,
                "from_cache": False,
                "EVAL_SCRORE": eval_score_val,
            }
            results.append(result_item)

            # เตรียม data สำหรับ cache (ไม่มี from_cache, EVAL_SCRORE)
            cache_data = {k: v for k, v in result_item.items() if k not in ("from_cache", "EVAL_SCRORE")}
            to_cache.append(cache_data)

        # ==========================================
        # สรุปรายเดือน: total, sla_met, sla_missed, sla_met_pct, eval_score
        # ==========================================
        monthly_summary = {}
        for month in sorted(monthly_stats.keys(), key=lambda x: int(x)):
            s = monthly_stats[month]
            total = s["total"]
            met = s["sla_met"]
            missed = s["sla_missed"]
            met_pct = round((met / total) * 100, 2) if total > 0 else 0.0

            # eval_score = sum(scores) / (จำนวนคนประเมิน × 10)
            eval_score = 0.0
            if s["eval_count"] > 0:
                eval_score = round(s["eval_total_score"] / (s["eval_count"] * 10), 2)

            monthly_summary[month] = {
                "total_tickets": total,
                "sla_met": met,
                "sla_missed": missed,
                "sla_met_pct": met_pct,
                "eval_score": eval_score,
            }

        return {
            "total_tickets": len(tickets),
            "calculated_tickets": len(results),
            "skipped_tickets": skipped,
            "sla_met_count": sla_met_count,
            "sla_missed_count": sla_missed_count,
            "monthly_summary": monthly_summary,
            "results": results,
            "_to_cache": to_cache,  # internal: สำหรับ background save
        }

    # ==========================================
    # 3. Background Save to Cache
    # ==========================================
    def save_to_cache(self, to_cache: list[dict]):
        """
        บันทึกผล SLA ลง Cache (เรียกจาก BackgroundTasks)
        """
        if not to_cache:
            return
        result = SLACache.save_batch(to_cache)
        if result.get("success"):
            print(f"💾 Cached {result.get('saved', 0)} SLA results")
        else:
            print(f"❌ Cache save failed: {result.get('error')}")

    # ==========================================
    # 4. SLA Calculation Logic
    # ==========================================
    def _calculate_working_minutes(
        self, start_dt: datetime, end_dt: datetime, holidays_set: set
    ) -> int:
        """
        คำนวณจำนวนนาทีทำงาน ระหว่าง start_dt → end_dt
        Rules:
        - เฉพาะ 08:00-17:00
        - หัก 12:00-13:00 (พักเที่ยง)
        - ข้าม วันอาทิตย์, วันหยุด, เสาร์ที่เป็นวันหยุด
        """
        if end_dt <= start_dt:
            return 0

        total_minutes = 0
        current_date = start_dt.date()
        end_date = end_dt.date()

        while current_date <= end_date:
            # ตรวจว่าเป็นวันทำงานไหม
            if not self._is_working_day(current_date, holidays_set):
                current_date += timedelta(days=1)
                continue

            # กำหนดเวลาเริ่ม-จบ ของวันนี้
            day_start = datetime.combine(current_date, WORK_START)
            day_end = datetime.combine(current_date, WORK_END)

            # Clamp เวลาจริง เข้ากรอบ workday
            effective_start = max(start_dt, day_start)
            effective_end = min(end_dt, day_end)

            if effective_start >= effective_end:
                current_date += timedelta(days=1)
                continue

            # คำนวณนาทีของวันนี้
            day_minutes = (effective_end - effective_start).total_seconds() / 60

            # หักเวลาพักเที่ยง (12:00-13:00)
            break_start = datetime.combine(current_date, BREAK_START)
            break_end = datetime.combine(current_date, BREAK_END)

            # คำนวณ overlap ของ effective time กับ break time
            overlap_start = max(effective_start, break_start)
            overlap_end = min(effective_end, break_end)

            if overlap_start < overlap_end:
                break_minutes = (overlap_end - overlap_start).total_seconds() / 60
                day_minutes -= break_minutes

            total_minutes += max(0, day_minutes)
            current_date += timedelta(days=1)

        return int(total_minutes)

    def _is_working_day(self, check_date: date, holidays_set: set) -> bool:
        """
        ตรวจว่าวันนี้เป็นวันทำงานไหม
        - วันอาทิตย์ → หยุดเสมอ
        - เสาร์ → ตรวจกับ holidays table (ถ้าเสาร์อยู่ใน holidays = หยุด)
        - วันธรรมดา → ตรวจกับ holidays table
        """
        # วันอาทิตย์ = หยุดเสมอ
        if check_date.weekday() == 6:  # Sunday
            return False

        # วันเสาร์ = ตรวจว่าเป็นวันหยุดไหม (เสาร์ที่เป็นวันหยุดจะอยู่ใน holidays)
        if check_date.weekday() == 5:  # Saturday
            # เสาร์ที่ไม่อยู่ใน holidays → ถือว่าทำงาน
            # เสาร์ที่อยู่ใน holidays → หยุด
            if check_date in holidays_set:
                return False
            return True

        # วันจันทร์-ศุกร์ ตรวจ holidays
        if check_date in holidays_set:
            return False

        return True

    # ==========================================
    # 5. Helpers
    # ==========================================
    def _load_holidays_set(self) -> set:
        """
        โหลดวันหยุดทั้งหมดจาก DB เป็น set ของ date
        ดึงจาก Holiday model (app.db.SOS_holiday)
        """
        try:
            holidays = Holiday.get_by_range()  # ดึงทั้งหมด
            return {h["date"] for h in holidays if "date" in h}
        except Exception as e:
            print(f"⚠️ Could not load holidays: {e}")
            return set()

    def _parse_req_date(self, raw: str) -> datetime | None:
        """
        Parse REQ_DATE format: "dd-MM-yyyy HH:mm"
        Example: "05-01-2026 08:29"
        """
        if not raw:
            return None
        try:
            return datetime.strptime(raw.strip(), "%d-%m-%Y %H:%M")
        except ValueError:
            # ลอง format อื่น
            try:
                return datetime.strptime(raw.strip(), "%Y-%m-%d %H:%M:%S")
            except ValueError:
                print(f"⚠️ Cannot parse REQ_DATE: {raw}")
                return None

    def _parse_acept_date(self, raw: str) -> datetime | None:
        """
        Parse ACEPT_DATE format: "yyyy-MM-dd HH:mm:ss"
        Example: "2026-01-05 08:37:28"
        """
        if not raw:
            return None
        try:
            return datetime.strptime(raw.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            # ลอง format อื่น
            try:
                return datetime.strptime(raw.strip(), "%d-%m-%Y %H:%M")
            except ValueError:
                print(f"⚠️ Cannot parse ACEPT_DATE: {raw}")
                return None
