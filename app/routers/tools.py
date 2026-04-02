import re
import logging
from pathlib import Path
from typing import Optional
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.responses import HTMLResponse
from ..schema.tools_validate import ScriptItem, ScriptsResponse, ComponentItem, ComponentsResponse
from jinja2 import Environment, FileSystemLoader
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/tools",
    tags=["tools"],
)
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "component")
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "tools" / "choice"
COMPONENT_DIR = Path(__file__).resolve().parent.parent / "tools" / "component"
INSTALL_SCRIPT = Path(__file__).resolve().parent.parent / "tools" / "install.ps1"

# นามสกุลไฟล์ที่อนุญาต (เพิ่มเติมได้ในอนาคต)
ALLOWED_EXTENSIONS: set[str] = {".ps1", ".cmd", ".bat", ".py", ".js"}

MAX_HEADER_LINES = 10  # อ่านแค่ 10 บรรทัดแรกเพื่อ performance

# Regex patterns สำหรับ parse metadata
_RE_META_NAME = re.compile(r"^#\s*MetaName:\s*(.+)$", re.IGNORECASE)
_RE_META_PRIORITY = re.compile(r"^#\s*MetaPriority:\s*([\d.]+)$", re.IGNORECASE)


# ─────────────────────────────────────────────
# Helper: parse metadata จาก header ของไฟล์
# ─────────────────────────────────────────────
def parse_metadata(filepath: Path) -> dict:
    """
    เปิดอ่านเฉพาะ 10 บรรทัดแรกของไฟล์ เพื่อดึง MetaName และ MetaPriority
    ผ่าน Regex โดยไม่อ่านทั้งไฟล์ เพื่อ performance ที่ดี
    """
    name: Optional[str] = None
    priority: float = 999.0  # default priority สูง (ท้ายรายการ) ถ้าไม่มี metadata

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for _ in range(MAX_HEADER_LINES):
                line = f.readline()
                if not line:
                    break

                line = line.strip()

                if name is None:
                    match = _RE_META_NAME.match(line)
                    if match:
                        name = match.group(1).strip()

                if priority == 999.0:
                    match = _RE_META_PRIORITY.match(line)
                    if match:
                        try:
                            priority = float(match.group(1))
                        except ValueError:
                            pass

                # หยุดเร็วถ้าเจอครบแล้ว
                if name is not None and priority != 999.0:
                    break

    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("Cannot read metadata from %s: %s", filepath.name, exc)

    return {
        "name": name or filepath.stem,  # fallback ใช้ชื่อไฟล์ (ไม่มี extension)
        "priority": priority,
    }


# ─────────────────────────────────────────────
# Helper: resolve path อย่างปลอดภัย
# ─────────────────────────────────────────────
def _safe_resolve(filename: str, base_dir: Path = SCRIPTS_DIR) -> Path:
    """
    Resolve filepath พร้อมป้องกัน directory traversal attack
    Raise HTTPException ถ้าไม่ปลอดภัยหรือไม่พบไฟล์
    """
    # ป้องกัน path traversal เบื้องต้น
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = base_dir / filename

    try:
        resolved = file_path.resolve(strict=False)
        scripts_resolved = base_dir.resolve(strict=False)

        if not str(resolved).startswith(str(scripts_resolved)):
            raise HTTPException(status_code=403, detail="Access denied")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"File '{filename}' not found",
        )

    return resolved


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

# ---------- Bootstrapper Install Script ----------
_INSTALL_DESCRIPTION = """
## 🚀 Quick Install via PowerShell

เปิด **PowerShell** (แนะนำ Run as Administrator) แล้วรันคำสั่ง:

```powershell
irm http://10.10.3.215:8181/tools/cli-tools/install.ps1 | iex
```

> เปลี่ยน `<your-server>` เป็น hostname หรือ IP ของ server จริง เช่น `10.10.3.215:8000`

---

### 📋 ขั้นตอนการทำงาน
| ลำดับ | ขั้นตอน | รายละเอียด |
|:---:|---|---|
| 1 | ดาวน์โหลด Installer | โหลด script เข้า memory ผ่าน `irm` |
| 2 | สร้าง Workspace | สร้างโฟลเดอร์ `%TEMP%\\itsupport_tools\\` |
| 3 | ดึงรายการ Tools | เรียก API เพื่อดูรายการ tool ที่มี |
| 4 | เลือก Tools | แสดงเมนู interactive ให้เลือก |
| 5 | ติดตั้ง | ดาวน์โหลดและรัน script ตามลำดับ priority |
| 6 | สรุปผล | แสดง report ผลการติดตั้ง |

---

### ⚠️ ข้อกำหนด
- **PowerShell 5.1+** (Windows 10/11 มีมาให้แล้ว)
- **สิทธิ์ Administrator** — ถ้า script ที่เลือกต้องแก้ไข system settings
- **เครือข่าย** — ต้องเข้าถึง API server ได้

### 🔗 API ที่เกี่ยวข้อง
- `GET /tools/cli-tools/choice` — ดูรายการ choice scripts ทั้งหมด
- `GET /tools/cli-tools/choice/download/{filename}` — ดาวน์โหลด choice script
- `GET /tools/cli-tools/component` — ดูรายการ components
- `GET /tools/cli-tools/component/download/{filename}` — ดาวน์โหลด component
"""


@router.get(
    "/cli-tools/install.ps1",
    summary="🚀 IT Support Tools Bootstrapper — irm | iex",
    description=_INSTALL_DESCRIPTION,
    response_class=PlainTextResponse,
    responses={
        200: {
            "description": "PowerShell installer script (text/plain)",
            "content": {"text/plain": {"example": "# IT Support Tools Bootstrapper Installer v2.0.0\n..."}},
        },
        404: {"description": "install.ps1 not found on server"},
    },
)
async def get_install_script():
    """
    ส่งคืน install.ps1 เป็น plain text สำหรับ ``irm | iex``

    Response จะเป็น ``text/plain; charset=utf-8`` เพื่อให้ PowerShell
    สามารถรับ script content แล้วส่งต่อไปยัง ``Invoke-Expression`` ได้ทันที
    """
    if not INSTALL_SCRIPT.exists():
        raise HTTPException(
            status_code=404,
            detail="install.ps1 not found on server",
        )

    content = INSTALL_SCRIPT.read_text(encoding="utf-8")
    return PlainTextResponse(content=content, media_type="text/plain; charset=utf-8")

@router.get(
    "/cli-tools/choice",
    response_model=ScriptsResponse,
    summary="List all available scripts with metadata",
    description=(
        "สแกนไฟล์ทั้งหมดในโฟลเดอร์ tools/choice ที่ลงท้ายด้วยนามสกุลที่รองรับ "
        "(.ps1, .cmd, .bat, .py, .js) แล้วดึง Metadata จาก header ของไฟล์"
    ),
)
async def get_scripts() -> ScriptsResponse:
    """
    ดึงรายการ script ทั้งหมดพร้อม metadata
    - อ่านเฉพาะ 10 บรรทัดแรกของแต่ละไฟล์
    - เรียงลำดับตาม priority จากน้อยไปมาก
    """
    if not SCRIPTS_DIR.exists():
        return ScriptsResponse()

    items: list[ScriptItem] = []

    for file_path in SCRIPTS_DIR.iterdir():
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue

        meta = parse_metadata(file_path)
        items.append(
            ScriptItem(
                name=meta["name"],
                script=file_path.name,
                priority=meta["priority"],
            )
        )

    # Sort ตาม priority จากน้อยไปมาก
    items.sort(key=lambda item: item.priority)

    return ScriptsResponse(
        status="success",
        message="Get all choice successfully",
        data=items,
    )


@router.get(
    "/cli-tools/choice/download/{filename:path}",
    summary="Download a script file",
    description=(
        "ดาวน์โหลดไฟล์ script จากโฟลเดอร์ tools/choice "
        "รองรับนามสกุล .ps1, .cmd, .bat, .py, .js"
    ),
    response_class=FileResponse,
    responses={
        404: {"description": "File not found"},
        400: {"description": "Invalid filename"},
        403: {"description": "Access denied"},
    },
)
async def download_script(filename: str):
    """
    ดาวน์โหลดไฟล์ script ตามชื่อไฟล์ที่ระบุ
    - ตรวจสอบ directory traversal
    - ตรวจสอบว่าไฟล์มีอยู่จริง
    - ส่ง FileResponse พร้อม filename header
    """
    resolved_path = _safe_resolve(filename, SCRIPTS_DIR)

    return FileResponse(
        path=str(resolved_path),
        filename=filename,
        media_type="application/octet-stream",
        headers={
            "Cache-Control": "no-cache",
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get(
    "/cli-tools/component",
    response_model=ComponentsResponse,
    summary="List all available components",
    description="สแกนไฟล์ทั้งหมดในโฟลเดอร์ tools/component ที่สามารถดาวน์โหลดได้",
)
async def list_components() -> ComponentsResponse:
    """
    ดึงรายการ component ทั้งหมดพร้อมขนาดไฟล์
    """
    if not COMPONENT_DIR.exists():
        return ComponentsResponse()

    items: list[ComponentItem] = []

    for file_path in COMPONENT_DIR.iterdir():
        if not file_path.is_file():
            continue
        items.append(
            ComponentItem(
                filename=file_path.name,
                size_bytes=file_path.stat().st_size,
            )
        )

    items.sort(key=lambda item: item.filename)

    return ComponentsResponse(
        status="success",
        message="Get all components successfully",
        data=items,
    )


@router.get(
    "/cli-tools/component/download/{filename:path}",
    summary="Download a component file",
    description=(
        "ดาวน์โหลดไฟล์ component จากโฟลเดอร์ tools/component "
        "เช่น fast_downloader.exe หรือ utility อื่นๆ"
    ),
    response_class=FileResponse,
    responses={
        404: {"description": "File not found"},
        400: {"description": "Invalid filename"},
        403: {"description": "Access denied"},
    },
)
async def download_component(filename: str):
    """
    ดาวน์โหลดไฟล์ component ตามชื่อไฟล์ที่ระบุ
    - ตรวจสอบ directory traversal
    - ตรวจสอบว่าไฟล์มีอยู่จริง
    - ส่ง FileResponse พร้อม filename header
    """
    resolved_path = _safe_resolve(filename, COMPONENT_DIR)

    return FileResponse(
        path=str(resolved_path),
        filename=filename,
        media_type="application/octet-stream",
        headers={
            "Cache-Control": "no-cache",
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/kaizen/preview", response_class=HTMLResponse)
async def generate_ticket_preview():
    """
    หน้า Form สำหรับทดสอบ generate-ticket
    - วาง JSON → กด Generate → เปิด HTML ใน Tab ใหม่
    """
    try:
        template = jinja_env.get_template("kaizen_application.html")
        html_content = template.render()
        return HTMLResponse(content=html_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template render error: {str(e)}")
