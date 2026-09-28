#!/usr/bin/env python3
import hashlib
import json
import ssl
import struct
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
image_url = "https://yolokfx.com/wp-content/uploads/2026/09/yolokfx-home-category-1552154990036918324.png"
rows = []
for version in (1, 2, 3):
    for manager in range(1, 7):
        slug = f"sh{version}-g{manager:03d}"
        if slug == "sh1-g004":
            continue
        req = urllib.request.Request(base + slug + "/", headers={"User-Agent": "Mozilla/5.0 MGS-QA/1.0", "Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as response:
            html = response.read().decode("utf-8", "replace")
            status = response.status
        text = text_of(html)
        assert status == 200, (slug, status)
        if version == 3:
            assert "Would you like to receive for free?" in text, slug
            assert "Home" in text and "Kids" not in text, slug
            assert "Electronics" in text and "Phones" not in text, slug
            assert image_url in html, slug
            assert html.count("data-mgs-dq-cta") == 7, slug
            assert html.count('class="mgs-dq-category"') == 6, slug
        else:
            assert "Get Free Products Delivered to Your Home" in text, slug
            assert "Would you like to get free products?" in text, slug
            assert image_url not in html, slug
            assert html.count("data-mgs-dq-cta") == 2, slug
        rows.append({"slug": slug, "status": status, "copy_ok": True})

image_req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0 MGS-QA/1.0"})
with urllib.request.urlopen(image_req, timeout=30, context=ssl.create_default_context()) as response:
    image = response.read()
    image_status = response.status
    image_type = response.headers.get_content_type()
assert image_status == 200 and image_type == "image/png"
assert image[:8] == b"\x89PNG\r\n\x1a\n"
width, height = struct.unpack(">II", image[16:24])
image_sha = hashlib.sha256(image).hexdigest()
assert (width, height) == (600, 600)
assert image_sha == "fa76c6812a3b3b7f129038b63400285357956d2abf6445d76cc7f4450ad8881f"
Path("/root/mgs-agent/work/yolokfx-home-20260922/home-category-public.png").write_bytes(image)

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
    "v3_routes_home_and_image": 6,
    "v1_v2_routes_unchanged": 11,
    "image": {"url": image_url, "status": image_status, "content_type": image_type, "width": width, "height": height, "sha256": image_sha},
    "negative_routes": negative,
    "routes": rows,
}
out = Path("/root/mgs-agent/work/yolokfx-home-20260922/public-validation.json")
out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in summary.items() if k != "routes"}, separators=(",", ":")))
