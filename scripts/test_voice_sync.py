import os
import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            '--use-fake-ui-for-media-stream',
            '--use-fake-device-for-media-stream',
        ]
    )
    context = browser.new_context(permissions=['microphone'])
    page = context.new_page()
    page.goto('http://localhost:3000')
    page.wait_for_selector('text=Bob Jones', timeout=10000)
    page.click('button:has-text("Bob Jones")')
    page.click('button:has-text("Sign In")')
    page.wait_for_selector('text=Enable Voice', timeout=10000)
    page.click('button:has-text("Enable Voice")')
    page.wait_for_selector('text=Waiting for', timeout=10000)
    status_text = page.locator('text=Waiting for').text_content()
    print('Voice status:', status_text)
    
    page.evaluate("window.__ARCHIE_STT__.simulateRecognitionEvent('Hey Archie', true)")
    time.sleep(1.0)
    print('Wake word test succeeded!')
    browser.close()

