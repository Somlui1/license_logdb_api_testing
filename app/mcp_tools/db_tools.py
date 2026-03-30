from pydantic import BaseModel
from .router_core import MCPRouter

router = MCPRouter("Database")

class DBResponse(BaseModel):
    data: list
    count: int

@router.tool()
def get_db_data(table_name: str) -> DBResponse:
    """Retrieve data from the specified database table."""
    return DBResponse(data=[{"id": 1, "name": f"Sample from {table_name}"}], count=1)
