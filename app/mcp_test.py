import fastmcp
import asyncio

async def test():
    mcp = fastmcp.FastMCP('test')
    
    @mcp.tool()
    def my_tool(x: int) -> int:
        """My logic"""
        return x
        
    tools = await mcp.list_tools()
    print([dict(t) if hasattr(t, '__dict__') else str(t) for t in tools])

asyncio.run(test())
