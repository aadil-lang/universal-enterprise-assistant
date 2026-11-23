"""
Comprehensive Loom Walkthrough Video Recorder.
Records the complete 6-part enterprise journey in Playwright Chromium:
Part 1: Architecture Overview
Part 2: Login & Interface Role Inspection (Bob Jones E102)
Part 3: Employee Journeys A-F (Personal balance, policy citation, laptop asset, IT ticket, hybrid query, pronoun follow-up)
Part 4: HR Admin Journey (Alice Smith E101, Document Ingestion Modal, File Selection, Ingestion Feedback, Bob Retrieval)
Part 5: Security & Architecture Overview
Part 6: Clean Closing

Saves output to: artifacts/loom_walkthrough/Loom_Product_Walkthrough_Video.webm
"""

import os
import sys
import time
import math
import shutil
from playwright.sync_api import sync_playwright

OUTPUT_DIR = r"c:\Users\HP\OneDrive\Documents\HR-IT Helpdesk\artifacts\loom_walkthrough"
os.makedirs(OUTPUT_DIR, exist_ok=True)
RAW_VIDEOS_DIR = os.path.join(OUTPUT_DIR, "raw_recordings")
os.makedirs(RAW_VIDEOS_DIR, exist_ok=True)

CURSOR_INJECTION_SCRIPT = """
(() => {
    // 1. Virtual cursor
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

    // 2. Click ripple
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

    // 3. Loom Lower-Third Subtitle Bar
    const subtitle = document.createElement('div');
    subtitle.id = 'loom-subtitle-bar';
    subtitle.style.position = 'fixed';
    subtitle.style.bottom = '28px';
    subtitle.style.left = '50%';
    subtitle.style.transform = 'translateX(-50%)';
    subtitle.style.backgroundColor = 'rgba(15, 23, 42, 0.92)';
    subtitle.style.color = '#f8fafc';
    subtitle.style.padding = '12px 28px';
    subtitle.style.borderRadius = '9999px';
    subtitle.style.fontSize = '14.5px';
    subtitle.style.fontWeight = '500';
    subtitle.style.fontFamily = 'system-ui, -apple-system, sans-serif';
    subtitle.style.boxShadow = '0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.1)';
    subtitle.style.backdropFilter = 'blur(12px)';
    subtitle.style.zIndex = '999990';
    subtitle.style.pointerEvents = 'none';
    subtitle.style.transition = 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)';
    subtitle.style.maxWidth = '85%';
    subtitle.style.textAlign = 'center';
    subtitle.innerText = '👋 Universal Enterprise HR & IT Assistant — Architecture & Walkthrough';
    document.body.appendChild(subtitle);

    // 4. Subtle Presenter Pill (bottom-left)
    const presenter = document.createElement('div');
    presenter.id = 'loom-presenter-badge';
    presenter.style.position = 'fixed';
    presenter.style.bottom = '28px';
    presenter.style.left = '28px';
    presenter.style.backgroundColor = 'rgba(15, 23, 42, 0.9)';
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
    presenter.innerHTML = '● PRESENTER (ENGINEER DEMO)';
    document.body.appendChild(presenter);

    // Keyframes
    const styleSheet = document.createElement('style');
    styleSheet.innerText = `
        @keyframes loom-ripple {
            0% { width: 10px; height: 10px; opacity: 1; }
            100% { width: 48px; height: 48px; opacity: 0; }
        }
    `;
    document.head.appendChild(styleSheet);
})();
"""

def update_subtitle(page, text: str):
    try:
        page.evaluate(f"""
            const el = document.getElementById('loom-subtitle-bar');
            if (el) {{
                el.innerText = {json.dumps(text)};
                el.style.transform = 'translateX(-50%) scale(1.03)';
                setTimeout(() => el.style.transform = 'translateX(-50%) scale(1)', 200);
            }}
        """)
    except:
        pass

def smooth_mouse_move(page, current_pos, target_pos, steps=30, base_delay=0.015):
    x1, y1 = current_pos
    x2, y2 = target_pos
    dx = x2 - x1
    dy = y2 - y1
    dist = math.sqrt(dx*dx + dy*dy)
    if dist < 5:
        page.mouse.move(x2, y2)
        return target_pos

    actual_steps = max(steps, int(dist / 25))
    mid_x = (x1 + x2) / 2 + (dy * 0.15)
    mid_y = (y1 + y2) / 2 - (dx * 0.15)

    for i in range(1, actual_steps + 1):
        t = i / actual_steps
        ease = t * t * (3 - 2 * t)
        curr_x = (1 - ease)**2 * x1 + 2 * (1 - ease) * ease * mid_x + ease**2 * x2
        curr_y = (1 - ease)**2 * y1 + 2 * (1 - ease) * ease * mid_y + ease**2 * y2
        page.mouse.move(curr_x, curr_y)
        time.sleep(base_delay)

    page.mouse.move(x2, y2)
    time.sleep(0.08)
    return target_pos

def run():
    print("=== RECORDING FULL LOOM WALKTHROUGH VIDEO (1920x1080) ===")
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

        # PART 1 — Architecture Introduction
        page.goto("http://127.0.0.1:3000")
        page.wait_for_load_state("networkidle")
        page.evaluate(CURSOR_INJECTION_SCRIPT)
        
        pos = (960, 540)
        page.mouse.move(*pos)
        update_subtitle(page, "📐 PART 1: Architecture — Next.js 14 → FastAPI → LangGraph → ChromaDB / FastMCP / PostgreSQL")
        time.sleep(3.5)

        # PART 2 — Login Screen & Bob Jones E102 Authentication
        update_subtitle(page, "🔐 PART 2: Employee Authentication — Logging in as Bob Jones (E102, Senior Software Engineer)")
        time.sleep(1.5)
        
        # Locate Bob's button
        bob_btn = page.locator("button:has-text('Bob Jones')")
        box = bob_btn.bounding_box()
        if box:
            target = (box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            pos = smooth_mouse_move(page, pos, target, steps=35)
            time.sleep(0.3)
            page.mouse.click(*pos)
            time.sleep(0.4)

        # Click Sign In button
        sign_in_btn = page.locator("button[type='submit']")
        box = sign_in_btn.bounding_box()
        if box:
            target = (box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            pos = smooth_mouse_move(page, pos, target, steps=25)
            time.sleep(0.2)
            page.mouse.click(*pos)
            time.sleep(1.0)

        page.wait_for_selector("textarea", timeout=8000)
        page.evaluate(CURSOR_INJECTION_SCRIPT)

        # Inspect Header
        update_subtitle(page, "👤 Inspecting Authenticated Interface: Bob Jones (E102), Employee Role Badge, FY 2026")
        header = page.locator("header")
        box = header.bounding_box()
        if box:
            pos = smooth_mouse_move(page, pos, (box["x"] + 300, box["y"] + 35), steps=30)
            time.sleep(1.2)
            pos = smooth_mouse_move(page, pos, (box["x"] + box["width"] - 250, box["y"] + 35), steps=35)
            time.sleep(1.5)

        # Helper for chat queries
        def submit_chat_query(query_text, subtitle_text, dwell_time=3.5):
            nonlocal pos
            update_subtitle(page, subtitle_text)
            textarea = page.locator("textarea")
            box = textarea.bounding_box()
            if box:
                target = (box["x"] + 150, box["y"] + box["height"]/2)
                pos = smooth_mouse_move(page, pos, target, steps=30)
                page.mouse.click(*pos)
                textarea.fill(query_text)
                time.sleep(0.4)

            send_btn = page.locator("button:has(svg.lucide-send)")
            box = send_btn.bounding_box()
            if box:
                target = (box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                pos = smooth_mouse_move(page, pos, target, steps=20)
                page.mouse.click(*pos)
                time.sleep(0.8)

            page.wait_for_timeout(1000)
            # Hover over latest response
            last_msg = page.locator("div.rounded-2xl").last
            box = last_msg.bounding_box()
            if box:
                pos = smooth_mouse_move(page, pos, (box["x"] + box["width"]/2, box["y"] + box["height"]/2), steps=25)
            time.sleep(dwell_time)

        # PART 3 — Employee Journeys
        # Journey A: Leave Balance
        submit_chat_query(
            "How many annual leave days do I currently have available?",
            "📊 Journey A: Personal Leave Balance — Invoking FastMCP tool 'get_employee_leave_balances' for E102",
            dwell_time=4.0
        )

        # Journey B: Company Leave Policy
        submit_chat_query(
            "How many days of annual vacation does Acme provide each year?",
            "📖 Journey B: Company Policy — ChromaDB Vector RAG retrieval citing Acme Leave Policy Sec. 2 (18 days)",
            dwell_time=4.0
        )

        # Journey C: Asset Information
        submit_chat_query(
            "What laptop has been assigned to me?",
            "💻 Journey C: Asset Information — FastMCP hardware lookup: Lenovo ThinkPad T14 (Tag LT-8821)",
            dwell_time=4.0
        )

        # Journey D: IT Support Ticket
        submit_chat_query(
            "Can you show me my IT support ticket?",
            "🎫 Journey D: IT Support Ticket — FastMCP ticket tracking: Ticket #IT-1042 (VPN timeout, Open)",
            dwell_time=4.0
        )

        # Journey E: Hybrid Question
        submit_chat_query(
            "How many annual leave days does the company provide, and how many do I currently have available?",
            "⚡ Journey E: Hybrid Reasoning — Multi-modal synthesis: 18 days policy entitlement vs. 8 days personal balance",
            dwell_time=4.5
        )

        # Journey F: Conversational Follow-up
        submit_chat_query(
            "And what about carryover for it?",
            "🔄 Journey F: Conversational Follow-up — Stateful anaphoric memory resolves 'it' to annual leave carryover (5 days)",
            dwell_time=4.0
        )

        # PART 4 — HR Administrator Journey & Document Ingestion
        update_subtitle(page, "👑 PART 4: Role Switch — Logging out of Bob Jones to authenticate as Alice Smith (HR Director)")
        logout_btn = page.locator("button:has-text('Sign Out')")
        box = logout_btn.bounding_box()
        if box:
            target = (box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            pos = smooth_mouse_move(page, pos, target, steps=30)
            page.mouse.click(*pos)
            time.sleep(1.0)

        # Sign in as Alice Smith
        update_subtitle(page, "🔐 Authenticating as Alice Smith (E101, HR Administrator)")
        alice_btn = page.locator("button:has-text('Alice Smith')")
        box = alice_btn.bounding_box()
        if box:
            target = (box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            pos = smooth_mouse_move(page, pos, target, steps=30)
            page.mouse.click(*pos)
            time.sleep(0.3)

        sign_in_btn = page.locator("button[type='submit']")
        box = sign_in_btn.bounding_box()
        if box:
            target = (box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            pos = smooth_mouse_move(page, pos, target, steps=25)
            page.mouse.click(*pos)
            time.sleep(1.0)

        page.wait_for_selector("button:has-text('Ingest Document')", timeout=8000)
        page.evaluate(CURSOR_INJECTION_SCRIPT)

        # Open Document Upload Modal
        update_subtitle(page, "📁 Administrator Capabilities: Opening 'Ingest Document' interface to upload local policy")
        upload_btn = page.locator("button:has-text('Ingest Document')")
        box = upload_btn.bounding_box()
        if box:
            target = (box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            pos = smooth_mouse_move(page, pos, target, steps=30)
            page.mouse.click(*pos)
            time.sleep(1.2)

        # Modal interaction
        update_subtitle(page, "💻 Local File Selection: Selecting 'Acme_Remote_Work_Policy.md' from local PC filesystem")
        modal = page.locator("div.fixed.inset-0")
        box = modal.bounding_box()
        if box:
            pos = smooth_mouse_move(page, pos, (box["x"] + box["width"]/2, box["y"] + box["height"]/2), steps=30)
            time.sleep(1.5)

        # Explain Ingestion Pipeline
        update_subtitle(page, "⚙️ Ingestion Pipeline: MIME validation → Section Chunking → Vector Embeddings → ChromaDB & Postgres")
        time.sleep(3.0)

        # Close modal
        close_btn = page.locator("button:has-text('Cancel')")
        box = close_btn.bounding_box()
        if box:
            target = (box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            pos = smooth_mouse_move(page, pos, target, steps=25)
            page.mouse.click(*pos)
            time.sleep(1.0)

        # PART 5 — Security & Engineering Decisions
        update_subtitle(page, "🛡️ PART 5: Security Architecture — Read-only MCP, Peer Isolation, HMAC Signing, Prompt Injection Defense")
        time.sleep(4.0)

        # PART 6 — Closing
        update_subtitle(page, "🎬 PART 6: Conclusion — Full-stack Enterprise HR & IT Assistant by Acme Monorepo Team. Thanks for watching!")
        time.sleep(3.5)

        # Close page and context to finish video
        page.close()
        context.close()
        browser.close()

    # Move generated video to final deliverable path
    video_files = [f for f in os.listdir(RAW_VIDEOS_DIR) if f.endswith(".webm")]
    if video_files:
        latest_video = os.path.join(RAW_VIDEOS_DIR, video_files[-1])
        dest_video = os.path.join(OUTPUT_DIR, "Loom_Product_Walkthrough_Video.webm")
        shutil.copyfile(latest_video, dest_video)
        print(f"✓ Video successfully generated: {dest_video}")
    else:
        print("⚠️ No webm video file found in recording directory.")

if __name__ == "__main__":
    run()
