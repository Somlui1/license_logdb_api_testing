from dotenv import load_dotenv
load_dotenv()

from .routers.watchguard import router as watchguard_router
from .routers.server_logs import router as server_logs_router
from .routers.SOS import SOS
from .routers.testing import app
from .routers.thai_karaoke import router as thai_karaoke_router
from .routers.tools import router as tools_router
from .routers.MCP import init_mcp_servers

app.include_router(watchguard_router)
app.include_router(server_logs_router)
app.include_router(SOS)
app.include_router(thai_karaoke_router)
app.include_router(tools_router)

# Initialize all multiple MCP sub-servers dynamically
init_mcp_servers(app)
