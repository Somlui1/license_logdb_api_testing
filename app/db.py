from sqlalchemy import UUID, Column, Integer, String, DateTime, Date, Time, Numeric, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app import valid 

Base = declarative_base()
schemas = ["autoform", "nx", "catia", "solidworks", "autodesk", "testing"]

class autodesk(Base):
        __tablename__ = "session_logs" # ตั้งชื่อ table ตามต้องการ
        __table_args__ = {"schema": "autodesk"}
        id = Column(Integer, primary_key=True)
        start_date = Column(Date)
        start_time = Column(Date)
        start_hours = Column(Integer)
        start_action = Column(String)
        end_date = Column(Date)
        end_time = Column(Date)
        end_hours = Column(Integer)
        end_action = Column(String)
        duration_minutes = Column(Numeric)
        host = Column(String)
        module = Column(String)
        username = Column(String)
        version = Column(String)
        batch_id = Column(UUID, nullable=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now())

class nx(Base):
        __tablename__ = "session_logs"
        __table_args__ = {"schema": "nx"}
        id = Column(Integer, primary_key=True, autoincrement=True)
        start_date = Column(Date)
        start_time = Column(Time)
        end_date = Column(Date)
        end_time = Column(Time)
        duration_minutes = Column(Numeric(10,2))
        hostname = Column(String)
        module = Column(String)
        username = Column(String)
        
        batch_id = Column(UUID, nullable=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now())

class autoform(Base):
        __tablename__ = "session_logs"
        __table_args__ = {"schema": "autoform"}
        
        id = Column(Integer, primary_key=True, autoincrement=True)
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
        batch_id = Column(UUID, nullable=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now())

class solidwork(Base):
        __tablename__ = "session_logs"
        __table_args__ = {"schema": "solidworks"}
        id = Column(Integer, primary_key=True, autoincrement=True)
        start_date = Column(Date)
        start_time = Column(Time)
        end_date = Column(Date)
        end_time = Column(Time)
        duration_minutes = Column(Numeric(10,2))
        feature = Column(String)
        username = Column(String)
        computer = Column(String)
        batch_id = Column(UUID, nullable=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now())

def raw_logs_table(schema_name: str):
    class RawLogs(Base):
        __tablename__ = "raw_logs"
        __table_args__ = {"schema": schema_name,"extend_existing": True }
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        batch_id = Column(UUID, nullable=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now())
        raw = Column(JSONB)  # PostgreSQL JSONB field

        @classmethod
        def from_pydantic(cls, pyd_model: valid.LicenseInput, batch_id=None):
            return cls(
                batch_id=batch_id,
                raw=pyd_model.data  # ✅ ตรงกับ field ของ LicenseInput
            )

    return RawLogs

#log_entry = rawLogs.from_pydantic(pyd_model, batch_id=share_uuid)

def greet(sqlalchemy_engine_url):
    engine = create_engine(sqlalchemy_engine_url)

    # สร้าง schemas
    with engine.begin() as conn:
        for schema_name in schemas:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
            raw_logs_table(schema_name)     
    #====================================
    # Define tables

    # สร้างทุก table
    Base.metadata.create_all(engine)


