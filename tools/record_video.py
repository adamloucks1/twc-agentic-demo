"""
Records a short preview video of the demo by driving it in a headless browser.

Usage:  python record_video.py [speedup]
        speedup defaults to 6 (raw ~4 min footage -> ~40s video)

Requires: pip install playwright imageio-ffmpeg && python -m playwright install chromium
The demo server must already be running at http://localhost:8765.

Output: media/demo-preview.mp4 (next to the project root)
"""

import os
import subprocess
import sys

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA = os.path.join(BASE, "media")
URL = "http://localhost:8765"
SPEEDUP = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0


def wait_done(page, timeout_ms=240000):
    """Wait for the live dot to switch on (run started) then off (run done)."""
    try:
        page.wait_for_function(
            "document.querySelector('#live-dot').classList.contains('on')",
            timeout=15000)
    except Exception:
        pass  # very fast run; may already be done
    page.wait_for_function(
        "!document.querySelector('#live-dot').classList.contains('on')",
        timeout=timeout_ms)


def main():
    os.makedirs(MEDIA, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=MEDIA,
            record_video_size={"width": 1280, "height": 720},
        )
        page = ctx.new_page()

        print("Scene 1: header + inbox")
        page.goto(URL)
        page.wait_for_selector(".mail", state="attached")  # state loaded
        page.click("#reset-btn")
        page.wait_for_timeout(2500)

        print("Scene 2a: plain chatbot (no business knowledge)")
        page.click(".mode-toggle .slider")          # agent -> chatbot
        page.locator(".chip").nth(0).click()        # Inconel lead time question
        wait_done(page)
        page.wait_for_timeout(1500)

        print("Scene 2b: agent mode (tools + context)")
        page.click(".mode-toggle .slider")          # chatbot -> agent
        page.locator(".chip").nth(0).click()        # same question
        wait_done(page)
        page.wait_for_timeout(2000)

        print("Scene 3: document analysis (invoice)")
        page.click('button.tab[data-tab="documents"]')
        page.locator(".doc-item").nth(0).click()    # invoice
        page.wait_for_timeout(1200)
        page.click("#analyze-doc")
        wait_done(page)
        page.wait_for_timeout(2000)

        print("Scene 4: morning workflow (first ~75s)")
        page.click('button.tab[data-tab="workflow"]')
        page.wait_for_timeout(1500)
        page.click("#run-workflow")
        page.wait_for_timeout(75000)                # let drafts start landing
        page.wait_for_timeout(2000)

        ctx.close()                                  # flushes the video file
        raw_path = page.video.path()
        browser.close()

    out_path = os.path.join(MEDIA, "demo-preview.mp4")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    print(f"Compressing {SPEEDUP}x -> {out_path}")
    subprocess.run([
        ffmpeg, "-y", "-i", raw_path,
        "-filter:v", f"setpts=PTS/{SPEEDUP},fps=30",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "26",
        out_path,
    ], check=True)
    os.remove(raw_path)

    size_mb = os.path.getsize(out_path) / 1e6
    print(f"Done: {out_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
