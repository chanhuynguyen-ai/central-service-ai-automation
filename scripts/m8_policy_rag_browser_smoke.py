"""Chromium smoke test for M8 permission-aware policy RAG.

Runs only against the disposable localhost demo stack with LLM_PROVIDER=mock.
The browser must receive a grounded answer from the new knowledge endpoint while
policy access filtering remains server-side.
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
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.set_default_timeout(20000)
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(BASE, wait_until="networkidle")
            sign_in(page)

            nav = page.get_by_role("navigation", name="Primary navigation")
            nav.get_by_role("button", name="AI assistant", exact=True).click()
            expect(page.get_by_role("heading", name="Policy assistant", exact=True)).to_be_visible()

            page.get_by_placeholder("Ask about a request or policy...").fill(
                "When may I request a managed laptop replacement?"
            )
            page.get_by_role("button", name="Send", exact=False).click()

            expect(page.get_by_text("Managed Device Replacement Policy", exact=False)).to_be_visible(timeout=30000)
            expect(page.get_by_text("repeated hardware failures", exact=False)).to_be_visible()
            page.screenshot(path=str(ARTIFACTS / "m8-policy-rag-grounded.png"), full_page=True)

            assert not errors, f"Browser runtime errors: {errors}"
            print("PASS: policy assistant -> permission-filtered knowledge endpoint -> grounded answer")
        except Exception:
            page.screenshot(path=str(ARTIFACTS / "m8-policy-rag-failure.png"), full_page=True)
            raise
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    run()
