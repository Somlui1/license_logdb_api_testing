from .routers.watchguard import router as watchguard_router
from .routers.server_logs import router as server_logs_router
from .routers.testing import app

#app = FastAPI()
app.include_router(watchguard_router)
app.include_router(server_logs_router)

