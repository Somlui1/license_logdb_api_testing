from sqlalchemy import UUID, Column, Integer, String, DateTime, Date,Float,Boolean,Time, Numeric, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
import decimal
import datetime
import uuid
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine_url_log_server = "postgresql://itsupport:aapico@10.10.3.215:5434/server_logs"
#license_logsdb.greet(engine_url_log_server)
engine_log_server = create_engine(engine_url_log_server)
Base = declarative_base()
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine_log_server)
schemas = ["ibm_spectrum","veeam"]

def greet(sqlalchemy_engine_url):
    engine = create_engine(sqlalchemy_engine_url)
    # สร้าง schemas
    with engine.begin() as conn:
        for schema_name in schemas:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))

greet(engine_url_log_server)

class ibm_spectrum(Base):
        __tablename__ = "remotereplication" # ตั้งชื่อ table ตามต้องการ
        __table_args__ = {"schema": "ibm_spectrum"}
        id = Column(Integer, primary_key=True)
        object_id = Column(Integer)
        consistency_group = Column(String)
        name = Column(String)
        source_target_host = Column(String)
        source_target_pool = Column(String)
        source_target_storage = Column(String)
        source_target_tier = Column(String)
        source_target_volume = Column(String)
        status = Column(String)
        type = Column(String) 
        batch_id = Column(UUID, nullable=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now())

Base.metadata.create_all(engine_log_server)



#class veeam_BackupJob(Base):
#    __tablename__ = "backup_jobs"
#    __table_args__ = {"schema": "veeam"}
#    id = Column(Integer, primary_key=True, autoincrement=True)
#    backup_job = Column(String(255), nullable=False)
#    server = Column(String(100), nullable=False)
#    start_time = Column(DateTime, nullable=True)
#    end_time = Column(DateTime, nullable=True)
#    duration = Column(Float, nullable=True)  # นาทีหรือชั่วโมง
#    status = Column(String(50), nullable=True)
#    progress = Column(String(50), nullable=True)
#    info = Column(String(255), nullable=True)
#    encrypted = Column(Boolean, nullable=True)
#    transfered_size = Column(Float, nullable=True)  # GB
#    percents = Column(Integer, nullable=True)