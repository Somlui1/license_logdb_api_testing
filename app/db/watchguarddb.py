from sqlalchemy import Text
from sqlalchemy import Boolean
from sqlalchemy import BigInteger,UUID,Column, Integer, String, DateTime, Date, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert # หรือจาก dialect ที่คุณใช้
#Base = declarative_base()

engine_url_watchguard = "postgresql://itsupport:aapico@10.10.3.215:5432/watchguard"
#watchguard.greet(engine_url_watchguard)
engine_watchguard = create_engine(engine_url_watchguard)
Base = declarative_base()
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine_watchguard)
schemas = ["Patch_logs"]

Base = declarative_base()

# ==========================================
# 1. Base Mixins (Utility Classes)
# ==========================================

class DatabaseOperationsMixin:
    """รวมคำสั่งจัดการ Database พื้นฐาน (Create/Truncate)"""

    @classmethod
    def get_table_fullname(cls):
        """คืนค่าชื่อตารางพร้อม Schema (ถ้ามี)"""
        schema = cls.__table_args__.get("schema") if hasattr(cls, "__table_args__") else None
        table = cls.__tablename__
        return f'"{schema}"."{table}"' if schema else f'"{table}"'

    @classmethod
    def truncate(cls, engine=engine_watchguard):
        """สั่งล้างข้อมูลในตาราง"""
        full_name = cls.get_table_fullname()
        with engine.begin() as conn:
            try:
                conn.execute(text(f'TRUNCATE TABLE {full_name} RESTART IDENTITY CASCADE;'))
                print(f"⚰️  Truncated table: {full_name}")
            except SQLAlchemyError as e:
                print(f"❌ Error during truncate {full_name}: {e}")
                raise

    @staticmethod
    def create_schemas_and_tables(base_metadata, schema_list: list[str], engine=engine_watchguard):
        """
        สร้าง Schema และ Table ทั้งหมด 
        (ย้าย engine มาไว้ท้ายสุดเพื่อให้ Syntax ถูกต้อง)
        """
        with engine.begin() as conn:
            for name in schema_list:
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{name}"'))
        base_metadata.create_all(engine)
        print("✅ Schemas and Tables checked/created.")

    @classmethod
    def setup_table(cls, engine=engine_watchguard):
        """สร้าง Schema และ Table ของ Class นี้โดยเฉพาะ"""
        # 1. ตรวจสอบและสร้าง Schema
        if hasattr(cls, "__table_args__") and isinstance(cls.__table_args__, dict):
            schema_name = cls.__table_args__.get("schema")
            if schema_name:
                with engine.begin() as conn:
                    conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
                    print(f"📂 Checked schema: {schema_name}")

        # 2. สร้าง Table
        try:
            cls.__table__.create(bind=engine, checkfirst=True)
            print(f"✅ Table setup complete: {cls.get_table_fullname()}")
        except SQLAlchemyError as e:
            print(f"❌ Error creating table {cls.__tablename__}: {e}")
            raise

class BulkOpsMixin:
    """รวมคำสั่ง Bulk Insert และ Upsert"""
    
    UPSERT_INDEX: list[str] = []

    @staticmethod
    def _chunked(iterable, size):
        """Helper function สำหรับแบ่งข้อมูลเป็นก้อนๆ"""
        for i in range(0, len(iterable), size):
            yield iterable[i:i + size]

    def _bulk_insert_core(self, session, data: list[dict], chunk_size: int = 600) -> int:
        """Logic หลักของ Bulk Insert with On Conflict Do Nothing"""
        if not self.UPSERT_INDEX:
             raise ValueError(f"{self.__class__.__name__}.UPSERT_INDEX is not defined")

        # ดึง Column object จริงๆ จากชื่อ string
        index_cols = [getattr(self.__class__, col) for col in self.UPSERT_INDEX]
        total_inserted = 0

        for batch in self._chunked(data, chunk_size):
            stmt = insert(self.__class__).values(batch)
            stmt = stmt.on_conflict_do_nothing(index_elements=index_cols)
            result = session.execute(stmt)
            total_inserted += result.rowcount or 0
            
        return total_inserted

    def save(self, payload: list[dict], chunk_size: int = 600) -> dict:
        """
        Public method สำหรับเรียกใช้ Upsert
        """
        if not payload:
            return {"success": True, "inserted": 0, "skipped": 0}

        with Session() as session:
            try:
                inserted = self._bulk_insert_core(session, payload, chunk_size)
                session.commit()
                return {
                    "success": True,
                    "inserted": inserted,
                    "skipped": len(payload) - inserted
                }
            except (SQLAlchemyError, ValueError) as e:
                session.rollback()
                return {
                    "success": False,
                    "inserted": 0,
                    "skipped": len(payload),
                    "error": str(e)
                }

    def save_bulk_simple(self, payload: list[dict], chunk_size: int = 5000):
        """
        บันทึกข้อมูลแบบ High Performance (SQLAlchemy Core)
        เร็วกว่าเดิมเพราะไม่สร้าง ORM Object ทีละตัว
        """
        if not payload:
            return {"success": True, "inserted": 0}

        print(f"DEBUG: 🚀 Starting Fast Insert for {len(payload)} rows...")
        total_saved = 0
        
        # 1. เตรียมรายชื่อ Column เพื่อกรองข้อมูล
        valid_columns = set(self.__table__.columns.keys())
        
        # สร้าง Session
        session = Session()
        try:
            # 2. แบ่ง Chunk (เพิ่มขนาดเป็น 5000 เพื่อความเร็ว)
            chunks = list(self._chunked(payload, chunk_size))
            total_chunks = len(chunks)

            for i, batch in enumerate(chunks, 1):
                # 3. กรองข้อมูล (สำคัญมาก: Core Insert ห้ามมี Key เกิน)
                cleaned_batch = []
                for item in batch:
                    # สร้าง dict ใหม่เฉพาะ key ที่ตรงกับ DB
                    clean_item = {k: v for k, v in item.items() if k in valid_columns}
                    cleaned_batch.append(clean_item)

                if cleaned_batch:
                    # 4. 🔥 จุดเปลี่ยนความเร็ว: ใช้ insert() ตรงๆ แทนการสร้าง Object
                    # (ต้อง import insert จาก sqlalchemy.dialects.postgresql หรือ sqlalchemy)
                    stmt = insert(self.__class__).values(cleaned_batch)
                    session.execute(stmt)
                    
                    total_saved += len(cleaned_batch)
                    print(f"   ↳ [Chunk {i}/{total_chunks}] ⚡ Inserted {len(cleaned_batch)} rows")

            # 5. Commit
            session.commit()
            print(f"✅ FAST SUCCESS: Inserted {total_saved} rows.")
            
            return {
                "success": True,
                "inserted": total_saved,
                "skipped": 0
            }

        except Exception as e:
            session.rollback()
            print(f"❌ DB Error: {e}")
            return {
                "success": False, 
                "error": str(e), 
                "inserted": 0
            }
        finally:
            session.close()

# ==========================================
# 2. Models (สืบทอดจาก Base และ Mixins)
# ==========================================

class available_patches_computer(Base, BulkOpsMixin, DatabaseOperationsMixin):
    __tablename__ = "available_patches_computers"
    __table_args__ = {"schema": "Patch_logs"}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    patch = Column(Text, unique=True)
    computers = Column(Integer, nullable=True)
    # ... columns อื่นๆ ...
    criticality = Column(Text, nullable=True)
    cves = Column(Text, nullable=True)
    kb_id = Column(Text, nullable=True)
    platform = Column(Text, nullable=True)
    product_family = Column(Text, nullable=True)
    program = Column(Text, nullable=True)
    program_version = Column(Text, nullable=True)
    version = Column(Text, nullable=True)
    vendor = Column(Text, nullable=True)
    release_date = Column(Date, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    UPSERT_INDEX = ["patch"]


class path_history_by_computer(Base, BulkOpsMixin, DatabaseOperationsMixin):
    __tablename__ = "path_history_by_computers"
    __table_args__ = {"schema": "Patch_logs"}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    Computer = Column(Text, nullable=False, comment="Computer Hostname")
    # ... columns อื่นๆ ...
    Client = Column(Text, comment="Client/Organization name")
    Computer_type = Column(Text, comment="Computer type (Workstation, Laptop)")
    IP_address = Column(Text, comment="IP address (supports IPv4/IPv6)")
    Domain = Column(Text, comment="Domain name")
    Platform = Column(Text, comment="Platform (Windows, macOS)")
    Group = Column(Text, comment="Computer group/OU")
    Date = Column(DateTime, comment="Date/time the alert was generated")
    Program = Column(Text, comment="Name of the program requiring the patch")
    Version = Column(Text, comment="Current version of the program")
    Patch = Column(Text, comment="Recommended patch or update")
    Criticality = Column(Text, comment="Severity level (Important, Unspecified)")
    KB_ID = Column(Text, comment="Related KB/QID number")
    Release_date = Column(DateTime, comment="Patch release date")
    Installation = Column(Text, comment="Installation status (Installed, Not Installed)")
    Installation_error = Column(Text, comment="Error message if installation failed")
    Download_URL = Column(Text, comment="URL for patch download")
    Result_code = Column(Text, comment="Installation result code")
    Description = Column(Text, comment="Additional description (often blank)")
    CVEs = Column(Text, comment="Comma-separated list of affected CVEs")
    KeyHash = Column(Text, unique=True, comment="Unique KeyHash for record identification")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    UPSERT_INDEX = ["KeyHash"]


class AvailablePatch(Base, BulkOpsMixin, DatabaseOperationsMixin):
    __tablename__ = 'available_patches'
    __table_args__ = {"schema": "Patch_logs"}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String, nullable=False, comment="Unique ID of the customer account (UUID)")
    # ... columns อื่นๆ ...
    site_id = Column(String, nullable=False, comment="Unique ID of the site (UUID)")
    site_name = Column(Text, comment="Name of the site/client")
    device_id = Column(String, nullable=False, comment="Unique ID of the device (UUID)")
    host_name = Column(Text, nullable=False, comment="Hostname of the device")
    device_type = Column(Integer, comment="Type code of the device")
    platform_id = Column(Integer, comment="ID for the operating system platform")
    vendor_id = Column(Integer, comment="Vendor ID code")
    family_id = Column(Integer, comment="Patch family ID code")
    version_id = Column(Integer, comment="Patch version ID code")
    vendor_name = Column(Text, comment="Vendor name (e.g., Microsoft, 7-Zip)")
    family_name = Column(Text, comment="Patch family name (e.g., .Net)")
    patch_id = Column(String, nullable=False, comment="Unique ID of the patch (UUID format)")
    patch_name = Column(Text, comment="Full name of the patch")
    program_name = Column(Text, comment="Name of the affected program")
    program_version = Column(Text, comment="Version of the affected program")
    patch_criticality = Column(Integer, comment="Criticality level code")
    patch_type = Column(Integer, comment="Type code of the patch")
    patch_management_status = Column(Integer, comment="Patch management status code")
    custom_group_folder_id = Column(String, comment="ID of the custom group folder (UUID)")
    isolation_state = Column(Integer, comment="Isolation state code")
    license_status = Column(Integer, comment="License status code")
    patch_installation_availability = Column(Integer, comment="Installation availability code")
    patch_release_date = Column(DateTime, comment="Date the patch was released")
    is_downloadable = Column(Boolean, comment="True if the patch is downloadable")
    is_allowed_manual_installation = Column(Boolean, comment="True if manual installation is allowed")
    automatic_reboot = Column(Boolean, comment="True if the patch requires automatic reboot")
    download_url = Column(Text, comment="Full download URL of the patch file")
    local_filename = Column(Text, comment="Local filename of the patch")
    patch_cve_ids = Column(Text, nullable=True, comment="CVE IDs from API")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Override save method เพื่อให้รองรับพฤติกรรมเดิม (Bulk Save แบบไม่มี Upsert Check)
    def save(self, payload: list[dict]):
        return self.save_bulk_simple(payload)

def greet_and_create_tables(sqlalchemy_engine):
    with sqlalchemy_engine.begin() as conn:
        for name in schemas:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{name}"'))


greet_and_create_tables(engine_watchguard)
Base.metadata.create_all(engine_watchguard)
#available_patches_computer.setup_table()
#path_history_by_computer.setup_table()
#AvailablePatch.setup_table()