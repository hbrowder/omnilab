#!/usr/bin/env python3
"""Capture a screenshot of the AI Lab Builder panel for the README (CRE-48).

Drives the running OmniLab frontend at http://localhost:5000, bypasses the
login gate by pre-seeding sessionStorage, opens the "Build with AI" panel,
types an example prompt, and saves a PNG to docs/demo-assets/ai-lab-builder.png.
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

OUT = pathlib.Path(__file__).resolve().parents[1] / "docs/demo-assets/ai-lab-builder.png"
URL = "http://localhost:5000/"
PROMPT = ("Build an OSPF lab with two areas (area 0 and area 1) connected by an "
          "ABR. Use FRRouting nodes and bring up OSPF on the right interfaces.")


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                  device_scale_factor=2)
        # Pre-seed auth so the Login gate lets us through.
        ctx.add_init_script("window.sessionStorage.setItem('omnilab_auth','1')")
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle", timeout=30000)

        # Open the panel.
        btn = page.get_by_role("button", name="Build with AI")
        btn.first.wait_for(state="visible", timeout=15000)
        btn.first.click()

        # Type an example prompt so the capture looks alive.
        ta = page.locator("textarea")
        ta.first.wait_for(state="visible", timeout=10000)
        ta.first.fill(PROMPT)

        page.wait_for_timeout(800)  # let layout/animations settle
        page.screenshot(path=str(OUT), full_page=False)
        browser.close()
    print(f"saved {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
