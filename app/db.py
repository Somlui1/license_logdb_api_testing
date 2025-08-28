from sqlalchemy import Column, Integer, String, DateTime, Date, Time, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()
# Dynamic schemas

# ตัวอย่าง session_logs สำหรับ software ต่างๆ
class NXSession(Base):
    __tablename__ = "session_logs"
    __table_args__ = {"schema": "nx"}
    id = Column(Integer, primary_key=True)
    start_date = Column(Date)
    start_time = Column(Time)
    end_date = Column(Date)
    end_time = Column(Time)
    duration_minutes = Column(Numeric(10,2))
    hostname = Column(String)
    module = Column(String)
    username = Column(String)

class AutoformSession(Base):
    __tablename__ = "session_logs"
    __table_args__ = {"schema": "autoform"}
    id = Column(Integer, primary_key=True)
    start_date = Column(Date)
    start_time = Column(Time)
    start_hours = Column(Integer)
    start_action = Column(String)
    end_date = Column(Date)
    end_time = Column(Time)
    end_hours = Column(Integer)
    end_action = Column(String)
    duration_minutes = Column(Numeric(10,2))
    host = Column(String)
    module = Column(String)
    username = Column(String)
    version = Column(String)

class SolidworkSession(Base):
    __tablename__ = "session_logs"
    __table_args__ = {"schema": "solidworks"}
    id = Column(Integer, primary_key=True)
    start_date = Column(Date)
    start_time = Column(Time)
    end_date = Column(Date)
    end_time = Column(Time)
    duration_minutes = Column(Numeric(10,2))
    feature = Column(String)
    username = Column(String)
    computer = Column(String)
