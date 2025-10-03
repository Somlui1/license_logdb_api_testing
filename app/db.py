from sqlalchemy import UUID, Column, Integer, String, DateTime, Date,Float, Time, Numeric, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app import validate 
import decimal
import datetime
import uuid

Base = declarative_base()
schemas = ["autoform", "nx", "catia", "solidworks", "autodesk", "testing"]
#class autodesk(Base):
#        __tablename__ = "session_logs" # ตั้งชื่อ table ตามต้องการ
#        __table_args__ = {"schema": "autodesk"}
#        id = Column(Integer, primary_key=True)
#        start_date = Column(Date)
#        start_time = Column(Date)
#        start_hours = Column(Integer)
#        start_action = Column(String)
#        end_date = Column(Date)
#        end_time = Column(Date)
#        end_hours = Column(Integer)
#        end_action = Column(String)
#        duration_minutes = Column(Numeric)
#        host = Column(String)
#        module = Column(String)
#        username = Column(String)
#        version = Column(String)
#        batch_id = Column(UUID, nullable=True)
#        created_at = Column(DateTime(timezone=True), server_default=func.now())

class CatiaBase(Base):
    __abstract__ = True   # บอก SQLAlchemy ว่านี่คือ base class ไม่ต้องสร้าง table
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String)
    hostname = Column(String)
    start_action = Column(String)
    start_datetime = Column(DateTime)
    end_datetime = Column(DateTime)
    duration_min = Column(Float)
    end_action = Column(String)
    product = Column(String)
    customer = Column(String)
    license_type = Column(String)
    count = Column(Integer)
    level = Column(String)
    hash_id = Column(String, unique=True)
    batch_id = Column(UUID, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    UPSERT_INDEX = ["hash_id"]
    UPSERT_FIELDS = [
        "username", "hostname", "start_action", "start_datetime", "end_datetime",
        "duration_min", "end_action", "product", "customer", "license_type",
        "count", "level", "hash_id", "batch_id"
    ]


class AA_catia(CatiaBase):
    __tablename__ = "AA_session_logs"
    __table_args__ = {"schema": "catia"}


class AHA_catia(CatiaBase):
    __tablename__ = "AHA_session_logs"
    __table_args__ = {"schema": "catia"}


class nx(Base):
        __tablename__ = "session_logs"
        __table_args__ = {"schema": "nx"}
        id = Column(Integer, primary_key=True, autoincrement=True)
        start_datetime = Column(DateTime)
        start_action = Column(String)
        end_datetime = Column(DateTime)
        end_action = Column(String)   
        duration_minutes = Column(Numeric(10,2))
        hostname = Column(String)
        module = Column(String)
        username = Column(String)       
        hash_id = Column(String,unique=True)
        batch_id = Column(UUID, nullable=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now())
        UPSERT_INDEX = ["hash_id"]
        UPSERT_FIELDS = [
        "start_datetime", "start_action", "end_datetime", "end_action",
        "duration_minutes", "hostname", "module", "username", "batch_id"
    ]
#     
#class solidwork(Base):
#        __tablename__ = "session_logs"
#        __table_args__ = {"schema": "solidworks"}
#        id = Column(Integer, primary_key=True, autoincrement=True)
#        start_date = Column(Date)
#        start_time = Column(Time)
#        end_date = Column(Date)
#        end_time = Column(Time)
#        duration_minutes = Column(Numeric(10,2))
#        feature = Column(String)
#        username = Column(String)
#        computer = Column(String)
#        batch_id = Column(UUID, nullable=True)
#        created_at = Column(DateTime(timezone=True), server_default=func.now())

class autoform(Base):
        __tablename__ = "session_logs"
        __table_args__ = {"schema": "autoform"}
        id = Column(Integer,autoincrement=True,primary_key=True)
        start_datetime = Column(DateTime)
        start_action = Column(String)
        end_datetime = Column(DateTime)
        end_action = Column(String)
        duration_minutes = Column(Numeric(10,2))
        host = Column(String)
        module = Column(String)
        username = Column(String)
        version = Column(String)
        hash    =Column( String)
        hash_id = Column(String,unique=True)
        #keyword = Column(String,unique=True)
        batch_id = Column(UUID, nullable=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now())

        UPSERT_INDEX = ["hash_id"]
        UPSERT_FIELDS = [
        "start_datetime", "start_action", "end_datetime", "end_action",
        "duration_minutes", "host", "module", "username", "version",
        "batch_id"
    ]
        
        def to_dict(self):
                d = self.__dict__.copy()
                d.pop('_sa_instance_state', None)  # เอา attribute internal ออก

                # แปลงข้อมูลประเภทพิเศษให้อยู่ในรูป JSON friendly
                for key, value in d.items():
                    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
                        d[key] = value.isoformat()
                    elif isinstance(value, decimal.Decimal):
                        d[key] = float(value)
                    elif isinstance(value, uuid.UUID):
                        d[key] = str(value)
                return d
        

def raw_logs_table(schema_name: str):
    class RawLogs(Base):
        __tablename__ = "raw_logs"
        __table_args__ = {"schema": schema_name,"extend_existing": True }
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        batch_id = Column(UUID, nullable=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now())
        raw = Column(JSONB)  # PostgreSQL JSONB field

        @classmethod
        def from_pydantic(cls, pyd_model: validate.LicenseInput, batch_id=None):
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


