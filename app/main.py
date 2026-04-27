from dotenv import load_dotenv
load_dotenv()

from fastapi.middleware.cors import CORSMiddleware
from .routers.watchguard import router as watchguard_router
from .routers.server_logs import router as server_logs_router
from .routers.SOS import SOS
from .routers.testing import app
from .routers.thai_karaoke import router as thai_karaoke_router
from .routers.tools import router as tools_router
from .routers.GLPI import router as glpi_router
from .routers.MCP import init_mcp_servers

app.include_router(watchguard_router)
app.include_router(server_logs_router)
app.include_router(SOS)
app.include_router(thai_karaoke_router)
app.include_router(tools_router)
app.include_router(glpi_router)

# Enable CORS for remote MCP client / bridge connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize all multiple MCP sub-servers dynamically
init_mcp_servers(app)
