from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
from app.service.GLPI_service import get_devices_by_tenant

router = APIRouter(prefix="/glpi", tags=["GLPI Computers"])

@router.get("/computers", summary="Get GLPI Computers by Tenant/Name")
def read_computers(
    name: Optional[str] = Query(None, description="Filter by computer name (partial match)"), 
    boolean: Optional[bool] = Query(None, description="Return existence check (true/false) instead of data")
):
    """
    Fetch computer devices from the GLPI database.
    - **name**: Search by computer name.
    - **boolean**: If true, returns whether any device exists matching the criteria.
    """
    return get_devices_by_tenant(name=name, boolean=boolean)
