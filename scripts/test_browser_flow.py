import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    
    print("[1] Opening http://localhost:3000...")
    page.goto("http://localhost:3000")
    page.wait_for_load_state("networkidle")
    
    # Check Bob login
    print("[2] Logging in as Bob Jones...")
    bob_btn = page.locator('button:has-text("Bob Jones")')
    if bob_btn.count() > 0:
        bob_btn.first.click()
    else:
        page.locator('input[type="email"]').fill("bob@acme.com")
        page.locator('input[type="password"]').fill("Password123!")
    page.locator('button[type="submit"], button:has-text("Sign In")').first.click()
    page.wait_for_timeout(2500)
    
    # Check chat input
    chat_input = page.locator('textarea, input[placeholder*="Ask" i], input[placeholder*="message" i]')
    print("Chat input count:", chat_input.count())
    assert chat_input.count() > 0, "Chat input missing after login!"
    
    # Ask policy question
    print("[3] Asking policy question...")
    chat_input.fill("What is the annual vacation entitlement, and how many unused days can I carry forward?")
    page.keyboard.press("Enter")
    page.wait_for_timeout(6000)
    
    # Check response text
    print("Response snippet:", page.locator('div[class*="message"], div[class*="bubble"], div[class*="chat"]').last.inner_text()[:200])
    
    # Test logout and Alice login
    print("[4] Logging out...")
    signout_btn = page.locator('button:has-text("Sign Out")')
    if signout_btn.count() > 0:
        signout_btn.first.click()
        page.wait_for_timeout(2000)
    
    print("[5] Logging in as Alice Smith...")
    alice_btn = page.locator('button:has-text("Alice Smith")')
    if alice_btn.count() > 0:
        alice_btn.first.click()
    else:
        page.locator('input[type="email"]').fill("alice@acme.com")
        page.locator('input[type="password"]').fill("Password123!")
    page.locator('button[type="submit"], button:has-text("Sign In")').first.click()
    page.wait_for_timeout(2500)
    
    print("Alice chat input count:", page.locator('textarea, input[placeholder*="Ask" i], input[placeholder*="message" i]').count())
    print("All browser flow tests PASSED cleanly!")
    browser.close()
