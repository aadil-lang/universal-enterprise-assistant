"""
Loom-Style Browser Video Recorder with Realistic Mouse Movement,
Click Visualizations, Floating Presenter Bubble, and Subtitles.
"""

import os
import sys
import time
import json
from playwright.sync_api import sync_playwright

BASE_DIR = r"c:\Users\HP\OneDrive\Documents\HR-IT Helpdesk"
VIDEOS_DIR = os.path.join(BASE_DIR, "videos")
os.makedirs(VIDEOS_DIR, exist_ok=True)

CURSOR_INJECTION_SCRIPT = """
(() => {
    // 1. Create stylish virtual cursor
    const cursor = document.createElement('div');
    cursor.id = 'loom-virtual-cursor';
    cursor.style.position = 'fixed';
    cursor.style.top = '0';
    cursor.style.left = '0';
    cursor.style.width = '24px';
    cursor.style.height = '24px';
    cursor.style.borderRadius = '50%';
    cursor.style.backgroundColor = 'rgba(59, 130, 246, 0.7)';
    cursor.style.border = '2.5px solid #ffffff';
    cursor.style.boxShadow = '0 0 12px rgba(59, 130, 246, 0.8), 0 2px 6px rgba(0,0,0,0.3)';
    cursor.style.pointerEvents = 'none';
    cursor.style.zIndex = '999999';
    cursor.style.transform = 'translate(-50%, -50%)';
    cursor.style.transition = 'transform 0.05s ease-out, background-color 0.15s ease';
    document.body.appendChild(cursor);

    // 2. Click ripple effect
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
        cursor.style.backgroundColor = 'rgba(59, 130, 246, 0.7)';
    });

    document.addEventListener('mousemove', (e) => {
        cursor.style.left = e.clientX + 'px';
        cursor.style.top = e.clientY + 'px';
    });

    // 3. Create Loom-style floating subtitle banner
    const subtitle = document.createElement('div');
    subtitle.id = 'loom-subtitle-bar';
    subtitle.style.position = 'fixed';
    subtitle.style.bottom = '24px';
    subtitle.style.left = '50%';
    subtitle.style.transform = 'translateX(-50%)';
    subtitle.style.backgroundColor = 'rgba(15, 23, 42, 0.92)';
    subtitle.style.color = '#f8fafc';
    subtitle.style.padding = '10px 22px';
    subtitle.style.borderRadius = '9999px';
    subtitle.style.fontSize = '13.5px';
    subtitle.style.fontWeight = '500';
    subtitle.style.fontFamily = 'system-ui, -apple-system, sans-serif';
    subtitle.style.boxShadow = '0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.1)';
    subtitle.style.backdropFilter = 'blur(10px)';
    subtitle.style.zIndex = '999990';
    subtitle.style.pointerEvents = 'none';
    subtitle.style.transition = 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)';
    subtitle.style.maxWidth = '80%';
    subtitle.style.textAlign = 'center';
    subtitle.innerText = '👋 Welcome to the Acme Enterprise HR & IT Assistant Demo';
    document.body.appendChild(subtitle);

    // 4. Create Loom-style circular webcam bubble in bottom-left corner
    const webcam = document.createElement('div');
    webcam.id = 'loom-webcam-bubble';
    webcam.style.position = 'fixed';
    webcam.style.bottom = '24px';
    webcam.style.left = '24px';
    webcam.style.width = '100px';
    webcam.style.height = '100px';
    webcam.style.borderRadius = '50%';
    webcam.style.background = 'linear-gradient(135deg, #1e293b, #0f172a)';
    webcam.style.border = '3px solid #3b82f6';
    webcam.style.boxShadow = '0 10px 30px rgba(0,0,0,0.5), 0 0 20px rgba(59,130,246,0.5)';
    webcam.style.zIndex = '999991';
    webcam.style.display = 'flex';
    webcam.style.flexDirection = 'column';
    webcam.style.alignItems = 'center';
    webcam.style.justifyContent = 'center';
    webcam.style.color = '#ffffff';
    webcam.style.fontFamily = 'system-ui, -apple-system, sans-serif';
    webcam.style.pointerEvents = 'none';
    webcam.innerHTML = `
        <div style="width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, #3b82f6, #6366f1); display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px; margin-bottom: 2px;">
            AI
        </div>
        <span style="font-size: 9px; font-weight: 700; color: #93c5fd; letter-spacing: 0.5px;">PRESENTER</span>
    `;
    document.body.appendChild(webcam);

    // Keyframe animation for ripple
    const styleSheet = document.createElement('style');
    styleSheet.textContent = `
        @keyframes loom-ripple {
            0% { width: 6px; height: 6px; opacity: 1; transform: translate(-50%, -50%) scale(1); }
            100% { width: 55px; height: 55px; opacity: 0; transform: translate(-50%, -50%) scale(1.6); }
        }
    `;
    document.head.appendChild(styleSheet);

    window.setLoomSubtitle = (text) => {
        const el = document.getElementById('loom-subtitle-bar');
        if (el) {
            el.style.opacity = '0';
            el.style.transform = 'translateX(-50%) translateY(6px)';
            setTimeout(() => {
                el.innerText = text;
                el.style.opacity = '1';
                el.style.transform = 'translateX(-50%) translateY(0)';
            }, 180);
        }
    };
})();
"""

def smooth_mouse_move(page, start_x, start_y, target_x, target_y, steps=25):
    """Interpolates human-like curved mouse trajectory."""
    for i in range(1, steps + 1):
        t = i / float(steps)
        # Ease in-out cubic interpolation
        t_ease = t * t * (3 - 2 * t)
        curr_x = start_x + (target_x - start_x) * t_ease
        curr_y = start_y + (target_y - start_y) * t_ease
        page.mouse.move(curr_x, curr_y)
        time.sleep(0.015)
    return target_x, target_y

def move_and_click(page, cur_x, cur_y, selector, steps=28, hover_pause=0.35):
    """Moves cursor smoothly to element center, pauses, and clicks."""
    el = page.wait_for_selector(selector)
    box = el.bounding_box()
    if not box:
        return cur_x, cur_y
    target_x = box["x"] + box["width"] / 2.0
    target_y = box["y"] + box["height"] / 2.0
    cur_x, cur_y = smooth_mouse_move(page, cur_x, cur_y, target_x, target_y, steps=steps)
    time.sleep(hover_pause)
    page.mouse.down()
    time.sleep(0.08)
    page.mouse.up()
    time.sleep(0.2)
    return cur_x, cur_y

def set_subtitle(page, text, sleep_seconds=2.0):
    """Updates the floating Loom subtitle banner."""
    page.evaluate(f"window.setLoomSubtitle({json.dumps(text)})")
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)

def main():
    print("=== RECORDING LOOM-STYLE BROWSER VIDEO ===")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--host-resolver-rules=MAP * 127.0.0.1",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=VIDEOS_DIR,
            record_video_size={"width": 1280, "height": 720}
        )

        page = context.new_page()
        page.goto("http://127.0.0.1:3000", wait_until="networkidle")
        page.evaluate(CURSOR_INJECTION_SCRIPT)

        # Virtual cursor start position (center)
        cur_x, cur_y = 640.0, 360.0
        page.mouse.move(cur_x, cur_y)
        time.sleep(1.0)

        # ---------------------------------------------------------------------
        # Scene 1: Introduction to Acme Assistant Login Screen
        # ---------------------------------------------------------------------
        set_subtitle(page, "👋 Welcome! Today we're exploring the Acme Enterprise HR & IT Assistant.", 3.0)
        set_subtitle(page, "🔒 Notice the unified authentication portal supporting role-based access control.", 3.0)

        # Point to Bob Jones demo login button
        set_subtitle(page, "👤 First, let's log in as Bob Jones (Senior Software Engineer, E102)...", 1.5)
        cur_x, cur_y = move_and_click(page, cur_x, cur_y, "button:has-text('Bob Jones')", steps=30, hover_pause=0.5)
        
        # Point to Sign In button
        set_subtitle(page, "🔑 Clicking 'Sign In' to verify credentials and issue a signed JWT access token...", 1.2)
        cur_x, cur_y = move_and_click(page, cur_x, cur_y, "button[type='submit']", steps=24, hover_pause=0.4)

        # ---------------------------------------------------------------------
        # Scene 2: Authenticated Chat Interface Overview
        # ---------------------------------------------------------------------
        page.wait_for_selector("header")
        page.evaluate(CURSOR_INJECTION_SCRIPT) # Re-inject for new page state if needed
        time.sleep(1.0)

        set_subtitle(page, "✨ We're inside! Look at the top navigation bar showing Acme Corporation, FY 2026.", 3.0)
        
        # Point to User Identity Pill in Header
        user_pill = page.wait_for_selector("div.hidden.sm\\:flex.items-center.space-x-2")
        box = user_pill.bounding_box()
        if box:
            cur_x, cur_y = smooth_mouse_move(page, cur_x, cur_y, box["x"] + box["width"]/2, box["y"] + box["height"]/2, steps=30)
            time.sleep(1.5)
        set_subtitle(page, "🏷️ Bob's identity (E102) and 'EMPLOYEE' role are confirmed. Admin tools are safely hidden.", 3.0)

        # ---------------------------------------------------------------------
        # Scene 3: Structured Record Query (FastMCP Leave Balance)
        # ---------------------------------------------------------------------
        set_subtitle(page, "💬 Let's ask a structured record query: 'What is my current annual leave balance?'", 2.0)
        
        # Move cursor to prompt suggestion chip or input
        textarea = page.wait_for_selector("textarea")
        t_box = textarea.bounding_box()
        cur_x, cur_y = smooth_mouse_move(page, cur_x, cur_y, t_box["x"] + 120, t_box["y"] + 20, steps=25)
        time.sleep(0.3)
        textarea.click()
        
        q1 = "How many annual leave days do I currently have available?"
        page.type("textarea", q1, delay=35)
        time.sleep(0.5)

        # Move to send button and click
        cur_x, cur_y = move_and_click(page, cur_x, cur_y, "button[title='Send query']", steps=20, hover_pause=0.3)
        set_subtitle(page, "⚡ Assistant queries the FastMCP employee database in real-time...", 1.8)

        # Wait for assistant response
        page.wait_for_selector("span:has-text('Employee Record')")
        time.sleep(1.0)
        
        # Hover over the assistant response card
        resp_card = page.wait_for_selector("div:has-text('8.00 days of annual leave')")
        r_box = resp_card.bounding_box()
        if r_box:
            cur_x, cur_y = smooth_mouse_move(page, cur_x, cur_y, r_box["x"] + 160, r_box["y"] + 40, steps=25)
        set_subtitle(page, "🎯 Exact calculation: 20 accrued - 10 used - 2 pending = 8.00 days available!", 3.5)

        # ---------------------------------------------------------------------
        # Scene 4: Unstructured Policy Query (RAG + Verifiable Citations)
        # ---------------------------------------------------------------------
        set_subtitle(page, "📜 Now let's test RAG retrieval on corporate policy documents...", 2.0)
        
        # Click textarea
        cur_x, cur_y = smooth_mouse_move(page, cur_x, cur_y, t_box["x"] + 120, t_box["y"] + 20, steps=22)
        textarea.click()
        
        q2 = "What is the annual vacation entitlement under company policy?"
        page.type("textarea", q2, delay=35)
        time.sleep(0.5)

        cur_x, cur_y = move_and_click(page, cur_x, cur_y, "button[title='Send query']", steps=18, hover_pause=0.3)
        set_subtitle(page, "🔍 Dense semantic retrieval searching active 14-chunk ChromaDB vector store...", 1.8)

        # Wait for policy response
        page.wait_for_selector("span:has-text('Company Policy')")
        time.sleep(1.0)

        # Hover over citation badge
        cite_badge = page.wait_for_selector("text=[Acme Leave Policy")
        c_box = cite_badge.bounding_box()
        if c_box:
            cur_x, cur_y = smooth_mouse_move(page, cur_x, cur_y, c_box["x"] + 100, c_box["y"] + 15, steps=25)
        set_subtitle(page, "📌 Grounded in truth: 18 days vacation leave cited from Acme Leave Policy, Section 2!", 3.8)

        # ---------------------------------------------------------------------
        # Scene 5: Hybrid Query (Policy Entitlement + Personal Balance)
        # ---------------------------------------------------------------------
        set_subtitle(page, "🔀 Now let's try a hybrid query combining both company policy and personal records...", 2.2)
        
        cur_x, cur_y = smooth_mouse_move(page, cur_x, cur_y, t_box["x"] + 120, t_box["y"] + 20, steps=20)
        textarea.click()

        q3 = "What is the annual leave policy, and how much leave do I have remaining?"
        page.type("textarea", q3, delay=30)
        time.sleep(0.4)

        cur_x, cur_y = move_and_click(page, cur_x, cur_y, "button[title='Send query']", steps=18, hover_pause=0.3)
        set_subtitle(page, "🧠 LangGraph orchestrates parallel RAG dense retrieval and authenticated FastMCP lookup...", 2.0)

        # Wait for hybrid response
        page.wait_for_selector("span:has-text('Hybrid Policy + Employee')")
        time.sleep(1.0)
        
        set_subtitle(page, "🌟 Duality achieved: The general 18-day entitlement is clearly distinguished from Bob's 8.00 days!", 4.0)

        # ---------------------------------------------------------------------
        # Scene 6: Sign Out and Switch to HR Administrator (Alice Smith E101)
        # ---------------------------------------------------------------------
        set_subtitle(page, "🔄 Now, let's demonstrate role elevation: Signing out and switching to HR Director Alice Smith...", 2.5)
        
        # Click Sign Out button in header
        cur_x, cur_y = move_and_click(page, cur_x, cur_y, "button:has-text('Sign Out')", steps=28, hover_pause=0.4)
        
        # Wait for login screen
        page.wait_for_selector("button:has-text('Alice Smith')")
        page.evaluate(CURSOR_INJECTION_SCRIPT)
        time.sleep(1.0)

        # Click Alice Smith demo account
        set_subtitle(page, "👑 Selecting Alice Smith (HR Admin, E101)...", 1.5)
        cur_x, cur_y = move_and_click(page, cur_x, cur_y, "button:has-text('Alice Smith')", steps=25, hover_pause=0.4)

        cur_x, cur_y = move_and_click(page, cur_x, cur_y, "button[type='submit']", steps=20, hover_pause=0.3)

        # ---------------------------------------------------------------------
        # Scene 7: HR Admin Interface & Document Ingestion Modal
        # ---------------------------------------------------------------------
        page.wait_for_selector("header")
        page.evaluate(CURSOR_INJECTION_SCRIPT)
        time.sleep(1.0)

        set_subtitle(page, "🟣 Note the purple 'HR Admin' badge! The administrative 'Ingest Document' button is now unlocked.", 3.2)
        
        # Hover over Ingest Document button
        cur_x, cur_y = move_and_click(page, cur_x, cur_y, "button:has-text('Ingest Document')", steps=25, hover_pause=0.5)

        # Wait for modal to open
        page.wait_for_selector("text=Ingest Policy Document")
        time.sleep(1.0)

        set_subtitle(page, "📁 The Document Ingestion Pipeline validates supported formats (.pdf, .docx, .md) and rejects invalid files.", 3.5)

        # Close modal
        cur_x, cur_y = move_and_click(page, cur_x, cur_y, "button:has-text('Cancel')", steps=24, hover_pause=0.4)

        # ---------------------------------------------------------------------
        # Scene 8: Conclusion
        # ---------------------------------------------------------------------
        set_subtitle(page, "✅ In summary: Zero hardcoded policy values, strict FastMCP data isolation, and robust RBAC.", 3.8)
        set_subtitle(page, "🚀 The Universal Enterprise HR & IT Assistant is verified, performant, and production-ready!", 4.0)

        time.sleep(2.0)
        
        # Close page and context to finalize video writing
        page.close()
        video_obj = page.video
        video_path = video_obj.path() if video_obj else None
        context.close()
        browser.close()

    print(f"=== VIDEO RECORDING COMPLETE ===")
    print(f"Generated Video Path: {video_path}")
    return video_path

if __name__ == "__main__":
    main()
