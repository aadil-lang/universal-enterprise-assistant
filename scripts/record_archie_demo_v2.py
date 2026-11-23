"""
Automated 1920x1080 Screen Recorder for Archie Product Demo (v2).
Demonstrates both Employee (Bob Jones) and HR Administrator (Alice Smith) Journeys.
Target Duration: Exactly 299.0 seconds (4:59).
Standard: ESR-STD-v2.4 | Repository: aadil-lang/universal-enterprise-assistant
"""

import os
import sys
import time
import json
import subprocess
from playwright.sync_api import sync_playwright

RAW_VIDEO_DIR = os.path.abspath("artifacts/demo/raw_video_archie_v2")
AUDIO_DIR = os.path.abspath("artifacts/demo/audio_archie_v2")
OUTPUT_DIR = os.path.abspath("artifacts/demo")
os.makedirs(RAW_VIDEO_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

CURSOR_SCRIPT = """
(() => {
    if (document.getElementById('demo-cursor')) return;
    const cursor = document.createElement('div');
    cursor.id = 'demo-cursor';
    cursor.style.position = 'fixed';
    cursor.style.width = '24px';
    cursor.style.height = '24px';
    cursor.style.borderRadius = '50%';
    cursor.style.backgroundColor = 'rgba(79, 70, 229, 0.9)';
    cursor.style.border = '2px solid #ffffff';
    cursor.style.boxShadow = '0 0 12px rgba(0,0,0,0.45)';
    cursor.style.pointerEvents = 'none';
    cursor.style.zIndex = '9999999';
    cursor.style.transition = 'transform 0.12s ease-out, background-color 0.15s ease';
    cursor.style.transform = 'translate(-50%, -50%)';
    cursor.style.top = '100px';
    cursor.style.left = '100px';
    document.body.appendChild(cursor);

    window.addEventListener('mousemove', (e) => {
        cursor.style.left = e.clientX + 'px';
        cursor.style.top = e.clientY + 'px';
    });

    window.addEventListener('mousedown', () => {
        cursor.style.transform = 'translate(-50%, -50%) scale(0.8)';
        cursor.style.backgroundColor = 'rgba(67, 56, 202, 1)';
    });

    window.addEventListener('mouseup', () => {
        cursor.style.transform = 'translate(-50%, -50%) scale(1)';
        cursor.style.backgroundColor = 'rgba(79, 70, 229, 0.9)';
    });
})();
"""

TITLE_CARD_SCRIPT = """
(() => {
    if (document.getElementById('demo-title-card')) return;
    const card = document.createElement('div');
    card.id = 'demo-title-card';
    card.style.position = 'fixed';
    card.style.inset = '0';
    card.style.backgroundColor = '#0f172a';
    card.style.display = 'flex';
    card.style.flexDirection = 'column';
    card.style.alignItems = 'center';
    card.style.justifyContent = 'center';
    card.style.zIndex = '9999998';
    card.style.color = '#ffffff';
    card.style.fontFamily = 'system-ui, -apple-system, sans-serif';
    card.style.transition = 'opacity 0.8s ease';
    card.innerHTML = `
        <div style="text-align: center; max-width: 850px; padding: 40px;">
            <div style="font-size: 64px; font-weight: 800; letter-spacing: -0.03em; margin-bottom: 16px; background: linear-gradient(135deg, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Archie
            </div>
            <div style="font-size: 28px; font-weight: 500; color: #e2e8f0; margin-bottom: 24px;">
                Personalized Conversational Voice Assistant
            </div>
            <div style="display: flex; justify-content: center; gap: 16px; margin-bottom: 24px;">
                <span style="display: inline-block; padding: 6px 18px; border-radius: 9999px; background: rgba(59, 130, 246, 0.2); border: 1px solid rgba(59, 130, 246, 0.4); font-size: 15px; font-weight: 600; color: #93c5fd;">
                    Employee Self-Service (Bob)
                </span>
                <span style="display: inline-block; padding: 6px 18px; border-radius: 9999px; background: rgba(168, 85, 247, 0.2); border: 1px solid rgba(168, 85, 247, 0.4); font-size: 15px; font-weight: 600; color: #d8b4fe;">
                    HR Administrator Governance (Alice)
                </span>
            </div>
            <div style="font-size: 18px; font-weight: 600; color: #94a3b8; letter-spacing: 0.05em; text-transform: uppercase;">
                One Assistant · One Conversation · Smarter Employee Services
            </div>
        </div>
    `;
    document.body.appendChild(card);
})();
"""

END_CARD_SCRIPT = """
(() => {
    let card = document.getElementById('demo-title-card');
    if (!card) {
        card = document.createElement('div');
        card.id = 'demo-title-card';
        card.style.position = 'fixed';
        card.style.inset = '0';
        card.style.backgroundColor = '#0f172a';
        card.style.display = 'flex';
        card.style.flexDirection = 'column';
        card.style.alignItems = 'center';
        card.style.justifyContent = 'center';
        card.style.zIndex = '9999998';
        card.style.color = '#ffffff';
        card.style.fontFamily = 'system-ui, -apple-system, sans-serif';
        document.body.appendChild(card);
    }
    card.style.opacity = '0';
    card.style.transition = 'opacity 0.8s ease';
    card.innerHTML = `
        <div style="text-align: center; max-width: 900px; padding: 40px;">
            <div style="display: inline-flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                <div style="width: 20px; height: 20px; border-radius: 50%; background: #22c55e;"></div>
                <span style="font-size: 16px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.1em;">Production Architecture Verified · ESR-STD-v2.4</span>
            </div>
            <div style="font-size: 68px; font-weight: 800; letter-spacing: -0.03em; margin-bottom: 16px; background: linear-gradient(135deg, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Archie
            </div>
            <div style="font-size: 30px; font-weight: 500; font-style: italic; color: #e2e8f0; margin-bottom: 32px;">
                One Assistant. One Conversation. Smarter Employee Services.
            </div>
            <div style="display: flex; justify-content: center; gap: 24px; color: #94a3b8; font-size: 15px;">
                <div><strong style="color: #cbd5e1;">Next.js 14</strong></div>
                <div>•</div>
                <div><strong style="color: #cbd5e1;">FastAPI</strong></div>
                <div>•</div>
                <div><strong style="color: #cbd5e1;">LangGraph</strong></div>
                <div>•</div>
                <div><strong style="color: #cbd5e1;">PostgreSQL</strong></div>
                <div>•</div>
                <div><strong style="color: #cbd5e1;">ChromaDB</strong></div>
                <div>•</div>
                <div><strong style="color: #cbd5e1;">FastMCP</strong></div>
            </div>
        </div>
    `;
    setTimeout(() => { card.style.opacity = '1'; }, 50);
})();
"""

def smooth_move(page, target_x, target_y, steps=18, delay=0.015):
    page.mouse.move(target_x, target_y, steps=steps)
    time.sleep(delay)

def smooth_click(page, locator, wait_after=1.0):
    try:
        box = locator.bounding_box()
        if box:
            target_x = box['x'] + box['width'] / 2
            target_y = box['y'] + box['height'] / 2
            smooth_move(page, target_x, target_y, steps=14)
            time.sleep(0.15)
        locator.click()
        time.sleep(wait_after)
    except Exception as e:
        print(f"Warning in smooth_click: {e}")
        locator.click(force=True)
        time.sleep(wait_after)

def smooth_type(page, locator, text, delay_per_char=0.020):
    try:
        box = locator.bounding_box()
        if box:
            smooth_move(page, box['x'] + box['width'] / 2, box['y'] + box['height'] / 2, steps=12)
            time.sleep(0.1)
        locator.click()
        locator.fill('')
        for char in text:
            page.keyboard.type(char)
            time.sleep(delay_per_char)
        time.sleep(0.2)
    except Exception as e:
        print(f"Warning in smooth_type: {e}")
        locator.fill(text)
        time.sleep(0.2)

def record_v2():
    SCENE_TARGETS = {
        "s1": 32.0,
        "s2": 35.0,
        "s3": 45.0,
        "s4": 40.0,
        "s5": 60.0,
        "s6": 53.0,
        "s7": 34.0,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--window-size=1920,1080",
                "--hide-scrollbars",
                "--autoplay-policy=no-user-gesture-required",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=RAW_VIDEO_DIR,
            record_video_size={"width": 1920, "height": 1080},
            permissions=["microphone"]
        )
        page = context.new_page()

        def inject_cursor():
            try:
                page.evaluate(CURSOR_SCRIPT)
            except Exception:
                pass

        # PRE-FLIGHT
        print("\n[Pre-flight] Preparing clean browser state...")
        page.goto("http://localhost:3000", timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(1000)
        try:
            page.evaluate("localStorage.clear(); sessionStorage.clear();")
            page.reload()
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(1000)
        except Exception:
            pass

        # =====================================================================
        # SCENE 1: Introduction & Dual-Persona Vision (32.0s)
        # =====================================================================
        s1_start = time.time()
        print("\n--- [Scene 1] Introduction & Dual-Persona Vision (Target: 32.0s) ---")
        page.evaluate(TITLE_CARD_SCRIPT)
        time.sleep(6.0)
        page.evaluate("(() => { const c = document.getElementById('demo-title-card'); if (c) { c.style.opacity = '0'; setTimeout(() => c.remove(), 800); } })()")
        time.sleep(1.0)
        inject_cursor()

        smooth_move(page, 960, 320, steps=25)
        time.sleep(4.0)
        smooth_move(page, 960, 480, steps=25)
        time.sleep(4.0)
        smooth_move(page, 960, 620, steps=20)
        time.sleep(4.0)

        rem = SCENE_TARGETS["s1"] - (time.time() - s1_start)
        if rem > 0:
            time.sleep(rem)
        print(f"Scene 1 completed in {time.time() - s1_start:.2f}s")

        # =====================================================================
        # SCENE 2: Bob Login & Voice Activation (35.0s)
        # =====================================================================
        s2_start = time.time()
        print("\n--- [Scene 2] Bob Login & Voice Activation (Target: 35.0s) ---")
        bob_btn = page.locator('button:has-text("Bob Jones")')
        if bob_btn.count() > 0:
            smooth_click(page, bob_btn.first, wait_after=1.2)
        else:
            email_input = page.locator('input[type="email"]')
            smooth_type(page, email_input, "bob@acme.com")
            pwd_input = page.locator('input[type="password"]')
            smooth_type(page, pwd_input, "Password123!")

        submit_btn = page.locator('button[type="submit"], button:has-text("Sign In")')
        smooth_click(page, submit_btn.first, wait_after=2.0)
        page.wait_for_selector('text=Archie', timeout=15000)
        inject_cursor()

        # Show identity
        smooth_move(page, 300, 140, steps=20)
        time.sleep(2.5)

        # Enable Voice Mode
        enable_btn = page.locator('button:has-text("Enable Voice")')
        if enable_btn.count() > 0:
            smooth_click(page, enable_btn.first, wait_after=1.5)

        page.wait_for_selector('text=Waiting for "Hey Archie"', timeout=10000)
        time.sleep(3.0)

        # Wake word: "Hey Archie"
        print("  Triggering 'Hey Archie'...")
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('Hey Archie', true)")
        time.sleep(1.0)

        smooth_move(page, 960, 200, steps=20)
        time.sleep(5.0)

        rem = SCENE_TARGETS["s2"] - (time.time() - s2_start)
        if rem > 0:
            time.sleep(rem)
        print(f"Scene 2 completed in {time.time() - s2_start:.2f}s")

        # =====================================================================
        # SCENE 3: Employee Info & Policy Retrieval (45.0s)
        # =====================================================================
        s3_start = time.time()
        print("\n--- [Scene 3] Employee Info & Policy Retrieval (Target: 45.0s) ---")
        page.evaluate("window.__ARCHIE_STATE_MACHINE__.manualActivateMic()")
        time.sleep(0.5)
        print("  Speaking query: 'How much annual leave do I have available?'")
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('How much annual leave do I have available?', true)")
        time.sleep(7.0)
        inject_cursor()

        smooth_move(page, 800, 450, steps=20)
        time.sleep(4.0)
        smooth_move(page, 800, 580, steps=20)
        time.sleep(4.0)

        rem = SCENE_TARGETS["s3"] - (time.time() - s3_start)
        if rem > 0:
            time.sleep(rem)
        print(f"Scene 3 completed in {time.time() - s3_start:.2f}s")

        # =====================================================================
        # SCENE 4: Continuous Dialogue & Text Switching (40.0s)
        # =====================================================================
        s4_start = time.time()
        print("\n--- [Scene 4] Continuous Dialogue & Text Switching (Target: 40.0s) ---")
        page.evaluate("window.__ARCHIE_STATE_MACHINE__.manualActivateMic()")
        time.sleep(0.5)
        print("  Speaking follow-up: 'Can I carry forward unused days to next year?'")
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('Can I carry forward unused days to next year?', true)")
        time.sleep(6.5)

        # Switch to typing
        chat_input = page.locator('textarea:not([disabled])')
        smooth_type(page, chat_input, "What is the maximum number of consecutive leave days allowed?")
        time.sleep(0.5)
        send_btn = page.locator('button[title="Send query"]')
        smooth_click(page, send_btn, wait_after=4.0)

        rem = SCENE_TARGETS["s4"] - (time.time() - s4_start)
        if rem > 0:
            time.sleep(rem)
        print(f"Scene 4 completed in {time.time() - s4_start:.2f}s")

        # =====================================================================
        # SCENE 5: Real HR Transaction & Explicit Confirmation (60.0s)
        # =====================================================================
        s5_start = time.time()
        print("\n--- [Scene 5] Real HR Transaction & Confirmation (Target: 60.0s) ---")
        page.evaluate("window.__ARCHIE_STATE_MACHINE__.manualActivateMic()")
        time.sleep(0.5)
        print("  Speaking request: 'I want to apply for annual leave from December 10 to December 12, 2026'")
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('I want to apply for annual leave from December 10 to December 12, 2026', true)")
        time.sleep(7.0)

        confirm_btn = page.locator('button:has-text("Confirm Submission")')
        page.wait_for_selector('button:has-text("Confirm Submission")', timeout=10000)
        inject_cursor()
        smooth_move(page, 750, 600, steps=20)
        time.sleep(3.0)

        # Attempt spoken confirmation: "Yes, submit it"
        print("  Attempting spoken confirmation: 'Yes, submit it'...")
        page.evaluate("window.__ARCHIE_STATE_MACHINE__.manualActivateMic()")
        time.sleep(0.5)
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('Yes, submit it', true)")
        time.sleep(4.5)

        smooth_move(page, 750, 700, steps=15)
        time.sleep(3.0)

        # Click UI button
        print("  Clicking UI [Confirm Submission] button...")
        smooth_click(page, confirm_btn.first, wait_after=3.5)
        page.wait_for_selector('text=Action Confirmed & Executed', timeout=15000)
        smooth_move(page, 750, 650, steps=15)
        time.sleep(5.0)

        rem = SCENE_TARGETS["s5"] - (time.time() - s5_start)
        if rem > 0:
            time.sleep(rem)
        print(f"Scene 5 completed in {time.time() - s5_start:.2f}s")

        # =====================================================================
        # SCENE 6: HR Administrator Journey: Alice Smith (53.0s)
        # =====================================================================
        s6_start = time.time()
        print("\n--- [Scene 6] HR Administrator Journey: Alice Smith (Target: 53.0s) ---")
        
        # Bob signs out
        signout_btn = page.locator('button:has-text("Sign Out")')
        if signout_btn.count() > 0:
            smooth_click(page, signout_btn.first, wait_after=2.0)

        inject_cursor()
        alice_btn = page.locator('button:has-text("Alice Smith")')
        if alice_btn.count() > 0:
            smooth_click(page, alice_btn.first, wait_after=1.0)
        
        submit_btn = page.locator('button[type="submit"], button:has-text("Sign In")')
        smooth_click(page, submit_btn.first, wait_after=2.5)

        page.wait_for_selector('text=Archie', timeout=15000)
        inject_cursor()

        # Alice's identity badge: Alice Smith (HR Director)
        smooth_move(page, 300, 140, steps=20)
        time.sleep(2.0)

        # Alice enables voice
        enable_btn = page.locator('button:has-text("Enable Voice")')
        if enable_btn.count() > 0:
            smooth_click(page, enable_btn.first, wait_after=1.5)

        # Alice wake phrase
        print("  Alice speaking wake phrase: 'Hey Archie'...")
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('Hey Archie', true)")
        time.sleep(3.5)

        # Alice cross-employee lookup query via voice
        print("  Alice querying E102 leave balance via voice...")
        page.evaluate("window.__ARCHIE_STATE_MACHINE__.manualActivateMic()")
        time.sleep(0.5)
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('What is the leave balance for employee E102?', true)")
        time.sleep(7.0)
        inject_cursor()

        # Highlight administrative cross-employee record
        smooth_move(page, 800, 520, steps=20)
        time.sleep(4.0)

        rem = SCENE_TARGETS["s6"] - (time.time() - s6_start)
        if rem > 0:
            time.sleep(rem)
        print(f"Scene 6 completed in {time.time() - s6_start:.2f}s")

        # =====================================================================
        # SCENE 7: Enterprise Architecture & Conclusion (34.0s)
        # =====================================================================
        s7_start = time.time()
        print("\n--- [Scene 7] Architecture & Conclusion (Target: 34.0s) ---")
        smooth_move(page, 960, 400, steps=15)
        page.mouse.wheel(0, -500)
        time.sleep(3.0)
        page.mouse.wheel(0, 500)
        time.sleep(3.0)

        print("  Displaying final closing card...")
        page.evaluate(END_CARD_SCRIPT)
        time.sleep(15.0)

        rem = SCENE_TARGETS["s7"] - (time.time() - s7_start)
        if rem > 0:
            time.sleep(rem)
        print(f"Scene 7 completed in {time.time() - s7_start:.2f}s")

        print("\nClosing context and browser to finalize raw video...")
        page.close()
        context.close()
        browser.close()
        print("Browser recording complete.")

if __name__ == "__main__":
    record_v2()
