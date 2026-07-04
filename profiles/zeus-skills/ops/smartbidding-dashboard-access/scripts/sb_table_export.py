#!/usr/bin/env python3
"""Reusable starter for exporting Smart Bidding dashboard tables.

Run through the canonical SB route:
  cd /root/mgs-agent
  set -a; source .env 2>/dev/null || true; set +a
  xvfb-run -a /tmp/sb-venv/bin/python scripts/sb_table_export.py \
    --tab "Broadcast Template" --company-filter digital-tr --out /tmp/sb-export.csv

This script intentionally does not print credentials, cookies, Auth0 codes, or tokens.
Adapt selectors/columns per table before production use.
"""
import argparse, asyncio, csv, pathlib, re
from playwright.async_api import async_playwright

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
DEFAULT_STATE = "/tmp/smartbidding_state_headed.json"
DEFAULT_URL = "https://app.smartbiddingdigital.com/accounts"

KNOWN_COLUMNS = {
    "Broadcast Template": ["COMPANY", "DOMAIN", "LANGUAGE", "NAME", "MESSAGES", "LEADS", "PAGES", "APPROVAL"],
    "Page": ["COMPANY", "DOMAIN", "URL", "USER NAME", "LOGIN", "PROFILE NAME", "PAGE ID", "FB PAGE ID", "PAGE NAME", "UTM CAMPAIGN", "LEADS TOTAL", "LEADS ACTIVE", "LEADS ACTIVE%", "SOURCE", "VERTICAL", "COUNTRY", "NOTES", "TEMPLATE NAME", "LANGUAGE", "BROADCAST_TIME", "CURRENT MESSAGE ID", "MESSAGE ID", "LAST SCHEDULE", "STATUS"],
}

async def export_table(args):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        ctx = await browser.new_context(storage_state=args.storage_state, viewport={"width": 1600, "height": 1000}, user_agent=UA)
        page = await ctx.new_page()
        await page.goto(args.url, wait_until="networkidle", timeout=90000)
        await page.wait_for_timeout(2000)

        # Select context explicitly; notifications may contain misleading words.
        if args.context:
            await page.locator(".p-dropdown").first.click(timeout=10000)
            await page.wait_for_timeout(500)
            await page.get_by_text(args.context, exact=True).last.click(timeout=10000)
            await page.wait_for_timeout(2500)

        if args.tab:
            await page.get_by_text(args.tab, exact=True).click(timeout=10000)
            await page.wait_for_timeout(3000)

        # Apply first-column filter by default (usually COMPANY).
        if args.company_filter:
            buttons = page.locator("button.p-column-filter-menu-button")
            for _ in range(20):
                if await buttons.count() >= 1:
                    break
                await page.wait_for_timeout(500)
            if await buttons.count() < 1:
                raise RuntimeError("No PrimeVue column filter buttons found")
            await buttons.nth(0).click(timeout=10000)
            await page.wait_for_timeout(500)
            inputs = page.locator(".p-column-filter-overlay input, input.p-inputtext, input")
            typed = False
            for i in range(await inputs.count()):
                inp = inputs.nth(i)
                try:
                    box = await inp.bounding_box(timeout=1000)
                    if box and box["width"] > 20 and box["height"] > 10:
                        await inp.fill(args.company_filter, timeout=3000)
                        typed = True
                        break
                except Exception:
                    pass
            if not typed:
                raise RuntimeError("Could not type into filter input")
            apply = page.get_by_role("button", name=re.compile("Apply", re.I))
            if await apply.count():
                await apply.first.click(timeout=5000)
            else:
                await page.keyboard.press("Enter")
            await page.wait_for_timeout(2000)

        headers = await page.evaluate(r'''() => [...document.querySelectorAll("thead th")]
          .map(th => (th.innerText || '').replace(/\n/g, ' ').replace(/\s+/g, ' ').trim())
          .filter(Boolean)
          .map(h => h.replace(/\s*(↑|↓|↕|Filter).*$/g, '').trim())''')
        wanted = KNOWN_COLUMNS.get(args.tab or "", [])
        headers = [h for h in headers if not wanted or h in wanted] or wanted
        if not headers:
            raise RuntimeError("Could not determine table headers")

        rows, seen = [], set()
        for _page_num in range(args.max_pages):
            page_rows = await page.evaluate(r'''(headers) => [...document.querySelectorAll('tbody tr')]
              .map(tr => {
                const cells = [...tr.querySelectorAll('td')].map(td => (td.innerText || '').replace(/\s+/g, ' ').trim());
                const obj = {};
                headers.forEach((h,i)=>obj[h]=cells[i]||'');
                return obj;
              }).filter(r => Object.values(r).some(Boolean))''', headers)
            for row in page_rows:
                key = tuple(row.get(h, "") for h in headers)
                if key not in seen:
                    rows.append(row); seen.add(key)
            next_btn = page.locator("button.p-paginator-next")
            if not await next_btn.count():
                break
            disabled = await next_btn.first.evaluate("el => el.classList.contains('p-disabled') || el.disabled")
            if disabled:
                break
            await next_btn.first.click(timeout=10000)
            await page.wait_for_timeout(1500)
        await browser.close()

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, lineterminator="\r\n")
        writer.writeheader(); writer.writerows(rows)
    print(f"rows={len(rows)} cols={len(headers)} out={out}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--context", default="Messenger")
    ap.add_argument("--tab", default="Broadcast Template", choices=["Broadcast Template", "Page"])
    ap.add_argument("--company-filter", default="digital-tr")
    ap.add_argument("--storage-state", default=DEFAULT_STATE)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-pages", type=int, default=50)
    asyncio.run(export_table(ap.parse_args()))
