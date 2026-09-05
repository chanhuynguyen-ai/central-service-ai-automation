"""Opt-in Chromium smoke against disposable localhost Docker/PostgreSQL only.

No token/header/network traces are saved. Screenshots contain demo data only.
"""
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
        page.set_default_timeout(25000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("dialog", lambda dialog: dialog.accept())
        nav = page.get_by_role("navigation", name="Primary navigation")

        def capture(name):
            # A full-page capture taken after clicking a lower-page button can
            # place sticky chrome mid-image. Capture the real page from its top.
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(ARTIFACTS / name), full_page=True)

        def logout():
            page.get_by_role("button", name="Sign out", exact=True).click()
            expect(page.get_by_role("heading", name="Sign in", exact=True)).to_be_visible()

        def open_task():
            nav.get_by_role("button", name="Approvals", exact=True).click()
            page.get_by_role("button").filter(has=page.get_by_text(TITLE, exact=True)).click()
            expect(page.get_by_role("form", name="Approval decision")).to_be_visible()

        def decide(action, comment):
            form = page.get_by_role("form", name="Approval decision")
            form.get_by_label("Decision", exact=True).select_option(action)
            form.get_by_label("Decision comment", exact=False).fill(comment)
            form.get_by_role("button", name="Record decision", exact=True).click()
            expect(page.get_by_role("form", name="Approval decision")).to_have_count(0)

        try:
            page.goto(BASE, wait_until="networkidle")
            sign_in(page, "employee@centralops.demo", "Employee123!")
            nav.get_by_role("button", name="Service catalog", exact=True).click()
            card = page.get_by_role("article").filter(has=page.get_by_role("heading", name="Laptop replacement", exact=True))
            card.get_by_role("button", name="Start draft").click()
            expect(page.get_by_role("button", name="Submit for approval", exact=True)).to_be_disabled()
            page.get_by_label("Request title", exact=False).fill(TITLE)
            page.get_by_label("Business context", exact=False).fill("The managed laptop fails during client meetings and needs replacement.")
            page.get_by_label("Reason for replacement", exact=False).fill("Repeated hardware failures during customer meetings.")
            page.get_by_label("Preferred device", exact=False).select_option("windows")
            page.get_by_label("Cost center", exact=False).fill("M3-INITIAL")
            page.get_by_role("button", name="Save draft", exact=True).click()
            expect(page.get_by_role("button", name="Submit for approval", exact=True)).to_be_enabled()
            page.get_by_role("button", name="Submit for approval", exact=True).click()
            expect(page.get_by_text("Request status: pending approval", exact=True)).to_be_visible()
            expect(page.get_by_role("heading", name="Attempt 1 / pending", exact=True)).to_be_visible()
            capture("m3-submitted.png")
            logout()
            sign_in(page, "approver@centralops.demo", "Approver123!")
            nav.get_by_role("button", name="Approvals", exact=True).click()
            expect(page.get_by_text("No assigned tasks in this view.", exact=True)).to_be_visible()
            logout()
            sign_in(page, "manager.finance@centralops.demo", "Manager123!")
            open_task()
            decide("request_changes", "Please use the approved cost center before resubmitting.")
            expect(page.get_by_text("Request status: changes requested", exact=True)).to_be_visible()
            capture("m3-changes-requested.png")
            logout()
            sign_in(page, "employee@centralops.demo", "Employee123!")
            nav.get_by_role("button", name="My drafts", exact=True).click()
            draft = page.get_by_role("article").filter(has=page.get_by_role("heading", name=TITLE, exact=True))
            draft.get_by_role("button", name="Continue editing", exact=True).click()
            page.get_by_label("Cost center", exact=False).fill("M3-APPROVED")
            page.get_by_role("button", name="Save draft", exact=True).click()
            expect(page.get_by_role("button", name="Submit for approval", exact=True)).to_be_enabled()
            page.get_by_role("button", name="Submit for approval", exact=True).click()
            expect(page.get_by_role("heading", name="Attempt 2 / pending", exact=True)).to_be_visible()
            expect(page.get_by_role("heading", name="Attempt 1 / changes requested", exact=True)).to_be_visible()
            logout()
            sign_in(page, "manager.finance@centralops.demo", "Manager123!")
            open_task()
            decide("approve", "Budget owner approval for the corrected cost center.")
            expect(page.get_by_text("Request status: pending approval", exact=True)).to_be_visible()
            logout()
            sign_in(page, "service.lead@centralops.demo", "ServiceLead123!")
            open_task()
            decide("approve", "Service owner approval recorded.")
            expect(page.get_by_text("Request status: approved", exact=True)).to_be_visible()
            expect(page.get_by_text("Approval completed. Service fulfillment has not started; it is a separate lifecycle.", exact=True)).to_be_visible()
            capture("m3-approved.png")
            logout()
            sign_in(page, "employee@centralops.demo", "Employee123!")
            nav.get_by_role("button", name="Submitted requests", exact=True).click()
            page.get_by_role("button").filter(has=page.get_by_text(TITLE, exact=True)).click()
            expect(page.get_by_text("M3-INITIAL", exact=True)).to_be_visible()
            expect(page.get_by_text("M3-APPROVED", exact=True)).to_be_visible()
            expect(page.get_by_text("Request status: approved", exact=True)).to_be_visible()
            assert not errors, f"Browser runtime errors: {errors}"
            print("PASS: real browser submit -> assigned-only inbox -> request changes -> edit/resubmit -> manager approve -> service lead approve -> immutable attempt history")
        except Exception:
            capture("m3-failure.png")
            raise
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    run()
