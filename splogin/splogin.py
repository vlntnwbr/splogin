from playwright.sync_api import sync_playwright


def check_browser_launch():
    with sync_playwright() as playwright:
        try:
            browser = playwright.firefox.launch()
            browser.close()
            return True
        except:
            return False
