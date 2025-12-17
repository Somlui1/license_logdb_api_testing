from pydantic import BaseModel, Field
from typing import Optional, Any, List
from datetime import date, time, datetime
from decimal import Decimal



class LicenseInput(BaseModel):
    host    : int                                 
    table   : str                             
    data    : List[Any]                         
    base64  : Optional[List[Any]] = None      
    
    class Config:
        extra = "ignore"  

class available_patches_computer(BaseModel):
    patch: str = Field(..., min_length=1)
    computers: Optional[int] = Field(None, ge=0)
    criticality: Optional[str] = None
    cves: Optional[str] = None
    kb_id: Optional[str] = None
    platform: Optional[str] = None
    product_family: Optional[str] = None
    program: Optional[str] = None
    program_version: Optional[str] = None
    version: Optional[str] = None
    vendor: Optional[str] = None
    release_date: Optional[date] = None

    class Config:
        from_attributes = True   # ใช้กับ ORM ได
        extra = "ignore"


class path_history_by_computer(BaseModel):
    Client: Optional[str] = None
    Computer_type: Optional[str] = None
    Computer: str = Field(..., min_length=1)
    IP_address: Optional[str] = None
    Domain: Optional[str] = None
    Platform: Optional[str] = None
    Group: Optional[str] = None

    # Patch alert details
    Date: Optional[datetime] = None
    Program: Optional[str] = None
    Version: Optional[str] = None
    Patch: Optional[str] = None
    Criticality: Optional[str] = None
    KB_ID: Optional[str] = None
    Release_date: Optional[datetime] = None

    # Status details
    Installation: Optional[str] = None
    Installation_error: Optional[str] = None
    Download_URL: Optional[Any] = None
    Result_code: Optional[str] = None
    Description: Optional[str] = None

    # Keys
    CVEs: Optional[str] = None
    KeyHash: str = Field(..., min_length=10)

    class Config:
        from_attributes = True   # ใช้กับ ORM ได
        extra = "ignore"


class AvailablePatch(BaseModel):
    # Identifiers
    id: int
    account_id: str
    site_id: str
    site_name: Optional[str] = None
    device_id: str
    host_name: str

    # Device & vendor IDs
    device_type: Optional[int] = None
    platform_id: Optional[int] = None
    vendor_id: Optional[int] = None
    family_id: Optional[int] = None
    version_id: Optional[int] = None
    vendor_name: Optional[str] = None
    family_name: Optional[str] = None

    # Patch details
    patch_id: str
    patch_name: Optional[str] = None
    program_name: Optional[str] = None
    program_version: Optional[str] = None
    patch_criticality: Optional[int] = None
    patch_type: Optional[int] = None

    # Status & dates
    patch_management_status: Optional[int] = None
    custom_group_folder_id: Optional[str] = None
    isolation_state: Optional[int] = None
    license_status: Optional[int] = None
    patch_installation_availability: Optional[int] = None
    patch_release_date: Optional[datetime] = None

    # Booleans
    is_downloadable: Optional[bool] = None
    is_allowed_manual_installation: Optional[bool] = None
    automatic_reboot: Optional[bool] = None

    # Paths / URLs
    download_url: Optional[Any] = None
    local_filename: Optional[str] = None

    class Config:
        from_attributes = True   # ใช้กับ ORM ได
        extra = "ignore"
