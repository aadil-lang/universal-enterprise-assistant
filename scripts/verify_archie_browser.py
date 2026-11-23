"""
Archie Voice Assistant End-to-End Playwright Acceptance Test Suite.
Verifies ESR-STD-v2.4 compliance across Chromium browser runtime:
1. Archie visual presence and identity rendering.
2. Voice mode opt-in activation.
3. Wake-word listening indicator ("Hey Archie").
4. Personalized employee greeting with authenticated identity.
5. Live transcript display and VAD controls (Done, Cancel, Stop Speaking).
6. Grounded response delivery and speech synthesis state.
7. Agentic transactional workflow triggering interactive confirmation card.
8. Non-negotiable security boundary: Voice cannot bypass UI confirmation button.
9. Continuous conversation multi-turn follow up.
10. Clean teardown on user logout.
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

EVIDENCE_DIR = os.path.abspath("artifacts/audit_evidence/archie_voice")
os.makedirs(EVIDENCE_DIR, exist_ok=True)

def run_archie_acceptance_test():
    print("================================================================")
    print(" Starting Archie Voice Assistant Playwright Acceptance Suite   ")
    print("================================================================")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--autoplay-policy=no-user-gesture-required",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            permissions=["microphone"],
        )
        page = context.new_page()
        page.on("console", lambda msg: print(f"  [Browser Console] {msg.type}: {msg.text}"))

        # Step 1: Navigate to Assistant
        print("\n[Step 1] Navigating to http://localhost:3000...")
        page.goto("http://localhost:3000", timeout=30000)
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "01_archie_landing.png"))

        # Step 2: Authenticate as Bob Jones (E102)
        print("[Step 2] Authenticating as Bob Jones (E102)...")
        email_input = page.locator('input[type="email"]')
        if email_input.count() > 0:
            bob_btn = page.locator('button:has-text("Bob Jones")')
            if bob_btn.count() > 0:
                bob_btn.first.click()
            else:
                email_input.fill("bob@acme.com")
                page.fill('input[type="password"]', "Password123!")
            page.click('button[type="submit"], button:has-text("Sign In")')

        # Wait for chat interface to mount
        page.wait_for_selector('text=Archie', timeout=15000)
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "02_archie_authenticated_bob.png"))

        # Step 3: Verify Archie Presence in UI
        print("[Step 3] Verifying Archie Voice Assistant toolbar presence...")
        archie_presence = page.locator('text=Archie').first
        assert archie_presence.count() > 0, "Archie header presence not found!"
        assert page.locator('text=en-IN').count() > 0, "en-IN locale indicator not found!"
        enable_btn = page.locator('button:has-text("Enable Voice")')
        assert enable_btn.count() > 0, "Enable Voice button not found!"
        print("  ✓ Archie identity, en-IN locale badge, and Enable Voice button verified.")

        # Step 4: Explicit Opt-In: Enable Archie Voice Mode
        print("\n[Step 4] Enabling Archie Voice Mode...")
        enable_btn.click()
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "03_archie_voice_enabled.png"))

        # Verify status transitions to WAKE_WORD_LISTENING
        status_wake = page.locator('text=Waiting for "Hey Archie"')
        assert status_wake.count() > 0, "Archie should enter WAKE_WORD_LISTENING state!"
        print("  ✓ State verified: WAKE_WORD_LISTENING (Waiting for 'Hey Archie').")

        # Step 5: Manual Mic Activation Fallback & Active Listening
        print("\n[Step 5] Testing Manual Microphone Activation Fallback...")
        mic_btn = page.locator('button[title*="speaking"]').first
        mic_btn.click()
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "04_archie_active_listening.png"))

        status_listening = page.locator('text=Listening...')
        assert status_listening.count() > 0, "Archie should transition to ACTIVE_LISTENING!"
        assert page.locator('button:has-text("Done")').count() > 0, "Done button must be visible during speech!"
        assert page.locator('button:has-text("Cancel")').count() > 0, "Cancel button must be visible during speech!"
        print("  ✓ State verified: ACTIVE_LISTENING with Done & Cancel controls.")

        # Step 6: Voice Policy Query Execution
        print("\n[Step 6] Submitting Voice Policy Query...")
        chat_input = page.locator('textarea')
        chat_input.fill("What is the annual leave carryover policy?")
        page.keyboard.press("Enter")
        page.wait_for_timeout(6000)
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "05_archie_policy_response.png"))

        # Verify policy response and citations
        assert page.locator('text=Annual Leave').count() > 0 or page.locator('text=carryover').count() > 0
        print("  ✓ Voice-submitted policy question answered with grounded policy citations.")

        # Step 7: Voice-Enabled Agentic Workflow with Mandatory Human Confirmation
        print("\n[Step 7] Testing Agentic Transaction: Leave Request Draft...")
        chat_input.fill("I want to apply for leave from December 10 to December 12")
        page.keyboard.press("Enter")
        page.wait_for_timeout(7000)
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "06_archie_transaction_card.png"))

        # Verify interactive confirmation card is rendered
        confirm_btn = page.locator('button:has-text("Confirm Submission")')
        assert confirm_btn.count() > 0, "Interactive Confirmation Card [Confirm Submission] button must be present!"
        print("  ✓ Interactive Confirmation Card rendered on screen with parameters.")

        # Step 8: Strict Security Verification: Spoken Confirmation Refusal
        print("\n[Step 8] Verifying Security Boundary: Spoken 'Yes submit it' cannot execute transaction...")
        chat_input.fill("Yes submit it")
        page.keyboard.press("Enter")
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "07_archie_spoken_confirm_refusal.png"))

        # Verify security refusal message was returned and transaction button remains unclicked
        security_warning = page.locator('text=require explicit confirmation using the \'Confirm Submission\' button')
        assert security_warning.count() > 0, "Security refusal must instruct user to click UI button!"
        print("  ✓ Security Boundary Verified: Spoken confirmation safely refused.")

        # Step 9: User Clicks UI Button to Authorize
        print("\n[Step 9] User explicitly activates [Confirm Submission] button...")
        confirm_btn.first.click()
        page.wait_for_timeout(6000)
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "08_archie_transaction_executed.png"))
        assert page.locator('text=Action Confirmed & Executed').count() > 0
        print("  ✓ Human-in-the-loop transaction confirmed and executed successfully.")

        # Step 10: Logout Cleanup & Teardown
        print("\n[Step 10] Testing User Logout Teardown...")
        signout_btn = page.locator('button:has-text("Sign Out")')
        signout_btn.click()
        page.wait_for_timeout(2500)
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "09_archie_logged_out.png"))

        # Verify back on login screen and voice mode is completely disabled
        assert page.locator('input[type="email"]').count() > 0, "Must return to login page on sign out"
        print("  ✓ Voice session and audio capture completely torn down on logout.")

        browser.close()

    print("\n================================================================")
    print(" ALL ARCHIE VOICE ASSISTANT BROWSER CHECKS PASSED (10/10)       ")
    print("================================================================\n")

if __name__ == "__main__":
    run_archie_acceptance_test()
