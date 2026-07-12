#!/usr/bin/env python3
"""Probe/analyze YouTube references with Ares's persistent Chromium profile.

This is Plan A for Ares YouTube references: keep a stable Chromium user-data-dir
so YouTube sees a returning browser profile instead of a fresh bot-like session.
It does not store passwords or print cookies. If the player is still challenged,
the script saves evidence and exits non-zero with a clear blocker.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

DEFAULT_PROFILE = Path("/root/.hermes/profiles/ares/browser-profiles/youtube-chromium")
DEFAULT_OUT = Path("/root/mgs-agent/data/ares/creative-ops/references/youtube-persistent")


def safe_slug(url: str) -> str:
    m = re.search(r"(?:shorts/|watch\?v=|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
    if m:
        return m.group(1)
    p = urlparse(url)
    s = re.sub(r"[^A-Za-z0-9_.-]+", "-", (p.netloc + p.path).strip("/"))
    return s[:80] or "youtube-reference"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--profile-dir", default=str(DEFAULT_PROFILE))
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT))
    ap.add_argument("--timeout-ms", type=int, default=45000)
    ap.add_argument("--headed", action="store_true", help="Run headful; use xvfb-run on headless VPS")
    ap.add_argument("--keep-open-seconds", type=int, default=0)
    args = ap.parse_args()

    profile_dir = Path(args.profile_dir)
    out_dir = Path(args.out_dir) / safe_slug(args.url)
    out_dir.mkdir(parents=True, exist_ok=True)
    profile_dir.mkdir(parents=True, exist_ok=True)

    status = {
        "ok": False,
        "url": args.url,
        "profile_dir": str(profile_dir),
        "out_dir": str(out_dir),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(profile_dir),
            headless=not args.headed,
            viewport={"width": 1280, "height": 1920},
            locale="en-US",
            timezone_id="America/New_York",
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--autoplay-policy=no-user-gesture-required",
            ],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        try:
            page.goto(args.url, wait_until="domcontentloaded", timeout=args.timeout_ms)
            page.wait_for_timeout(5000)
            # Try accepting common consent if it appears; ignore if absent.
            for label in ["Accept all", "I agree", "Reject all"]:
                try:
                    page.get_by_text(label, exact=False).first.click(timeout=1500)
                    page.wait_for_timeout(1500)
                    break
                except Exception:
                    pass
            try:
                page.keyboard.press("Space")
                page.wait_for_timeout(2500)
            except Exception:
                pass
            title = page.title()
            body_text = page.locator("body").inner_text(timeout=5000)[:4000]
            video_info = page.evaluate("""
                () => {
                  const v = document.querySelector('video');
                  return v ? {
                    currentSrc: v.currentSrc || '',
                    currentTime: v.currentTime,
                    duration: Number.isFinite(v.duration) ? v.duration : null,
                    readyState: v.readyState,
                    paused: v.paused,
                    videoWidth: v.videoWidth,
                    videoHeight: v.videoHeight,
                    networkState: v.networkState
                  } : null;
                }
            """)
            player_response = page.evaluate("""
                () => {
                  const pr = window.ytInitialPlayerResponse || null;
                  if (!pr) return null;
                  const ps = pr.playabilityStatus || {};
                  const vd = pr.videoDetails || {};
                  return {status: ps.status || null, reason: ps.reason || null, title: vd.title || null, author: vd.author || null, lengthSeconds: vd.lengthSeconds || null};
                }
            """)
            screenshot = out_dir / "screenshot.png"
            page.screenshot(path=str(screenshot), full_page=False)
            status.update({
                "title": title,
                "body_excerpt": body_text,
                "video": video_info,
                "player_response": player_response,
                "screenshot": str(screenshot),
            })
            playable = bool(video_info and video_info.get("readyState", 0) > 0 and (video_info.get("videoWidth") or 0) > 0)
            challenged = any(s in body_text.lower() for s in ["sign in to confirm", "not a bot", "unusual traffic", "confirm you're not a bot"])
            status["ok"] = playable and not challenged
            if args.keep_open_seconds > 0:
                time.sleep(args.keep_open_seconds)
        except PlaywrightTimeoutError as e:
            status.update({"error": f"timeout: {e}"})
        except Exception as e:
            status.update({"error": repr(e)})
        finally:
            (out_dir / "status.json").write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n")
            context.close()

    print(json.dumps({k: status.get(k) for k in ["ok", "url", "title", "profile_dir", "out_dir", "screenshot", "video", "player_response", "error"]}, indent=2, ensure_ascii=False))
    return 0 if status.get("ok") else 10


if __name__ == "__main__":
    raise SystemExit(main())
