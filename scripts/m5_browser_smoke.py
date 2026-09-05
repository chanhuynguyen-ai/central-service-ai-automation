"""Opt-in M5 browser smoke against disposable localhost Docker/PostgreSQL only."""
import os
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright

from m2_browser_smoke import sign_in

BASE = os.getenv("E2E_WEB_URL", "http://localhost:3000")
ARTIFACTS = Path("artifacts")
TITLE = "M3 browser: governed laptop replacement"


def run():
    if os.getenv("CENTRALOPS_E2E") != "1" or urlparse(BASE).hostname not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("Requires explicit opt-in and disposable localhost stack.")
    ARTIFACTS.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        page.set_default_timeout(30000)
        page.on("dialog", lambda dialog: dialog.accept())
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def capture(name):
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(ARTIFACTS / name), full_page=True)

        try:
            page.goto(BASE, wait_until="networkidle")
            sign_in(page, "service.agent@centralops.demo", "ServiceAgent123!")
            page.goto(f"{BASE}/service-queue", wait_until="networkidle")
            expect(page.get_by_role("heading", name="Service fulfillment", exact=True)).to_be_visible()
            card = page.get_by_role("article").filter(has=page.get_by_role("heading", name=TITLE, exact=True))
            expect(card).to_be_visible()
            expect(card.get_by_text("queued", exact=True)).to_be_visible()
            capture("m5-queued.png")

            card.get_by_role("button", name="Claim work", exact=True).click()
            expect(card.get_by_text("assigned", exact=True)).to_be_visible()
            expect(card.get_by_text("Central Service Agent", exact=True)).to_be_visible()
            card.get_by_role("button", name="start", exact=True).click()
            expect(card.get_by_text("in progress", exact=True)).to_be_visible()
            card.get_by_role("button", name="Wait for requester", exact=True).click()
            expect(card.get_by_text("waiting requester", exact=True)).to_be_visible()
            card.get_by_role("button", name="resume", exact=True).click()
            expect(card.get_by_text("in progress", exact=True)).to_be_visible()
            card.get_by_label("Resolution summary", exact=False).fill("Replacement laptop prepared, configured, and handed to the requester.")
            card.get_by_role("button", name="resolve", exact=True).click()
            expect(card.get_by_text("resolved", exact=True)).to_be_visible()
            expect(card.get_by_text("Replacement laptop prepared, configured, and handed to the requester.", exact=True)).to_be_visible()
            card.get_by_role("button", name="close", exact=True).click()
            expect(card.get_by_text("closed", exact=True)).to_be_visible()
            capture("m5-closed.png")

            page.evaluate("sessionStorage.clear()")
            page.goto(BASE, wait_until="networkidle")
            sign_in(page, "employee@centralops.demo", "Employee123!")
            nav = page.get_by_role("navigation", name="Primary navigation")
            nav.get_by_role("button", name="Submitted requests", exact=True).click()
            page.get_by_role("button").filter(has=page.get_by_text(TITLE, exact=True)).click()
            expect(page.get_by_text("Request status: completed", exact=True)).to_be_visible()
            expect(page.get_by_text("Request closed", exact=True)).to_be_visible()
            capture("m5-requester-completed.png")

            assert not errors, f"Browser runtime errors: {errors}"
            print("PASS: queued -> claimed -> started -> requester wait -> resumed -> resolved -> closed; requester sees completed timeline")
        except Exception:
            capture("m5-failure.png")
            raise
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    run()
