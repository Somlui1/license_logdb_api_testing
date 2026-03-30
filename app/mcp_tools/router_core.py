from typing import Callable, List

class MCPRouter:
    """
    A router for organizing MCP tools into specific categories or modules.
    Similar in concept to FastAPI's APIRouter.
    """
    def __init__(self, name: str):
        self.name = name
        self.tools: List[Callable] = []

    def tool(self):
        """
        Decorator to register a function as an MCP tool.
        
        Example:
            router = MCPRouter("Math")
            
            @router.tool()
            def add(a: int, b: int) -> int:
                '''Add two numbers'''
                return a + b
        """
        def decorator(func: Callable) -> Callable:
            self.tools.append(func)
            return func
        return decorator
