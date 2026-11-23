"""
Automated 1920x1080 Screen Recorder for Archie Product Demo (60 FPS CFR Target).
Synchronized with Archie Product Demo Narration.
Standard: ESR-STD-v2.4 | Repository: aadil-lang/universal-enterprise-assistant
"""

import os
import sys
import time
import json
import subprocess
from playwright.sync_api import sync_playwright

RAW_VIDEO_DIR = os.path.abspath("artifacts/demo/raw_video_archie")
AUDIO_DIR = os.path.abspath("artifacts/demo/audio_archie")
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
    cursor.style.backgroundColor = 'rgba(79, 70, 229, 0.9)'; // Indigo branding
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
        <div style="text-align: center; max-width: 800px; padding: 40px;">
            <div style="font-size: 64px; font-weight: 800; letter-spacing: -0.03em; margin-bottom: 16px; background: linear-gradient(135deg, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Archie
            </div>
            <div style="font-size: 28px; font-weight: 500; color: #e2e8f0; margin-bottom: 24px;">
                Personalized Conversational Voice Assistant
            </div>
            <div style="display: inline-block; padding: 8px 20px; border-radius: 9999px; background: rgba(99, 102, 241, 0.2); border: 1px solid rgba(99, 102, 241, 0.4); font-size: 18px; font-weight: 600; color: #a5b4fc; letter-spacing: 0.05em; text-transform: uppercase;">
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
        <div style="text-align: center; max-width: 850px; padding: 40px;">
            <div style="display: inline-flex; align-items: center; gap: 12px; margin-bottom: 20px;">
                <div style="width: 20px; height: 20px; border-radius: 50%; background: #22c55e;"></div>
                <span style="font-size: 16px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.1em;">Production Architecture Verified</span>
            </div>
            <div style="font-size: 68px; font-weight: 800; letter-spacing: -0.03em; margin-bottom: 16px; background: linear-gradient(135deg, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Archie
            </div>
            <div style="font-size: 32px; font-weight: 500; font-style: italic; color: #e2e8f0; margin-bottom: 32px;">
                One Assistant. One Conversation. Smarter Employee Services.
            </div>
            <div style="display: flex; justify-content: center; gap: 32px; color: #94a3b8; font-size: 15px;">
                <div><strong style="color: #cbd5e1;">Next.js</strong> Frontend</div>
                <div>•</div>
                <div><strong style="color: #cbd5e1;">FastAPI</strong> Backend</div>
                <div>•</div>
                <div><strong style="color: #cbd5e1;">LangGraph</strong> Orchestration</div>
                <div>•</div>
                <div><strong style="color: #cbd5e1;">PostgreSQL</strong> Persistence</div>
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

def smooth_type(page, locator, text, delay_per_char=0.022):
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

def record_archie_demo():
    # Load timings if available
    timings_file = os.path.join(AUDIO_DIR, "scene_timings.json")
    scene_targets = {}
    if os.path.exists(timings_file):
        with open(timings_file, "r", encoding="utf-8") as f:
            tdata = json.load(f)
            for sc, info in tdata.get("scenes", {}).items():
                scene_targets[sc] = info["duration"]
    print("Loaded scene duration targets:", scene_targets)

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

        # PRE-FLIGHT: Navigate to http://localhost:3000 and ensure logged out
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
        # SCENE 1: Introduction (Target: ~24s)
        # =====================================================================
        s1_target = scene_targets.get("s1", 24.5)
        print(f"\n--- [Scene 1] Introduction (Target: {s1_target:.2f}s) ---")
        s1_start = time.time()
        
        # Display title card for first 4.5 seconds
        page.evaluate(TITLE_CARD_SCRIPT)
        time.sleep(4.5)
        # Fade out title card
        page.evaluate("(() => { const c = document.getElementById('demo-title-card'); if (c) { c.style.opacity = '0'; setTimeout(() => c.remove(), 800); } })()")
        time.sleep(1.0)
        inject_cursor()

        # Smooth camera / cursor movements over landing page
        smooth_move(page, 960, 320, steps=25)
        time.sleep(3.0)
        smooth_move(page, 960, 480, steps=25)
        time.sleep(3.0)
        smooth_move(page, 960, 620, steps=20)
        time.sleep(3.0)

        # Pad remaining time for Scene 1
        elapsed = time.time() - s1_start
        if elapsed < s1_target:
            time.sleep(s1_target - elapsed)
        print(f"Scene 1 completed in {time.time() - s1_start:.2f}s")

        # =====================================================================
        # SCENE 2: Personalized Voice Interaction (Target: ~30s)
        # =====================================================================
        s2_target = scene_targets.get("s2", 30.5)
        print(f"\n--- [Scene 2] Personalized Voice Interaction (Target: {s2_target:.2f}s) ---")
        s2_start = time.time()

        # Move to Bob Jones login
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

        # Show authenticated identity
        smooth_move(page, 300, 140, steps=20) # Over identity badge
        time.sleep(2.5)

        # Move to Archie Voice Assistant control widget & Click "Enable Voice"
        enable_btn = page.locator('button:has-text("Enable Voice")')
        if enable_btn.count() > 0:
            smooth_click(page, enable_btn.first, wait_after=1.5)
        
        # State enters WAKE_WORD_LISTENING
        page.wait_for_selector('text=Waiting for "Hey Archie"', timeout=10000)
        time.sleep(2.5)

        # Trigger Wake Phrase: "Hey Archie"
        print("  Triggering 'Hey Archie' wake phrase...")
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('Hey Archie', true)")
        time.sleep(1.0)

        # Archie transitions to GREETING / SPEAKING
        # Greeting plays: "Hey Bob! Good afternoon. How can I help you today?"
        smooth_move(page, 960, 200, steps=20) # Over Archie status banner
        time.sleep(4.5)

        elapsed = time.time() - s2_start
        if elapsed < s2_target:
            time.sleep(s2_target - elapsed)
        print(f"Scene 2 completed in {time.time() - s2_start:.2f}s")

        # =====================================================================
        # SCENE 3: Employee Info & Policy Retrieval (Target: ~39s)
        # =====================================================================
        s3_target = scene_targets.get("s3", 39.0)
        print(f"\n--- [Scene 3] Employee Info & Policy Retrieval (Target: {s3_target:.2f}s) ---")
        s3_start = time.time()

        # Activate mic & submit voice query: "How much annual leave do I have available?"
        page.evaluate("window.__ARCHIE_STATE_MACHINE__.manualActivateMic()")
        time.sleep(0.5)
        print("  Speaking query: 'How much annual leave do I have available?'")
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('How much annual leave do I have available?', true)")
        
        # Wait for chat response to arrive
        time.sleep(7.0)
        inject_cursor()

        # Smoothly move down over the response card and policy citations
        smooth_move(page, 800, 450, steps=20)
        time.sleep(3.0)
        smooth_move(page, 800, 580, steps=20)
        time.sleep(4.0)

        elapsed = time.time() - s3_start
        if elapsed < s3_target:
            time.sleep(s3_target - elapsed)
        print(f"Scene 3 completed in {time.time() - s3_start:.2f}s")

        # =====================================================================
        # SCENE 4: Multi-turn Conversation & Text Switching (Target: ~29s)
        # =====================================================================
        s4_target = scene_targets.get("s4", 29.0)
        print(f"\n--- [Scene 4] Multi-turn & Text Switching (Target: {s4_target:.2f}s) ---")
        s4_start = time.time()

        # Multi-turn follow-up without wake word
        page.evaluate("window.__ARCHIE_STATE_MACHINE__.manualActivateMic()")
        time.sleep(0.5)
        print("  Speaking follow-up: 'Can I carry forward unused days to next year?'")
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('Can I carry forward unused days to next year?', true)")
        time.sleep(6.5)

        # Switch to typing in the same chat thread
        chat_input = page.locator('textarea:not([disabled])')
        smooth_type(page, chat_input, "What is the maximum number of consecutive leave days allowed?")
        time.sleep(0.5)
        send_btn = page.locator('button[title="Send query"]')
        smooth_click(page, send_btn, wait_after=3.5)

        elapsed = time.time() - s4_start
        if elapsed < s4_target:
            time.sleep(s4_target - elapsed)
        print(f"Scene 4 completed in {time.time() - s4_start:.2f}s")

        # =====================================================================
        # SCENE 5: Real HR Transaction & Confirmation (Target: ~52s)
        # =====================================================================
        s5_target = scene_targets.get("s5", 52.0)
        print(f"\n--- [Scene 5] Real HR Transaction & Confirmation (Target: {s5_target:.2f}s) ---")
        s5_start = time.time()

        # Submit leave application via voice
        page.evaluate("window.__ARCHIE_STATE_MACHINE__.manualActivateMic()")
        time.sleep(0.5)
        print("  Speaking request: 'I want to apply for annual leave from December 10 to December 12, 2026'")
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('I want to apply for annual leave from December 10 to December 12, 2026', true)")
        time.sleep(7.0)

        # Confirmation card rendered with [Confirm Submission] button
        confirm_btn = page.locator('button:has-text("Confirm Submission")')
        page.wait_for_selector('button:has-text("Confirm Submission")', timeout=10000)
        inject_cursor()
        smooth_move(page, 750, 600, steps=20) # Hover near confirmation details
        time.sleep(2.5)

        # Spoken confirmation attempt: "Yes, submit it"
        print("  Attempting spoken confirmation: 'Yes, submit it'...")
        page.evaluate("window.__ARCHIE_STATE_MACHINE__.manualActivateMic()")
        time.sleep(0.5)
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('Yes, submit it', true)")
        time.sleep(4.0)

        # Highlight refusal message and unclicked button
        smooth_move(page, 750, 700, steps=15)
        time.sleep(2.5)

        # Explicit UI confirmation: click [Confirm Submission] button
        print("  Clicking explicit UI [Confirm Submission] button...")
        smooth_click(page, confirm_btn.first, wait_after=3.5)
        page.wait_for_selector('text=Action Confirmed & Executed', timeout=15000)
        smooth_move(page, 750, 650, steps=15) # Over green execution badge
        time.sleep(4.0)

        elapsed = time.time() - s5_start
        if elapsed < s5_target:
            time.sleep(s5_target - elapsed)
        print(f"Scene 5 completed in {time.time() - s5_start:.2f}s")

        # =====================================================================
        # SCENE 6: Additional Enterprise Capabilities (Target: ~26s)
        # =====================================================================
        s6_target = scene_targets.get("s6", 26.0)
        print(f"\n--- [Scene 6] Additional Enterprise Capabilities (Target: {s6_target:.2f}s) ---")
        s6_start = time.time()

        # Query open requests/tickets
        chat_input = page.locator('textarea:not([disabled])')
        smooth_type(page, chat_input, "What is the status of my open requests?")
        time.sleep(0.5)
        send_btn = page.locator('button[title="Send query"]')
        smooth_click(page, send_btn, wait_after=5.0)

        smooth_move(page, 800, 600, steps=20)
        time.sleep(4.0)

        elapsed = time.time() - s6_start
        if elapsed < s6_target:
            time.sleep(s6_target - elapsed)
        print(f"Scene 6 completed in {time.time() - s6_start:.2f}s")

        # =====================================================================
        # SCENE 7: Architecture & Conclusion (Target: ~28s)
        # =====================================================================
        s7_target = scene_targets.get("s7", 28.0)
        print(f"\n--- [Scene 7] Architecture & Conclusion (Target: {s7_target:.2f}s) ---")
        s7_start = time.time()

        # Smooth scroll through unified chat thread
        smooth_move(page, 960, 400, steps=15)
        page.mouse.wheel(0, -600)
        time.sleep(3.0)
        page.mouse.wheel(0, 600)
        time.sleep(3.0)

        # Show final title card
        print("  Displaying final closing card...")
        page.evaluate(END_CARD_SCRIPT)
        time.sleep(12.0)

        elapsed = time.time() - s7_start
        if elapsed < s7_target:
            time.sleep(s7_target - elapsed)
        print(f"Scene 7 completed in {time.time() - s7_start:.2f}s")

        # Close page and context to flush video
        print("\nClosing context and browser to finalize raw video...")
        page.close()
        context.close()
        browser.close()
        print("Browser recording complete.")

if __name__ == "__main__":
    record_archie_demo()
