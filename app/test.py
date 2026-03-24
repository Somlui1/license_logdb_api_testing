from dotenv import load_dotenv
load_dotenv()
from .routers.tools import router as tools_router
from fastapi import FastAPI

app = FastAPI()
app.include_router(tools_router)
