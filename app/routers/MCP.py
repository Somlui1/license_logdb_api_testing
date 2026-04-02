import os
import sys
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Dict, Any, Callable
from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastmcp import FastMCP
from app.mcp_tools.router_core import MCPRouter
# Import different tool categories
from app.mcp_tools.intranet import router as intranet_router
from app.mcp_tools.glpi_server import router as glpi_router

# API Router for exposing MCP testing via Swagger UI
mcp_docs_router = APIRouter(prefix="/mcp", tags=["MCP Management"])

# Registry to hold our tool functions for dynamic execution
tool_registry: Dict[str, Callable] = {}
tool_metadata = []

def register_isolated_mcp_server(app: FastAPI, router: MCPRouter, mount_path: str):
    """Creates a standalone FastMCP server for the given router and mounts it to FastAPI."""
    server_name = f"{router.name} MCP Server"
    server_instance = FastMCP(server_name)
    
    for tool_func in router.tools:
        # 1. Register tool to this specific FastMCP isolated server
        server_instance.tool()(tool_func)
        
        # 2. Store in our internal registry for the dynamic execution endpoint
        tool_registry[tool_func.__name__] = tool_func
        
        tool_metadata.append({
            "category": router.name,
            "name": tool_func.__name__,
            "description": tool_func.__doc__,
            "sse_endpoint": f"{mount_path}/sse"
        })
        
    # Generate the SSE HTTP app
    sse_app = server_instance.http_app(transport="sse")
    # Mount into main FastAPI app endpoint
    app.mount(mount_path, sse_app)



@mcp_docs_router.get("/tools", summary="List all MCP tools across all categories")
def get_all_mcp_tools():
    """Returns a list of all active tools across all isolated MCP servers."""
    return {
        "architecture": "Multi-Server",
        "tools": tool_metadata
    }

@mcp_docs_router.post("/execute/{tool_name}", summary="🛠️ Dynamic Tool Execution")
async def execute_tool_dynamically(tool_name: str, request: Request):
    """
    Execute ANY registered MCP tool by passing its name in the URL.
    
    - **tool_name**: The name of the function (e.g. `get_db_data` or `list_tables`)
    - **Request Body**: Pass arguments as a JSON object (if required by the tool). 
    
    *ตัวอย่าง Body สำหรับฟังก์ชันรับค่า param `table_name`:*
    `{"table_name": "users"}`
    """
    if tool_name not in tool_registry:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found.")
        
    tool_func = tool_registry[tool_name]
    
    try:
        kwargs = await request.json() if await request.body() else {}
    except Exception:
        kwargs = {}
        
    try:
        import inspect
        if inspect.iscoroutinefunction(tool_func):
            result = await tool_func(**kwargs)
        else:
            result = tool_func(**kwargs)
        return {"status": "success", "tool_returned": result}
    except TypeError as e:
        raise HTTPException(status_code=400, detail=f"Argument format error (Did you send the right JSON body?): {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {e}")


@mcp_docs_router.get("/what-is-mcp", summary="📖 What is MCP? (For IT Team)")
def explain_mcp_protocol():
    """
    ## อธิบายการทำงานของ MCP (Model Context Protocol) 🚀
    
    <img src="/mcp-static/MCP_infographic.png" width="800" alt="MCP Infographic" style="border-radius:10px; margin-bottom:20px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"/>
    
    **MCP Server** คือเซิร์ฟเวอร์ที่ทำหน้าที่เป็น 'กระบอกเสียงและเครื่องมือ' ให้กับวงจร AI (เช่น Claude Desktop หรือ AI Agent ตัวอื่นๆ)
    
    **เมื่อ AI (เรียกว่า MCP Client) เชื่อมต่อเข้ามาครั้งแรก มันจะทำกระบวนการดังนี้:**
    1. **Handshake:** เชื่อมต่อผ่าน SSE Endpoint และส่ง POST Message `initialize`
    2. **Discovery:** AI จะส่งคำสั่ง `tools/list` เข้ามา เพื่อถามเซิร์ฟเวอร์ว่า "ที่นี่มีเครื่องมือ (ฟังก์ชัน) อะไรให้ฉันใช้บ้าง?"
    
    ⬇️ **ข้อมูลตรง Response Body ด้านล่างนี้คือ "ภาพจำลองสิ่งที่ MCP Server ตอบกลับ AI"** ⬇️
    เมื่อ AI ได้รับ JSON ก้อนนี้ มันจะนำ `inputSchema` ไปวิเคราะห์ ทำให้มันฉลาดพอที่จะรู้ว่าอ้อต้องดึง DB ยังไง
    """
    
    return {
        "1_client_action": "Client HTTP GET /mcp/sse (รอรับข้อมูลแบบ Stream)",
        "2_client_request": {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        },
        "3_server_response_to_ai": {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": [
                    {
                        "name": "get_db_data",
                        "description": "Retrieve data from the specified database table.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "table_name": {"type": "string", "title": "Table Name"}
                            },
                            "required": ["table_name"]
                        }
                    }
                ]
            }
        },
        "4_next_step": "AI จะเข้าใจแล้วว่ามีกี่เครื่องมือให้เรียกใช้"
    }

@mcp_docs_router.get("/download/claude-config", summary="⬇️ Download Claude Desktop Config")
def download_claude_config():
    """บรรจุไฟล์ config สำหรับแอป Claude ให้โหลดไปใส่ใน %APPDATA%\\Claude"""
    python_path = sys.executable
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    script_path = os.path.join(root_dir, "run_mcp_stdio.py")
    
    config = {
        "mcpServers": {
            "apico-mcp-server": {
                "command": python_path,
                "args": [script_path]
            }
        }
    }
    return JSONResponse(content=config, headers={"Content-Disposition": 'attachment; filename="claude_desktop_config.json"'})

    
def init_mcp_servers(app: FastAPI):
    """Main initialization hook to plug isolated MCP servers into FastAPI."""
    # Mount static files to serve the MCP Infographic for Swagger UI
    component_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "component")
    if os.path.exists(component_dir):
        app.mount("/mcp-static", StaticFiles(directory=component_dir), name="mcp_static")

    # Map each module to its isolated URL path
    # Endpoint SSE will become example: http://127.0.0.1:8000/mcp/glpi/sse
    mcp_modules = [
        # {"router": db_router, "path": "/mcp/db"},
        # {"router": email_router, "path": "/mcp/email"},
        # {"router": intranet_router, "path": "/mcp/intranet"},
        # {"router": ad_router, "path": "/mcp/ad"},
        {"router": glpi_router, "path": "/mcp/glpi"},
    ]

    for module in mcp_modules:
        register_isolated_mcp_server(app, module["router"], module["path"])
    
    # Finally, include the documentation router so Swagger sees the endpoints
    app.include_router(mcp_docs_router)
