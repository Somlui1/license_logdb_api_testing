from pydantic import BaseModel, Field
from typing import List


class ScriptItem(BaseModel):
    """Schema สำหรับข้อมูลของแต่ละ script file"""
    name: str = Field(..., description="ชื่อ script ที่ดึงมาจาก MetaName")
    script: str = Field(..., description="ชื่อไฟล์ script เช่น program.ps1")
    priority: float = Field(..., description="ลำดับความสำคัญจาก MetaPriority")


class ScriptsResponse(BaseModel):
    """Schema สำหรับ response ของ GET /scripts"""
    status: str = Field(default="success", description="สถานะของ request")
    message: str = Field(default="Get all choice successfully", description="ข้อความอธิบาย")
    data: List[ScriptItem] = Field(default_factory=list, description="รายการ script ทั้งหมด")


class ComponentItem(BaseModel):
    """Schema สำหรับข้อมูลของแต่ละ component file"""
    filename: str = Field(..., description="ชื่อไฟล์ component")
    size_bytes: int = Field(..., description="ขนาดไฟล์ (bytes)")


class ComponentsResponse(BaseModel):
    """Schema สำหรับ response ของ GET /cli-tools/component"""
    status: str = Field(default="success", description="สถานะของ request")
    message: str = Field(default="Get all components successfully", description="ข้อความอธิบาย")
    data: List[ComponentItem] = Field(default_factory=list, description="รายการ component ทั้งหมด")
