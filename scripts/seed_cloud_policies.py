"""
Cloud Corporate Policy Seeder
Universal Enterprise HR & IT Assistant

Uploads and vector-indexes authoritative enterprise policy documents
into the deployed cloud instance (Render/Qdrant/Neon) using HR Admin credentials.

Usage:
  python scripts/seed_cloud_policies.py --api-url "https://acme-assistant-api.onrender.com"
"""

import os
import sys
import argparse
from pathlib import Path
import httpx

def seed_policies(api_url: str):
    api_url = api_url.rstrip("/")
    print("=" * 60)
    print(" Acme Assistant — Cloud Policy Seeding Tool")
    print(f" Target API: {api_url}")
    print("=" * 60)

    # Step 1: Health probe
    print("\n[1/3] Checking API health...")
    try:
        r = httpx.get(f"{api_url}/health/live", timeout=15.0)
        if r.status_code != 200:
            print(f"[ERROR] API health check failed with status {r.status_code}: {r.text}")
            sys.exit(1)
        print(" -> API is healthy and reachable!")
    except Exception as e:
        print(f"[ERROR] Could not connect to {api_url}: {e}")
        sys.exit(1)

    # Step 2: Authenticate as HR Admin (Alice E101)
    print("\n[2/3] Authenticating as HR Admin (Alice E101)...")
    try:
        auth_res = httpx.post(
            f"{api_url}/api/v1/auth/login",
            json={"email": "alice@acme.com", "password": "Password123!"},
            timeout=15.0,
        )
        if auth_res.status_code != 200:
            print(f"[ERROR] Login failed: {auth_res.text}")
            sys.exit(1)
        token = auth_res.json().get("access_token")
        if not token:
            print(f"[ERROR] No access_token in login response: {auth_res.json()}")
            sys.exit(1)
        print(" -> Successfully authenticated as Alice Smith (HR Director)!")
    except Exception as e:
        print(f"[ERROR] Auth request failed: {e}")
        sys.exit(1)

    # Step 3: Upload and index policies
    headers = {"Authorization": f"Bearer {token}"}
    base_dir = Path(__file__).resolve().parent.parent
    uploads_dir = base_dir / "data" / "uploads"

    candidate_files = [
        ("Acme_Remote_Work_Policy.md", "Acme Remote Work Policy", "HR"),
        ("leave.md", "Acme Leave & Vacation Policy", "HR"),
        ("equipment.md", "Acme IT Equipment & Asset Policy", "IT"),
    ]

    print("\n[3/3] Uploading and indexing enterprise policy documents...")
    client = httpx.Client(headers=headers, timeout=60.0)

    for filename, title, category in candidate_files:
        filepath = uploads_dir / filename
        if not filepath.exists():
            print(f" -> Skipping {filename} (not found locally)")
            continue

        print(f" -> Ingesting '{title}' ({filename})...")
        with open(filepath, "rb") as f:
            files = {"file": (filename, f, "text/markdown")}
            data = {"title": title, "category": category}
            
            try:
                res = client.post(f"{api_url}/documents/upload", files=files, data=data)
                if res.status_code in (200, 201):
                    doc_data = res.json()
                    chunk_count = doc_data.get("chunks_count", 0)
                    print(f"    [OK] Ingested successfully: {chunk_count} chunks indexed into vector store.")
                else:
                    print(f"    [WARNING] Upload returned status {res.status_code}: {res.text}")
            except Exception as e:
                print(f"    [ERROR] Upload failed for {filename}: {e}")

    print("\n" + "=" * 60)
    print(" Policy seeding process completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed corporate policies into cloud backend.")
    parser.add_argument("--api-url", type=str, required=True, help="Base URL of deployed API (e.g. https://acme-api.onrender.com)")
    args = parser.parse_args()

    seed_policies(args.api_url)
