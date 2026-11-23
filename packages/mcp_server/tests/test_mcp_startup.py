"""
Tests for Acme Corporation Model Context Protocol (MCP) Server.
Verifies FastMCP Streamable HTTP transport foundation and genuine client handshake
using dynamic port allocation, bounded readiness polling, and clean thread teardown.
"""

import asyncio
import socket
import threading
import time
import httpx
from starlette.testclient import TestClient

from app.auth.models import CallerIdentity, UserRole
from app.auth.signer import create_internal_auth_headers
from app.main import app, settings


def find_free_port() -> int:
    """Dynamically allocate an available ephemeral TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_mcp_health_probes():
    """Verify non-protocol liveness and discovery endpoints."""
    client = TestClient(app)
    
    # Test /health/live
    live_resp = client.get("/health/live")
    assert live_resp.status_code == 200
    live_data = live_resp.json()
    assert live_data["status"] == "ok"
    assert live_data["service"] == "acme-mcp-server"
    assert live_data["transport"] == "streamable_http"
    assert live_data["mcp_endpoint"] == "/mcp"
    assert live_data["demo_fiscal_year"] == 2026

    # Test /
    root_resp = client.get("/")
    assert root_resp.status_code == 200
    root_data = root_resp.json()
    assert root_data["status"] == "online"
    assert root_data["mcp_endpoint"] == "/mcp"


def test_mcp_protocol_streamable_http_handshake():
    """
    Verify genuine MCP protocol initialization and capability handshake
    over Streamable HTTP transport using the official MCP ClientSession.
    """
    import uvicorn
    from mcp.client.streamable_http import streamable_http_client
    from mcp.client.session import ClientSession

    port = find_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    uvi_server = uvicorn.Server(config)

    thread = threading.Thread(target=uvi_server.run, daemon=True)
    thread.start()

    # Bounded readiness polling: poll /health/live up to 5.0 seconds
    deadline = time.time() + 5.0
    server_ready = False
    while time.time() < deadline:
        try:
            resp = httpx.get(f"http://127.0.0.1:{port}/health/live", timeout=0.5)
            if resp.status_code == 200:
                server_ready = True
                break
        except Exception:
            time.sleep(0.1)

    assert server_ready, f"FastMCP server failed to start on port {port} within 5.0s"

    auth_headers = create_internal_auth_headers(
        CallerIdentity(
            user_id="b0000000-0000-0000-0000-000000000102",
            employee_number="E102",
            role=UserRole.EMPLOYEE,
        ),
        secret=settings.INTERNAL_MCP_SECRET,
    )

    async def _handshake():
        url = f"http://127.0.0.1:{port}/mcp"
        async with httpx.AsyncClient(headers=auth_headers) as http_client:
            async with streamable_http_client(url, http_client=http_client) as streams:
                read_stream, write_stream = streams[0], streams[1]
                async with ClientSession(read_stream, write_stream) as session:
                    init_result = await session.initialize()
                    
                    # Verify protocol capabilities and server identity
                    srv_info = getattr(init_result, "serverInfo", getattr(init_result, "server_info", None))
                    assert srv_info is not None
                    assert srv_info.name == "acme-mcp-server"
                    assert init_result.capabilities is not None
                    
                    # In Phase 2.2: Verify that exactly the 4 approved employee tools are exposed
                    tools_result = await session.list_tools()
                    tool_names = {t.name for t in tools_result.tools}
                    expected_tools = {
                        "get_employee_profile",
                        "get_employee_leave_balances",
                        "get_employee_assigned_assets",
                        "get_employee_it_tickets",
                    }
                    assert tool_names == expected_tools, f"Exposed tools {tool_names} do not match expected {expected_tools}"
                    assert len(tools_result.tools) == 4

    try:
        asyncio.run(_handshake())
    finally:
        uvi_server.should_exit = True
        thread.join(timeout=3.0)
