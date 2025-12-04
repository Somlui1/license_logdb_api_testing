from fastapi import FastAPI,Request
from .routers.watchguard import router as watchguard_router
from .routers.server_logs import router as server_logs_router
from .routers.testing import app
from urllib.parse import urlencode
#app = FastAPI()
app.include_router(watchguard_router)
app.include_router(server_logs_router)

@app.get("/")
def home(request: Request, Query_parameter: str | None = None):
    
    query_string = urlencode(request.query_params)
    if Query_parameter:
        return {"Query_parameter": Query_parameter}
    
    return {"uery_string": query_string}

