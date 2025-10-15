from sqlalchemy import UUID, Column, Integer, String, DateTime,BigInteger,Date,Float, Time, Numeric, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
#from license_logsdb import chunked, bulk_upsert


engine_url_log_server = "postgresql://itsupport:aapico@10.10.3.215:5432/server_logs"
#license_logsdb.greet(engine_url_log_server)
engine_log_server = create_engine(engine_url_log_server)
Base = declarative_base()
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine_log_server)
schemas = ["ibm_spectrum","veeam"]

def chunked(iterable, size):
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]

def bulk_upsert(session, orm_class, data: list[dict], chunk_size: int = 600):
    for batch in chunked(data, chunk_size):
        stmt = insert(orm_class).values(batch)
        set_dict = {field: stmt.excluded[field] for field in orm_class.UPSERT_FIELDS}
        stmt = stmt.on_conflict_do_update(
            index_elements=orm_class.UPSERT_INDEX,
            set_=set_dict
        )
        session.execute(stmt)
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
        
        UPSERT_INDEX = ["id"]  # หรือ column ที่ unique จริง
        UPSERT_FIELDS = [
            "object_id", "consistency_group", "name", "source_target_host",
            "source_target_pool", "source_target_storage", "source_target_tier",
            "source_target_volume", "status", "type", "batch_id"
        ]
    
        def save(self, payload: list[dict]):
            """บันทึกข้อมูลแบบ bulk upsert"""
            with Session() as session:
                try:
                    session.bulk_save_objects([self(**data) for data in payload])
                    session.commit()
                except SQLAlchemyError as e:
                    session.rollback()
                
class veeambackupjob(Base):
        __tablename__ = "backup_jobs"
        __table_args__ = {"schema": "veeam"}
        id = Column(Integer, primary_key=True, autoincrement=True)
        # ข้อมูลหลัก
        veeamserver = Column(String)
        backupjob = Column(String)
        server = Column(String)
        starttime = Column(DateTime)       
        endtime = Column(DateTime)
        duration = Column(String)
        status = Column(String)
        progress = Column(Float)            
        info = Column(String)
        encrypted = Column(String)
        transferedsize = Column(Float)
        transferedsize_byte = Column(BigInteger)       
        percents = Column(Float)
        # ข้อมูลเชิงตัวเลข
        totalobjects = Column(Integer)
        processedsize = Column(BigInteger)       
        processedusedsize = Column(BigInteger)
        readsize = Column(BigInteger)
        readedaveragesize = Column(BigInteger)
        # เวลาที่เกี่ยวข้อง
        starttimelocal = Column(DateTime)
        stoptimelocal = Column(DateTime)
        starttimeutc = Column(DateTime)
        stoptimeutc = Column(DateTime)
        # ข้อมูลเชิง performance
        avgspeed = Column(BigInteger)             
        totalsize = Column(BigInteger)
        totalusedsize = Column(BigInteger)
        usedspaceration = Column(Float)
        totalsizedelta = Column(BigInteger)
        totalusedsizedelta = Column(BigInteger)
        
        hash_id = Column(String,unique=True)
        batch_id = Column(UUID, nullable=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now())
        UPSERT_INDEX = ["hash_id"]  # column ที่ unique จริง
        UPSERT_FIELDS = [
        "backupjob", "server", "starttime", "endtime", "duration", "status", 
        "progress", "info", "encrypted", "transferedsize", "transferedsize_byte", 
        "percents", "totalobjects", "processedsize", "processedusedsize", "readsize", 
        "readedaveragesize", "starttimelocal", "stoptimelocal", "starttimeutc", 
        "stoptimeutc", "avgspeed", "totalsize", "totalusedsize", "usedspaceration", 
        "totalsizedelta", "totalusedsizedelta", "batch_id"
    ]
        def save(self, payload: list[dict]):
               """บันทึกข้อมูลแบบ bulk upsert"""
               with Session() as session:
                   try:
                       bulk_upsert(session, self.__class__, payload, chunk_size=600)
                       session.commit()
                       print("✅ Data upsert successfully")
                   except SQLAlchemyError as e:
                       session.rollback()
                       print(f"❌ Error during upsert: {e}")       



Base.metadata.create_all(engine_log_server)
#class veeam_BackupJob(Base):
#    __tablename__ = "backup_jobs"
#    __table_args__ = {"schema": "veeam"}
#    id = Column(Integer, primary_key=True, autoincrement=True)
#    backup_job = Column(String)
#    server = Column(String)
#    start_time = Column(DateTime, nullable=True)
#    end_time = Column(DateTime, nullable=True)
#    duration = Column(Float, nullable=True)  # นาทีหรือชั่วโมง
#    status = Column(String)
#    progress = Column(String)
#    info = Column(String)
#    encrypted = Column(Boolean, nullable=True)
#    transfered_size = Column(Float, nullable=True)  # GB
#    percents = Column(Integer, nullable=True)