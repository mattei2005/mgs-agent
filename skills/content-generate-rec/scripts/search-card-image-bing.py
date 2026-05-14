#!/usr/bin/env python3
"""
Bing Images fallback for card image search via Playwright local.
Usage: python3 search-card-image-bing.py <card_name>
Output (stdout): JSON {path, mime, tier, source, status}
Exit 0 = found, Exit 1 = NEEDS_MANUAL
"""

import sys, json, os, urllib.request, urllib.parse, time, subprocess, re
from datetime import datetime

CARD_MIN_WIDTH  = int(os.environ.get("CARD_MIN_WIDTH",  200))
CARD_MIN_HEIGHT = int(os.environ.get("CARD_MIN_HEIGHT", 100))
LOG = "/root/mgs-agent/logs/generate-rec.log"

# UK review sites that reliably host good card images
PRIORITY_DOMAINS = [
    "headforpoints.com",
    "backtodefault.com",
    "moneysavingexpert.com",
    "which.co.uk",
    "thisismoney.co.uk",
    "lovemoney.com",
    "creditcardcompare.com.au",
]


def log(msg):
    ts = datetime.now().isoformat(timespec='seconds')
    try:
        with open(LOG, 'a') as f:
            f.write(f"[{ts}] search-card-image-bing {msg}\n")
    except Exception:
        pass


def make_slug(name):
    s = name.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')


def download(url, path):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(url, headers=headers)
    data = urllib.request.urlopen(req, timeout=15).read()
    with open(path, 'wb') as f:
        f.write(data)
    return len(data)


def get_dimensions(path):
    # Try ImageMagick identify first
    try:
        r = subprocess.run(['identify', '-format', '%w %h', path],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            parts = r.stdout.strip().split()
            if len(parts) >= 2:
                return int(parts[0]), int(parts[1])
    except Exception:
        pass
    # Fallback: PIL
    try:
        from PIL import Image
        return Image.open(path).size
    except Exception:
        pass
    return None, None


def get_mime(path, ext):
    try:
        r = subprocess.run(['file', '-b', '--mime-type', path],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return f"image/{ext}"


def needs_manual(reason):
    print(json.dumps({
        "path": None, "mime": None, "tier": 0,
        "source": None, "status": "NEEDS_MANUAL", "reason": reason
    }))
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        needs_manual("missing_card_name_arg")

    card_name = sys.argv[1]
    card_slug = make_slug(card_name)
    log(f"START card={card_name} slug={card_slug}")

    # -- 1. Import Playwright ------------------------------------------------
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("FAIL playwright_not_installed")
        needs_manual("playwright_not_installed")

    # -- 2. Bing Images search -----------------------------------------------
    query = urllib.parse.quote_plus(f"{card_name} credit card")
    bing_url = (
        f"https://www.bing.com/images/search"
        f"?q={query}&qft=+filterui:imagesize-large"
    )

    urls = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="en-GB",
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.new_page()
            page.goto(bing_url, timeout=30000)
            time.sleep(3)

            items = page.query_selector_all('a.iusc')
            log(f"BING candidates={len(items)}")

            for item in items[:40]:
                m_attr = item.get_attribute('m')
                if not m_attr:
                    continue
                try:
                    data = json.loads(m_attr)
                    murl = data.get('murl', '')
                    desc = data.get('t', '')
                    if murl:
                        urls.append({'url': murl, 'desc': desc})
                except Exception:
                    pass

            browser.close()
    except Exception as e:
        log(f"FAIL playwright_error={e}")
        needs_manual(f"playwright_error: {e}")

    if not urls:
        log("FAIL no_bing_results")
        needs_manual("no_bing_results")

    # -- 3. Score candidates -------------------------------------------------
    kw_pattern = card_slug.replace('-', '|')
    scored = []
    for item in urls:
        url  = item['url']
        desc = item['desc'].lower()
        low  = url.lower()
        score = 0

        # Priority domain boost
        for domain in PRIORITY_DOMAINS:
            if domain in low:
                score += 8
                break

        # Keyword match
        if re.search(kw_pattern, low):  score += 5
        if re.search(kw_pattern, desc): score += 3

        # Format bonuses
        if '.webp' in low: score += 2
        if '.png'  in low: score += 2
        if '.jpg'  in low or '.jpeg' in low: score += 1

        # Penalise noise
        if re.search(r'(thumb|icon|logo|sprite|favicon|banner|ytimg|youtube|avatar)', low):
            score -= 4

        scored.append((score, url))

    scored.sort(key=lambda x: -x[0])

    # -- 4. Download & validate top candidates --------------------------------
    for score, url in scored[:10]:
        if score <= 0:
            break

        ext = url.split('.')[-1].split('?')[0].lower()
        if ext not in ('png', 'jpg', 'jpeg', 'webp'):
            ext = 'jpg'

        tmp = f"/tmp/card-bing-{card_slug}-{os.getpid()}.{ext}"

        try:
            size = download(url, tmp)
        except Exception as e:
            log(f"REJECT download_failed url={url} err={e}")
            continue

        if size < 5000:
            log(f"REJECT file_too_small size={size} url={url}")
            try: os.unlink(tmp)
            except Exception: pass
            continue

        w, h = get_dimensions(tmp)

        if w is not None:
            if w < CARD_MIN_WIDTH or h < CARD_MIN_HEIGHT:
                log(f"REJECT too_small w={w} h={h} url={url}")
                try: os.unlink(tmp)
                except Exception: pass
                continue
            aspect = w / h
            if not (1.2 <= aspect <= 2.2):
                log(f"REJECT bad_aspect w={w} h={h} aspect={aspect:.3f} url={url}")
                try: os.unlink(tmp)
                except Exception: pass
                continue
        else:
            log(f"WARN dimension_check_skipped url={url}")

        # ✅ Accepted
        final = f"/tmp/card-{card_slug}.{ext}"
        try:
            os.rename(tmp, final)
        except Exception:
            final = tmp

        mime = get_mime(final, ext)
        log(f"ACCEPT tier=4 score={score} w={w} h={h} url={url} path={final}")
        print(json.dumps({
            "path":   final,
            "mime":   mime,
            "tier":   4,
            "source": url,
            "status": "OK",
        }))
        sys.exit(0)

    log(f"FAIL all_candidates_rejected card={card_name}")
    needs_manual("all_bing_candidates_rejected")


if __name__ == '__main__':
    main()
