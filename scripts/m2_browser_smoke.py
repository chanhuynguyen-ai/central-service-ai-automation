"""Real Chromium + production Docker + PostgreSQL smoke test for M2.

Only run against the disposable localhost demo stack, with CENTRALOPS_E2E=1.
The script intentionally writes demo drafts; never point it at production.
No token values or request headers are printed or saved in artifacts.
"""
import os
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright

BASE = os.getenv("E2E_WEB_URL", "http://localhost:3000")
ARTIFACTS = Path("artifacts")


def sign_in(page, email, password):
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Password", exact=True).fill(password)
    page.get_by_role("button", name="Sign in to workspace", exact=True).click()
    expect(page.get_by_role("heading", name="Service operations overview", exact=True)).to_be_visible(timeout=30000)


def run():
    if os.getenv("CENTRALOPS_E2E") != "1" or urlparse(BASE).hostname not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("This test requires CENTRALOPS_E2E=1 and a disposable localhost stack.")
    ARTIFACTS.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.set_default_timeout(20000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(BASE, wait_until="networkidle")
            sign_in(page, "employee@centralops.demo", "Employee123!")
            nav = page.get_by_role("navigation", name="Primary navigation")
            expect(nav.get_by_role("button", name="Approvals", exact=True)).to_have_count(0)
            nav.get_by_role("button", name="Service catalog", exact=True).click()
            card = page.get_by_role("article").filter(has=page.get_by_role("heading", name="Laptop replacement", exact=True))
            expect(card).to_be_visible()
            page.screenshot(path=str(ARTIFACTS / "m2-catalog.png"), full_page=True)
            card.get_by_role("button", name="Start draft").click()
            page.get_by_role("button", name="Save draft", exact=True).click()
            expect(page.get_by_role("status")).to_contain_text("Draft saved")
            expect(page.get_by_text("This field is required.", exact=True).first).to_be_visible()
            page.get_by_label("Request title", exact=False).fill("M2 browser: replace failing laptop")
            page.get_by_label("Business context", exact=False).fill("The laptop shuts down during client meetings and needs replacement.")
            page.get_by_label("Reason for replacement", exact=False).fill("Repeated hardware failure during meetings.")
            page.get_by_label("Preferred device", exact=False).select_option("windows")
            page.get_by_label("Cost center", exact=False).fill("IT-DEMO-001")
            page.get_by_role("button", name="Save draft", exact=True).click()
            expect(page.get_by_role("status")).to_contain_text("Required fields are complete")
            page.screenshot(path=str(ARTIFACTS / "m2-draft.png"), full_page=True)
            nav.get_by_role("button", name="My drafts", exact=True).click()
            item = page.get_by_role("article").filter(has=page.get_by_role("heading", name="M2 browser: replace failing laptop", exact=True))
            expect(item).to_be_visible()
            page.screenshot(path=str(ARTIFACTS / "m2-my-drafts.png"), full_page=True)
            item.get_by_role("button", name="Continue editing").click()
            expect(page.get_by_label("Cost center", exact=False)).to_have_value("IT-DEMO-001")
            page.reload(wait_until="networkidle")
            expect(page.get_by_role("heading", name="Service operations overview", exact=True)).to_be_visible()
            nav.get_by_role("button", name="My drafts", exact=True).click()
            page.get_by_role("button", name="Continue editing", exact=True).click()
            expect(page.get_by_label("Preferred device", exact=False)).to_have_value("windows")
            page.get_by_role("button", name="Sign out", exact=True).click()
            expect(page.get_by_role("heading", name="Sign in", exact=True)).to_be_visible()
            sign_in(page, "other.employee@centralops.demo", "Employee123!")
            nav.get_by_role("button", name="My drafts", exact=True).click()
            expect(page.get_by_text("You have no saved drafts.", exact=True)).to_be_visible()
            page.get_by_role("button", name="Sign out", exact=True).click()
            sign_in(page, "manager.finance@centralops.demo", "Manager123!")
            expect(nav.get_by_role("button", name="Approvals")).to_be_visible()
            page.get_by_role("button", name="Sign out", exact=True).click()
            assert not errors, f"Browser runtime errors: {errors}"
            print("PASS: catalog -> incomplete draft -> typed form -> save -> reopen -> reload -> logout -> ownership isolation -> manager navigation")
        except Exception:
            page.screenshot(path=str(ARTIFACTS / "m2-failure.png"), full_page=True)
            raise
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    run()
