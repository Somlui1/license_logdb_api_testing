from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter(
    prefix="/download",
    tags=["download"]
)

# Base directory for downloadable scripts
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


@router.get(
    "/program.ps1",
    summary="Download program.ps1",
    description="Download the program.ps1 PowerShell script",
    response_class=FileResponse,
)
async def download_program_ps1():
    file_path = SCRIPTS_DIR / "program.ps1"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="program.ps1 not found")

    return FileResponse(
        path=str(file_path),
        filename="program.ps1",
        media_type="application/octet-stream",
    )
