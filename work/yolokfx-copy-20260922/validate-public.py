#!/usr/bin/env python3
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path

base = "https://yolokfx.com/quiz/us/"
active = []
for version in (1, 2, 3):
    for manager in range(1, 7):
        slug = f"sh{version}-g{manager:03d}"
        if slug == "sh1-g004":
            continue
        active.append((version, slug))

results = []
for version, slug in active:
    url = base + slug + "/"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 MGS-QA/1.0", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as response:
        status = response.status
        html = response.read().decode("utf-8", "replace")
        headers = {k.lower(): v for k, v in response.headers.items()}
    assert status == 200, (slug, status)
    assert "Get Free Products Delivered to Your Home" in html, slug
    assert "Get Free SHEIN Products Delivered to Your Home" not in html, slug
    assert "Would you like to get free SHEIN products?" not in html, slug
    assert "What would you like to receive?" not in html, slug
    if version in (1, 2):
        assert "Would you like to get free products?" in html, slug
        assert html.count("data-mgs-dq-cta") == 2, slug
    else:
        assert html.count("data-mgs-dq-cta") == 7, slug
        assert html.count('class="mgs-dq-category"') == 6, slug
    results.append({
        "slug": slug,
        "status": status,
        "bytes": len(html.encode("utf-8")),
        "cf_cache_status": headers.get("cf-cache-status"),
        "age": headers.get("age"),
        "title_ok": True,
        "question_ok": version in (1, 2),
    })

negative = []
for slug in ("sh1-g004", "sh9-g999"):
    url = base + slug + "/"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 MGS-QA/1.0", "Cache-Control": "no-cache"})
    try:
        urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context())
        status = 200
    except urllib.error.HTTPError as exc:
        status = exc.code
    assert status == 404, (slug, status)
    negative.append({"slug": slug, "status": status})

summary = {
    "site": "yolokfx.com",
    "active_routes_expected": 17,
    "active_routes_validated": len(results),
    "all_active_http_200": True,
    "new_copy_present": True,
    "old_copy_absent": True,
    "negative_routes": negative,
    "routes": results,
}
out = Path("/root/mgs-agent/work/yolokfx-copy-20260922/public-http-validation.json")
out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in summary.items() if k != "routes"}, separators=(",", ":")))
