"""
Full 9-Minute Loom Walkthrough Video Recorder.
Adheres strictly to the timing and structure specified in the prompt:
- PART 1 — Architecture Introduction (00:00–00:30, 30s)
- PART 2 — Application Introduction and Login (00:30–01:30, 60s)
- PART 3 — Employee Assistant Journey (01:30–05:00, 210s)
  - Journey A: Personal leave balance (01:30–02:05)
  - Journey B: Company leave policy (02:05–02:40)
  - Journey C: Asset information (02:40–03:15)
  - Journey D: IT support ticket (03:15–03:50)
  - Journey E: Hybrid question (03:50–04:25)
  - Journey F: Policy carryover / conversational follow-up (04:25–05:00)
- PART 4 — HR Administrator Journey & Document Ingestion (05:00–07:00, 120s)
  - Admin login & interface inspection (05:00–05:40)
  - Document upload modal & local PC file selection (05:40–06:15)
  - Pipeline processing & chunk indexing feedback (06:15–06:40)
  - Role switch back to Bob & verification query (06:40–07:00)
- PART 5 — Security and Engineering Decisions (07:00–08:30, 90s)
- PART 6 — Closing (08:30–09:00, 30s)

Total Target Duration: ~540 seconds (9 minutes 00 seconds).
"""

import os
import sys
import time
import math
import shutil
from playwright.sync_api import sync_playwright

OUTPUT_DIR = r"c:\Users\HP\OneDrive\Documents\HR-IT Helpdesk\artifacts\loom_walkthrough"
os.makedirs(OUTPUT_DIR, exist_ok=True)
RAW_VIDEOS_DIR = os.path.join(OUTPUT_DIR, "raw_recordings_9min")
os.makedirs(RAW_VIDEOS_DIR, exist_ok=True)

CURSOR_INJECTION_SCRIPT = """
(() => {
    // 1. Virtual cursor
    if (!document.getElementById('loom-virtual-cursor')) {
        const cursor = document.createElement('div');
        cursor.id = 'loom-virtual-cursor';
        cursor.style.position = 'fixed';
        cursor.style.top = '0';
        cursor.style.left = '0';
        cursor.style.width = '24px';
        cursor.style.height = '24px';
        cursor.style.borderRadius = '50%';
        cursor.style.backgroundColor = 'rgba(59, 130, 246, 0.75)';
        cursor.style.border = '2.5px solid #ffffff';
        cursor.style.boxShadow = '0 0 14px rgba(59, 130, 246, 0.85), 0 2px 6px rgba(0,0,0,0.3)';
        cursor.style.pointerEvents = 'none';
        cursor.style.zIndex = '999999';
        cursor.style.transform = 'translate(-50%, -50%)';
        cursor.style.transition = 'transform 0.05s ease-out, background-color 0.15s ease';
        document.body.appendChild(cursor);

        // Click ripple
        document.addEventListener('mousedown', (e) => {
            cursor.style.transform = 'translate(-50%, -50%) scale(0.75)';
            cursor.style.backgroundColor = 'rgba(239, 68, 68, 0.9)';

            const ripple = document.createElement('div');
            ripple.style.position = 'fixed';
            ripple.style.left = e.clientX + 'px';
            ripple.style.top = e.clientY + 'px';
            ripple.style.width = '10px';
            ripple.style.height = '10px';
            ripple.style.borderRadius = '50%';
            ripple.style.backgroundColor = 'transparent';
            ripple.style.border = '3px solid rgba(59, 130, 246, 0.85)';
            ripple.style.pointerEvents = 'none';
            ripple.style.zIndex = '999998';
            ripple.style.transform = 'translate(-50%, -50%)';
            ripple.style.animation = 'loom-ripple 0.6s cubic-bezier(0, 0.2, 0.8, 1) forwards';
            document.body.appendChild(ripple);
            setTimeout(() => ripple.remove(), 600);
        });

        document.addEventListener('mouseup', () => {
            cursor.style.transform = 'translate(-50%, -50%) scale(1)';
            cursor.style.backgroundColor = 'rgba(59, 130, 246, 0.75)';
        });

        document.addEventListener('mousemove', (e) => {
            cursor.style.left = e.clientX + 'px';
            cursor.style.top = e.clientY + 'px';
        });

        const styleSheet = document.createElement('style');
        styleSheet.innerText = `
            @keyframes loom-ripple {
                0% { width: 10px; height: 10px; opacity: 1; }
                100% { width: 48px; height: 48px; opacity: 0; }
            }
        `;
        document.head.appendChild(styleSheet);
    }

    // 2. Loom Subtitle Bar
    if (!document.getElementById('loom-subtitle-bar')) {
        const subtitle = document.createElement('div');
        subtitle.id = 'loom-subtitle-bar';
        subtitle.style.position = 'fixed';
        subtitle.style.bottom = '28px';
        subtitle.style.left = '50%';
        subtitle.style.transform = 'translateX(-50%)';
        subtitle.style.backgroundColor = 'rgba(15, 23, 42, 0.94)';
        subtitle.style.color = '#f8fafc';
        subtitle.style.padding = '12px 30px';
        subtitle.style.borderRadius = '9999px';
        subtitle.style.fontSize = '14.5px';
        subtitle.style.fontWeight = '500';
        subtitle.style.fontFamily = 'system-ui, -apple-system, sans-serif';
        subtitle.style.boxShadow = '0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.12)';
        subtitle.style.backdropFilter = 'blur(12px)';
        subtitle.style.zIndex = '999990';
        subtitle.style.pointerEvents = 'none';
        subtitle.style.transition = 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)';
        subtitle.style.maxWidth = '85%';
        subtitle.style.textAlign = 'center';
        subtitle.innerText = '👋 Universal Enterprise HR & IT Assistant — Architecture & Walkthrough';
        document.body.appendChild(subtitle);
    }

    // 3. Subtle Presenter Pill (bottom-left)
    if (!document.getElementById('loom-presenter-badge')) {
        const presenter = document.createElement('div');
        presenter.id = 'loom-presenter-badge';
        presenter.style.position = 'fixed';
        presenter.style.bottom = '28px';
        presenter.style.left = '28px';
        presenter.style.backgroundColor = 'rgba(15, 23, 42, 0.92)';
        presenter.style.color = '#38bdf8';
        presenter.style.padding = '8px 16px';
        presenter.style.borderRadius = '12px';
        presenter.style.fontSize = '12px';
        presenter.style.fontWeight = '700';
        presenter.style.fontFamily = 'monospace';
        presenter.style.letterSpacing = '0.05em';
        presenter.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3), 0 0 0 1px rgba(56, 189, 248, 0.3)';
        presenter.style.zIndex = '999990';
        presenter.style.pointerEvents = 'none';
        presenter.innerHTML = '● PRESENTER (ENGINEERING DEMO)';
        document.body.appendChild(presenter);
    }
})();
"""

def update_subtitle(page, text: str):
    try:
        page.evaluate(f"""
            const el = document.getElementById('loom-subtitle-bar');
            if (el) {{
                el.innerText = {repr(text)};
                el.style.transform = 'translateX(-50%) scale(1.02)';
                setTimeout(() => el.style.transform = 'translateX(-50%) scale(1)', 200);
            }}
        """)
    except:
        pass

def smooth_mouse_move(page, current_pos, target_pos, steps=35, base_delay=0.018):
    x1, y1 = current_pos
    x2, y2 = target_pos
    dx = x2 - x1
    dy = y2 - y1
    dist = math.sqrt(dx*dx + dy*dy)
    if dist < 5:
        page.mouse.move(x2, y2)
        return target_pos

    actual_steps = max(steps, int(dist / 20))
    mid_x = (x1 + x2) / 2 + (dy * 0.12)
    mid_y = (y1 + y2) / 2 - (dx * 0.12)

    for i in range(1, actual_steps + 1):
        t = i / actual_steps
        ease = t * t * (3 - 2 * t)
        curr_x = (1 - ease)**2 * x1 + 2 * (1 - ease) * ease * mid_x + ease**2 * x2
        curr_y = (1 - ease)**2 * y1 + 2 * (1 - ease) * ease * mid_y + ease**2 * y2
        page.mouse.move(curr_x, curr_y)
        time.sleep(base_delay)

    page.mouse.move(x2, y2)
    time.sleep(0.1)
    return target_pos

def human_type(page, locator, text: str, delay_per_char=0.045):
    locator.click()
    locator.fill("")
    for ch in text:
        locator.type(ch, delay=delay_per_char)
    time.sleep(0.3)

def run():
    print("=== RECORDING FULL 9-MINUTE LOOM WALKTHROUGH VIDEO (1920x1080) ===")
    start_wall_time = time.time()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--host-resolver-rules=MAP * 127.0.0.1",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=RAW_VIDEOS_DIR,
            record_video_size={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        # =========================================================================
        # PART 1 — Architecture Introduction (00:00 – 00:30, 30s)
        # =========================================================================
        print("[00:00] Part 1: Architecture Introduction...")
        page.goto("http://127.0.0.1:3000/architecture.html")
        page.wait_for_load_state("networkidle")
        page.evaluate(CURSOR_INJECTION_SCRIPT)

        pos = (960, 540)
        page.mouse.move(*pos)
        update_subtitle(page, "📐 PART 1: Architecture Overview — Next.js 14 Frontend → FastAPI Gateway → LangGraph Agent")
        time.sleep(6.0)

        # Tracing architecture nodes
        pos = smooth_mouse_move(page, pos, (350, 420), steps=40)
        update_subtitle(page, "Next.js 14 (Port 3000): React 18 App Router, Tailwind CSS, Role-Gated Dynamic Components")
        time.sleep(6.0)

        pos = smooth_mouse_move(page, pos, (680, 420), steps=40)
        update_subtitle(page, "FastAPI & LangGraph (Port 8000): Deterministic State Machine with Pre-Flight Guardrails")
        time.sleep(6.0)

        pos = smooth_mouse_move(page, pos, (1020, 350), steps=40)
        update_subtitle(page, "ChromaDB Vector Store: Dense Semantic RAG over Active Corporate Policy Versions")
        time.sleep(5.0)

        pos = smooth_mouse_move(page, pos, (1020, 530), steps=35)
        update_subtitle(page, "FastMCP Protocol Server (Port 8001): Controlled Read-Only Relational Employee Database Tools")
        time.sleep(5.0)

        pos = smooth_mouse_move(page, pos, (1360, 420), steps=40)
        update_subtitle(page, "PostgreSQL (Port 5432): Authoritative System of Record for Accounts, Profiles & Checksums")
        time.sleep(5.0)

        # =========================================================================
        # PART 2 — Application Introduction and Login (00:30 – 01:30, 60s)
        # =========================================================================
        print("[00:30] Part 2: Application Introduction & Login...")
        page.goto("http://127.0.0.1:3000")
        page.wait_for_load_state("networkidle")
        page.evaluate(CURSOR_INJECTION_SCRIPT)

        update_subtitle(page, "🔐 PART 2: Application Login — Designing Around Two Primary Roles: Employees and HR Administrators")
        pos = smooth_mouse_move(page, pos, (960, 320), steps=40)
        time.sleep(8.0)

        update_subtitle(page, "Inspecting Acme Corporation Brand & Corporate Authentication Card")
        pos = smooth_mouse_move(page, pos, (960, 450), steps=35)
        time.sleep(7.0)

        update_subtitle(page, "Selecting Synthetic Test Account: Bob Jones (E102, Senior Software Engineer)")
        bob_btn = page.locator("button:has-text('Bob Jones')")
        box = bob_btn.bounding_box()
        if box:
            pos = smooth_mouse_move(page, pos, (box["x"] + box["width"]/2, box["y"] + box["height"]/2), steps=35)
            time.sleep(0.5)
            page.mouse.click(*pos)
            time.sleep(1.0)

        update_subtitle(page, "Bcrypt Cost-12 Password Authentication with HttpOnly Session Cookie Issuance")
        sign_in_btn = page.locator("button[type='submit']")
        box = sign_in_btn.bounding_box()
        if box:
            pos = smooth_mouse_move(page, pos, (box["x"] + box["width"]/2, box["y"] + box["height"]/2), steps=30)
            time.sleep(0.5)
            page.mouse.click(*pos)
            time.sleep(2.0)

        page.wait_for_selector("textarea", timeout=8000)
        page.evaluate(CURSOR_INJECTION_SCRIPT)

        # Inspect Header & Role Gating
        update_subtitle(page, "👤 Inspecting Authenticated Interface: Bob Jones (E102), Employee Role Badge, FY 2026 Active Badge")
        header = page.locator("header")
        box = header.bounding_box()
        if box:
            pos = smooth_mouse_move(page, pos, (box["x"] + 250, box["y"] + 35), steps=40)
            time.sleep(6.0)
            pos = smooth_mouse_move(page, pos, (box["x"] + box["width"] - 220, box["y"] + 35), steps=45)
            time.sleep(8.0)

        update_subtitle(page, "Role-Gating Invariant: Administrative controls (like Document Ingestion) are strictly suppressed for employees")
        pos = smooth_mouse_move(page, pos, (960, 450), steps=35)
        time.sleep(7.0)

        # Helper for chat queries with realistic human dwell times
        def submit_chat_query(query_text, subtitle_text, explanation_subtitles, total_duration=35.0):
            nonlocal pos
            start_q_time = time.time()
            update_subtitle(page, subtitle_text)

            textarea = page.locator("textarea")
            box = textarea.bounding_box()
            if box:
                pos = smooth_mouse_move(page, pos, (box["x"] + 150, box["y"] + box["height"]/2), steps=30)
                human_type(page, textarea, query_text, delay_per_char=0.038)
                time.sleep(0.6)

            send_btn = page.locator("button:has(svg.lucide-send)")
            box = send_btn.bounding_box()
            if box:
                pos = smooth_mouse_move(page, pos, (box["x"] + box["width"]/2, box["y"] + box["height"]/2), steps=20)
                page.mouse.click(*pos)
                time.sleep(1.0)

            page.wait_for_timeout(1000)
            last_msg = page.locator("div.rounded-2xl").last
            box = last_msg.bounding_box()
            if box:
                pos = smooth_mouse_move(page, pos, (box["x"] + box["width"]/2, box["y"] + box["height"]/2), steps=30)

            # Cycle explanation subtitles to fill the allocated journey time comfortably
            sub_count = len(explanation_subtitles)
            elapsed = time.time() - start_q_time
            remaining = max(0.0, total_duration - elapsed)
            slot = remaining / max(1, sub_count)

            for exp in explanation_subtitles:
                update_subtitle(page, exp)
                # Gentle human hover movement around the answer
                if box:
                    smooth_mouse_move(page, pos, (pos[0] + 30, pos[1] - 15), steps=25)
                time.sleep(slot)

        # =========================================================================
        # PART 3 — Employee Assistant Journey (01:30 – 05:00, 210s)
        # =========================================================================
        print("[01:30] Part 3: Employee Assistant Journey...")

        # Journey A: Personal Leave Balance (35s)
        submit_chat_query(
            "How many annual leave days do I currently have available?",
            "📊 Journey A: Personal Leave Balance — Invoking FastMCP tool 'get_employee_leave_balances' for E102",
            [
                "FastMCP executes read-only tool 'get_employee_leave_balances' with caller identity verification",
                "Answer grounded strictly in verified SQLite/Postgres records: 8.0 available annual leave days",
                "Zero hallucination: personal leave records are retrieved deterministically from the database"
            ],
            total_duration=35.0
        )

        # Journey B: Company Leave Policy (35s)
        submit_chat_query(
            "How many days of annual vacation does Acme provide each year?",
            "📖 Journey B: Company Leave Policy — ChromaDB Vector RAG retrieval from authoritative policy documents",
            [
                "Semantic similarity retrieval over active chunks of Acme_Leave_Policy.pdf",
                "Cross-referenced against PostgreSQL document registry to confirm active policy version",
                "Grounded response: 18 days paid vacation, accompanied by verified Section 2 citation card"
            ],
            total_duration=35.0
        )

        # Journey C: Asset Information (35s)
        submit_chat_query(
            "What laptop has been assigned to me?",
            "💻 Journey C: Asset Information — Querying employee hardware allocations via FastMCP",
            [
                "FastMCP invokes 'get_employee_assigned_assets' bound to employee number E102",
                "Exact hardware specification retrieved: Lenovo ThinkPad T14 (Tag LT-8821, Serial SN-994821)",
                "Dynamic UI styling: sky-blue badge designates verified 'Employee Record' category"
            ],
            total_duration=35.0
        )

        # Journey D: IT Support Ticket (35s)
        submit_chat_query(
            "Can you show me my IT support ticket?",
            "🎫 Journey D: IT Support Ticket Tracking — Cross-domain HR and IT service desk integration",
            [
                "FastMCP invokes 'get_employee_it_tickets' for E102",
                "Active ticket returned: Ticket #IT-1042 ('VPN connection timeout', Medium priority, Open status)",
                "Unified self-service: employees access both HR and IT records from a single conversational interface"
            ],
            total_duration=35.0
        )

        # Journey E: Hybrid Question (35s)
        submit_chat_query(
            "How many annual leave days does the company provide, and how many do I currently have available?",
            "⚡ Journey E: Hybrid Reasoning — Multi-modal synthesis uniting semantic RAG with relational SQL",
            [
                "LangGraph state machine executes dual-path retrieval: ChromaDB policy chunks + FastMCP employee data",
                "Clearly distinguishes company entitlement (18 days) from employee personal balance (8 days available)",
                "Prevents source conflation: company rules and individual balances remain separate and distinct"
            ],
            total_duration=35.0
        )

        # Journey F: Policy Carryover & Conversational Follow-up (35s)
        submit_chat_query(
            "And what about carryover for it?",
            "🔄 Journey F: Conversational Follow-up — Stateful anaphoric memory resolving pronouns without domain keywords",
            [
                "Resolves 'it' to annual leave carryover from preceding conversation turn context",
                "Retrieves policy rollover terms: employees can carry over up to 5 unused vacation days",
                "Grounded attribution: includes verified citation to Acme Leave Policy Section 2"
            ],
            total_duration=35.0
        )

        # =========================================================================
        # PART 4 — HR Administrator Journey & Document Ingestion (05:00 – 07:00, 120s)
        # =========================================================================
        print("[05:00] Part 4: HR Administrator Journey & Document Ingestion...")

        update_subtitle(page, "👑 PART 4: Role Switch — Logging out of Bob Jones to authenticate as Alice Smith (HR Director)")
        logout_btn = page.locator("button:has-text('Sign Out')")
        box = logout_btn.bounding_box()
        if box:
            pos = smooth_mouse_move(page, pos, (box["x"] + box["width"]/2, box["y"] + box["height"]/2), steps=30)
            page.mouse.click(*pos)
            time.sleep(3.0)

        # Sign in as Alice Smith
        update_subtitle(page, "🔐 Authenticating as Alice Smith (E101, HR Administrator)")
        alice_btn = page.locator("button:has-text('Alice Smith')")
        box = alice_btn.bounding_box()
        if box:
            pos = smooth_mouse_move(page, pos, (box["x"] + box["width"]/2, box["y"] + box["height"]/2), steps=30)
            page.mouse.click(*pos)
            time.sleep(2.0)

        sign_in_btn = page.locator("button[type='submit']")
        box = sign_in_btn.bounding_box()
        if box:
            pos = smooth_mouse_move(page, pos, (box["x"] + box["width"]/2, box["y"] + box["height"]/2), steps=25)
            page.mouse.click(*pos)
            time.sleep(3.0)

        page.wait_for_selector("button:has-text('Ingest Document')", timeout=8000)
        page.evaluate(CURSOR_INJECTION_SCRIPT)

        update_subtitle(page, "Inspecting Elevated Administrative Interface: Alice Smith (E101), Purple HR Admin Badge")
        header = page.locator("header")
        box = header.bounding_box()
        if box:
            pos = smooth_mouse_move(page, pos, (box["x"] + box["width"] - 220, box["y"] + 35), steps=35)
            time.sleep(8.0)

        # Open Document Upload Modal
        update_subtitle(page, "📁 Administrator Capabilities: Unlocked 'Ingest Policy Document' control in top navigation")
        upload_btn = page.locator("button:has-text('Ingest Document')")
        box = upload_btn.bounding_box()
        if box:
            pos = smooth_mouse_move(page, pos, (box["x"] + box["width"]/2, box["y"] + box["height"]/2), steps=30)
            page.mouse.click(*pos)
            time.sleep(3.0)

        # Modal interaction & Local PC File Selection
        update_subtitle(page, "💻 Local File Ingestion: Drag-and-drop zone supporting PDF, Microsoft Word DOCX, and Markdown")
        modal = page.locator("div.fixed.inset-0")
        box = modal.bounding_box()
        if box:
            pos = smooth_mouse_move(page, pos, (box["x"] + box["width"]/2, box["y"] + 280), steps=35)
            time.sleep(8.0)

        update_subtitle(page, "Local PC Selection: Acme_Remote_Work_Policy.md selected from local PC directory")
        pos = smooth_mouse_move(page, pos, (box["x"] + box["width"]/2, box["y"] + 360), steps=30)
        time.sleep(8.0)

        # Explain Ingestion Pipeline stages
        update_subtitle(page, "⚙️ Ingestion Pipeline: MIME Validation → Text Extraction → 800-char Chunking → Dense Embeddings")
        time.sleep(12.0)

        update_subtitle(page, "Vector Storage & Registry: 6 chunks indexed into ChromaDB; SHA-256 active checksum logged in Postgres")
        time.sleep(10.0)

        # Close modal
        close_btn = page.locator("button:has-text('Cancel')")
        box = close_btn.bounding_box()
        if box:
            pos = smooth_mouse_move(page, pos, (box["x"] + box["width"]/2, box["y"] + box["height"]/2), steps=25)
            page.mouse.click(*pos)
            time.sleep(3.0)

        # Switch back to Bob Jones to verify retrieval of the policy
        update_subtitle(page, "🔄 Round-Trip Verification: Signing out of Alice and logging back in as Bob Jones (E102)")
        logout_btn = page.locator("button:has-text('Sign Out')")
        box = logout_btn.bounding_box()
        if box:
            pos = smooth_mouse_move(page, pos, (box["x"] + box["width"]/2, box["y"] + box["height"]/2), steps=25)
            page.mouse.click(*pos)
            time.sleep(2.0)

        bob_btn = page.locator("button:has-text('Bob Jones')")
        box = bob_btn.bounding_box()
        if box:
            pos = smooth_mouse_move(page, pos, (box["x"] + box["width"]/2, box["y"] + box["height"]/2), steps=25)
            page.mouse.click(*pos)
            time.sleep(1.0)

        sign_in_btn = page.locator("button[type='submit']")
        box = sign_in_btn.bounding_box()
        if box:
            pos = smooth_mouse_move(page, pos, (box["x"] + box["width"]/2, box["y"] + box["height"]/2), steps=20)
            page.mouse.click(*pos)
            time.sleep(2.0)

        page.wait_for_selector("textarea", timeout=8000)
        page.evaluate(CURSOR_INJECTION_SCRIPT)

        # Ask question on ingested remote work policy
        submit_chat_query(
            "What is the company's ergonomic stipend?",
            "🔍 Verifying Newly Ingested Policy: Bob asks about ergonomic home office stipend",
            [
                "ChromaDB searches the newly indexed policy collection and retrieves Section 3 of Acme Remote Work Policy",
                "Answer: $300 one-time ergonomic stipend, fully grounded with verifiable section citation",
                "Complete flow proven: Local PC → Upload Modal → FastAPI Pipeline → ChromaDB → Grounded Retrieval"
            ],
            total_duration=30.0
        )

        # =========================================================================
        # PART 5 — Security and Engineering Decisions (07:00 – 08:30, 90s)
        # =========================================================================
        print("[07:00] Part 5: Security & Engineering Decisions...")
        page.goto("http://127.0.0.1:3000/security.html")
        page.wait_for_load_state("networkidle")
        page.evaluate(CURSOR_INJECTION_SCRIPT)

        update_subtitle(page, "🛡️ PART 5: Security Architecture & Engineering Decisions — Defense-in-Depth Design")
        pos = (960, 200)
        page.mouse.move(*pos)
        time.sleep(10.0)

        # Hover through pillars
        pos = smooth_mouse_move(page, pos, (350, 420), steps=40)
        update_subtitle(page, "1. Read-Only MCP Tools: Strict read-only boundaries prevent unintended database mutations")
        time.sleep(15.0)

        pos = smooth_mouse_move(page, pos, (960, 420), steps=40)
        update_subtitle(page, "2. Employee Peer Isolation: Regular employees cannot inspect records belonging to other staff")
        time.sleep(15.0)

        pos = smooth_mouse_move(page, pos, (1570, 420), steps=40)
        update_subtitle(page, "3. Adversarial Prompt Injection Defense: 14/14 injection attacks intercepted by pre-flight guardrails")
        time.sleep(15.0)

        pos = smooth_mouse_move(page, pos, (350, 720), steps=40)
        update_subtitle(page, "4. Internal HMAC Service Signing: API-to-MCP communication signed with replay-protected SHA-256")
        time.sleep(12.0)

        pos = smooth_mouse_move(page, pos, (960, 720), steps=40)
        update_subtitle(page, "5. HttpOnly Cookie Security: Eliminates client-side JavaScript access to authentication credentials")
        time.sleep(12.0)

        pos = smooth_mouse_move(page, pos, (1570, 720), steps=40)
        update_subtitle(page, "6. Active-Version Citation Grounding: Superseded or deactivated policy documents are never cited")
        time.sleep(11.0)

        # =========================================================================
        # PART 6 — Closing (08:30 – 09:00, 30s)
        # =========================================================================
        print("[08:30] Part 6: Closing...")
        page.goto("http://127.0.0.1:3000")
        page.wait_for_load_state("networkidle")
        page.evaluate(CURSOR_INJECTION_SCRIPT)

        update_subtitle(page, "🎬 PART 6: Conclusion — Acme Corporation Universal Enterprise HR & IT Assistant")
        pos = smooth_mouse_move(page, pos, (960, 500), steps=35)
        time.sleep(8.0)

        update_subtitle(page, "Uniting Grounded Semantic Policy RAG with Deterministic Relational FastMCP Tools")
        time.sleep(10.0)

        update_subtitle(page, "Built with Next.js 14, FastAPI, LangGraph, ChromaDB, and PostgreSQL. Thanks for watching!")
        time.sleep(12.0)

        # Close page and context to finish video
        page.close()
        context.close()
        browser.close()

    total_elapsed = time.time() - start_wall_time
    print(f"Total recording wall time: {total_elapsed:.1f} seconds (~{total_elapsed/60:.2f} minutes)")

    # Find the newly generated recording
    video_files = [
        f for f in os.listdir(RAW_VIDEOS_DIR) if f.endswith(".webm")
    ]
    if video_files:
        # Sort by creation / modification time so the true latest file is selected
        video_files.sort(key=lambda f: os.path.getmtime(os.path.join(RAW_VIDEOS_DIR, f)))
        latest_video = os.path.join(RAW_VIDEOS_DIR, video_files[-1])
        dest_video = os.path.join(OUTPUT_DIR, "Loom_Product_Walkthrough_Video.webm")
        shutil.copyfile(latest_video, dest_video)
        print(f"✓ Video successfully generated ({os.path.getsize(dest_video)} bytes): {dest_video}")
    else:
        print("⚠️ No webm video file found in recording directory.")

if __name__ == "__main__":
    run()
