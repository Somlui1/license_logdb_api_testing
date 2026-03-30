from pydantic import BaseModel
from .router_core import MCPRouter

router = MCPRouter("Email")

@router.tool()
def sending_email(to: str, subject: str, body: str) -> str:
    """Send an email to a user."""
    return f"Email successfully sent to '{to}' with subject: '{subject}'"
