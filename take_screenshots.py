import time
from playwright.sync_api import sync_playwright

def take_screenshots():
    print("Starting browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 1920x1080 for nice wide screenshots
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        print("Logging in...")
        page.goto("http://localhost:5000/login")
        page.fill("input[name='username']", "admin")
        page.fill("input[name='password']", "admin123")
        page.click("button[type='submit']")
        
        # Wait for dashboard to load
        page.wait_for_url("**/dashboard")
        time.sleep(2) # Give charts time to render
        page.screenshot(path="dashboard.png")
        print("Saved dashboard.png")

        # Task List
        page.goto("http://localhost:5000/tasks")
        time.sleep(1)
        page.screenshot(path="task_list.png")
        print("Saved task_list.png")

        # Kanban
        page.goto("http://localhost:5000/kanban")
        time.sleep(1)
        page.screenshot(path="kanban_board.png")
        print("Saved kanban_board.png")

        # Timeline
        page.goto("http://localhost:5000/timeline")
        time.sleep(3) # Timeline chart takes a bit to load
        page.screenshot(path="timeline.png", full_page=True)
        print("Saved timeline.png")

        # Calendar
        page.goto("http://localhost:5000/calendar")
        time.sleep(3) # Calendar takes a bit to load
        page.screenshot(path="calendar.png", full_page=True)
        print("Saved calendar.png")

        # New Task Form
        page.goto("http://localhost:5000/tasks/new")
        time.sleep(1)
        page.screenshot(path="new_task.png", full_page=True)
        print("Saved new_task.png")

        browser.close()
        print("Done!")

if __name__ == "__main__":
    take_screenshots()
