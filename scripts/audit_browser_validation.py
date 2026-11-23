"""
Safe Additional Browser Validation Script for Phase 2.1A Audit.
Interacts directly with the running application via Playwright Headless Chromium:
1. Navigates to http://127.0.0.1:3000
2. Authenticates as Bob Jones (E102)
3. Submits one representative query ("How many annual leave days do I currently have available?")
4. Captures screenshot, Playwright trace archive, console logs, and network activity.
"""

import json
import os
import sys
import time
from playwright.sync_api import sync_playwright

BASE_DIR = r"c:\Users\HP\OneDrive\Documents\HR-IT Helpdesk"
EVIDENCE_DIR = os.path.join(BASE_DIR, "audit", "EVIDENCE")
os.makedirs(EVIDENCE_DIR, exist_ok=True)

screenshot_path = os.path.join(EVIDENCE_DIR, "bob_browser_journey.png")
trace_path = os.path.join(EVIDENCE_DIR, "trace.zip")
console_log_path = os.path.join(EVIDENCE_DIR, "browser_console.log")
network_log_path = os.path.join(EVIDENCE_DIR, "network_activity.json")

console_messages = []
network_events = []

def main():
    print("=== STARTING BROWSER VALIDATION ===")
    with sync_playwright() as p:
        # Launch Chromium headless with IPv4 resolution mapping
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--host-resolver-rules=MAP * 127.0.0.1",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=None
        )

        # Enable Playwright tracing
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

        page = context.new_page()

        # Capture console messages
        def on_console(msg):
            entry = f"[{msg.type}] {msg.text}"
            console_messages.append(entry)
            print(f"Browser Console: {entry}")
        page.on("console", on_console)

        # Capture network requests & responses
        def on_response(response):
            if "/api/" in response.url or "/health" in response.url:
                try:
                    body_sample = response.text()[:200]
                except Exception:
                    body_sample = "<binary/unreadable>"
                network_events.append({
                    "url": response.url,
                    "status": response.status,
                    "method": response.request.method,
                    "response_preview": body_sample
                })
                print(f"Network: {response.request.method} {response.url} -> {response.status}")
        page.on("response", on_response)

        # 1. Navigate to frontend
        print("Navigating to http://127.0.0.1:3000...")
        page.goto("http://127.0.0.1:3000", wait_until="networkidle", timeout=30000)

        # 2. Verify login form
        print(f"Page title: {page.title()}")
        assert "Acme" in page.title() or "Assistant" in page.title(), f"Unexpected title: {page.title()}"

        # Wait for form elements
        page.wait_for_selector("input#email", timeout=10000)
        page.wait_for_selector("input#password", timeout=10000)

        # 3. Enter credentials for Bob Jones
        print("Filling credentials for Bob Jones (E102)...")
        page.fill("input#email", "bob@acme.com")
        page.fill("input#password", "Password123!")

        # Click Sign In button
        page.click("button[type='submit']")

        # 4. Wait for ChatInterface to mount
        print("Waiting for chat interface to mount...")
        page.wait_for_selector("header", timeout=15000)
        # Verify user identity in header
        header_text = page.inner_text("header")
        print(f"Header text: {header_text.replace(chr(10), ' ')}")
        assert "Bob Jones" in header_text or "E102" in header_text, "Bob Jones identity not found in header"

        # 5. Submit query
        query = "How many annual leave days do I currently have available?"
        print(f"Submitting query: '{query}'...")
        textarea = page.wait_for_selector("textarea", timeout=10000)
        textarea.fill(query)

        # Click send button and wait for /api/v1/chat response or error
        print("Clicking Send button and awaiting /api/v1/chat response...")
        try:
            with page.expect_response(lambda r: "/chat" in r.url, timeout=60000) as response_info:
                page.click("button[title='Send query']")
            chat_resp = response_info.value
            print(f"Chat API response status: {chat_resp.status}")
            try:
                chat_data = chat_resp.json()
                print(f"Chat API answer preview: {chat_data}")
            except Exception as e:
                print(f"Could not parse chat JSON: {e}")
        except Exception as e:
            print(f"Chat response wait encountered: {e}")

        # 6. Wait for assistant message to render in UI
        print("Waiting for assistant message to render in DOM...")
        time.sleep(3)  # Allow rendering to settle

        # Extract message text
        messages_elements = page.query_selector_all("main div.text-sm")
        response_texts = [el.inner_text() for el in messages_elements]
        print(f"Rendered messages found: {len(response_texts)}")
        for i, txt in enumerate(response_texts):
            print(f"  Msg [{i}]: {txt[:120]}...")

        # 7. Capture screenshot
        print(f"Saving screenshot to {screenshot_path}...")
        page.screenshot(path=screenshot_path, full_page=True)

        # 8. Stop tracing and save trace
        print(f"Saving trace to {trace_path}...")
        context.tracing.stop(path=trace_path)

        # Close
        browser.close()

    # Write logs
    with open(console_log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(console_messages))

    with open(network_log_path, "w", encoding="utf-8") as f:
        json.dump(network_events, f, indent=2)

    print("=== BROWSER VALIDATION COMPLETE ===")
    print(f"Screenshot: {screenshot_path} (exists: {os.path.exists(screenshot_path)})")
    print(f"Trace:      {trace_path} (exists: {os.path.exists(trace_path)})")
    print(f"Network:    {network_log_path} (events: {len(network_events)})")

if __name__ == "__main__":
    main()
