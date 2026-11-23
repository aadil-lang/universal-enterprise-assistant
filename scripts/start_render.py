#!/usr/bin/env python3
"""
Production Entrypoint for Render Free Web Service
Universal Enterprise HR & IT Assistant

Responsibilities:
1. Spawns the FastMCP tool server on internal loopback (127.0.0.1:8001).
   - Guaranteed private: never exposed to the public internet or external networks.
2. Waits for FastMCP health on loopback.
3. Launches the public FastAPI orchestration gateway on 0.0.0.0:$PORT.
4. Manages process lifecycles and handles SIGTERM/SIGINT graceful shutdown.
"""

import os
import sys
import time
import socket
import signal
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [RenderEntrypoint] %(message)s"
)
logger = logging.getLogger("start_render")

MCP_PROCESS = None
API_PROCESS = None

def signal_handler(sig, frame):
    logger.info("Received termination signal %s. Shutting down child processes...", sig)
    if API_PROCESS and API_PROCESS.poll() is None:
        API_PROCESS.terminate()
    if MCP_PROCESS and MCP_PROCESS.poll() is None:
        MCP_PROCESS.terminate()
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def wait_for_port(host: str, port: int, timeout: float = 15.0) -> bool:
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except (OSError, ConnectionRefusedError):
            time.sleep(0.3)
    return False

def main():
    global MCP_PROCESS, API_PROCESS

    port = int(os.environ.get("PORT", "8000"))
    mcp_port = int(os.environ.get("MCP_PORT", "8001"))
    mcp_host = "127.0.0.1"  # STRICTLY internal loopback

    # Ensure internal settings match
    os.environ["MCP_HOST"] = mcp_host
    os.environ["MCP_PORT"] = str(mcp_port)

    # Ensure PYTHONPATH includes both services
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    api_dir = os.path.join(base_dir, "apps", "api")
    mcp_dir = os.path.join(base_dir, "packages", "mcp_server")

    current_pythonpath = os.environ.get("PYTHONPATH", "")
    new_pythonpath = f"{api_dir}{os.pathsep}{mcp_dir}"
    if current_pythonpath:
        new_pythonpath = f"{new_pythonpath}{os.pathsep}{current_pythonpath}"
    os.environ["PYTHONPATH"] = new_pythonpath

    logger.info("=" * 65)
    logger.info("Starting Acme Universal Enterprise Assistant on Render Free")
    logger.info("Public API Port : %d", port)
    logger.info("Private MCP Port: %d (bound to %s)", mcp_port, mcp_host)
    logger.info("=" * 65)

    # Step 1: Start FastMCP as private internal subprocess
    mcp_cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", mcp_host,
        "--port", str(mcp_port),
        "--app-dir", mcp_dir
    ]
    logger.info("Launching private FastMCP tool server on %s:%d...", mcp_host, mcp_port)
    MCP_PROCESS = subprocess.Popen(mcp_cmd)

    # Step 2: Wait for FastMCP loopback socket
    logger.info("Waiting for FastMCP tool server to become ready...")
    if not wait_for_port(mcp_host, mcp_port, timeout=20.0):
        logger.error("FATAL: FastMCP tool server failed to bind to %s:%d within timeout.", mcp_host, mcp_port)
        if MCP_PROCESS.poll() is not None:
            logger.error("FastMCP process exited with code %d", MCP_PROCESS.returncode)
        if MCP_PROCESS:
            MCP_PROCESS.kill()
        sys.exit(1)
    logger.info("FastMCP tool server is ready on %s:%d (Strictly Isolated).", mcp_host, mcp_port)

    # Step 3: Start public FastAPI gateway
    api_cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--app-dir", api_dir
    ]
    logger.info("Launching public FastAPI gateway on 0.0.0.0:%d...", port)
    API_PROCESS = subprocess.Popen(api_cmd)

    # Step 4: Monitor processes
    while True:
        if API_PROCESS.poll() is not None:
            logger.error("FastAPI gateway exited with code %d. Shutting down.", API_PROCESS.returncode)
            if MCP_PROCESS and MCP_PROCESS.poll() is None:
                MCP_PROCESS.terminate()
            sys.exit(API_PROCESS.returncode)

        if MCP_PROCESS.poll() is not None:
            logger.error("Private FastMCP process unexpectedly terminated with code %d. Shutting down.", MCP_PROCESS.returncode)
            if API_PROCESS and API_PROCESS.poll() is None:
                API_PROCESS.terminate()
            sys.exit(MCP_PROCESS.returncode)

        time.sleep(1)

if __name__ == "__main__":
    main()
