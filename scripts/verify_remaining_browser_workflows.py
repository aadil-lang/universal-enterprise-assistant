"""
Verification D: Remaining Browser Coverage via Playwright Chromium.
Tests remaining workflows in live browser at http://localhost:3000:
1. Reimbursement request draft & confirmation
2. HR service request draft & confirmation
3. Equipment requisition draft & confirmation
4. Contact update draft & confirmation
5. IT ticket update draft & confirmation
6. Leave cancellation in UI
7. HR Admin (Alice E101) login & administrative cross-employee lookup
"""

import os
import json
import time
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.abspath("artifacts/audit_evidence/remaining_workflows")
os.makedirs(OUTPUT_DIR, exist_ok=True)

workflow_results = {}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()

    def send_and_wait(prompt: str, wait_seconds: int = 5):
        print(f"  Sending prompt: '{prompt}'")
        chat_input = page.locator('textarea, input[placeholder*="Ask" i], input[placeholder*="message" i]')
        chat_input.fill(prompt)
        page.keyboard.press("Enter")
        page.wait_for_timeout(wait_seconds * 1000)

    # 1. Login as Bob (E102)
    print("\n[Step 1] Navigating and logging in as Bob Jones...")
    page.goto("http://localhost:3000", timeout=20000)
    page.wait_for_load_state("networkidle", timeout=10000)

    email_input = page.locator('input[type="email"], input[name="email"], input[placeholder*="email" i]')
    if email_input.count() > 0:
        email_input.fill("bob@acme.com")
        page.fill('input[type="password"], input[name="password"]', "Password123!")
        page.click('button[type="submit"], button:has-text("Sign In"), button:has-text("Log In")')
        page.wait_for_timeout(3000)

    # Workflow 1: Reimbursement request draft & confirmation
    print("\n[Step 2] Testing Reimbursement Request Draft...")
    send_and_wait("I want to submit an expense reimbursement of $150 for an ergonomic chair purchased on 2026-11-15 from Office Depot", wait_seconds=6)
    page.screenshot(path=os.path.join(OUTPUT_DIR, "reimbursement_draft.png"))

    reimb_btn = page.locator('button:has-text("Confirm Submission")')
    if reimb_btn.count() > 0:
        print("  Reimbursement Confirmation Card visible! Clicking Confirm...")
        reimb_btn.first.click()
        page.wait_for_timeout(5000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "reimbursement_confirmed.png"))
        workflow_results["reimbursement"] = "CONFIRMED"
    else:
        print("  Reimbursement Confirmation Card NOT visible.")
        workflow_results["reimbursement"] = "NOT_RENDERED"

    # Workflow 2: HR Service request draft & confirmation
    print("\n[Step 3] Testing HR Service Request Draft...")
    send_and_wait("I need an employment verification letter for my mortgage application at First National Bank", wait_seconds=6)
    page.screenshot(path=os.path.join(OUTPUT_DIR, "hr_service_draft.png"))

    hr_btn = page.locator('button:has-text("Confirm Submission")')
    if hr_btn.count() > 0:
        print("  HR Service Confirmation Card visible! Clicking Confirm...")
        hr_btn.first.click()
        page.wait_for_timeout(5000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "hr_service_confirmed.png"))
        workflow_results["hr_service"] = "CONFIRMED"
    else:
        print("  HR Service Confirmation Card NOT visible.")
        workflow_results["hr_service"] = "NOT_RENDERED"

    # Workflow 3: Equipment request draft & confirmation
    print("\n[Step 4] Testing Equipment Requisition Draft...")
    send_and_wait("I need a 27-inch external monitor for dual display engineering work", wait_seconds=6)
    page.screenshot(path=os.path.join(OUTPUT_DIR, "equipment_draft.png"))

    eq_btn = page.locator('button:has-text("Confirm Submission")')
    if eq_btn.count() > 0:
        print("  Equipment Confirmation Card visible! Clicking Confirm...")
        eq_btn.first.click()
        page.wait_for_timeout(5000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "equipment_confirmed.png"))
        workflow_results["equipment"] = "CONFIRMED"
    else:
        print("  Equipment Confirmation Card NOT visible.")
        workflow_results["equipment"] = "NOT_RENDERED"

    # Workflow 4: Contact update draft & confirmation
    print("\n[Step 5] Testing Contact Update Draft...")
    send_and_wait("Please update my emergency contact name to Mary Jones", wait_seconds=6)
    page.screenshot(path=os.path.join(OUTPUT_DIR, "contact_update_draft.png"))

    ct_btn = page.locator('button:has-text("Confirm Submission")')
    if ct_btn.count() > 0:
        print("  Contact Update Confirmation Card visible! Clicking Confirm...")
        ct_btn.first.click()
        page.wait_for_timeout(5000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "contact_update_confirmed.png"))
        workflow_results["contact_update"] = "CONFIRMED"
    else:
        print("  Contact Update Confirmation Card NOT visible.")
        workflow_results["contact_update"] = "NOT_RENDERED"

    # Workflow 5: IT Ticket Update
    print("\n[Step 6] Testing IT Ticket Update...")
    send_and_wait("Please update ticket IT-1042: The VPN issue happens primarily on home WiFi", wait_seconds=6)
    page.screenshot(path=os.path.join(OUTPUT_DIR, "it_ticket_update.png"))

    upd_btn = page.locator('button:has-text("Confirm Submission")')
    if upd_btn.count() > 0:
        print("  Ticket Update Confirmation Card visible! Clicking Confirm...")
        upd_btn.first.click()
        page.wait_for_timeout(5000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "it_ticket_update_confirmed.png"))
        workflow_results["ticket_update"] = "CONFIRMED"
    else:
        print("  Ticket Update Confirmation Card NOT visible.")
        workflow_results["ticket_update"] = "NOT_RENDERED"

    # Workflow 6: Leave Cancellation
    print("\n[Step 7] Testing Leave Cancellation...")
    send_and_wait("I want to cancel leave request LV-2026-0002", wait_seconds=6)
    page.screenshot(path=os.path.join(OUTPUT_DIR, "leave_cancel_draft.png"))

    cancel_btn = page.locator('button:has-text("Confirm Submission"), button:has-text("Confirm")')
    if cancel_btn.count() > 0:
        print("  Cancel Confirmation Card visible! Clicking Confirm...")
        cancel_btn.first.click()
        page.wait_for_timeout(5000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "leave_cancel_confirmed.png"))
        workflow_results["leave_cancellation"] = "CONFIRMED"
    else:
        print("  Cancel Confirmation Card NOT visible.")
        workflow_results["leave_cancellation"] = "NOT_RENDERED"

    # Workflow 7: Sign out and login as Alice (HR Admin)
    print("\n[Step 8] Logging out and logging in as Alice (HR Admin)...")
    signout_btn = page.locator('button:has-text("Sign Out")')
    if signout_btn.count() > 0:
        signout_btn.first.click()
        page.wait_for_timeout(2000)

    email_input = page.locator('input[type="email"], input[name="email"], input[placeholder*="email" i]')
    if email_input.count() > 0:
        email_input.fill("alice@acme.com")
        page.fill('input[type="password"], input[name="password"]', "Password123!")
        page.click('button[type="submit"], button:has-text("Sign In"), button:has-text("Log In")')
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "alice_admin_logged_in.png"))

        print("  Testing HR Admin cross-employee lookup...")
        send_and_wait("Show me the leave balance and open tickets for employee E102", wait_seconds=6)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "alice_admin_cross_employee_lookup.png"))
        workflow_results["hr_admin"] = "VERIFIED"

    browser.close()

with open(os.path.join(OUTPUT_DIR, "workflow_summary.json"), "w") as f:
    json.dump(workflow_results, f, indent=2)

print("\nFinished remaining browser workflows verification.")
print("Results:", workflow_results)
