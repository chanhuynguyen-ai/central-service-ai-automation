"""Opt-in M6 notification smoke against disposable localhost Docker/PostgreSQL only."""
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright

from m2_browser_smoke import sign_in

BASE = os.getenv("E2E_WEB_URL", "http://localhost:3000")
MAILPIT = os.getenv("E2E_MAILPIT_URL", "http://localhost:8025")
ARTIFACTS = Path("artifacts")


def mail_subjects():
    with urlopen(f"{MAILPIT}/api/v1/messages", timeout=5) as response:  # noqa: S310 - localhost guard below
        payload = json.load(response)
    messages = payload.get("messages", []) if isinstance(payload, dict) else []
    return [str(row.get("Subject", "")) for row in messages if isinstance(row, dict)]


def run():
    if os.getenv("CENTRALOPS_E2E") != "1":
        raise RuntimeError("Requires CENTRALOPS_E2E=1.")
    if urlparse(BASE).hostname not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("Browser target must be disposable localhost.")
    if urlparse(MAILPIT).hostname not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("Mail target must be disposable localhost.")

    deadline = time.time() + 45
    subjects = []
    while time.time() < deadline:
        try:
            subjects = mail_subjects()
        except Exception:
            subjects = []
        if any(subject in {"Approval task assigned", "Changes requested", "Request approved", "Service work assigned", "Request resolved"} for subject in subjects):
            break
        time.sleep(2)
    assert subjects, "Mailpit did not receive any asynchronous notification email."

    ARTIFACTS.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.set_default_timeout(25000)
        try:
            page.goto(BASE, wait_until="networkidle")
            sign_in(page, "employee@centralops.demo", "Employee123!")
            bell = page.get_by_role("button", name=re.compile(r"^Notifications"))
            expect(bell).to_be_visible()
            bell.click()
            expect(page.get_by_role("heading", name="Notifications", exact=True)).to_be_visible()
            expect(page.get_by_text("Changes requested", exact=True).first).to_be_visible()
            mark_all = page.get_by_role("button", name="Mark all read", exact=True)
            if mark_all.is_enabled():
                mark_all.click()
                expect(page.get_by_text("0 unread", exact=True)).to_be_visible()
            page.screenshot(path=str(ARTIFACTS / "m6-notifications.png"), full_page=True)
            print("PASS: async email reached Mailpit and in-app notification center is readable")
        except Exception:
            page.screenshot(path=str(ARTIFACTS / "m6-failure.png"), full_page=True)
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    run()
