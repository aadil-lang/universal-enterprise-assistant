"""
UI Verification Script for Markdown Formatting & Escaped Asterisks Fix.
Logs into the live web UI, verifies Markdown rendering, and captures screenshot.
"""

import os
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_PATH = r"c:\Users\HP\OneDrive\Documents\HR-IT Helpdesk\artifacts\markdown_fix_verification.png"
os.makedirs(os.path.dirname(SCREENSHOT_PATH), exist_ok=True)

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 850})

        print("1. Navigating to http://localhost:3000...")
        page.goto("http://localhost:3000", wait_until="networkidle", timeout=30000)
        time.sleep(1)

        # Check if already logged in or needs login
        if page.locator("input[type='email']").count() > 0:
            print("2. Logging in as Bob Jones (bob@acme.com)...")
            page.fill("input[type='email']", "bob@acme.com")
            page.fill("input[type='password']", "Password123!")
            page.click("button[type='submit']")
            page.wait_for_selector("textarea", timeout=15000)
            print("✓ Logged in successfully.")
            time.sleep(1)
        else:
            print("✓ Session already active.")

        # Test live question submission
        query = "How much sick leave do I have available according to policy and my balance?"
        print(f"3. Submitting query: '{query}'...")
        page.fill("textarea", query)
        page.click("button:has(svg.lucide-send)")

        # Wait for assistant response to appear
        page.wait_for_selector("div.max-w-2xl.rounded-2xl:has(strong)", timeout=20000)
        print("✓ Response received.")
        time.sleep(2)

        # Inspect DOM for strong tags
        strong_elements = page.locator("div.max-w-2xl strong").all_inner_texts()
        print(f"✓ Found {len(strong_elements)} bold (strong) elements in response: {strong_elements}")

        # Check for unwanted raw asterisks or backslashes
        message_body = page.locator("div.max-w-2xl div.text-sm").last.inner_text()
        has_escaped_asterisks = "\\*\\*" in message_body
        has_unrendered_double_asterisks = "**" in message_body

        print(f"Has literal \\*\\*: {has_escaped_asterisks}")
        print(f"Has unrendered **: {has_unrendered_double_asterisks}")
        assert not has_escaped_asterisks, "Found escaped asterisks in message body!"
        assert not has_unrendered_double_asterisks, "Found unrendered ** in message body!"

        # Capture screenshot
        page.screenshot(path=SCREENSHOT_PATH, full_page=True)
        print(f"✓ Verification screenshot captured at: {SCREENSHOT_PATH}")

        browser.close()

if __name__ == "__main__":
    run()
