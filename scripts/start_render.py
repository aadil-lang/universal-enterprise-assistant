#!/usr/bin/env python3
"""
Single-Container Unified Runner for Render Free Tier.
Runs:
  1. FastMCP server on 127.0.0.1:8001 (internal background process)
  2. Database migrations (if DATABASE_URL is configured)
  3. FastAPI backend on 0.0.0.0:$PORT (default 10000, public web service)
"""

import os
import sys
import time
import subprocess
import signal

def main():
    port = os.getenv("PORT", "10000")
    print(f"=== Starting Acme Assistant Unified Backend on Port {port} ===")

    # 1. Ensure environment variables for internal local routing
    os.environ["MCP_HOST"] = "127.0.0.1"
    os.environ["MCP_PORT"] = "8001"
    os.environ["CHROMA_HOST"] = "127.0.0.1"
    os.environ["CHROMA_PORT"] = "8000"

    # Set Python path so both apps/api and packages/mcp_server are importable
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    api_dir = os.path.join(base_dir, "apps", "api")
    mcp_dir = os.path.join(base_dir, "packages", "mcp_server")
    sys.path.insert(0, api_dir)
    sys.path.insert(0, mcp_dir)

    # 2. Run Database Migrations if DATABASE_URL is set
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        print("[MIGRATION] DATABASE_URL detected. Running database initialization...")
        try:
            from scripts.init_remote_db import run_migrations
            run_migrations(db_url)
        except Exception as e:
            print(f"[MIGRATION WARNING] Migration attempt resulted in: {e}")
            print("[MIGRATION WARNING] Continuing startup...")

    # 3. Start FastMCP Server on 127.0.0.1:8001
    print("[MCP] Starting internal FastMCP server on 127.0.0.1:8001...")
    mcp_proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1",
            "--port", "8001"
        ],
        cwd=mcp_dir,
        env=dict(os.environ, PYTHONPATH=f"{mcp_dir};{api_dir}")
    )

    # Wait 2 seconds for MCP server to spin up
    time.sleep(2)

    # 4. Start FastAPI Gateway on 0.0.0.0:$PORT
    print(f"[API] Starting public FastAPI orchestrator on 0.0.0.0:{port}...")
    api_proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", "0.0.0.0",
            "--port", str(port)
        ],
        cwd=api_dir,
        env=dict(os.environ, PYTHONPATH=f"{api_dir};{mcp_dir}")
    )

    def shutdown(signum, frame):
        print("\nShutting down unified services...")
        mcp_proc.terminate()
        api_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    # Monitor processes
    while True:
        if mcp_proc.poll() is not None:
            print("[ERROR] FastMCP process exited unexpectedly!")
            api_proc.terminate()
            sys.exit(1)
        if api_proc.poll() is not None:
            print("[ERROR] FastAPI process exited unexpectedly!")
            mcp_proc.terminate()
            sys.exit(api_proc.returncode)
        time.sleep(1)

if __name__ == "__main__":
    main()
