from pydantic import BaseModel
from .router_core import MCPRouter

# Set up a router for the 'system' category
router = MCPRouter("System")

class SystemStatus(BaseModel):
    status: str
    uptime_seconds: int

@router.tool()
def get_system_status() -> SystemStatus:
    """Get the current system status and uptime."""
    return SystemStatus(status="OK", uptime_seconds=3600)

@router.tool()
def echo_message(message: str) -> str:
    """Echo a given message back to the user."""
    return f"You said: {message}"
