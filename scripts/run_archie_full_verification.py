"""
Full Verification Runner for Archie Voice Assistant.
Spawns demo backend (port 8000) and Next.js frontend (port 3000),
waits for readiness, executes the Playwright acceptance suite,
and terminates the processes cleanly.
"""

import os
import sys
import time
import urllib.request
import subprocess

BASE_DIR = os.path.abspath(".")
sys.path.insert(0, BASE_DIR)
from scripts.verify_archie_browser import run_archie_acceptance_test
WEB_DIR = os.path.join(BASE_DIR, "apps", "web")

def wait_for_url(url, timeout=35, name="service"):
    start = time.time()
    print(f"Waiting for {name} at {url}...", flush=True)
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "HealthCheck"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status in (200, 404):
                    print(f"✓ {name} is ready! (HTTP {resp.status})", flush=True)
                    return True
        except Exception:
            time.sleep(1)
    print(f"❌ Timed out waiting for {name} at {url}", flush=True)
    return False

def main():
    backend_proc = None
    frontend_proc = None
    backend_log = open(os.path.join(BASE_DIR, "artifacts", "demo_backend.log"), "w", encoding="utf-8")
    frontend_log = open(os.path.join(BASE_DIR, "artifacts", "demo_frontend.log"), "w", encoding="utf-8")

    try:
        # 1. Start Backend Server
        print("[1] Starting Demo Backend Server on http://127.0.0.1:8000...", flush=True)
        backend_proc = subprocess.Popen(
            [sys.executable, os.path.join(BASE_DIR, "scripts", "run_demo_backend.py")],
            cwd=BASE_DIR,
            stdout=backend_log,
            stderr=backend_log,
        )

        # 2. Start Frontend Server
        print("[2] Starting Next.js Dev Server on http://localhost:3000...", flush=True)
        frontend_proc = subprocess.Popen(
            ["npx", "next", "dev", "-p", "3000"],
            cwd=WEB_DIR,
            stdout=frontend_log,
            stderr=frontend_log,
            shell=True,
        )

        # 3. Wait for Readiness
        backend_ready = wait_for_url("http://127.0.0.1:8000/health", timeout=35, name="Backend API")
        frontend_ready = wait_for_url("http://localhost:3000", timeout=40, name="Next.js Frontend")

        if not backend_ready or not frontend_ready:
            print("❌ Services failed to start within timeout.")
            sys.exit(1)

        print("\n Services are live! Executing Playwright Browser Acceptance Suite...\n")
        run_archie_acceptance_test()

    finally:
        print("\n Cleaning up server processes...")
        if frontend_proc:
            try:
                subprocess.run(f"taskkill /F /T /PID {frontend_proc.pid}", shell=True, capture_output=True)
            except Exception:
                pass
        if backend_proc:
            try:
                subprocess.run(f"taskkill /F /T /PID {backend_proc.pid}", shell=True, capture_output=True)
            except Exception:
                pass
        print("✓ Cleanup completed.")

if __name__ == "__main__":
    main()
