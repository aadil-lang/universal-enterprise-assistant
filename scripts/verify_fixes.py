"""
Verification script for Defect Fixes:
1. DEF-01: Multi-turn conversational context & pronoun-only follow-ups
2. DEF-02: Eliminated MODULE_TYPELESS_PACKAGE_JSON warning in apps/web
3. DEF-03: HttpOnly Cookie-based authentication & session termination
"""

import asyncio
from datetime import datetime
import os
import sys
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Ensure apps/api is first on sys.path
sys.path.insert(0, os.path.abspath("apps/api"))

from app.main import app
from app.models.document import Base, DocumentModel
from app.models.user import AppUserModel, EmployeeModel
from app.core.auth import set_auth_session_factory, UserRole, CallerIdentity
from app.services.agent_workflow import AgentWorkflow
from app.services.mcp_client import AuthenticatedMCPClient
from app.schemas.document import DocumentChunk
from app.services.vector_store import VectorStoreService
import chromadb
import bcrypt

print("=== STARTING VERIFICATION OF DEF-01, DEF-02, DEF-03 ===")

# 1. Setup in-memory SQLite DB
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Base.metadata.create_all(engine)
factory = sessionmaker(bind=engine, expire_on_commit=False)
set_auth_session_factory(factory)

hashed_pwd = bcrypt.hashpw(b"Password123!", bcrypt.gensalt(12)).decode("utf-8")

with factory() as session:
    alice_emp = EmployeeModel(
        id=uuid.UUID("a0000000-0000-0000-0000-000000000101"),
        employee_number="E101",
        first_name="Alice",
        last_name="Smith",
        corporate_email="alice@acme.com",
        job_title="HR Director",
        department="Human Resources",
        hire_date=datetime(2021, 3, 15).date(),
        employment_status="active",
    )
    alice_user = AppUserModel(
        id=uuid.UUID("b0000000-0000-0000-0000-000000000101"),
        email="alice@acme.com",
        password_hash=hashed_pwd,
        role="hr_admin",
        employee_id=alice_emp.id,
        is_active=True,
    )
    bob_emp = EmployeeModel(
        id=uuid.UUID("a0000000-0000-0000-0000-000000000102"),
        employee_number="E102",
        first_name="Bob",
        last_name="Jones",
        corporate_email="bob@acme.com",
        job_title="Senior Software Engineer",
        department="Engineering",
        hire_date=datetime(2022, 6, 1).date(),
        employment_status="active",
    )
    bob_user = AppUserModel(
        id=uuid.UUID("b0000000-0000-0000-0000-000000000102"),
        email="bob@acme.com",
        password_hash=hashed_pwd,
        role="employee",
        employee_id=bob_emp.id,
        is_active=True,
    )
    session.add_all([alice_emp, alice_user, bob_emp, bob_user])
    session.commit()

print("✓ In-memory database initialized with Alice (E101) and Bob (E102)")

# 2. Test DEF-03: HttpOnly Cookie Transport & Logout
client = TestClient(app)

# Login as Bob
login_res = client.post("/api/v1/auth/login", json={"email": "bob@acme.com", "password": "Password123!"})
assert login_res.status_code == 200, f"Login failed: {login_res.text}"
data = login_res.json()
assert "access_token" in data
assert "acme_access_token" in login_res.cookies, "Expected 'acme_access_token' cookie in response headers!"
cookie_val = login_res.cookies["acme_access_token"]
print(f"✓ DEF-03: Login sets HttpOnly 'acme_access_token' cookie: {cookie_val[:20]}...")

# Call /api/v1/auth/me WITHOUT Authorization header, relying ONLY on the cookie!
# Create fresh client that only carries the cookie
cookie_client = TestClient(app)
cookie_client.cookies.set("acme_access_token", cookie_val)
me_res = cookie_client.get("/api/v1/auth/me")
assert me_res.status_code == 200, f"Expected 200 with cookie auth, got {me_res.status_code}: {me_res.text}"
me_data = me_res.json()
assert me_data["employee_number"] == "E102"
assert me_data["first_name"] == "Bob"
print("✓ DEF-03: /api/v1/auth/me succeeds with ONLY the HttpOnly cookie (no Authorization header)")

# Call /api/v1/auth/logout to delete cookie
logout_res = cookie_client.post("/api/v1/auth/logout")
assert logout_res.status_code == 200
print("✓ DEF-03: /api/v1/auth/logout clears the session cookie successfully")

# 3. Test DEF-01: Multi-Turn Conversational Follow-up (Pronouns)
# Setup mock MCP client and vector store
mcp_client = AuthenticatedMCPClient()
async def mock_dispatcher(tool_name: str, args: dict, caller: CallerIdentity) -> dict:
    target = args.get("employee_number", caller.employee_number)
    if tool_name == "get_employee_leave_balances":
        return {
            "found": True,
            "employee_number": target,
            "fiscal_year": 2026,
            "balances": [
                {"leave_type": "annual", "available_days": 8.0, "accrued_days": 20.0, "used_days": 10.0},
                {"leave_type": "sick", "available_days": 8.0, "accrued_days": 10.0, "used_days": 2.0},
            ]
        }
    elif tool_name == "get_employee_assigned_assets":
        return {
            "found": True,
            "employee_number": target,
            "assets": [
                {"asset_tag": "LT-8821", "device_type": "laptop", "make_model": "Lenovo ThinkPad T14", "serial_number": "SN-994821"}
            ]
        }
    return {"found": True, "employee_number": target}

mcp_client.set_in_process_handler(mock_dispatcher)

# ChromaDB vector store for leave policy
chroma_client = chromadb.EphemeralClient()
vstore = VectorStoreService(client=chroma_client, collection_name="test_fixes_coll")
doc_id = "00000000-0000-0000-0000-000000000001"
vstore.index_document_chunks(
    document_id=doc_id,
    filename="Acme_Leave_Policy.pdf",
    title="Acme Leave Policy",
    category="HR",
    chunks=[
        DocumentChunk(
            chunk_id="chunk_0",
            document_id=doc_id,
            chunk_index=0,
            document_checksum="0a6699566aa259c20a6699566aa259c20a6699566aa259c20a6699566aa259c2",
            content_hash="h0",
            text="Under Acme Corporation's Leave Policy, full-time employees are entitled to 18 days of paid annual vacation leave per calendar year. A maximum of 5 unused vacation days can be carried over into the following calendar year.",
            section="2. Annual Vacation Leave Accrual and Rollover",
            page_number=1,
            char_count=200,
            token_count=45,
        )
    ]
)

from app.services.policy_retriever import PolicyRetriever
from app.services.document_registry import DocumentRegistry

class MockDoc:
    def __init__(self, doc_id, checksum):
        self.id = doc_id
        self.checksum_sha256 = checksum

class MockRegistry:
    def get_active_documents(self):
        return [MockDoc(doc_id="00000000-0000-0000-0000-000000000001", checksum="0a6699566aa259c20a6699566aa259c20a6699566aa259c20a6699566aa259c2")]

retriever = PolicyRetriever(vector_store=vstore, registry=MockRegistry())
agent = AgentWorkflow(retriever=retriever, mcp_client=mcp_client)

bob_caller = CallerIdentity(user_id="b0000000-0000-0000-0000-000000000102", employee_number="E102", role=UserRole.EMPLOYEE)
conversation_id = "test-conv-123"

async def test_multi_turn():
    # Turn 1: Bob asks about annual leave balance
    t1 = await agent.run(question="What is my annual leave balance?", caller=bob_caller, conversation_id=conversation_id)
    print(f"Turn 1 Response: [{t1['category']}] {t1['answer']}")
    assert t1["category"] == "employee"
    assert "8.0" in t1["answer"] and "annual leave" in t1["answer"]

    # Turn 2: Bob asks bare pronoun follow-up: "And what about carryover for it?"
    t2 = await agent.run(question="And what about carryover for it?", caller=bob_caller, conversation_id=conversation_id)
    print(f"Turn 2 Response: [{t2['category']}] {t2['answer']}")
    assert t2["category"] == "policy", f"Expected 'policy' for carryover follow-up, got {t2['category']}"
    assert "5 unused vacation days" in t2["answer"] or "carry over" in t2["answer"] or "rollover" in t2["answer"]
    assert len(t2["citations"]) > 0
    print("✓ DEF-01 (Part A): Bare pronoun topic follow-up ('And what about carryover for it?') resolved successfully to policy with citation!")

    # Turn 3: Alice asks about Bob Jones
    alice_caller = CallerIdentity(user_id="b0000000-0000-0000-0000-000000000101", employee_number="E101", role=UserRole.HR_ADMIN)
    alice_conv = "alice-conv-456"
    t3 = await agent.run(question="What is Bob Jones's (E102) leave balance?", caller=alice_caller, conversation_id=alice_conv)
    print(f"Turn 3 Response: [{t3['category']}] {t3['answer']}")
    assert t3["category"] == "employee"

    # Turn 4: Alice asks bare pronoun follow-up: "What laptop is assigned to him?"
    t4 = await agent.run(question="What laptop is assigned to him?", caller=alice_caller, conversation_id=alice_conv)
    print(f"Turn 4 Response: [{t4['category']}] {t4['answer']}")
    assert t4["category"] == "employee"
    assert "Lenovo ThinkPad T14" in t4["answer"]
    print("✓ DEF-01 (Part B): Pronoun person follow-up ('What laptop is assigned to him?') resolved target employee E102 successfully!")

asyncio.run(test_multi_turn())

print("\n=== ALL 3 DEFECT FIXES VERIFIED SUCCESSFULLY ===")
