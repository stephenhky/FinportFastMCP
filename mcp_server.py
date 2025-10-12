
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse


# Create a basic server instance
mcp = FastMCP(name="Financial Calculator MCP Server")


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    """
    Health check for the MCP server.
    """
    return PlainTextResponse("OK")


@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"


if __name__ == "__main__":
    mcp.run()
