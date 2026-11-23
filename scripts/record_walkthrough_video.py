"""
Automated 1920x1080 Screen Recorder for Acme HR & IT Assistant Walkthrough.
Records all 7 scenes in live Chromium, synchronized with the narration audio.
"""

import os
import time
import subprocess
import json
from playwright.sync_api import sync_playwright

RAW_VIDEO_DIR = os.path.abspath("artifacts/demo/raw_video")
OUTPUT_DIR = os.path.abspath("artifacts/demo")
os.makedirs(RAW_VIDEO_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Scene duration targets in seconds (matching narration audio exactly)
SCENE_DURATIONS = {
    "scene1": 28.06,
    "scene2": 31.39,
    "scene3": 35.38,
    "scene4": 25.15,
    "scene5": 22.99,
    "scene6": 29.42,
    "scene7": 33.24
}

CURSOR_SCRIPT = """
(() => {
    if (document.getElementById('demo-cursor')) return;
    const cursor = document.createElement('div');
    cursor.id = 'demo-cursor';
    cursor.style.position = 'fixed';
    cursor.style.width = '22px';
    cursor.style.height = '22px';
    cursor.style.borderRadius = '50%';
    cursor.style.backgroundColor = 'rgba(239, 68, 68, 0.9)';
    cursor.style.border = '2px solid #ffffff';
    cursor.style.boxShadow = '0 0 10px rgba(0,0,0,0.45)';
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
        cursor.style.backgroundColor = 'rgba(220, 38, 38, 1)';
    });

    window.addEventListener('mouseup', () => {
        cursor.style.transform = 'translate(-50%, -50%) scale(1)';
        cursor.style.backgroundColor = 'rgba(239, 68, 68, 0.9)';
    });
})();
"""

def smooth_move(page, target_x, target_y, steps=15, delay=0.015):
    page.mouse.move(target_x, target_y, steps=steps)
    time.sleep(delay)

def smooth_click(page, locator, wait_after=1.0):
    try:
        box = locator.bounding_box()
        if box:
            target_x = box['x'] + box['width'] / 2
            target_y = box['y'] + box['height'] / 2
            smooth_move(page, target_x, target_y, steps=12)
            time.sleep(0.15)
        locator.click()
        time.sleep(wait_after)
    except Exception as e:
        print(f"Warning in smooth_click: {e}")
        locator.click(force=True)
        time.sleep(wait_after)

def smooth_type(page, locator, text, delay_per_char=0.02):
    try:
        box = locator.bounding_box()
        if box:
            smooth_move(page, box['x'] + box['width'] / 2, box['y'] + box['height'] / 2, steps=10)
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

def record_walkthrough():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--window-size=1920,1080",
                "--hide-scrollbars",
                "--disable-gpu"
            ]
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=RAW_VIDEO_DIR,
            record_video_size={"width": 1920, "height": 1080}
        )
        page = context.new_page()

        def inject_cursor():
            try:
                page.evaluate(CURSOR_SCRIPT)
            except Exception:
                pass

        total_start = time.time()

        # =========================================================================
        # SCENE 1: Introduction (Target: 28.06s)
        # =========================================================================
        scene1_start = time.time()
        print("\n--- [Scene 1] Recording Introduction (Target: 28.06s) ---")
        page.goto("http://localhost:3000", timeout=20000)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2000)
        inject_cursor()

        # Move mouse gently around the login card showcasing the clean interface
        smooth_move(page, 960, 320, steps=20)
        time.sleep(2.5)
        smooth_move(page, 960, 440, steps=15)
        time.sleep(2.5)
        smooth_move(page, 960, 540, steps=15)
        time.sleep(2.5)
        smooth_move(page, 960, 680, steps=15)

        elapsed = time.time() - scene1_start
        remaining = SCENE_DURATIONS["scene1"] - elapsed
        if remaining > 0:
            time.sleep(remaining)
        print(f"  Scene 1 recorded in: {time.time() - scene1_start:.2f}s")

        # =========================================================================
        # SCENE 2: Employee Login & Policy Assistant (Target: 31.39s)
        # =========================================================================
        scene2_start = time.time()
        print("\n--- [Scene 2] Recording Employee Login & Policy Q&A (Target: 31.39s) ---")
        # Click the one-click Bob Jones demo card
        bob_btn = page.locator('button:has-text("Bob Jones")')
        if bob_btn.count() > 0:
            smooth_click(page, bob_btn.first, wait_after=0.5)

        submit_btn = page.locator('button[type="submit"], button:has-text("Sign In")')
        smooth_click(page, submit_btn.first, wait_after=2.5)

        inject_cursor()
        chat_input = page.locator('textarea, input[placeholder*="Ask" i], input[placeholder*="message" i]')
        smooth_type(page, chat_input, "What is the annual vacation entitlement, and how many unused days can I carry forward?", delay_per_char=0.015)
        page.keyboard.press("Enter")

        # Wait for policy response with citations to appear
        page.wait_for_timeout(6000)
        inject_cursor()

        # Hover over the citation badge / response
        smooth_move(page, 960, 480, steps=15)
        time.sleep(2.0)
        smooth_move(page, 960, 560, steps=15)

        elapsed = time.time() - scene2_start
        remaining = SCENE_DURATIONS["scene2"] - elapsed
        if remaining > 0:
            time.sleep(remaining)
        print(f"  Scene 2 recorded in: {time.time() - scene2_start:.2f}s")

        # =========================================================================
        # SCENE 3: Leave Application & Explicit Confirmation (Target: 35.38s)
        # =========================================================================
        scene3_start = time.time()
        print("\n--- [Scene 3] Recording Leave Application & Confirmation (Target: 35.38s) ---")
        smooth_type(page, chat_input, "I want to apply for annual leave from December 10 to December 12", delay_per_char=0.015)
        page.keyboard.press("Enter")

        # Wait for confirmation card to render
        page.wait_for_timeout(6000)
        inject_cursor()

        # Hover over the confirmation card parameters
        confirm_btn = page.locator('button:has-text("Confirm Submission")')
        if confirm_btn.count() > 0:
            smooth_move(page, 960, 580, steps=15)
            time.sleep(1.5)
            smooth_click(page, confirm_btn.first, wait_after=5.0)

        inject_cursor()

        # Query status
        smooth_type(page, chat_input, "What is the status of my latest leave request?", delay_per_char=0.015)
        page.keyboard.press("Enter")
        page.wait_for_timeout(5000)
        inject_cursor()

        elapsed = time.time() - scene3_start
        remaining = SCENE_DURATIONS["scene3"] - elapsed
        if remaining > 0:
            time.sleep(remaining)
        print(f"  Scene 3 recorded in: {time.time() - scene3_start:.2f}s")

        # =========================================================================
        # SCENE 4: IT Support Ticket (Target: 25.15s)
        # =========================================================================
        scene4_start = time.time()
        print("\n--- [Scene 4] Recording IT Support Ticket (Target: 25.15s) ---")
        smooth_type(page, chat_input, "My laptop screen is flickering constantly, please raise an IT ticket", delay_per_char=0.015)
        page.keyboard.press("Enter")

        page.wait_for_timeout(6000)
        inject_cursor()

        confirm_btn = page.locator('button:has-text("Confirm Submission")')
        if confirm_btn.count() > 0:
            smooth_click(page, confirm_btn.first, wait_after=5.0)

        inject_cursor()
        smooth_move(page, 960, 680, steps=15)

        elapsed = time.time() - scene4_start
        remaining = SCENE_DURATIONS["scene4"] - elapsed
        if remaining > 0:
            time.sleep(remaining)
        print(f"  Scene 4 recorded in: {time.time() - scene4_start:.2f}s")

        # =========================================================================
        # SCENE 5: Reimbursement Request (Target: 22.99s)
        # =========================================================================
        scene5_start = time.time()
        print("\n--- [Scene 5] Recording Expense Reimbursement (Target: 22.99s) ---")
        smooth_type(page, chat_input, "I want to submit an expense reimbursement of $150 for an ergonomic chair purchased on 2026-11-15 from Office Depot", delay_per_char=0.015)
        page.keyboard.press("Enter")

        page.wait_for_timeout(6000)
        inject_cursor()

        confirm_btn = page.locator('button:has-text("Confirm Submission")')
        if confirm_btn.count() > 0:
            smooth_click(page, confirm_btn.first, wait_after=5.0)

        inject_cursor()
        smooth_move(page, 960, 720, steps=15)

        elapsed = time.time() - scene5_start
        remaining = SCENE_DURATIONS["scene5"] - elapsed
        if remaining > 0:
            time.sleep(remaining)
        print(f"  Scene 5 recorded in: {time.time() - scene5_start:.2f}s")

        # =========================================================================
        # SCENE 6: HR Administrator Access (Target: 29.42s)
        # =========================================================================
        scene6_start = time.time()
        print("\n--- [Scene 6] Recording HR Administrator Cross-Employee Access (Target: 29.42s) ---")
        signout_btn = page.locator('button:has-text("Sign Out")')
        if signout_btn.count() > 0:
            smooth_click(page, signout_btn.first, wait_after=2.0)

        inject_cursor()
        alice_btn = page.locator('button:has-text("Alice Smith")')
        if alice_btn.count() > 0:
            smooth_click(page, alice_btn.first, wait_after=0.5)

        submit_btn = page.locator('button[type="submit"], button:has-text("Sign In")')
        smooth_click(page, submit_btn.first, wait_after=2.5)

        inject_cursor()
        chat_input = page.locator('textarea, input[placeholder*="Ask" i], input[placeholder*="message" i]')
        smooth_type(page, chat_input, "Show me the leave balance and open tickets for employee E102", delay_per_char=0.015)
        page.keyboard.press("Enter")

        page.wait_for_timeout(6000)
        inject_cursor()

        smooth_move(page, 960, 500, steps=15)
        time.sleep(2.0)
        smooth_move(page, 960, 680, steps=15)

        elapsed = time.time() - scene6_start
        remaining = SCENE_DURATIONS["scene6"] - elapsed
        if remaining > 0:
            time.sleep(remaining)
        print(f"  Scene 6 recorded in: {time.time() - scene6_start:.2f}s")

        # =========================================================================
        # SCENE 7: Architecture and Conclusion (Target: 33.24s)
        # =========================================================================
        scene7_start = time.time()
        print("\n--- [Scene 7] Recording Architecture and Conclusion (Target: 33.24s) ---")
        smooth_move(page, 960, 450, steps=20)
        page.mouse.wheel(0, -600)
        time.sleep(2.5)
        page.mouse.wheel(0, 400)
        time.sleep(2.5)
        smooth_move(page, 960, 540, steps=15)

        elapsed = time.time() - scene7_start
        remaining = SCENE_DURATIONS["scene7"] - elapsed
        if remaining > 0:
            time.sleep(remaining)
        print(f"  Scene 7 recorded in: {time.time() - scene7_start:.2f}s")

        print(f"\nTotal recording duration: {time.time() - total_start:.2f}s")

        # Closing context flushes the video file
        video_path = page.video.path()
        context.close()
        browser.close()
        print(f"Raw video saved at: {video_path}")
        return video_path

if __name__ == "__main__":
    raw_video = record_walkthrough()
    print("Screen recording finished successfully.")
