"""
Screen Recorder for Archie Professional Product Demo.
Tight synchronization with natural narration audio segments.
Includes acoustic echo gate to prevent microphone feedback loop.
Resolution: 1920x1080 | 60 FPS CFR
Standard: ESR-STD-v2.4 | Repository: aadil-lang/universal-enterprise-assistant
"""

import os
import sys
import time
import json
from playwright.sync_api import sync_playwright

RAW_VIDEO_DIR = os.path.abspath("artifacts/demo/raw_video_professional")
AUDIO_DIR = os.path.abspath("artifacts/demo/audio_professional")
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
            <div style="display: inline-block; padding: 8px 24px; border-radius: 9999px; background: rgba(99, 102, 241, 0.2); border: 1px solid rgba(99, 102, 241, 0.4); font-size: 16px; font-weight: 600; color: #a5b4fc; letter-spacing: 0.05em; text-transform: uppercase;">
                One Assistant Â· One Conversation Â· Smarter Employee Services
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
            <div style="font-size: 68px; font-weight: 800; letter-spacing: -0.03em; margin-bottom: 16px; background: linear-gradient(135deg, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Archie
            </div>
            <div style="font-size: 32px; font-weight: 500; font-style: italic; color: #e2e8f0; margin-bottom: 32px;">
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

def record_demo():
    # Load timings from audio generation
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
        # SCENE 1: Introduction (Target: 28.04s)
        # s1_01: "Hello everyone." (0.00s - 2.37s)
        # s1_02: "Today, I'd like to show you Archie..." (2.37s - 9.67s)
        # s1_03: "The idea behind Archie is quite simple..." (9.67s - 21.75s)
        # s1_04: "Instead, they can interact with one assistant..." (21.75s - 28.04s)
        # =====================================================================
        s1_start = time.time()
        print(f"\n--- [Scene 1] Introduction (Target: {SCENE_TARGETS['s1']:.2f}s) ---")
        page.evaluate(TITLE_CARD_SCRIPT)

        # Title card visible while narrator introduces Archie
        wait_until(s1_start, 8.5)
        # Fade out title card smoothly before s1_03 begins
        page.evaluate("(() => { const c = document.getElementById('demo-title-card'); if (c) { c.style.opacity = '0'; setTimeout(() => c.remove(), 800); } })()")
        wait_until(s1_start, 9.67)
        inject_cursor()

        # Present clean login screen while narrator explains the core concept
        smooth_move(page, 960, 320, steps=25)
        wait_until(s1_start, 15.0)
        smooth_move(page, 960, 480, steps=25)
        wait_until(s1_start, 21.75)
        # Prepare near login options
        smooth_move(page, 960, 420, steps=20)
        wait_until(s1_start, SCENE_TARGETS["s1"])
        print(f"Scene 1 completed in {time.time() - s1_start:.2f}s")

        # =====================================================================
        # SCENE 2: Personalized Voice Interaction (Target: 25.21s)
        # s2_01: "Let's start by logging in as an employee." (0.00s - 3.77s)
        # s2_02: "Here, I'm logged in as Bob." (3.77s - 6.94s)
        # s2_03: "Once voice mode is enabled, I can simply say, 'Hey Archie'." (6.94s - 12.37s)
        # s2_04: ARCHIE: "Hey Bob! Good afternoon. How can I help you today?" (12.37s - 18.79s)
        # s2_05: "Archie recognizes the authenticated employee..." (18.79s - 25.21s)
        # =====================================================================
        s2_start = time.time()
        print(f"\n--- [Scene 2] Personalized Voice Interaction (Target: {SCENE_TARGETS['s2']:.2f}s) ---")
        
        # 0.00s - 3.77s: Click Bob Jones quick login
        bob_btn = page.locator('button:has-text("Bob Jones")')
        if bob_btn.count() > 0:
            smooth_click(page, bob_btn.first, wait_after=0.8)
        else:
            email_input = page.locator('input[type="email"]')
            smooth_type(page, email_input, "bob@acme.com")
            pwd_input = page.locator('input[type="password"]')
            smooth_type(page, pwd_input, "Password123!")

        # 3.77s: Click Sign In as narrator says "Here, I'm logged in as Bob"
        wait_until(s2_start, 3.77)
        submit_btn = page.locator('button[type="submit"], button:has-text("Sign In")')
        smooth_click(page, submit_btn.first, wait_after=1.5)
        page.wait_for_selector('text=Archie', timeout=15000)
        inject_cursor()

        # 6.94s: Move to and click Enable Voice as narrator introduces voice mode
        wait_until(s2_start, 7.2)
        enable_btn = page.locator('button:has-text("Enable Voice")')
        if enable_btn.count() > 0:
            smooth_click(page, enable_btn.first, wait_after=1.0)
        page.wait_for_selector('text=Waiting for', timeout=10000)

        # 12.37s: Trigger "Hey Archie" wake word exactly as Archie begins speaking
        wait_until(s2_start, 12.37)
        print("  [12.37s] Triggering 'Hey Archie' on cue...")
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('Hey Archie', true)")
        
        # 18.79s: Move cursor over Bob Jones greeting in header
        wait_until(s2_start, 18.79)
        smooth_move(page, 960, 200, steps=20)
        
        wait_until(s2_start, SCENE_TARGETS["s2"])
        print(f"Scene 2 completed in {time.time() - s2_start:.2f}s")

        # =====================================================================
        # SCENE 3: Employee Info & Policy Retrieval (Target: 44.33s)
        # s3_01: "Let's ask Archie about the employee's available annual leave." (0.00s - 4.76s)
        # s3_02: "How much annual leave do I have available?" (4.76s - 8.56s)
        # s3_03: ARCHIE: "You have 8 days of annual leave available..." (8.56s - 15.13s)
        # s3_04: "Archie retrieves the information from Bob's employee record..." (15.13s - 22.48s)
        # s3_05: "At the same time, it speaks a shorter, more conversational version..." (22.48s - 28.72s)
        # s3_06: "So the employee can listen to the response while still having..." (28.72s - 35.58s)
        # s3_07: "This is an important part of the design..." (35.58s - 44.33s)
        # =====================================================================
        s3_start = time.time()
        print(f"\n--- [Scene 3] Employee Info & Policy Retrieval (Target: {SCENE_TARGETS['s3']:.2f}s) ---")
        
        # Cursor moves toward chat/voice area
        smooth_move(page, 960, 220, steps=15)
        
        # 4.76s: Narrator asks: "How much annual leave do I have available?"
        wait_until(s3_start, 4.76)
        print("  [4.76s] Speaking query on cue: 'How much annual leave do I have available?'")
        page.evaluate("window.__ARCHIE_STATE_MACHINE__.manualActivateMic()")
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('How much annual leave do I have available?', true)")

        # 8.56s: Archie response appears on screen as Archie speaks
        wait_until(s3_start, 8.56)
        page.wait_for_selector('text=annual leave', timeout=15000)
        inject_cursor()

        # 15.13s: Highlight leave balance breakdown in chat
        wait_until(s3_start, 15.13)
        smooth_move(page, 800, 480, steps=20)

        # 22.48s: Highlight voice bar concise summary
        wait_until(s3_start, 22.48)
        smooth_move(page, 550, 140, steps=20)

        # 28.72s: Scroll smoothly down to keep full context visible
        wait_until(s3_start, 28.72)
        page.mouse.wheel(0, 150)
        smooth_move(page, 800, 520, steps=15)

        wait_until(s3_start, SCENE_TARGETS["s3"])
        print(f"Scene 3 completed in {time.time() - s3_start:.2f}s")

        # =====================================================================
        # SCENE 4: Continuous Dialogue & Text Switching (Target: 32.22s)
        # s4_01: "Archie also supports continuous conversations." (0.00s - 3.96s)
        # s4_02: "Can I carry forward unused days to next year?" (3.96s - 8.00s)
        # s4_03: ARCHIE: "Yes, you can carry forward up to 5 unused annual leave days..." (8.00s - 15.56s)
        # s4_04: "I can ask a follow-up question without repeating the wake phrase..." (15.56s - 22.95s)
        # s4_05: "I can also switch back to typing whenever I want..." (22.95s - 32.22s)
        # =====================================================================
        s4_start = time.time()
        print(f"\n--- [Scene 4] Continuous Dialogue & Text Switching (Target: {SCENE_TARGETS['s4']:.2f}s) ---")
        smooth_move(page, 700, 250, steps=15)

        # 3.96s: Follow-up spoken question without wake word
        wait_until(s4_start, 3.96)
        print("  [3.96s] Speaking follow-up on cue: 'Can I carry forward unused days to next year?'")
        page.evaluate("window.__ARCHIE_STATE_MACHINE__.manualActivateMic()")
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('Can I carry forward unused days to next year?', true)")

        # 8.00s: Archie speaks answer, response appears with policy citation
        wait_until(s4_start, 8.00)
        page.wait_for_selector('text=carry forward', timeout=15000)
        inject_cursor()

        # 15.56s: Highlight policy citation card
        wait_until(s4_start, 15.56)
        smooth_move(page, 800, 600, steps=20)

        # 22.95s: Switch to typing seamlessly as narrator explains text switching
        wait_until(s4_start, 22.95)
        print("  [22.95s] Switching to typed input on cue...")
        chat_input = page.locator('textarea:not([disabled])')
        smooth_type(page, chat_input, "What is the maximum number of consecutive leave days allowed?")
        send_btn = page.locator('button[title="Send query"]')
        smooth_click(page, send_btn, wait_after=1.0)

        wait_until(s4_start, SCENE_TARGETS["s4"])
        print(f"Scene 4 completed in {time.time() - s4_start:.2f}s")

        # =====================================================================
        # SCENE 5: Real HR Transaction & Confirmation (Target: 72.08s)
        # s5_01: "Beyond answering questions, Archie can also help employees..." (0.00s - 7.44s)
        # s5_02: "For example, here I'm creating a leave request." (7.44s - 11.81s)
        # s5_03: "I want to apply for annual leave from December 10 to December 12, 2026." (11.81s - 19.00s)
        # s5_04: ARCHIE: "I have prepared your leave request for 3 working days..." (19.00s - 31.38s)
        # s5_05: "Archie checks the request details, validates the available balance..." (31.38s - 38.05s)
        # s5_06: "Now, notice something important. Even if I say, 'Yes, submit it'..." (38.05s - 47.95s)
        # s5_07: ARCHIE: "Spoken confirmation is not permitted for transactions..." (47.95s - 57.67s)
        # s5_08: "For sensitive enterprise actions, the employee must review..." (57.67s - 65.76s)
        # s5_09: "Once I confirm, the backend persists the request..." (65.76s - 72.08s)
        # =====================================================================
        s5_start = time.time()
        print(f"\n--- [Scene 5] Real HR Transaction & Confirmation (Target: {SCENE_TARGETS['s5']:.2f}s) ---")
        
        # Position view comfortably
        smooth_move(page, 750, 400, steps=15)
        page.mouse.wheel(0, 200)

        # 11.81s: User speaks transaction request on cue
        wait_until(s5_start, 11.81)
        print("  [11.81s] Speaking transaction request on cue...")
        page.evaluate("window.__ARCHIE_STATE_MACHINE__.manualActivateMic()")
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('I want to apply for annual leave from December 10 to December 12, 2026', true)")

        # 19.00s: Archie speaks, transaction card renders
        wait_until(s5_start, 19.00)
        confirm_btn = page.locator('button:has-text("Confirm Submission")')
        page.wait_for_selector('button:has-text("Confirm Submission")', timeout=15000)
        inject_cursor()

        # 31.38s: Highlight draft leave card details (dates, days, remaining balance)
        wait_until(s5_start, 31.38)
        smooth_move(page, 750, 580, steps=20)

        # 38.05s: Narrator mentions spoken confirmation attempt
        wait_until(s5_start, 40.0)
        print("  [40.00s] Attempting spoken confirmation: 'Yes, submit it'...")
        page.evaluate("window.__ARCHIE_STATE_MACHINE__.manualActivateMic()")
        page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('Yes, submit it', true)")

        # 47.95s: Archie speaks rejection ("Spoken confirmation is not permitted...")
        wait_until(s5_start, 47.95)
        smooth_move(page, 750, 720, steps=15)

        # 57.67s: Narrator explains mandatory UI button confirmation requirement
        wait_until(s5_start, 58.5)
        smooth_move(page, 750, 640, steps=20)

        # 61.50s: Click UI [Confirm Submission] button
        wait_until(s5_start, 61.50)
        print("  [61.50s] Clicking UI [Confirm Submission] button on cue...")
        smooth_click(page, confirm_btn.first, wait_after=1.5)
        page.wait_for_selector('text=Action Confirmed & Executed', timeout=15000)

        # 65.76s: Highlight executed status banner
        wait_until(s5_start, 65.76)
        smooth_move(page, 750, 680, steps=15)

        wait_until(s5_start, SCENE_TARGETS["s5"])
        print(f"Scene 5 completed in {time.time() - s5_start:.2f}s")

        # =====================================================================
        # SCENE 6: Broader Enterprise Capabilities (Target: 20.60s)
        # s6_01: "The same assistant also supports workflows such as IT support tickets..." (0.00s - 11.33s)
        # s6_02: "All of these follow the same principle: Archie prepares and validates..." (11.33s - 20.60s)
        # =====================================================================
        s6_start = time.time()
        print(f"\n--- [Scene 6] Broader Enterprise Capabilities (Target: {SCENE_TARGETS['s6']:.2f}s) ---")
        
        # 1.00s: Move to chat input and type open requests query
        wait_until(s6_start, 1.0)
        chat_input = page.locator('textarea:not([disabled])')
        smooth_type(page, chat_input, "What is the status of my open requests?")
        
        wait_until(s6_start, 4.0)
        send_btn = page.locator('button[title="Send query"]')
        smooth_click(page, send_btn, wait_after=1.0)

        # 11.33s: Backend status card renders cleanly; highlight open IT ticket & leave requests
        wait_until(s6_start, 11.33)
        smooth_move(page, 800, 600, steps=20)

        wait_until(s6_start, SCENE_TARGETS["s6"])
        print(f"Scene 6 completed in {time.time() - s6_start:.2f}s")

        # =====================================================================
        # SCENE 7: Architecture & Closing (Target: 25.46s)
        # s7_01: "Under the hood, Archie brings together company policy retrieval..." (0.00s - 9.84s)
        # s7_02: "My goal with this project was to make everyday employee services simpler..." (9.84s - 19.66s)
        # s7_03: "And that's Archie â€” your conversational HR and IT assistant." (19.66s - 25.46s)
        # =====================================================================
        s7_start = time.time()
        print(f"\n--- [Scene 7] Architecture & Closing (Target: {SCENE_TARGETS['s7']:.2f}s) ---")
        
        # 0.00s - 9.84s: Smooth upward scroll reviewing the continuous conversational journey
        smooth_move(page, 960, 400, steps=15)
        page.mouse.wheel(0, -600)
        wait_until(s7_start, 5.0)
        page.mouse.wheel(0, 600)
        
        # 9.84s: Display final closing architecture card
        wait_until(s7_start, 9.84)
        print("  [9.84s] Displaying final closing card on cue...")
        page.evaluate(END_CARD_SCRIPT)

        wait_until(s7_start, SCENE_TARGETS["s7"])
        print(f"Scene 7 completed in {time.time() - s7_start:.2f}s")

        print("\nClosing context and browser to finalize raw video...")
        page.close()
        context.close()
        browser.close()
        print("Browser recording complete.")

if __name__ == "__main__":
    record_demo()
