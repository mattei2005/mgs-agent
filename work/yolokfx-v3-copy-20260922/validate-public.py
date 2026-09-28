#!/usr/bin/env python3
import json
import ssl
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)

def text_of(source):
    parser = TextParser()
    parser.feed(source)
    return " ".join(" ".join(parser.parts).split())

base = "https://yolokfx.com/quiz/us/"
rows = []
for version in (1, 2, 3):
    for manager in range(1, 7):
        slug = f"sh{version}-g{manager:03d}"
        if slug == "sh1-g004":
            continue
        req = urllib.request.Request(base + slug + "/", headers={"User-Agent": "Mozilla/5.0 MGS-QA/1.0", "Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as response:
            html = response.read().decode("utf-8", "replace")
            headers = {k.lower(): v for k, v in response.headers.items()}
            status = response.status
        text = text_of(html)
        assert status == 200, (slug, status)
        if version == 3:
            assert "Would you like to receive for free?" in text, slug
            assert "Get Free Products Delivered to Your Home" not in text, slug
            assert "Electronics" in text and "Phones" not in text, slug
            assert html.count("data-mgs-dq-cta") == 7, slug
            assert html.count('class="mgs-dq-category"') == 6, slug
        else:
            assert "Get Free Products Delivered to Your Home" in text, slug
            assert "Would you like to get free products?" in text, slug
            assert "Would you like to receive for free?" not in text, slug
            assert html.count("data-mgs-dq-cta") == 2, slug
        rows.append({"slug": slug, "status": status, "cf_cache_status": headers.get("cf-cache-status"), "last_modified": headers.get("last-modified"), "copy_ok": True})

negative = []
for slug in ("sh1-g004", "sh9-g999"):
    req = urllib.request.Request(base + slug + "/", headers={"User-Agent": "Mozilla/5.0 MGS-QA/1.0", "Cache-Control": "no-cache"})
    try:
        urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context())
        status = 200
    except urllib.error.HTTPError as exc:
        status = exc.code
    assert status == 404, (slug, status)
    negative.append({"slug": slug, "status": status})

summary = {
    "site": "yolokfx.com",
    "active_routes_validated": len(rows),
    "all_active_http_200": True,
    "v3_routes_new_title_and_electronics": 6,
    "v1_v2_routes_unchanged": 11,
    "negative_routes": negative,
    "routes": rows,
}
out = Path("/root/mgs-agent/work/yolokfx-v3-copy-20260922/public-validation.json")
out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in summary.items() if k != "routes"}, separators=(",", ":")))
