from playwright.sync_api import Page, expect, sync_playwright
import sys

def verify_suggestions(page: Page):
    page.goto("http://127.0.0.1:8000")

    # Check Nav for Suggestions Tab
    print("Checking Nav tabs...")
    suggestion_tab = page.locator(".nav-tab:has-text('Suggestions')")
    if suggestion_tab.count() == 0:
        print("FAIL: Suggestion tab missing")
        sys.exit(1)

    # Go to Suggestions page
    suggestion_tab.click()
    page.wait_for_selector("#page-suggestions.active")

    # Generate suggestions
    print("Generating suggestions...")
    page.click("#sug-gen-btn")
    page.wait_for_timeout(5000) # Give it some time

    page.screenshot(path="verification/suggestions_active.png")
    print("Screenshot saved to verification/suggestions_active.png")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            verify_suggestions(page)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
        finally:
            browser.close()
