import sys
import os
import asyncio
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

# URL ของเซิร์ฟเวอร์ FastAPI (แก้เป็น IP เครื่องเซิร์ฟเวอร์องค์กรของคุณ)
SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp/sse")

# ใส่ Auth headers ถ้ามีการทำ Authentication
HEADERS = {
    # "Authorization": "Bearer your-token-here"
}

async def main():
    """
    Bridge Mode: รับค่าผ่าน stdio จาก Claude 
    และ Forward ยิงไปยัง Remote FastAPI MCR Server
    """
    try:
        # เปิด Connection แบบ SSE กับเซิร์ฟเวอร์หลัก (FastAPI)
        async with sse_client(SERVER_URL, headers=HEADERS) as (read_stream, write_stream):
            # ผูกสายระหว่างหน้าบ้านกับ Client session 
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                print(f"Connected to remote server at {SERVER_URL}", file=sys.stderr)
                
                # ปกติถ้าใช้ไลบรารีภายนอกเช่น mcp-proxy มักจะมีความสามารถ pipe อัตโนมัติ. 
                # (หากพบว่าบรรทัดล่างไม่ทำงานเนื่องจาก SDK เวอร์ชั่นไม่ตรง ให้ติดตั้งและใช้ mcp-proxy แทนตามวิธีที่ 1)
                import mcp.server.stdio as stdio_server
                await stdio_server.run(session)
                
    except Exception as e:
        print(f"Error bridging to remote server: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
