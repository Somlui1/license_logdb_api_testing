from sqlalchemy import Text
from sqlalchemy import Boolean
from sqlalchemy import JSON, UUID, BigInteger, Column, Integer, String, DateTime, Date,Float, Time, Numeric, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

#Base = declarative_base()
engine_url_watchguard = "postgresql://itsupport:aapico@10.10.3.215:5432/watchguard"
#watchguard.greet(engine_url_watchguard)
engine_watchguard = create_engine(engine_url_watchguard)
Base = declarative_base()
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine_watchguard)
schemas = ["Patch_logs"]

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

class available_patches_computer(Base):
        __tablename__ = "available_patches_computers"
        __table_args__ = {"schema": "Patch_logs"}
        id = Column(Integer, primary_key=True, autoincrement=True)
        patch = Column(Text,unique=True)
        computers = Column(Integer, nullable=True)
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
        UPSERT_FIELDS = []
        
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


class path_history_by_computer(Base):
    __tablename__ = "path_history_by_computers"
    __table_args__ = {"schema": "Patch_logs"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    Client = Column(Text, nullable=False, comment="Client/Organization name")
    Computer_type = Column(Text, comment="Computer type (Workstation, Laptop)")
    Computer = Column(Text, nullable=False, comment="Computer Hostname")
    IP_address = Column(Text, comment="IP address (supports IPv4/IPv6)")
    Domain = Column(Text, comment="Domain name")
    Platform = Column(Text, comment="Platform (Windows, macOS)")
    Group = Column(Text, comment="Computer group/OU")
    # Patch Alert Details
    Date = Column(DateTime, comment="Date/time the alert was generated") # DateTime is kept
    Program = Column(Text, comment="Name of the program requiring the patch")
    Version = Column(Text, comment="Current version of the program")
    Patch = Column(Text, comment="Recommended patch or update")
    Criticality = Column(Text, comment="Severity level (Important, Unspecified)")
    KB_ID = Column(Text, comment="Related KB/QID number")
    Release_date = Column(DateTime, comment="Patch release date") # DateTime is kept
    # Status Details
    Installation = Column(Text, comment="Installation status (Installed, Not Installed)")
    Installation_error = Column(Text, comment="Error message if installation failed")
    Download_URL = Column(Text, comment="URL for patch download")
    Result_code = Column(Text, comment="Installation result code")
    Description = Column(Text, comment="Additional description (often blank)")
    # Keys and Large Text Fields
    CVEs = Column(Text, comment="Comma-separated list of affected CVEs")
    KeyHash = Column(Text, comment="Unique KeyHash for record identification")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    UPSERT_INDEX = ["KeyHash"]
    UPSERT_FIELDS = []

# Create the Base Class for model declaration
Base = declarative_base()

class AvailablePatch(Base):
    __tablename__ = 'available_patches'
    __table_args__ = {"schema": "Patch_logs"}
    # Primary Key
    id = Column(BigInteger, primary_key=True)  # Use BigInteger for large ID sets
    # 1. Identifiers (Using String(36) for UUIDs)
    account_id = Column(String(36), nullable=False, comment="Unique ID of the customer account (UUID)")
    site_id = Column(String(36), nullable=False, comment="Unique ID of the site (UUID)")
    site_name = Column(Text, comment="Name of the site/client")
    device_id = Column(String(36), nullable=False, comment="Unique ID of the device (UUID)")
    host_name = Column(Text, nullable=False, comment="Hostname of the device")
    # 2. Device & Vendor IDs (Integers for codes)
    device_type = Column(Integer, comment="Type code of the device")
    platform_id = Column(Integer, comment="ID for the operating system platform")
    vendor_id = Column(Integer, comment="Vendor ID code")
    family_id = Column(Integer, comment="Patch family ID code")
    version_id = Column(Integer, comment="Patch version ID code")
    vendor_name = Column(Text, comment="Vendor name (e.g., Microsoft, 7-Zip)")
    family_name = Column(Text, comment="Patch family name (e.g., .Net)")
    # 3. Patch Details
    patch_id = Column(String(36), nullable=False, comment="Unique ID of the patch (UUID format)")
    patch_name = Column(Text, comment="Full name of the patch (e.g., .NET Framework 4.8.1 (KB...))")
    program_name = Column(Text, comment="Name of the affected program")
    program_version = Column(Text, comment="Version of the affected program")
    patch_criticality = Column(Integer, comment="Criticality level code (e.g., 101, 205)")
    patch_type = Column(Integer, comment="Type code of the patch")
    # 4. Status & Dates
    patch_management_status = Column(Integer, comment="Patch management status code")
    custom_group_folder_id = Column(String(36), comment="ID of the custom group folder (UUID)")
    isolation_state = Column(Integer, comment="Isolation state code")
    license_status = Column(Integer, comment="License status code")
    patch_installation_availability = Column(Integer, comment="Installation availability code")
    patch_release_date = Column(DateTime, comment="Date the patch was released") # Used DateTime
    # 5. Booleans (True/False flags)
    is_downloadable = Column(Boolean, comment="True if the patch is downloadable")
    is_allowed_manual_installation = Column(Boolean, comment="True if manual installation is allowed")
    automatic_reboot = Column(Boolean, comment="True if the patch requires automatic reboot")
    # 6. File Paths/URLs (Large Text)
    download_url = Column(Text, comment="Full download URL of the patch file")
    local_filename = Column(Text, comment="Local filename of the patch")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

def greet_and_create_tables(sqlalchemy_engine):
    with sqlalchemy_engine.begin() as conn:
        for name in schemas:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{name}"'))
    Base.metadata.create_all(sqlalchemy_engine)

greet_and_create_tables(engine_watchguard)
#log_entry = rawLogs.from_pydantic(pyd_model, batch_id=share_uuid)
#def greet(sqlalchemy_engine_url):
#    engine = create_engine(sqlalchemy_engine_url)
#
#    # สร้าง schemas
#    with engine.begin() as conn:
#        for name in schemas:
#            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{name}"'))
#            raw_logs_table(schema_name=name)
#            raw_logs_table(schema_name=name,table_name='raw_logs')
#            
#    #====================================
#    # Define tables
#    # สร้างทุก table
#    Base.metadata.create_all(engine)

#greet(engine_url_watchguard)
Base.metadata.create_all(engine_watchguard)
