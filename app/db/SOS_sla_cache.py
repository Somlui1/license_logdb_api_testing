from sqlalchemy import Column, Integer, String, Boolean, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func

# ใช้ engine/Base/Session เดียวกับ SOS_holiday.py
from app.db.SOS_holiday import engine_sos, Session

Base = declarative_base()


class SLACache(Base):
    """
    ตาราง Cache สำหรับผลคำนวณ SLA ของแต่ละ Ticket
    เพื่อไม่ต้องคำนวณซ้ำ ถ้าเคยคำนวณแล้ว
    """
    __tablename__ = "sos_sla_cache"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String, unique=True, nullable=False, comment="REQ_NO จาก SOS")
    it_empno = Column(String, nullable=True, comment="รหัสพนักงาน IT ที่รับ Ticket")
    req_user = Column(String, nullable=True, comment="ผู้แจ้ง Ticket")
    req_des = Column(String, nullable=True, comment="รายละเอียดปัญหา")
    created_at_ticket = Column(DateTime(timezone=True), nullable=False, comment="REQ_DATE วันที่สร้าง Ticket")
    accepted_at = Column(DateTime(timezone=True), nullable=True, comment="ACEPT_DATE วันที่รับ Ticket")
    working_minutes = Column(Integer, nullable=True, comment="จำนวนนาทีทำงานที่คำนวณได้")
    sla_met = Column(Boolean, nullable=True, comment="True = ผ่าน SLA (≤480 นาที)")
    cached_at = Column(DateTime(timezone=True), server_default=func.now(), comment="วันที่ Cache")

    # ========== Class Methods ==========

    @classmethod
    def get_by_ticket_id(cls, ticket_id: str) -> dict | None:
        """
        ค้นหา Cache ด้วย ticket_id (REQ_NO)
        คืนค่า dict หรือ None ถ้าไม่พบ
        """
        with Session() as session:
            try:
                result = session.query(cls).filter(cls.ticket_id == str(ticket_id)).first()
                if result:
                    return {
                        "ticket_id": result.ticket_id,
                        "it_empno": result.it_empno,
                        "req_user": result.req_user,
                        "req_des": result.req_des,
                        "created_at_ticket": result.created_at_ticket,
                        "accepted_at": result.accepted_at,
                        "working_minutes": result.working_minutes,
                        "sla_met": result.sla_met,
                        "cached_at": result.cached_at,
                    }
                return None
            except SQLAlchemyError as e:
                print(f"❌ Error fetching SLA cache: {e}")
                return None

    @classmethod
    def save_one(cls, data: dict) -> dict:
        """
        Upsert ผล SLA 1 รายการ (ON CONFLICT ticket_id → UPDATE)
        """
        with Session() as session:
            try:
                stmt = insert(cls).values(**data)

                # อัพเดททุก column ยกเว้น id กับ ticket_id
                update_cols = {
                    k: getattr(stmt.excluded, k)
                    for k in data.keys()
                    if k not in ("id", "ticket_id")
                }
                stmt = stmt.on_conflict_do_update(
                    index_elements=[cls.__table__.c.ticket_id],
                    set_=update_cols,
                )

                session.execute(stmt)
                session.commit()
                return {"success": True, "ticket_id": data.get("ticket_id")}
            except SQLAlchemyError as e:
                session.rollback()
                print(f"❌ Error saving SLA cache: {e}")
                return {"success": False, "error": str(e)}

    @classmethod
    def save_batch(cls, payload: list[dict]) -> dict:
        """
        Upsert หลายรายการพร้อมกัน
        """
        if not payload:
            return {"success": True, "saved": 0}

        with Session() as session:
            try:
                total = 0
                for data in payload:
                    stmt = insert(cls).values(**data)
                    update_cols = {
                        k: getattr(stmt.excluded, k)
                        for k in data.keys()
                        if k not in ("id", "ticket_id")
                    }
                    stmt = stmt.on_conflict_do_update(
                        index_elements=[cls.__table__.c.ticket_id],
                        set_=update_cols,
                    )
                    session.execute(stmt)
                    total += 1

                session.commit()
                return {"success": True, "saved": total}
            except SQLAlchemyError as e:
                session.rollback()
                print(f"❌ Error batch saving SLA cache: {e}")
                return {"success": False, "error": str(e)}

    @classmethod
    def get_by_range(cls, start_date=None, end_date=None) -> list[dict]:
        """
        ค้นหา Cache ตามช่วงวันที่ของ created_at_ticket
        """
        with Session() as session:
            try:
                query = session.query(cls)
                if start_date:
                    query = query.filter(cls.created_at_ticket >= start_date)
                if end_date:
                    query = query.filter(cls.created_at_ticket <= end_date)

                results = query.order_by(cls.created_at_ticket).all()
                return [
                    {
                        "ticket_id": r.ticket_id,
                        "it_empno": r.it_empno,
                        "req_user": r.req_user,
                        "req_des": r.req_des,
                        "created_at_ticket": r.created_at_ticket,
                        "accepted_at": r.accepted_at,
                        "working_minutes": r.working_minutes,
                        "sla_met": r.sla_met,
                        "cached_at": r.cached_at,
                    }
                    for r in results
                ]
            except SQLAlchemyError as e:
                print(f"❌ Error fetching SLA cache range: {e}")
                return []


# ========== สร้างตารางอัตโนมัติเมื่อ import ==========
def init_sla_cache():
    """สร้างตาราง sos_sla_cache ถ้ายังไม่มี"""
    try:
        Base.metadata.create_all(engine_sos)
        print("✅ SLA Cache table checked/created.")
    except Exception as e:
        print(f"❌ Error creating SLA cache table: {e}")


init_sla_cache()
