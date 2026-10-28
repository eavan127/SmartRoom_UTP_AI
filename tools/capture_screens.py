"""Walk through every screen of prototype/index.html and save screenshots to docs/screenshots/.

Opens the HTML file directly (no server) with a fixed 09:20 demo clock.
Needs: pip install playwright (uses the installed Edge or Chrome).

Usage: python tools/capture_screens.py [--channel msedge] [--width 1280 --height 800]
"""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
PAGE = (ROOT / "prototype" / "index.html").as_uri() + "?time=09:20"


def main(channel, width, height):
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=channel)
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(PAGE)
        n = [0]

        def shot(name):
            page.wait_for_timeout(700)  # let the scan flash finish
            n[0] += 1
            page.screenshot(path=str(OUT / f"{n[0]:02d}_{name}.png"))
            print("saved", name)

        def click(text):
            page.locator("button, .tile", has_text=text).first.click()

        def pick(booking_id):
            page.locator(f"button[onclick=\"pick('{booking_id}')\"]").click()

        def staff_login():
            page.fill("#pin", "1234")
            click("Log in")

        # collect: success path
        shot("home")
        click("Collect Room Card"); shot("collect_select_booking")
        pick("IB-2026-1041"); shot("collect_face_scan_start")
        click("Scan face"); click("Scan face"); shot("collect_face_scan_progress")
        click("Unknown face"); shot("collect_face_not_recognised")
        click("Scan face"); click("Scan face"); shot("collect_approved_locker_open")
        click("Card taken"); shot("collect_done")
        click("Finish")

        # collect: denied path + staff override
        click("Collect Room Card"); pick("IB-2026-1042")
        click("Scan face")
        for _ in range(3):
            click("Unknown face")
        shot("collect_denied")
        click("Call staff"); shot("staff_login")
        staff_login(); shot("staff_override")
        click("Approve and open locker"); shot("staff_override_approved")
        click("Card taken"); click("Finish")

        # return
        click("Return Room Card"); shot("return_select_card")
        pick("IB-2026-1041")
        for _ in range(4):
            click("Scan face")
        shot("return_locker_open")
        click("Card returned"); shot("return_done")
        click("Finish")

        # staff log and settings
        click("Staff"); staff_login()
        click("Card log"); shot("staff_card_log")
        click("Settings"); shot("staff_settings")
        browser.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default="msedge", help="msedge or chrome")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=800)
    a = ap.parse_args()
    main(a.channel, a.width, a.height)
