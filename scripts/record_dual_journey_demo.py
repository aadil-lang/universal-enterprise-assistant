"""
Dual Journey Screen Recorder for Archie Product Demo (Synchronized).
Features:
1. HR Administrator Journey (Alice Smith):
   - RBAC verification (HR Admin badge)
   - Policy Document Ingestion (Acme_Remote_Work_Policy.md)
   - Real-time indexing into ChromaDB (6 chunks generated)
   - Administrative policy retrieval & citation
   - Clean Sign Out
2. Employee Journey (Bob Jones):
   - Employee RBAC verification
   - Archie Voice Mode activation & "Hey Archie" wake word
   - Personalized greeting
   - Spoken leave balance query & multimodal response
   - Continuous dialogue & modality switching to text
   - Transactional leave request with balance validation
   - Security rejection of spoken confirmation ("Yes, submit it")
   - Mandatory UI button confirmation & execution
   - Open requests & multi-domain ticket query
3. Architecture Closing & Summary:
   - Full conversational journey review
   - Tech stack closing card (Next.js 14, FastAPI, LangGraph, PostgreSQL, ChromaDB)

Resolution: 1920x1080 | 60 FPS CFR | Duration: 299.07s (4:59)
Standard: ESR-STD-v2.4 | Repository: aadil-lang/universal-enterprise-assistant
"""

import os
import sys
import time
import json
from playwright.sync_api import sync_playwright

RAW_VIDEO_DIR = os.path.abspath("artifacts/demo/raw_video_dual_journey")
AUDIO_DIR = os.path.abspath("artifacts/demo/audio_dual_journey")
OUTPUT_DIR = os.path.abspath("artifacts/demo")
POLICY_FILE = os.path.abspath("data/policies/Acme_Remote_Work_Policy.md")

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
        <div style="text-align: center; max-width: 920px; padding: 40px;">
            <div style="font-size: 64px; font-weight: 800; letter-spacing: -0.03em; margin-bottom: 16px; background: linear-gradient(135deg, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Archie
            </div>
            <div style="font-size: 28px; font-weight: 500; color: #e2e8f0; margin-bottom: 24px;">
                Personalized Conversational Voice Assistant for Enterprise HR & IT
            </div>
            <div style="display: flex; justify-content: center; gap: 16px; margin-bottom: 24px;">
                <span style="padding: 6px 18px; border-radius: 9999px; background: rgba(168, 85, 247, 0.2); border: 1px solid rgba(168, 85, 247, 0.4); font-size: 14px; font-weight: 600; color: #d8b4fe;">
                    HR Admin Governance &amp; Ingestion
                </span>
                <span style="padding: 6px 18px; border-radius: 9999px; background: rgba(59, 130, 246, 0.2); border: 1px solid rgba(59, 130, 246, 0.4); font-size: 14px; font-weight: 600; color: #93c5fd;">
                    Multimodal Employee Self-Service
                </span>
            </div>
            <div style="font-size: 16px; font-weight: 500; color: #94a3b8; letter-spacing: 0.05em; text-transform: uppercase;">
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
        <div style="text-align: center; max-width: 950px; padding: 40px;">
            <div style="font-size: 68px; font-weight: 800; letter-spacing: -0.03em; margin-bottom: 16px; background: linear-gradient(135deg, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Archie
            </div>
            <div style="font-size: 30px; font-weight: 500; font-style: italic; color: #e2e8f0; margin-bottom: 32px;">
                One Assistant. One Conversation. Smarter Employee Services.
            </div>
            <div style="display: flex; justify-content: center; gap: 20px; color: #94a3b8; font-size: 15px; margin-bottom: 24px;">
                <div><strong style="color: #cbd5e1;">Next.js 14</strong></div>
                <div>•</div>
                <div><strong style="color: #cbd5e1;">FastAPI</strong></div>
                <div>•</div>
                <div><strong style="color: #cbd5e1;">LangGraph</strong></div>
                <div>•</div>
                <div><strong style="color: #cbd5e1;">FastMCP</strong></div>
                <div>•</div>
                <div><strong style="color: #cbd5e1;">PostgreSQL</strong></div>
                <div>•</div>
                <div><strong style="color: #cbd5e1;">ChromaDB</strong></div>
            </div>
            <div style="font-size: 14px; color: #64748b;">
                Production Quality Engineering · ESR-STD-v2.4
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

def wait_until(scene_start, target_offset):
    """Accurately waits until a target offset within the scene is reached."""
    elapsed = time.time() - scene_start
    remaining = target_offset - elapsed
    if remaining > 0:
        time.sleep(remaining)

def record_dual_journey_demo():
    timings_path = os.path.join(AUDIO_DIR, "scene_timings.json")
    with open(timings_path, "r", encoding="utf-8") as f:
        tdata = json.load(f)
        SCENE_TARGETS = tdata["scenes"]
    print("Loaded exact audio scene targets:", SCENE_TARGETS)

    # Clean old raw videos
    for old_v in os.listdir(RAW_VIDEO_DIR):
        try:
            os.remove(os.path.join(RAW_VIDEO_DIR, old_v))
        except Exception:
            pass

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--window-size=1920,1080",
                "--hide-scrollbars",
                "--autoplay-policy=no-user-gesture-required",
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=RAW_VIDEO_DIR,
            record_video_size={"width": 1920, "height": 1080},
            permissions=["microphone"]
        )

        # Inject acoustic isolation script to prevent physical mic feedback loop
        context.add_init_script("""
            if (window.webkitSpeechRecognition || window.SpeechRecognition) {
                const OrigSR = window.webkitSpeechRecognition || window.SpeechRecognition;
                class ControlledSpeechRecognition extends OrigSR {
                    start() {
                        if (this.onstart) {
                            setTimeout(() => this.onstart(), 20);
                        }
                    }
                    stop() {
                        if (this.onend) {
                            setTimeout(() => this.onend(), 20);
                        }
                    }
                    abort() {
                        if (this.onend) {
                            setTimeout(() => this.onend(), 20);
                        }
                    }
                }
                window.webkitSpeechRecognition = ControlledSpeechRecognition;
                window.SpeechRecognition = ControlledSpeechRecognition;
            }
        """)

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
        # SCENE 1: Introduction & Product Vision (Target: 21.47s)
        # =====================================================================
        s1_start = time.time()
        print(f"\n--- [Scene 1] Introduction & Product Vision (Target: {SCENE_TARGETS['s1']:.2f}s) ---")
        page.evaluate(TITLE_CARD_SCRIPT)

        # Title card visible while narrator introduces Archie & dual journey
        wait_until(s1_start, 9.89)
        # Fade out title card smoothly before s1_03
        page.evaluate("(() => { const c = document.getElementById('demo-title-card'); if (c) { c.style.opacity = '0'; setTimeout(() => c.remove(), 800); } })()")
        wait_until(s1_start, 11.0)
        inject_cursor()

        # Present clean login screen with both Alice Smith and Bob Jones demo options
        smooth_move(page, 960, 320, steps=25)
        wait_until(s1_start, 16.0)
        smooth_move(page, 850, 620, steps=25) # Hovering Alice
        wait_until(s1_start, SCENE_TARGETS["s1"])
        print(f"Scene 1 completed in {time.time() - s1_start:.2f}s")

        # =====================================================================
        # SCENE 2: HR Admin Journey — Document Ingestion & RBAC (Target: 67.57s)
        # s2_01: 0.00s - 3.89s (Intro)
        # s2_02: 3.89s - 9.17s (Login as Alice)
        # s2_03: 9.17s - 17.11s (HR Admin badge)
        # s2_04: 17.11s - 26.48s (Click Ingest Document)
        # s2_05: 26.48s - 32.17s (Upload Remote Work Policy)
        # s2_06: 32.17s - 41.12s (Upload & Index ChromaDB)
        # s2_07: 41.12s - 47.01s (Confirmation 6 chunks)
        # s2_08: 47.01s - 53.73s (Test query in chat)
        # s2_09: 53.73s - 60.74s (Authoritative citations)
        # s2_10: 60.74s - 67.57s (Sign out as Alice)
        # =====================================================================
        s2_start = time.time()
        print(f"\n--- [Scene 2] HR Admin Journey — Document Ingestion & RBAC (Target: {SCENE_TARGETS['s2']:.2f}s) ---")
        
        # Click Alice Smith quick login at 3.89s
        wait_until(s2_start, 4.0)
        alice_btn = page.locator('button:has-text("Alice Smith")')
        smooth_click(page, alice_btn.first, wait_after=0.8)

        # Click Sign In at 6.0s
        wait_until(s2_start, 6.0)
        submit_btn = page.locator('button[type="submit"], button:has-text("Sign In")')
        smooth_click(page, submit_btn.first, wait_after=1.5)
        page.wait_for_selector('text=Alice Smith', timeout=15000)
        inject_cursor()

        # Highlight purple HR Admin badge at 11.5s
        wait_until(s2_start, 11.5)
        smooth_move(page, 720, 30, steps=20)

        # Move to & Click "Ingest Document" button at 20.0s
        wait_until(s2_start, 20.0)
        ingest_btn = page.locator('button:has-text("Ingest Document")')
        smooth_click(page, ingest_btn.first, wait_after=1.5)
        page.wait_for_selector('text=Ingest Policy Document', timeout=10000)
        inject_cursor()

        # Select Policy File (Acme_Remote_Work_Policy.md) at 27.5s
        wait_until(s2_start, 27.5)
        print("  [27.5s] Selecting Acme_Remote_Work_Policy.md...")
        file_input = page.locator('#doc-file-input')
        file_input.set_input_files(POLICY_FILE)
        time.sleep(1.0)

        # Click "Upload & Index" at 33.0s
        wait_until(s2_start, 33.0)
        upload_btn = page.locator('button:has-text("Upload & Index")')
        smooth_click(page, upload_btn.first, wait_after=2.0)
        page.wait_for_selector('text=Document Ingested & Indexed Successfully', timeout=20000)
        inject_cursor()

        # Highlight success banner (Chunks generated & indexed) at 41.5s
        wait_until(s2_start, 41.5)
        smooth_move(page, 960, 300, steps=15)

        # Close modal at 47.0s
        wait_until(s2_start, 47.0)
        close_btn = page.locator('button:has-text("Cancel")')
        if close_btn.count() > 0:
            smooth_click(page, close_btn.first, wait_after=0.8)

        # Alice tests retrieval in chat at 48.0s
        wait_until(s2_start, 48.0)
        chat_input = page.locator('textarea:not([disabled])')
        smooth_type(page, chat_input, "What are the eligibility requirements for remote work?")
        send_btn = page.locator('button[title="Send query"]')
        smooth_click(page, send_btn, wait_after=1.5)
        page.wait_for_selector('text=remote work', timeout=15000)
        inject_cursor()

        # Highlight citations at 55.0s
        wait_until(s2_start, 55.0)
        smooth_move(page, 800, 480, steps=20)

        # Alice signs out at 62.0s
        wait_until(s2_start, 62.0)
        signout_btn = page.locator('button:has-text("Sign Out")')
        smooth_click(page, signout_btn.first, wait_after=1.5)
        page.wait_for_selector('text=Acme Assistant', timeout=15000)

        wait_until(s2_start, SCENE_TARGETS["s2"])
        print(f"Scene 2 completed in {time.time() - s2_start:.2f}s")

        # =====================================================================
        # SCENE 3: Employee Journey — Authentication & Voice Activation (Target: 37.38s)
        # s3_01: 0.00s - 3.72s (Intro)
        # s3_02: 3.72s - 8.76s (Login as Bob)
        # s3_03: 8.76s - 16.71s (Employee permissions & Enable Voice)
        # s3_04: 16.71s - 23.96s (Waiting for wake word)
        # s3_05: 23.96s - 30.29s (Archie speaks greeting)
        # s3_06: 30.29s - 37.38s (Personalized identity confirmed)
        # =====================================================================
        s3_start = time.time()
        print(f"\n--- [Scene 3] Employee Journey — Authentication & Voice Activation (Target: {SCENE_TARGETS['s3']:.2f}s) ---")
        
        # Click Bob Jones at 3.72s
        wait_until(s3_start, 3.8)
        bob_btn = page.locator('button:has-text("Bob Jones")')
        smooth_click(page, bob_btn.first, wait_after=0.8)

        # Click Sign In at 5.5s
        wait_until(s3_start, 5.5)
        submit_btn = page.locator('button[type="submit"], button:has-text("Sign In")')
        smooth_click(page, submit_btn.first, wait_after=2.0)
        page.wait_for_selector('text=Bob Jones', timeout=15000)
        inject_cursor()

        # Click Enable Voice at 13.0s
        wait_until(s3_start, 13.0)
        enable_btn = page.locator('button:has-text("Enable Voice")')
        smooth_click(page, enable_btn.first, wait_after=1.0)
        page.wait_for_selector('text=Waiting for', timeout=10000)

        # 23.96s: Trigger "Hey Archie" wake word exactly on cue
        wait_until(s3_start, 23.96)
        print("  [23.96s] Triggering 'Hey Archie' wake word on cue...")
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('Hey Archie', true)")

        # Highlight Archie greeting & Bob identity at 30.5s
        wait_until(s3_start, 30.5)
        smooth_move(page, 960, 200, steps=20)

        wait_until(s3_start, SCENE_TARGETS["s3"])
        print(f"Scene 3 completed in {time.time() - s3_start:.2f}s")

        # =====================================================================
        # SCENE 4: Employee Policy Retrieval & Multimodal Response (Target: 38.47s)
        # s4_01: 0.00s - 4.97s (Intro)
        # s4_02: 4.97s - 8.63s (How much annual leave do I have available?)
        # s4_03: 8.63s - 15.11s (Archie speaks answer)
        # s4_04: 15.11s - 23.22s (Structured metrics in chat)
        # s4_05: 23.22s - 31.62s (Conversational voice summary)
        # s4_06: 31.62s - 38.47s (Multimodal benefits)
        # =====================================================================
        s4_start = time.time()
        print(f"\n--- [Scene 4] Employee Policy Retrieval & Multimodal Response (Target: {SCENE_TARGETS['s4']:.2f}s) ---")
        smooth_move(page, 960, 220, steps=15)
        
        # 4.97s: Bob asks leave balance query on cue
        wait_until(s4_start, 4.97)
        print("  [4.97s] Speaking query on cue: 'How much annual leave do I have available?'")
        page.evaluate("window.__ARCHIE_STATE_MACHINE__.manualActivateMic()")
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('How much annual leave do I have available?', true)")

        # Response renders on screen as Archie speaks
        wait_until(s4_start, 9.0)
        page.wait_for_selector('text=annual leave', timeout=15000)
        inject_cursor()

        # Highlight balance numbers in chat at 15.5s
        wait_until(s4_start, 15.5)
        smooth_move(page, 800, 480, steps=20)

        # Highlight voice bar summary at 23.5s
        wait_until(s4_start, 23.5)
        smooth_move(page, 550, 140, steps=20)

        # Scroll smoothly down at 31.5s
        wait_until(s4_start, 31.5)
        page.mouse.wheel(0, 150)
        smooth_move(page, 800, 520, steps=15)

        wait_until(s4_start, SCENE_TARGETS["s4"])
        print(f"Scene 4 completed in {time.time() - s4_start:.2f}s")

        # =====================================================================
        # SCENE 5: Continuous Dialogue & Seamless Modality Switching (Target: 34.53s)
        # s5_01: 0.00s - 5.83s (Intro)
        # s5_02: 5.83s - 9.70s (Can I carry forward unused days to next year?)
        # s5_03: 9.70s - 17.17s (Archie speaks carry-forward rule)
        # s5_04: 17.17s - 26.29s (Context retained, switch to text)
        # s5_05: 26.29s - 34.53s (Typed question in same session)
        # =====================================================================
        s5_start = time.time()
        print(f"\n--- [Scene 5] Continuous Dialogue & Seamless Modality Switching (Target: {SCENE_TARGETS['s5']:.2f}s) ---")
        smooth_move(page, 700, 250, steps=15)

        # 5.83s: Spoken follow-up without wake word
        wait_until(s5_start, 5.83)
        print("  [5.83s] Speaking follow-up: 'Can I carry forward unused days to next year?'")
        page.evaluate("window.__ARCHIE_STATE_MACHINE__.manualActivateMic()")
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('Can I carry forward unused days to next year?', true)")

        # Archie answers, policy citation appears at 10.0s
        wait_until(s5_start, 10.0)
        page.wait_for_selector('text=carry forward', timeout=15000)
        inject_cursor()

        # Highlight citation card at 17.5s
        wait_until(s5_start, 17.5)
        smooth_move(page, 800, 600, steps=20)

        # Switch to typing on cue at 26.5s
        wait_until(s5_start, 26.5)
        print("  [26.5s] Switching to typed input on cue...")
        chat_input = page.locator('textarea:not([disabled])')
        smooth_type(page, chat_input, "What is the maximum number of consecutive leave days allowed?")
        send_btn = page.locator('button[title="Send query"]')
        smooth_click(page, send_btn, wait_after=1.0)

        wait_until(s5_start, SCENE_TARGETS["s5"])
        print(f"Scene 5 completed in {time.time() - s5_start:.2f}s")

        # =====================================================================
        # SCENE 6: Real HR Transaction & Mandatory Human Confirmation (Target: 67.73s)
        # s6_01: 0.00s - 6.19s (Intro)
        # s6_02: 6.19s - 15.30s (Apply for annual leave Dec 10-12)
        # s6_03: 15.30s - 27.46s (Archie prepares 3 working days draft)
        # s6_04: 27.46s - 35.31s (Validates balance & displays card)
        # s6_05: 35.31s - 45.78s (Spoken confirmation refusal safeguard)
        # s6_06: 45.78s - 55.36s (Archie rejects voice confirmation)
        # s6_07: 55.36s - 67.73s (Explicit UI click executes transaction)
        # =====================================================================
        s6_start = time.time()
        print(f"\n--- [Scene 6] Real HR Transaction & Mandatory Human Confirmation (Target: {SCENE_TARGETS['s6']:.2f}s) ---")
        
        smooth_move(page, 750, 400, steps=15)
        page.mouse.wheel(0, 200)

        # 6.19s: Spoken leave application request
        wait_until(s6_start, 6.5)
        print("  [6.5s] Speaking leave request on cue...")
        page.evaluate("window.__ARCHIE_STATE_MACHINE__.manualActivateMic()")
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('I want to apply for annual leave from December 10 to December 12, 2026', true)")

        # Transaction card renders at 16.0s
        wait_until(s6_start, 16.0)
        confirm_btn = page.locator('button:has-text("Confirm Submission")')
        page.wait_for_selector('button:has-text("Confirm Submission")', timeout=15000)
        inject_cursor()

        # Highlight draft card at 28.0s
        wait_until(s6_start, 28.0)
        smooth_move(page, 750, 580, steps=20)

        # Spoken confirmation attempt: "Yes, submit it" at 36.0s
        wait_until(s6_start, 36.0)
        print("  [36.0s] Attempting spoken confirmation: 'Yes, submit it'...")
        page.evaluate("window.__ARCHIE_STATE_MACHINE__.manualActivateMic()")
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('Yes, submit it', true)")

        # Refusal notice renders at 46.0s
        wait_until(s6_start, 46.0)
        smooth_move(page, 750, 720, steps=15)

        # Explicit click on [Confirm Submission] button at 56.0s
        wait_until(s6_start, 56.0)
        print("  [56.0s] Clicking UI [Confirm Submission] button...")
        smooth_click(page, confirm_btn.first, wait_after=1.5)
        page.wait_for_selector('text=Action Confirmed & Executed', timeout=15000)

        # Highlight executed status at 62.0s
        wait_until(s6_start, 62.0)
        smooth_move(page, 750, 680, steps=15)

        wait_until(s6_start, SCENE_TARGETS["s6"])
        print(f"Scene 6 completed in {time.time() - s6_start:.2f}s")

        # =====================================================================
        # SCENE 7: Multi-Domain Enterprise Requests & Closing (Target: 31.92s)
        # s7_01: 0.00s - 5.83s (Intro)
        # s7_02: 5.83s - 14.81s (Open requests status query)
        # s7_03: 14.81s - 25.35s (Architecture review & scroll)
        # s7_04: 25.35s - 31.92s (Closing card)
        # =====================================================================
        s7_start = time.time()
        print(f"\n--- [Scene 7] Multi-Domain Enterprise Requests & Closing (Target: {SCENE_TARGETS['s7']:.2f}s) ---")
        
        # 5.83s: Type open requests query
        wait_until(s7_start, 6.0)
        chat_input = page.locator('textarea:not([disabled])')
        smooth_type(page, chat_input, "What is the status of my open requests?")
        send_btn = page.locator('button[title="Send query"]')
        smooth_click(page, send_btn, wait_after=1.0)

        # Highlight open requests at 11.0s
        wait_until(s7_start, 11.0)
        smooth_move(page, 800, 600, steps=20)

        # Smooth upward scroll reviewing entire journey at 15.0s
        wait_until(s7_start, 15.0)
        page.mouse.wheel(0, -600)
        time.sleep(2.0)
        page.mouse.wheel(0, 600)

        # Display final architectural closing card at 25.35s
        wait_until(s7_start, 25.35)
        print("  [25.35s] Displaying final architecture closing card...")
        page.evaluate(END_CARD_SCRIPT)

        wait_until(s7_start, SCENE_TARGETS["s7"])
        print(f"Scene 7 completed in {time.time() - s7_start:.2f}s")

        print("\nClosing browser...")
        page.close()
        context.close()
        browser.close()
        print("Dual journey recording complete.")

if __name__ == "__main__":
    record_dual_journey_demo()
