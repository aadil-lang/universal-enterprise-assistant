"""
Remote Database Initializer & Migration Tool
Universal Enterprise HR & IT Assistant

Usage:
  python scripts/init_remote_db.py --url "postgresql://user:password@host:port/database"
  or set DATABASE_URL environment variable.
"""

import os
import sys
import argparse
from pathlib import Path

def get_connection(db_url: str):
    # Try importing psycopg (psycopg3) or psycopg2
    try:
        import psycopg
        # Clean URL if contains driver prefix
        clean_url = db_url.replace("postgresql+psycopg://", "postgresql://").replace("postgresql+psycopg2://", "postgresql://")
        return psycopg.connect(clean_url, autocommit=True)
    except ImportError:
        try:
            import psycopg2
            clean_url = db_url.replace("postgresql+psycopg://", "postgresql://").replace("postgresql+psycopg2://", "postgresql://")
            conn = psycopg2.connect(clean_url)
            conn.autocommit = True
            return conn
        except ImportError:
            print("[ERROR] Neither psycopg nor psycopg2 is installed. Install via pip install psycopg[binary].")
            sys.exit(1)

def run_migrations(db_url: str, force: bool = False):
    print(f"\n=======================================================")
    print(f" Acme Assistant — Remote Database Migration Tool")
    print(f"=======================================================\n")

    base_dir = Path(__file__).resolve().parent.parent
    sql_dir = base_dir / "infrastructure" / "postgres" / "init"
    
    sql_files = [
        sql_dir / "001_schema.sql",
        sql_dir / "002_seed.sql",
        sql_dir / "003_transactional_schema.sql"
    ]

    for f in sql_files:
        if not f.exists():
            print(f"[ERROR] Migration file not found: {f}")
            sys.exit(1)

    print(f"Connecting to database...")
    try:
        conn = get_connection(db_url)
        cursor = conn.cursor()
        print("Connected successfully!")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        sys.exit(1)

    # Check existing tables
    try:
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Existing tables in public schema: {len(tables)} {tables}")
    except Exception as e:
        tables = []

    if "users" in tables and not force:
        print("\n[INFO] 'users' table already exists. Database appears to be initialized.")
        print("Use --force if you wish to re-run all initialization scripts.")
        return

    print("\nExecuting SQL migration scripts in order:")
    for sql_file in sql_files:
        print(f"  -> Running {sql_file.name}...")
        with open(sql_file, "r", encoding="utf-8") as f:
            sql_content = f.read()
        
        try:
            cursor.execute(sql_content)
            print(f"     [OK] {sql_file.name} applied successfully.")
        except Exception as e:
            print(f"     [WARNING/ERROR] while executing {sql_file.name}: {e}")

    # Verify tables
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    final_tables = [row[0] for row in cursor.fetchall()]
    print(f"\n[SUCCESS] Migration completed! Active tables ({len(final_tables)}):")
    for t in sorted(final_tables):
        print(f"  - {t}")

    # Verify sample user count
    if "users" in final_tables:
        cursor.execute("SELECT count(*) FROM users;")
        user_count = cursor.fetchone()[0]
        print(f"\nUser count on record: {user_count} (Alice, Bob, etc.)")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize remote PostgreSQL database for Acme HR & IT Assistant.")
    parser.add_argument("--url", type=str, default=os.getenv("DATABASE_URL"), help="PostgreSQL connection string")
    parser.add_argument("--force", action="store_true", help="Force re-run migrations even if tables exist")
    args = parser.parse_args()

    if not args.url:
        print("[ERROR] No DATABASE_URL specified. Provide --url or set DATABASE_URL environment variable.")
        sys.exit(1)

    run_migrations(args.url, force=args.force)

