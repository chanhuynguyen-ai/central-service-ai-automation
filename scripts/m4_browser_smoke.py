"""Opt-in M4 privacy smoke after the M3 browser flow, on disposable localhost."""
import os
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright

from m2_browser_smoke import sign_in
from m3_browser_smoke import TITLE

BASE = os.getenv("E2E_WEB_URL", "http://localhost:3000")
ARTIFACTS = Path("artifacts")
PUBLIC = '<img src=x onerror="window.__m4Xss=true"> M4 public update'
INTERNAL = "M4 restricted service coordination: do not disclose to requester."


def run():
    if os.getenv("CENTRALOPS_E2E") != "1" or urlparse(BASE).hostname not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("Requires explicit opt-in on a disposable localhost stack.")
    ARTIFACTS.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        page.set_default_timeout(25000)
        page.on("dialog", lambda dialog: dialog.accept())
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        nav = page.get_by_role("navigation", name="Primary navigation")

        def open_submission():
            nav.get_by_role("button", name="Submitted requests", exact=True).click()
            page.get_by_role("button").filter(has=page.get_by_text(TITLE, exact=True)).click()
            expect(page.get_by_text("Request status: approved", exact=True)).to_be_visible()
            expect(page.get_by_role("button", name="Refresh activity", exact=True)).to_be_enabled()

        def logout():
            page.get_by_role("button", name="Sign out", exact=True).click()
            expect(page.get_by_role("heading", name="Sign in", exact=True)).to_be_visible()

        def capture(filename):
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(ARTIFACTS / filename), full_page=True)

        try:
            page.goto(BASE, wait_until="networkidle")
            sign_in(page, "employee@centralops.demo", "Employee123!")
            expect(nav.get_by_role("button", name="Audit log", exact=True)).to_have_count(0)
            open_submission()
            expect(page.get_by_role("button", name="Internal notes", exact=True)).to_have_count(0)
            form = page.get_by_role("form", name="Add request comment")
            form.get_by_label("Public comment", exact=True).fill(PUBLIC)
            form.get_by_role("button", name="Post comment", exact=True).click()
            expect(page.get_by_text(PUBLIC, exact=True)).to_be_visible()
            assert not page.evaluate("Boolean(window.__m4Xss)"), "Comment HTML executed"
            page.reload(wait_until="networkidle")
            open_submission()
            expect(page.get_by_text(PUBLIC, exact=True)).to_be_visible()
            logout()
            sign_in(page, "manager.finance@centralops.demo", "Manager123!")
            open_submission()
            expect(page.get_by_text(PUBLIC, exact=True)).to_be_visible()
            page.get_by_role("button", name="Internal notes", exact=True).click()
            form = page.get_by_role("form", name="Add request comment")
            form.get_by_label("Internal note", exact=True).fill(INTERNAL)
            form.get_by_role("button", name="Post comment", exact=True).click()
            expect(page.get_by_text(INTERNAL, exact=True)).to_be_visible()
            capture("m4-reviewer-notes.png")
            logout()
            sign_in(page, "employee@centralops.demo", "Employee123!")
            open_submission()
            expect(page.get_by_text(INTERNAL, exact=True)).to_have_count(0)
            expect(page.get_by_role("button", name="Internal notes", exact=True)).to_have_count(0)
            expect(page.get_by_text("Internal note added", exact=True)).to_have_count(0)
            expect(page.get_by_text(PUBLIC, exact=True)).to_be_visible()
            capture("m4-requester-timeline.png")
            logout()
            sign_in(page, "other.employee@centralops.demo", "Employee123!")
            nav.get_by_role("button", name="Submitted requests", exact=True).click()
            expect(page.get_by_text("No submitted requests in your scope yet.", exact=True)).to_be_visible()
            expect(page.get_by_text(TITLE, exact=True)).to_have_count(0)
            logout()
            sign_in(page, "auditor@centralops.demo", "Auditor123!")
            open_submission()
            page.get_by_role("button", name="Internal notes", exact=True).click()
            expect(page.get_by_text(INTERNAL, exact=True)).to_be_visible()
            expect(page.get_by_role("form", name="Add request comment")).to_have_count(0)
            nav.get_by_role("button", name="Audit log", exact=True).click()
            audit = page.get_by_role("region", name="Audit workspace")
            expect(audit.get_by_role("button", name="Apply filters", exact=True)).to_be_enabled()
            audit.get_by_label("Event type", exact=True).fill("internal_note_added")
            audit.get_by_role("button", name="Apply filters", exact=True).click()
            expect(audit.get_by_text("internal_note_added", exact=True)).to_be_visible()
            expect(page.get_by_text(INTERNAL, exact=True)).to_have_count(0)
            expect(page.get_by_text(PUBLIC, exact=True)).to_have_count(0)
            capture("m4-audit-log.png")
            assert not errors, f"Browser errors: {errors}"
            print("PASS: public discussion persists, HTML escaped, internal note and event filtered, cross-account privacy, auditor read-only, safe privileged audit")
        except Exception:
            capture("m4-failure.png")
            raise
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    run()
