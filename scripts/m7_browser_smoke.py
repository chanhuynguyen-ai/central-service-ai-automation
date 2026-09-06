"""Chromium smoke test for M7 AI-assisted request intake.

Runs only against the disposable localhost demo stack with LLM_PROVIDER=mock.
The AI suggestion must remain advisory and become a normal editable unsaved draft.
"""
import os
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright

BASE = os.getenv("E2E_WEB_URL", "http://localhost:3000")
ARTIFACTS = Path("artifacts")


def sign_in(page) -> None:
    page.get_by_label("Email", exact=True).fill("employee@centralops.demo")
    page.get_by_label("Password", exact=True).fill("Employee123!")
    page.get_by_role("button", name="Sign in to workspace", exact=True).click()
    expect(page.get_by_role("heading", name="Service operations overview", exact=True)).to_be_visible(timeout=30000)


def run() -> None:
    if os.getenv("CENTRALOPS_E2E") != "1" or urlparse(BASE).hostname not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("This test requires CENTRALOPS_E2E=1 and a disposable localhost stack.")
    ARTIFACTS.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        page.set_default_timeout(20000)
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(BASE, wait_until="networkidle")
            sign_in(page)
            nav = page.get_by_role("navigation", name="Primary navigation")
            nav.get_by_role("button", name="Service catalog", exact=True).click()

            expect(page.get_by_role("heading", name="Describe what you need", exact=True)).to_be_visible()
            request_text = (
                "My work laptop keeps failing during client calls and I need a Windows laptop replacement. "
                "Cost center IT-DEMO-777."
            )
            page.get_by_label("Your request", exact=True).fill(request_text)
            page.get_by_role("button", name="Suggest request", exact=True).click()

            expect(page.get_by_text("Laptop replacement", exact=True).first).to_be_visible()
            expect(page.get_by_text("Advisory only", exact=True)).to_be_visible()
            expect(page.get_by_text("reason, device, cost_center", exact=True)).to_be_visible()
            expect(page.get_by_text("No required fields missing.", exact=True)).to_be_visible()
            page.screenshot(path=str(ARTIFACTS / "m7-ai-suggestion.png"), full_page=True)

            page.get_by_role("button", name="Review this draft", exact=True).click()
            expect(page.get_by_label("Business context", exact=False)).to_have_value(request_text)
            expect(page.get_by_label("Reason for replacement", exact=False)).to_have_value(request_text)
            expect(page.get_by_label("Preferred device", exact=False)).to_have_value("windows")
            expect(page.locator('input[name="cost_center"]')).to_have_value("IT-DEMO-777")
            expect(page.get_by_text("AI suggestion loaded into an unsaved draft", exact=False)).to_be_visible()

            page.get_by_role("button", name="Save draft", exact=True).click()
            expect(page.get_by_role("status")).to_contain_text("Required fields are complete")
            page.screenshot(path=str(ARTIFACTS / "m7-ai-draft-reviewed.png"), full_page=True)

            # Saving remains a separate explicit action and submission still requires
            # the existing human approval button; AI itself never invokes it.
            expect(page.get_by_role("button", name="Submit for approval", exact=True)).to_be_enabled()
            assert not errors, f"Browser runtime errors: {errors}"
            print("PASS: AI intake -> published catalog suggestion -> human review -> editable normal draft")
        except Exception:
            page.screenshot(path=str(ARTIFACTS / "m7-failure.png"), full_page=True)
            raise
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    run()
