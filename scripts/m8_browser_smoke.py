"""Opt-in Phase 8 attachment smoke against disposable localhost Docker/MinIO."""
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
    fixture = ARTIFACTS / "attachment-evidence.txt"
    fixture.write_text("CentralOps attachment smoke evidence.\n", encoding="utf-8")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1100}, accept_downloads=True)
        page = context.new_page()
        page.set_default_timeout(30000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def capture(name):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.screenshot(path=str(ARTIFACTS / name), full_page=True)

        try:
            page.goto(BASE, wait_until="networkidle")
            sign_in(page, "employee@centralops.demo", "Employee123!")
            nav = page.get_by_role("navigation", name="Primary navigation")
            nav.get_by_role("button", name="Submitted requests", exact=True).click()
            page.get_by_role("button").filter(has=page.get_by_text(TITLE, exact=True)).click()
            expect(page.get_by_role("region", name="Request attachments")).to_be_visible()

            chooser = page.locator('input[type="file"]')
            chooser.set_input_files(str(fixture))
            expect(page.get_by_text("Attachment uploaded.", exact=True)).to_be_visible()
            expect(page.get_by_text("attachment-evidence.txt", exact=True)).to_be_visible()
            capture("m8-attachment-ready.png")

            with page.expect_download() as download_info:
                page.get_by_role("button", name="Download", exact=True).click()
            download = download_info.value
            downloaded = ARTIFACTS / "m8-downloaded-evidence.txt"
            download.save_as(str(downloaded))
            assert downloaded.read_text(encoding="utf-8") == fixture.read_text(encoding="utf-8")
            assert not errors, f"Browser runtime errors: {errors}"
            print("PASS: requester presigns upload -> browser PUTs to MinIO -> completes -> lists -> authorized download matches bytes")
        except Exception:
            capture("m8-failure.png")
            raise
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    run()
