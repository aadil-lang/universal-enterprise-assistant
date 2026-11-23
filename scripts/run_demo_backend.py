"""
Demo Backend Server for Video Recording.
Serves the FastAPI application on http://127.0.0.1:8000
with in-memory SQLite seed data and 14-chunk active ChromaDB policy index.
"""

import os
import sys
import hashlib
import time
from datetime import date
import uuid

BASE_DIR = r"c:\Users\HP\OneDrive\Documents\HR-IT Helpdesk"
sys.path.insert(0, os.path.join(BASE_DIR, "apps", "api"))

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

os.environ["APP_ENV"] = "development"
if not os.environ.get("LLM_PROVIDER"):
    os.environ["LLM_PROVIDER"] = "gemini"

import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uvicorn
import chromadb

from app.config.settings import get_settings
from app.core.auth import CallerIdentity, UserRole, set_auth_session_factory
from app.models.document import Base
from app.models.user import AppUserModel, EmployeeModel
from app.routers.chat import set_agent_workflow
from app.services.agent_workflow import AgentWorkflow
from app.services.chunker import chunk_extracted_segments
from app.services.document_extractor import extract_text_from_document
from app.services.llm_service import LLMService
from app.services.mcp_client import AuthenticatedMCPClient, MCPAuthorizationError
from app.services.policy_retriever import PolicyRetriever
from app.services.vector_store import VectorStoreService
from app.main import app

def setup_in_memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    with factory() as session:
        pw_hash = bcrypt.hashpw(b"Password123!", bcrypt.gensalt(12)).decode("utf-8")

        # Alice E101 (HR Admin)
        alice_emp = EmployeeModel(
            id=uuid.UUID("a0000000-0000-0000-0000-000000000101"),
            employee_number="E101",
            first_name="Alice",
            last_name="Smith",
            corporate_email="alice@acme.com",
            job_title="HR Director",
            department="Human Resources",
            hire_date=date(2021, 3, 15),
            employment_status="active",
        )
        alice_user = AppUserModel(
            id=uuid.UUID("b0000000-0000-0000-0000-000000000101"),
            email="alice@acme.com",
            password_hash=pw_hash,
            role="hr_admin",
            employee_id=alice_emp.id,
            is_active=True,
        )

        # Bob E102 (Employee)
        bob_emp = EmployeeModel(
            id=uuid.UUID("a0000000-0000-0000-0000-000000000102"),
            employee_number="E102",
            first_name="Bob",
            last_name="Jones",
            corporate_email="bob@acme.com",
            job_title="Senior Software Engineer",
            department="Engineering",
            hire_date=date(2022, 6, 1),
            employment_status="active",
        )
        bob_user = AppUserModel(
            id=uuid.UUID("b0000000-0000-0000-0000-000000000102"),
            email="bob@acme.com",
            password_hash=pw_hash,
            role="employee",
            employee_id=bob_emp.id,
            is_active=True,
        )

        # Carol E103 (Employee)
        carol_emp = EmployeeModel(
            id=uuid.UUID("a0000000-0000-0000-0000-000000000103"),
            employee_number="E103",
            first_name="Carol",
            last_name="Davis",
            corporate_email="carol@acme.com",
            job_title="Marketing Specialist",
            department="Marketing",
            hire_date=date(2023, 1, 10),
            employment_status="active",
        )
        carol_user = AppUserModel(
            id=uuid.UUID("b0000000-0000-0000-0000-000000000103"),
            email="carol@acme.com",
            password_hash=pw_hash,
            role="employee",
            employee_id=carol_emp.id,
            is_active=True,
        )

        session.add_all([alice_emp, alice_user, bob_emp, bob_user, carol_emp, carol_user])
        session.commit()

    set_auth_session_factory(factory)
    return factory


def setup_vector_store():
    settings = get_settings()
    client = chromadb.EphemeralClient()
    store = VectorStoreService(client=client, collection_name="demo_acme_policies")

    files = [
        ("data/policies/Acme_Leave_Policy.pdf", "00000000-0000-0000-0000-000000000001", "Acme Leave Policy", "HR"),
        ("data/policies/Acme_IT_Equipment_Policy.docx", "00000000-0000-0000-0000-000000000002", "Acme IT Equipment Policy", "IT"),
        ("data/policies/Acme_Remote_Work_Policy.md", "00000000-0000-0000-0000-000000000003", "Acme Remote Work Policy", "IT"),
    ]

    active_map = {}
    for rel_path, doc_id, title, cat in files:
        full_path = os.path.join(BASE_DIR, rel_path)
        with open(full_path, "rb") as f:
            content = f.read()
        filename = os.path.basename(full_path)
        chk = hashlib.sha256(content).hexdigest()
        active_map[doc_id] = chk
        segments = extract_text_from_document(filename, content)
        chunks = chunk_extracted_segments(
            document_id=doc_id,
            document_checksum=chk,
            segments=segments,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        store.index_document_chunks(doc_id, filename, title, cat, chunks)

    return store, active_map


def create_in_process_mcp_client():
    mcp_client = AuthenticatedMCPClient()

    async def in_process_dispatcher(tool_name: str, args: dict, caller: CallerIdentity) -> dict:
        target = args.get("employee_number", "").strip()
        if caller.role == UserRole.EMPLOYEE and target != caller.employee_number:
            raise MCPAuthorizationError("Access Denied: You are not authorized to view records for this employee.")

        if tool_name == "get_employee_leave_balances":
            if target == "E102":
                return {
                    "found": True,
                    "employee_number": "E102",
                    "fiscal_year": 2026,
                    "balances": [
                        {
                            "leave_type": "annual",
                            "accrued_days": 20.0,
                            "used_days": 10.0,
                            "pending_days": 2.0,
                            "available_days": 8.0,
                            "fiscal_year": 2026,
                        },
                        {
                            "leave_type": "sick",
                            "accrued_days": 10.0,
                            "used_days": 2.0,
                            "pending_days": 0.0,
                            "available_days": 8.0,
                            "fiscal_year": 2026,
                        },
                    ],
                }
            elif target == "E103":
                return {
                    "found": True,
                    "employee_number": "E103",
                    "fiscal_year": 2026,
                    "balances": [
                        {
                            "leave_type": "annual",
                            "accrued_days": 18.0,
                            "used_days": 4.0,
                            "pending_days": 0.0,
                            "available_days": 14.0,
                            "fiscal_year": 2026,
                        }
                    ],
                }
            return {"found": False, "message": f"Employee {target} not found."}

        elif tool_name == "get_employee_assigned_assets":
            if target == "E102":
                return {
                    "found": True,
                    "employee_number": "E102",
                    "assets": [
                        {
                            "asset_tag": "LT-8821",
                            "device_type": "laptop",
                            "make_model": "Lenovo ThinkPad T14",
                            "serial_number": "SN-994821",
                            "condition_status": "active",
                        }
                    ],
                }
            return {"found": True, "employee_number": target, "assets": []}

        elif tool_name == "get_employee_it_tickets":
            if target == "E102":
                return {
                    "found": True,
                    "employee_number": "E102",
                    "tickets": [
                        {
                            "ticket_number": "IT-1042",
                            "title": "VPN connection timeout",
                            "category": "network",
                            "priority": "medium",
                            "status": "open",
                        }
                    ],
                }
            return {"found": True, "employee_number": target, "tickets": []}

        elif tool_name == "get_employee_profile":
            if target == "E102":
                return {
                    "found": True,
                    "employee": {
                        "employee_number": "E102",
                        "first_name": "Bob",
                        "last_name": "Jones",
                        "job_title": "Senior Software Engineer",
                        "department": "Engineering",
                        "employment_status": "active",
                    },
                }
            elif target == "E101":
                return {
                    "found": True,
                    "employee": {
                        "employee_number": "E101",
                        "first_name": "Alice",
                        "last_name": "Smith",
                        "job_title": "HR Director",
                        "department": "Human Resources",
                        "employment_status": "active",
                    },
                }
            return {"found": False, "message": f"Employee {target} not found."}

        raise ValueError(f"Unknown tool: {tool_name}")

    mcp_client.call_tool = in_process_dispatcher
    return mcp_client


def setup_app():
    setup_in_memory_db()
    store, active_map = setup_vector_store()

    def get_live_active_map():
        m = dict(active_map)
        try:
            from app.services.document_registry import DocumentRegistry
            reg = DocumentRegistry()
            docs = reg.get_active_documents()
            for d in docs:
                m[str(d.id)] = d.checksum
        except Exception:
            pass
        return m

    retriever = PolicyRetriever(vector_store=store)
    retriever.get_active_version_map = get_live_active_map
    mcp_client = create_in_process_mcp_client()
    llm_service = LLMService()
    workflow = AgentWorkflow(retriever=retriever, mcp_client=mcp_client, llm_service=llm_service)
    set_agent_workflow(workflow)

    from app.routers.documents import get_pipeline
    from app.services.ingestion_pipeline import IngestionPipeline
    pipeline = IngestionPipeline(vector_store=store)
    app.dependency_overrides[get_pipeline] = lambda: pipeline

    print("✓ Demo backend initialized with in-memory DB, live ChromaDB, and real IngestionPipeline.")


if __name__ == "__main__":
    setup_app()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

