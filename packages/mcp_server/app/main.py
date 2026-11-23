"""
Acme Corporation Model Context Protocol (MCP) Server.
Establishes a genuine MCP protocol endpoint using the official Python MCP SDK
with FastMCP Streamable HTTP transport and dedicated health probes.
"""

from typing import Optional

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.auth.middleware import HMACAuthMiddleware
from app.config.settings import get_mcp_settings
from app.tools.employee_tools import register_employee_tools
from app.tools.transaction_tools import register_transactional_tools

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as err:
    raise ImportError(
        "FastMCP Streamable HTTP interface is required but not found in the installed MCP SDK. "
        "Please ensure 'mcp>=1.3.0,<2.0.0' is installed."
    ) from err

try:
    from mcp.server.transport_security import TransportSecuritySettings
except ImportError:
    TransportSecuritySettings = None

settings = get_mcp_settings()


def create_mcp_server() -> FastMCP:
    """Factory function creating a configured FastMCP server instance."""
    kwargs = {
        "name": settings.MCP_SERVICE_NAME,
        "instructions": "Acme Corporation Internal Model Context Protocol Server.",
    }
    if TransportSecuritySettings is not None:
        kwargs["transport_security"] = TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        )

    server = FastMCP(**kwargs)

    # Register the approved genuine MCP employee database tools
    register_employee_tools(server)
    register_transactional_tools(server)

    @server.custom_route("/health/live", methods=["GET"])
    async def liveness_probe(request: Request) -> JSONResponse:
        """Liveness probe indicating process is active."""
        return JSONResponse(
            {
                "status": "ok",
                "service": settings.MCP_SERVICE_NAME,
                "transport": "streamable_http",
                "mcp_endpoint": "/mcp",
                "demo_fiscal_year": settings.DEMO_FISCAL_YEAR,
            }
        )

    @server.custom_route("/", methods=["GET"])
    async def root_probe(request: Request) -> JSONResponse:
        """Root info probe for internal discovery."""
        return JSONResponse(
            {
                "service": settings.MCP_SERVICE_NAME,
                "status": "online",
                "transport": "streamable_http",
                "mcp_endpoint": "/mcp",
                "demo_fiscal_year": settings.DEMO_FISCAL_YEAR,
            }
        )

    return server


def create_mcp_app(server: Optional[FastMCP] = None, secret: Optional[str] = None):
    """Factory function returning the ASGI app wrapped with HMACAuthMiddleware."""
    srv = server or create_mcp_server()
    base_app = srv.streamable_http_app()
    return HMACAuthMiddleware(base_app, secret=secret)


# Initialize the module-level FastMCP instance and ASGI application
mcp_server = create_mcp_server()
app = create_mcp_app(server=mcp_server)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.MCP_HOST,
        port=settings.MCP_PORT,
        reload=False,
    )
