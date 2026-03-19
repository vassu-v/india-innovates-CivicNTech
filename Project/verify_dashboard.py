from playwright.sync_api import Page, expect, sync_playwright
import os
import time
import datetime
import sys
import http.client

# This script performs a comprehensive end-to-end verification of the Co-Pilot Dashboard.
# It assumes the server is running on http://localhost:8000 and the database has been seeded.

def test_all_features(page: Page):
    print("Starting end-to-end verification...")

    # Register a global dialog handler for alerts, confirms, and prompts
    def handle_dialog(dialog):
        print(f"  - Handling dialog: {dialog.type} ('{dialog.message}')")
        if dialog.type == "prompt":
            # Dynamic date (today + 30 days) for extension
            new_date = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
            dialog.accept(new_date)
        else:
            dialog.accept()

    page.on("dialog", handle_dialog)

    # 1. Home Page
    print("1. Verifying Home Page...")
    page.goto("http://localhost:8000")
    page.wait_for_selector("#top-user-name")
    # Use a flexible check for the name since it might have been updated
    name = page.locator("#top-user-name").inner_text()
    print(f"  - Logged in as: {name}")
    page.screenshot(path="verify_1_home.png")

    # 2. To-Do Page
    print("2. Verifying To-Do Page actions...")
    page.click(".nav-tab:has-text('To-Do')")
    page.wait_for_selector("#page-todo.active")
    page.wait_for_selector("#page-todo .todo-item", timeout=10000)

    # Complete an item
    print("  - Completing an item...")
    page.locator("#page-todo .todo-item").first.locator(".todo-text").click()
    page.wait_for_timeout(2000)

    # Extend an item
    print("  - Extending an item...")
    page.locator("#page-todo .todo-item").first.locator(".gen-btn:has-text('Extend')").click()
    page.wait_for_timeout(2000)
    page.screenshot(path="verify_2_todo.png")

    # 3. Commitments Page
    print("3. Verifying Commitments Page...")
    page.click(".nav-tab:has-text('Commitments')")
    page.wait_for_selector("#page-commitments.active")
    page.wait_for_selector("#page-commitments .todo-item, #page-commitments .issue-item", timeout=10000)
    page.screenshot(path="verify_3_commitments.png")

    # 4. Digest Page
    print("4. Verifying Digest Page...")
    page.click(".nav-tab:has-text('Digest')")
    page.wait_for_selector("#page-digest.active")
    page.screenshot(path="verify_4_digest.png")

    # 5. Upload Meeting
    print("5. Verifying Meeting Upload...")
    page.click(".nav-tab:has-text('Upload Meeting')")
    page.wait_for_selector("#page-upload.active")

    transcript_path = "temp_transcript.txt"
    with open(transcript_path, "w") as f:
        f.write("I will ensure the park in Ward 42 is cleaned. I will also fix the lights.")

    page.set_input_files("#meeting-file-input", transcript_path)
    page.fill("#meeting-date", "2026-03-05")
    page.click("#meeting-upload-btn")
    page.wait_for_selector("#meeting-upload-status", state="visible", timeout=20000)
    page.screenshot(path="verify_5_upload.png")
    os.remove(transcript_path)

    # 6. Log Issue Page (Vector Clustering)
    print("6. Verifying Log Issue (Vector Clustering)...")
    page.click(".nav-tab:has-text('Log Issue')")
    page.wait_for_selector("#page-issues.active")
    page.fill('#page-issues input[placeholder="Full name"]', "Verification User")
    page.fill('#page-issues input[placeholder="Mobile number"]', "9999999999")
    page.fill('#page-issues input[placeholder*="Ward"]', "Ward 42")
    page.fill('#page-issues textarea', "Drains are overflowing near the community center.")
    page.click("#page-issues .submit-btn")
    page.wait_for_selector("#submit-confirm", state="visible")
    page.screenshot(path="verify_6_log_issue.png")

    # 7. Profile Page
    print("7. Verifying Profile Page...")
    page.click(".nav-tab:has-text('Profile')")
    page.wait_for_selector("#page-profile.active")

    new_name = "Shri Rajendra Kumar Verma"
    page.fill("#prof-name", new_name)
    page.click("#page-profile button:has-text('Save Changes')")
    page.wait_for_selector("#prof-confirm", state="visible")

    page.goto("http://localhost:8000")
    page.wait_for_selector("#top-user-name")
    expect(page.locator("#top-user-name")).to_contain_text(new_name)
    print("  - Profile persistence verified.")

    # 8. Context Injection
    print("8. Verifying Context Injection...")
    page.click(".nav-tab:has-text('Profile')")
    page.wait_for_selector("#page-profile.active")

    ctx_path = "temp_context.txt"
    with open(ctx_path, "w") as f:
        f.write("Detailed demographic data for Ward 42: 50,000 residents.")
    page.set_input_files("#ctx-file-input", ctx_path)
    page.fill("#ctx-label", "Ward 42 Demographics")
    page.click("#ctx-upload-btn")
    page.wait_for_selector("#inject-confirm", state="visible")
    page.screenshot(path="verify_8_context.png")
    os.remove(ctx_path)

    # 9. Chat System
    print("9. Verifying Chat System...")
    page.click(".nav-tab:has-text('Chat')")
    page.wait_for_selector("#page-chat.active")
    page.fill(".chat-input", "Who is the MLA?")
    page.click(".chat-send")
    # Wait for response bubble to appear and not be "thinking"
    page.wait_for_selector(".bubble.ai:not(.thinking)", timeout=30000)
    page.screenshot(path="verify_9_chat.png")

    print("\nVerification complete! Screenshots saved as verify_*.png")

if __name__ == "__main__":
    # Check if server is up
    conn = http.client.HTTPConnection("127.0.0.1", 8000)
    try:
        conn.request("GET", "/")
        res = conn.getresponse()
        if res.status != 200:
            raise RuntimeError(f"Server returned status {res.status}")
    except (OSError, http.client.HTTPException, RuntimeError) as exc:
        print("Error: Dashboard server not found at http://localhost:8000. Please start it first.")
        print("  Command: PYTHONPATH=Project python -m uvicorn main:app --app-dir Project --port 8000")
        sys.exit(1)
    finally:
        conn.close()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        try:
            test_all_features(page)
        except Exception as e:
            print(f"\nVerification failed: {e}")
            page.screenshot(path="verify_error.png")
            sys.exit(1)
        finally:
            browser.close()
