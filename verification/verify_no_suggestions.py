from playwright.sync_api import Page, expect, sync_playwright
import sys

def verify_no_suggestions(page: Page):
    page.goto("http://127.0.0.1:8000")

    # Check Home Page for Suggestion Card (should be gone)
    print("Checking Home page...")
    suggestion_card = page.locator(".home-card:has-text('Strategic Suggestions')")
    if suggestion_card.count() > 0:
        print("FAIL: Suggestion card still exists on Home page")
        sys.exit(1)
    else:
        print("OK: Suggestion card removed from Home page")

    # Check Nav for Suggestions Tab (should be gone)
    print("Checking Nav tabs...")
    suggestion_tab = page.locator(".nav-tab:has-text('Suggestions')")
    if suggestion_tab.count() > 0:
        print("FAIL: Suggestion tab still exists in Nav")
        sys.exit(1)
    else:
        print("OK: Suggestion tab removed from Nav")

    # Check Page Div for Suggestions (should be gone)
    print("Checking Page divs...")
    suggestion_page = page.locator("#page-suggestions")
    if suggestion_page.count() > 0:
        print("FAIL: Suggestion page div still exists")
        sys.exit(1)
    else:
        print("OK: Suggestion page div removed")

    page.screenshot(path="verification/no_suggestions.png")
    print("Screenshot saved to verification/no_suggestions.png")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            verify_no_suggestions(page)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
        finally:
            browser.close()
