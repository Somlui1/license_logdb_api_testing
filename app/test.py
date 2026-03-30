from dotenv import load_dotenv
load_dotenv()
from .routers.testing import app
from .routers.MCP import init_mcp_servers

# Initialize all multiple MCP sub-servers dynamically
init_mcp_servers(app)
