import sys
import os
import asyncio
import httpx
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

# URL defaults to the central master endpoint we just created
SERVER_URL = os.getenv("MCP_SERVER_URL", "https://127.0.0.1:8000/mcp/sse")

async def main():
    """
    Bridge Mode: Connects to a remote SSE MCP Server and bridges it to Stdio.
    Useful for Claude Desktop or ADK Agent to talk to a FastAPI/FastMCP backend.
    """
    try:
        # Check if we are using HTTPS and if we should ignore cert verification (local dev)
        verify_ssl = os.getenv("MCP_VERIFY_SSL", "false").lower() == "true"
        
        if not verify_ssl and SERVER_URL.startswith("https"):
            print("Warning: SSL verification is disabled for bridge.", file=sys.stderr)

        # Standard httpx client to handle SSL settings
        async with httpx.AsyncClient(verify=verify_ssl) as http_client:
            print(f"Connecting to remote MCP server: {SERVER_URL}", file=sys.stderr)
            
            # SSE Client via our custom http_client
            async with sse_client(SERVER_URL, sse_read_timeout=60, sse_headers={}) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    
                    print(f"Connected! Bridge is active for {SERVER_URL}", file=sys.stderr)
                    
                    import mcp.server.stdio as stdio_server
                    await stdio_server.run(session)
                
    except httpx.HTTPStatusError as e:
        print(f"Error: Server returned status {e.response.status_code} at {SERVER_URL}", file=sys.stderr)
        if e.response.status_code == 404:
            print("Hint: Check if the endpoint path (e.g. /mcp/sse) matches your FastAPI mount.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Bridge Error: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # Fix for Windows ProactorEventLoop issues with pipes/anyio if needed
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(main())
