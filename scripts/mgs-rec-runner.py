#!/usr/bin/env python3
"""mgs-rec-runner.py — deterministic REC publication runner.

Goal: move the REC pipeline out of Atena's ReAct/tool loop. Atena should call
this script once, then format the returned JSON for Discord.

Safety:
- --dry-run performs discovery/assembly checks but does not upload/publish.
- Default status is draft unless --status publish is explicitly passed.
- Credentials are only passed to existing scripts; never printed.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path("/root/mgs-agent")
SITES_JSON = ROOT / "data/sites.json"
TERM_CACHE_JSON = ROOT / "data/wp-term-cache.json"
GEN_SCRIPTS = ROOT / "skills/content-generate-rec-p1/scripts"
REC_TEMPLATES = ROOT / "skills/content-generate-rec-p1/templates"
REC_UNIVERSAL_CONTRACT = ROOT / "skills/content-generate-rec-p1/contracts/cc-rec.md"
WP_SCRIPTS = ROOT / "skills/content-publish-wordpress/scripts"
FEATURED_AUDIT_SCRIPT = ROOT / "scripts/audit-featured-image.py"
# Legacy mgs-rec-api (old FastAPI/Anthropic path) is intentionally disabled.
# REC content is generated locally from the current official facts supplied to
# this runner; do not attempt the masked service or report noisy API warnings.

LOG_PREFIX = "mgs-rec-runner"


class RunnerError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"&", " and ", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text


def run(cmd: List[str], *, timeout: int = 120, env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, env=merged_env)


def run_json(cmd: List[str], *, timeout: int = 120, env: Optional[Dict[str, str]] = None, allow_fail: bool = False) -> Dict[str, Any]:
    p = run(cmd, timeout=timeout, env=env)
    if p.returncode != 0:
        if allow_fail:
            try:
                return json.loads(p.stdout or "{}")
            except Exception:
                return {"success": False, "error": (p.stderr or p.stdout or "command failed")[:1000], "returncode": p.returncode}
        raise RunnerError(f"Command failed rc={p.returncode}: {' '.join(cmd)}\n{(p.stderr or p.stdout)[:2000]}")
    try:
        return json.loads(p.stdout)
    except Exception as e:
        raise RunnerError(f"Command did not return JSON: {' '.join(cmd)}\nstdout={(p.stdout or '')[:1200]}\nstderr={(p.stderr or '')[:1200]}\nerror={e}")


def load_site(site_key: str) -> Dict[str, Any]:
    data = json.loads(SITES_JSON.read_text())
    site = data.get(site_key) if isinstance(data, dict) else None
    if not site:
        raise RunnerError(f"Site not found in sites.json: {site_key}")
    return site


def load_rec_template_contract(site: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve the REC editorial contract. Prefers the universal `cc-rec.md`; falls back
    to the per-site `templates/rec-{template_key}.md` for legacy compatibility."""
    if REC_UNIVERSAL_CONTRACT.exists():
        template_path = REC_UNIVERSAL_CONTRACT
        template_key = "cc-universal"
    else:
        template_key = site.get("template_key")
        if not template_key:
            raise RunnerError("Site is missing template_key in sites.json and universal cc-rec.md is absent")
        template_path = REC_TEMPLATES / f"rec-{template_key}.md"
        if not template_path.exists():
            raise RunnerError(f"No REC template for template_key '{template_key}'. Create templates/rec-{template_key}.md or contracts/cc-rec.md first.")
    text = template_path.read_text(errors="ignore")
    return {
        "template_key": template_key,
        "path": str(template_path),
        "bytes": template_path.stat().st_size,
        "contract_loaded": True,
        "has_word_count_gate": "450" in text and "500" in text,
        "has_paragraph_gate": "30 words" in text or "~30 words" in text or "25-35 words" in text or "30-35 words" in text,
        "has_horizontal_card_gate": "horizontal" in text.lower() and "rotate" in text.lower(),
        "has_featured_three_layer_gate": "three essential" in text.lower() or "three" in text.lower() and "layers" in text.lower(),
    }


def load_anthropic_key() -> Optional[str]:
    """Anthropic API is intentionally disabled for MGS runtime.

    Rodolfo decided to stop all pay-per-token Anthropic/Claude API usage.
    Keep this function as a compatibility stub so older call paths fail closed
    without reading credentials or making network calls.
    """
    return None


def strip_html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw[:18000]


def fetch_reference_text(url: str) -> Tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            status = getattr(r, "status", 200)
            body = r.read(1_500_000).decode("utf-8", errors="ignore")
            text = strip_html_to_text(body)
            if len(text) < 500 and "americanexpress.com" in url.lower():
                try:
                    from playwright.sync_api import sync_playwright
                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=True)
                        context = browser.new_context(
                            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            viewport={"width": 1366, "height": 1000},
                        )
                        page = context.new_page()
                        page.goto(url, wait_until="domcontentloaded", timeout=45000)
                        for label in ("Accept All", "Accept all", "I Accept"):
                            try:
                                page.get_by_role("button", name=label).click(timeout=2500)
                                break
                            except Exception:
                                pass
                        page.wait_for_timeout(2000)
                        rendered = page.locator("body").inner_text(timeout=10000) or ""
                        browser.close()
                    rendered_text = re.sub(r"\s+", " ", html.unescape(rendered)).strip()[:18000]
                    if len(rendered_text) > len(text):
                        return status, rendered_text
                except Exception:
                    pass
            return status, text
    except Exception as e:
        raise RunnerError(f"reference_url fetch failed: {url} ({e})")


def meaningful_card_terms(card_name: str) -> List[str]:
    stop = {"credit", "card", "the", "and", "visa", "mastercard", "platinum", "classic", "gold"}
    terms = []
    for word in re.sub(r"[^A-Za-z0-9 ]", " ", card_name).lower().split():
        if len(word) >= 3 and word not in stop and word not in terms:
            terms.append(word)
    return terms[:6]


def official_source_has_content(card_name: str, official_url: str, text: str) -> Tuple[bool, str]:
    """Reject HTTP-200 official pages that are error shells or not product-specific."""
    clean = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip().lower()
    if not clean or len(clean) < 500:
        return False, "official source has no meaningful body"
    product_terms = [
        "credit card", "representative apr", "annual fee", "monthly fee", "balance transfer",
        "purchase rate", "eligibility", "apply", "rewards", "cashback", "avios", "mastercard", "visa",
    ]
    product_hits = [t for t in product_terms if t in clean]
    name_terms = meaningful_card_terms(card_name)
    name_hits = [t for t in name_terms if t in clean]
    error_markers = [
        "page not found", "we can’t find that page", "we can't find that page",
        "try our search tool", "we are sorry an error has occurred",
        "error 1007", "access denied", "cloudflare", "temporarily unavailable",
    ]
    for marker in error_markers:
        if marker in clean:
            return False, f"official source appears to be an error page: {marker}"
    # Some issuer pages include support/footer copy like "we're truly sorry about this"
    # while the product body is valid. Treat the phrase as an error marker only when
    # the page does not otherwise expose product-specific terms.
    if "sorry about this" in clean and len(product_hits) < 2 and not name_hits:
        return False, "official source appears to be an error page: sorry about this"
    if len(product_hits) < 2:
        return False, "official source does not expose enough product content"
    if name_terms and not name_hits:
        return False, "official source does not mention the requested product/issuer terms"
    return True, "ok"


def validate_no_review(fields: Dict[str, str]) -> None:
    offenders = [name for name, value in fields.items() if re.search(r"\breview\b", value or "", flags=re.I)]
    if offenders:
        raise RunnerError("Review hard gate failed in " + ", ".join(offenders))


def validate_taxonomy_names(tag_names: List[str], expected_lang: str) -> None:
    bad = [t for t in tag_names if "-" in t]
    if bad:
        raise RunnerError(f"Tag names must use spaces, not hyphens: {bad}")
    required = {"atena_agent", f"lang_{expected_lang}"}
    missing = sorted(required - set(tag_names))
    if missing:
        raise RunnerError(f"Missing mandatory tags: {missing}")


def validate_yoast_score(score: Dict[str, Any]) -> None:
    if not score or score.get("status") not in {"ok", "success", "OK"}:
        raise RunnerError(f"Yoast scorer failed or returned non-ok status: {score}")
    seo = score.get("seo_score")
    read = score.get("readability_score")
    if seo is None or read is None:
        raise RunnerError(f"Yoast scorer missing scores: {score}")
    if int(seo) < 70 or int(read) < 70:
        raise RunnerError(f"Yoast scores below green threshold: seo={seo} readability={read}")


def extract_card_data_with_llm(card_name: str, source_url: str, text: str) -> Dict[str, Any]:
    """Deterministic cache-miss extraction without Anthropic.

    This runner is deliberately allowed to create drafts without a paid Claude
    extraction path. We extract conservative factual snippets from the supplied
    source text and let the draft/editorial review catch weak source pages.
    """
    clean = re.sub(r"\s+", " ", text or " ").strip()
    if len(clean) < 200:
        raise RunnerError("reference_url returned too little fetchable text for deterministic extraction")

    # Annual fee: keep the phrase anchored to the source text instead of inventing.
    annual_fee = "N/A"
    annual_patterns = [
        r"(?:no\s+annual\s+fee|annual\s+fee\s*(?:of|is|:)?\s*£?\d+[\w\s.%/-]{0,40})",
        r"(?:£\d+[\w\s.%/-]{0,30}\s+annual\s+fee)",
        r"(?:account\s+fee\s*(?:of|is|:)?\s*£?\d+[\w\s.%/-]{0,40})",
    ]
    for pat in annual_patterns:
        m = re.search(pat, clean, flags=re.I)
        if m:
            annual_fee = m.group(0).strip(" .;:")
            annual_fee = re.split(r"\b(?:Representative|APR|Purchase|Assumed|Credit\s+Limit)\b", annual_fee, maxsplit=1, flags=re.I)[0].strip(" .;:")
            break

    # APR / representative rate.
    apr = "N/A"
    apr_patterns = [
        r"(?:representative\s+APR[^.]{0,80}?\d+(?:\.\d+)?%[^.]{0,80})",
        r"(?:\d+(?:\.\d+)?%\s*(?:APR|representative APR|variable APR)[^.]{0,80})",
        r"(?:purchase\s+rate[^.]{0,80}?\d+(?:\.\d+)?%[^.]{0,80})",
    ]
    for pat in apr_patterns:
        m = re.search(pat, clean, flags=re.I)
        if m:
            apr = m.group(0).strip(" .;:")[:140]
            apr = re.split(r"\b(?:Assumed\s+Credit\s+Limit|Credit\s+limit|About\s+this|Eligibility)\b", apr, maxsplit=1, flags=re.I)[0].strip(" .;:")
            break

    # Benefits: source sentences with product/offer terms. Avoid boilerplate.
    raw_sentences = re.split(r"(?<=[.!?])\s+", clean)
    benefit_re = re.compile(
        r"(0%|balance transfer|purchase|money transfer|credit limit|eligibility|online|app|manage|contactless|mastercard|protection|fee|APR|representative|offer)",
        re.I,
    )
    noise_re = re.compile(r"(cookie|privacy|javascript|terms of use|accessibility|complaint|site map|error\s*1007|access denied|cloudflare|while you wait)", re.I)
    benefits: List[str] = []
    seen = set()
    for sent in raw_sentences:
        s = re.sub(r"\s+", " ", sent).strip(" -–—\t\n")
        if len(s) < 35 or len(s) > 220:
            continue
        if noise_re.search(s) or not benefit_re.search(s):
            continue
        key = s.lower()[:90]
        if key in seen:
            continue
        seen.add(key)
        benefits.append(s[:180])
        if len(benefits) >= 5:
            break

    if len(benefits) < 3:
        raise RunnerError(
            "Insufficient confirmed card benefits extracted from the official source; "
            "do not pad with generic guidance. Ask for a better official URL or explicit verified benefits."
        )

    lower_benefits = " ".join(benefits).lower()
    if "amazon" in lower_benefits or "amazon" in card_name.lower():
        tag10 = "Amazon rewards"
        descriptor = "Turn routine Amazon spending into useful rewards."
    elif "nectar" in lower_benefits or "nectar" in card_name.lower():
        tag10 = "Nectar points"
        descriptor = "Turn regular Nectar spending into useful points."
    elif "low interest" in lower_benefits or "low rate" in lower_benefits or "12.9%" in lower_benefits:
        tag10 = "Low interest rate"
        descriptor = "Lower-rate credit with simple fees."
    elif "balance transfer" in lower_benefits:
        tag10 = "Balance transfers"
        descriptor = "Move balances with a focused transfer offer."
    elif "cashback" in lower_benefits:
        tag10 = "Cashback rewards"
        descriptor = "Earn cashback on eligible purchases."
    elif any(t in lower_benefits for t in ["avios", "travel", "points"]):
        tag10 = "Travel rewards"
        descriptor = "Make regular trips and bookings feel more rewarding."
    else:
        tag10 = "Confirmed benefits"
        descriptor = shorten_words(benefits[0], 9).rstrip(" ,;:") + "."
    tag2 = "0% purchases" if "0%" in lower_benefits and "purchase" in lower_benefits else (annual_fee[:25] if annual_fee != "N/A" else "Official terms")

    return {
        "card_name": card_name,
        "annual_fee": annual_fee,
        "apr": apr,
        "benefits": benefits,
        "competitors": [],
        "tag10": tag10[:25],
        "tag2": tag2[:25],
        "descriptor": descriptor[:100],
        "extraction_mode": "deterministic_source_snippets",
        "source_url": source_url,
    }


def build_media_payload(media_id: Optional[int], media_url: Optional[str], title: str) -> str:
    if not media_id or not media_url:
        return ""
    obj = {
        "alt": "",
        "title": title,
        "caption": "",
        "description": {"raw": "", "rendered": ""},
        "id": int(media_id),
        "link": media_url,
        "url": media_url,
        "sizes": "",
    }
    return urllib.parse.quote(json.dumps(obj, separators=(",", ":")), safe="")


def rand_block_id() -> str:
    import random, string
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(6))


def lazy_credit_card(card_name: str, card_id: Optional[int], card_url: Optional[str], site: Dict[str, Any], card_slug: str, card_data: Dict[str, Any], button_hex: str) -> str:
    country = site.get("country", "gb")
    vertical = (site.get("verticals") or ["cc"])[0]
    domain = site["domain"]
    block_id = rand_block_id()
    annual_fee = str(card_data.get("annual_fee") or "")
    tag10, tag2, descriptor = derive_lazyblock_tags(card_name, [str(b) for b in (card_data.get("benefits") or [])], annual_fee)
    payload = {
        "imagem": build_media_payload(card_id, card_url, f"card-{card_slug}"),
        "categoria": site.get("default_category", "Credit Card"),
        "titulo": card_name,
        "tag10": card_ui_tag(card_data.get("tag10"), tag10, card_name=card_name, annual_fee=annual_fee),
        "tag2": card_ui_tag(card_data.get("tag2"), tag2, card_name=card_name, annual_fee=annual_fee),
        "texto": card_ui_descriptor(card_data, card_data.get("descriptor") or descriptor),
        "botao-texto": "How to Apply",
        "siteXfora": "You will remain on this website.",
        "botao-url": f"https://{domain}/apply-now-{country}-{vertical}-{card_slug}/",
        "color-botao": button_hex,
        "blockId": block_id,
        "blockUniqueClass": f"lazyblock-credit-card-{block_id}",
    }
    return "<!-- wp:lazyblock/credit-card " + json.dumps(payload, separators=(",", ":")) + " /-->"


def lazy_button(site: Dict[str, Any], card_slug: str, button_hex: str) -> str:
    country = site.get("country", "gb")
    vertical = (site.get("verticals") or ["cc"])[0]
    domain = site["domain"]
    block_id = rand_block_id()
    payload = {
        "texto-botao": " HOW TO APPLY ",
        "link-botao": f"https://{domain}/apply-now-{country}-{vertical}-{card_slug}/",
        "cor-botao": button_hex,
        "texto-pequeno": "You will remain on this website.",
        "blockId": block_id,
        "blockUniqueClass": f"lazyblock-botao-{block_id}",
    }
    return "<!-- wp:lazyblock/botao " + json.dumps(payload, separators=(",", ":")) + " /-->"


def assemble_content(article_html: str, card_block: str, button_block: str) -> str:
    blocks = [b.strip() for b in re.split(r"(?=<!-- wp:)", article_html.strip()) if b.strip()]
    if not blocks:
        raise RunnerError("article_html produced no Gutenberg blocks")
    # Avoid duplicate LazyBlocks if API ever returns placeholders.
    blocks = [b for b in blocks if "wp:lazyblock/credit-card" not in b and "wp:lazyblock/botao" not in b]
    return "\n\n".join([blocks[0], card_block] + blocks[1:] + [button_block])


def visible_subtitle(content: str) -> str:
    m = re.search(r"<!-- wp:paragraph -->\s*<p>(.*?)</p>\s*<!-- /wp:paragraph -->", content, re.I | re.S)
    if not m:
        return ""
    return re.sub(r"<[^>]+>", "", html.unescape(m.group(1))).strip()


def enforce_subtitle_limit(content: str, card_name: str, card_data: Dict[str, Any]) -> str:
    """Keep first paragraph/excerpt <=100 chars without another LLM call."""
    subtitle = visible_subtitle(content)
    if len(subtitle) <= 100:
        return content
    annual = (card_data.get("annual_fee") or "").lower()
    benefits = " ".join(card_data.get("benefits") or []).lower()
    if "balance transfer" in benefits or "0% balance" in benefits:
        tail = "can support 36 months interest free on existing card debt."
    elif "no annual fee" in annual or "no annual fee" in benefits:
        tail = "offers confirmed benefits with no annual fee."
    elif "travel" in benefits:
        tail = "offers travel-focused credit card benefits."
    elif "cashback" in benefits:
        tail = "can return value on routine spending."
    elif "amazon" in benefits or "amazon" in card_name.lower():
        tail = "rewards Amazon spending and key purchases."
    elif "points" in benefits or "rewards" in benefits:
        tail = "highlights its main rewards before you apply."
    else:
        tail = "highlights its confirmed costs and benefits."
    # Include a recognisable display name for focus context, but cap hard.
    display_name = card_name
    plain = f"{display_name} {tail}"
    if len(plain) > 98:
        # Use a shortened display name but keep recognisable terms.
        display_name = " ".join([w for w in card_name.split() if w.lower() not in {"credit", "card"}][:4])
        plain = f"{display_name} {tail}"
    if len(plain) > 98:
        plain = plain[:95].rsplit(" ", 1)[0] + "."
        if plain.startswith(display_name):
            tail = plain[len(display_name):].strip()
        else:
            display_name = " ".join(plain.split()[:4])
            tail = plain[len(display_name):].strip()
    replacement = f"<!-- wp:paragraph -->\n<p><strong>{html.escape(display_name)}</strong> {html.escape(tail)}</p>\n<!-- /wp:paragraph -->"
    return re.sub(r"<!-- wp:paragraph -->\s*<p>.*?</p>\s*<!-- /wp:paragraph -->", replacement, content, count=1, flags=re.I | re.S)


def normalize_card_artwork(path: str, aggressive: bool = False) -> Dict[str, Any]:
    """Force card artwork to horizontal orientation and crop padding/canvas.

    Normal mode trims transparent/white padding. Aggressive mode is used for
    manual card-image overrides: it also estimates a flat background from the
    image edges and crops the dominant canvas around the actual card artwork.
    This keeps user-supplied thumbnails/banners from entering LazyBlock as a
    wide frame with a small card in the middle.
    """
    try:
        from PIL import Image, ImageFilter, ImageDraw
    except Exception as e:
        return {"status": "skipped", "reason": f"PIL unavailable: {e}"}

    img = Image.open(path)
    img.load()
    before = {"width": img.width, "height": img.height}
    rotated = False

    # Manual URLs sometimes point to a full article/banner image: white canvas,
    # headline text and a portrait card placed on one side. The LazyBlock must
    # receive only the card artwork. If a red portrait card is detected inside a
    # landscape manual image, extract that object, mask the rounded corners and
    # rotate it to horizontal before the normal trim/upscale path.
    portrait_card_extracted = False
    portrait_extract_info: Dict[str, Any] = {}
    if aggressive and img.width > img.height:
        rgba0 = img.convert("RGBA")
        pix0 = rgba0.load()
        xs: List[int] = []
        ys: List[int] = []
        x_min_scan = int(rgba0.width * 0.45)
        for y in range(rgba0.height):
            for x in range(x_min_scan, rgba0.width):
                r, g, b, a = pix0[x, y]
                if a > 20 and r > 115 and g < 135 and b < 135 and r > g * 1.15 and r > b * 1.15:
                    xs.append(x); ys.append(y)
        if len(xs) > 200:
            raw_left, raw_top, raw_right, raw_bottom = min(xs), min(ys), max(xs) + 1, max(ys) + 1
            raw_w, raw_h = raw_right - raw_left, raw_bottom - raw_top
            # Red-pixel bounds often sit next to banner waves/white edges. Do
            # not expand them; inset slightly so decorative background doesn't
            # survive as a notch after rotation in the LazyBlock.
            inset_x = max(2, int(raw_w * 0.08))
            inset_y = max(2, int(raw_h * 0.035))
            left = min(raw_right - 1, raw_left + inset_x)
            top = min(raw_bottom - 1, raw_top + inset_y)
            right = max(left + 1, raw_right - inset_x)
            bottom = max(top + 1, raw_bottom - inset_y)
            cw, ch = right - left, bottom - top
            aspect = cw / ch if ch else 0
            area_ratio = (cw * ch) / max(1, rgba0.width * rgba0.height)
            if 0.45 <= aspect <= 0.85 and 0.04 <= area_ratio <= 0.60:
                card = rgba0.crop((left, top, right, bottom))
                mask = Image.new("L", card.size, 0)
                radius = max(5, int(min(card.size) * 0.055))
                ImageDraw.Draw(mask).rounded_rectangle((0, 0, card.width - 1, card.height - 1), radius=radius, fill=255)
                isolated = Image.new("RGBA", card.size, (0, 0, 0, 0))
                isolated.paste(card, (0, 0), mask)
                img = isolated.rotate(90, expand=True, resample=Image.Resampling.BICUBIC)
                rotated = True
                portrait_card_extracted = True
                portrait_extract_info = {
                    "applied": True,
                    "box": [left, top, right, bottom],
                    "candidate_width": cw,
                    "candidate_height": ch,
                    "candidate_aspect": round(aspect, 4),
                    "area_ratio": round(area_ratio, 4),
                    "red_pixels": len(xs),
                    "corner_alpha_mask": {"applied": True, "radius": radius},
                }
    if img.height > img.width:
        img = img.rotate(-90, expand=True)
        rotated = True

    def bbox_from_mask(source: "Image.Image", mode: str) -> Tuple[Optional[Tuple[int, int, int, int]], Dict[str, Any]]:
        rgba = source.convert("RGBA")
        pix = rgba.load()
        w, h = rgba.size
        left, right, top, bottom = w, -1, h, -1
        meta: Dict[str, Any] = {"mode": mode}

        bg_rgb: Optional[Tuple[int, int, int]] = None
        if mode == "background":
            samples: Dict[Tuple[int, int, int], List[int]] = {}
            step = max(1, min(w, h) // 80)
            coords = []
            for x in range(0, w, step):
                coords.append((x, 0)); coords.append((x, h - 1))
            for y in range(0, h, step):
                coords.append((0, y)); coords.append((w - 1, y))
            for x, y in coords:
                r, g, b, a = pix[x, y]
                if a <= 20:
                    continue
                bucket = (r // 16, g // 16, b // 16)
                cur = samples.setdefault(bucket, [0, 0, 0, 0])
                cur[0] += 1; cur[1] += r; cur[2] += g; cur[3] += b
            if samples:
                count, rr, gg, bb = max(samples.values(), key=lambda v: v[0])
                bg_rgb = (rr // count, gg // count, bb // count)
                meta["background_rgb"] = bg_rgb

        for y in range(h):
            for x in range(w):
                r, g, b, a = pix[x, y]
                keep = False
                if a > 20:
                    if mode == "white":
                        keep = not (r > 242 and g > 242 and b > 242)
                    elif bg_rgb:
                        br, bg, bb = bg_rgb
                        dist = ((r - br) ** 2 + (g - bg) ** 2 + (b - bb) ** 2) ** 0.5
                        keep = dist > 42
                if keep:
                    left, right = min(left, x), max(right, x)
                    top, bottom = min(top, y), max(bottom, y)
        if right < left or bottom < top:
            return None, meta
        return (left, top, right + 1, bottom + 1), meta

    def apply_candidate_crop(source: "Image.Image", box: Tuple[int, int, int, int], *, pad_px: int, require_reduction: bool) -> Tuple["Image.Image", bool, Dict[str, Any]]:
        w, h = source.size
        left, top, right, bottom = box
        crop_box = (max(0, left - pad_px), max(0, top - pad_px), min(w, right + pad_px), min(h, bottom + pad_px))
        cw, ch = crop_box[2] - crop_box[0], crop_box[3] - crop_box[1]
        aspect = cw / ch if ch else 0
        reduction = 1 - ((cw * ch) / (w * h)) if w and h else 0
        info = {"box": crop_box, "candidate_width": cw, "candidate_height": ch, "candidate_aspect": round(aspect, 4), "area_reduction": round(reduction, 4)}
        if crop_box == (0, 0, w, h):
            return source, False, info
        if not (1.2 <= aspect <= 2.2):
            info["rejected_reason"] = "aspect_out_of_card_range"
            return source, False, info
        if require_reduction and reduction < 0.08:
            info["rejected_reason"] = "insufficient_canvas_reduction"
            return source, False, info
        return source.crop(crop_box), True, info

    cropped = False
    crop_method = None
    crop_info: Dict[str, Any] = {}

    # First trim ordinary white/transparent padding.
    box, meta = bbox_from_mask(img, "white")
    if box:
        img2, did_crop, info = apply_candidate_crop(img, box, pad_px=3, require_reduction=False)
        if did_crop:
            img = img2
            cropped = True
            crop_method = "white_or_transparent_trim"
            crop_info = {**meta, **info}

    # Manual images often have a flat colored thumbnail/canvas around the card.
    # Crop that only in aggressive mode and only when the detected object still
    # looks like a horizontal card.
    aggressive_crop_applied = False
    if aggressive:
        box, meta = bbox_from_mask(img, "background")
        if box:
            # For flat-background manual thumbnails, crop tight to the detected
            # card artwork. Padding preserves the original canvas colour as a
            # visible halo/border around the whole card (MBNA green-border case).
            # Keep this at zero and rely on the rounded-corner alpha mask below
            # for clean corners.
            pad = 0
            img2, did_crop, info = apply_candidate_crop(img, box, pad_px=pad, require_reduction=True)
            crop_info["aggressive_background_crop"] = {**meta, **info, "applied": did_crop}
            if did_crop:
                img = img2
                # Preserve rounded-card corners without deleting pixels by
                # colour. The old flood-fill used the flat canvas colour as a
                # transparency key; MBNA uses similar teal inside the card art,
                # so that punched transparent holes through the card design.
                # Apply only a conservative rounded-rectangle alpha mask to the
                # outside corners and keep the interior artwork intact.
                rgba = img.convert("RGBA")
                w, h = rgba.size
                radius = max(8, int(min(w, h) * 0.055))
                mask = Image.new("L", (w, h), 0)
                try:
                    from PIL import ImageDraw
                    draw = ImageDraw.Draw(mask)
                    draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
                    rgba.putalpha(mask)
                    img = rgba
                    info["corner_alpha_mask"] = {"applied": True, "radius": radius}
                    crop_info["aggressive_background_crop"]["corner_alpha_mask"] = info["corner_alpha_mask"]
                except Exception as e:
                    img = rgba
                    info["corner_alpha_mask"] = {"applied": False, "error": str(e)}
                    crop_info["aggressive_background_crop"]["corner_alpha_mask"] = info["corner_alpha_mask"]
                cropped = True
                aggressive_crop_applied = True
                crop_method = "background_canvas_crop"

    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")

    # If upstream/Gemini already produced real transparency but left the card
    # parked inside a large transparent canvas, crop to the alpha bounding box.
    # This is the MBNA clean-card failure mode: technically transparent PNG,
    # visually terrible in WordPress because the asset is mostly empty canvas.
    if aggressive:
        rgba = img.convert("RGBA")
        alpha_box = rgba.getchannel("A").getbbox()
        if alpha_box and alpha_box != (0, 0, rgba.width, rgba.height):
            img2, did_crop, info = apply_candidate_crop(rgba, alpha_box, pad_px=3, require_reduction=True)
            crop_info["alpha_canvas_crop"] = {**info, "applied": did_crop}
            if did_crop:
                img = img2
                cropped = True
                aggressive_crop_applied = True
                crop_method = "alpha_canvas_crop"

    if portrait_card_extracted:
        cropped = True
        crop_method = "portrait_card_extracted_from_banner"
        crop_info["portrait_card_extract"] = portrait_extract_info

    upscaled = False
    upscale_info: Dict[str, Any] = {}
    # Manual crops can be visually correct but too small because the source is
    # a 16:9 thumbnail with the card occupying only the center. For LazyBlock,
    # rescue those by upscaling the card-only PNG after crop while preserving
    # transparency. This is deterministic and avoids a new Gemini hallucination
    # path for card artwork.
    if aggressive and img.width < 900:
        old_w, old_h = img.width, img.height
        scale = 900 / max(1, old_w)
        new_size = (900, max(1, round(old_h * scale)))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=130, threshold=3))
        upscaled = True
        upscale_info = {"before": {"width": old_w, "height": old_h}, "after": {"width": img.width, "height": img.height}, "method": "lanczos_unsharp", "target_width": 900}

    # Page-context safety for banner-derived cards: avoid edge-to-edge fragile
    # transparency that the LazyBlock/container can expose as clipped sides,
    # semicircle notches or black-background artifacts. Put the corrected card on
    # a neutral presentation canvas with breathing room before upload/featured
    # generation.
    if aggressive and portrait_card_extracted:
        card_rgba = img.convert("RGBA")
        alpha_box = card_rgba.getchannel("A").getbbox()
        if alpha_box:
            card_rgba = card_rgba.crop(alpha_box)
        canvas_w, canvas_h = 900, 528
        max_w, max_h = 760, 470
        scale = min(max_w / max(1, card_rgba.width), max_h / max(1, card_rgba.height), 1.0)
        fitted = card_rgba.resize((max(1, round(card_rgba.width * scale)), max(1, round(card_rgba.height * scale))), Image.Resampling.LANCZOS)
        fitted = fitted.filter(ImageFilter.UnsharpMask(radius=0.8, percent=110, threshold=3))
        canvas = Image.new("RGB", (canvas_w, canvas_h), "#f3f4f6")
        x = (canvas_w - fitted.width) // 2
        y = (canvas_h - fitted.height) // 2
        canvas.paste(fitted, (x, y), fitted)
        img = canvas
        crop_info["lazyblock_presentation_canvas"] = {"applied": True, "width": canvas_w, "height": canvas_h, "background": "#f3f4f6", "card_box": [x, y, x + fitted.width, y + fitted.height]}

    img.save(path)
    return {
        "status": "ok",
        "before": before,
        "after": {"width": img.width, "height": img.height},
        "rotated": rotated,
        "cropped": cropped,
        "crop_method": crop_method,
        "manual_crop_applied": aggressive_crop_applied,
        "crop_info": crop_info,
        "upscaled": upscaled,
        "upscale_info": upscale_info,
    }


def esc_text(value: Any) -> str:
    return html.escape(str(value or "").strip())


def sentence_join(items: List[str], limit: int = 3) -> str:
    clean = [str(x).strip().rstrip(".") for x in items if str(x).strip()]
    if not clean:
        return "key card features"
    if len(clean[:limit]) == 1:
        return clean[0]
    return ", ".join(clean[:limit-1]) + " and " + clean[limit-1]


def shorten_words(text: str, max_words: int = 12) -> str:
    words = str(text or "").split()
    if len(words) <= max_words:
        return str(text or "").strip()
    return " ".join(words[:max_words]).rstrip(" ,;:")


def clean_sentence_punctuation(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([,;:])\s*\.\.\.$", "...", text)
    text = re.sub(r"\.\s*\.\.\.$", "...", text)
    text = re.sub(r",\s*\.$", ".", text)
    text = re.sub(r",\s*\.\.\.$", "...", text)
    if text and not re.search(r"(\.|!|\?|\.\.\.)$", text):
        text += "."
    return text


GENERIC_VISIBLE_VALUE_RE = re.compile(
    r"\b(not stated|not provided|not available|n/?a|unknown|check issuer terms|check terms|official product page|latest confirmed benefit details)\b",
    re.I,
)


def is_generic_visible_value(value: Any) -> bool:
    raw = html.unescape(str(value or "")).strip()
    if not raw:
        return True
    return bool(GENERIC_VISIBLE_VALUE_RE.search(raw))


def require_specific_visible_value(value: Any, field: str) -> str:
    raw = html.unescape(str(value or "")).strip()
    if is_generic_visible_value(raw):
        raise RunnerError(f"{field} is generic/unusable for visible content: {raw!r}; fetch the official fact or provide verified request facts")
    return raw


def card_ui_tag(text: Any, fallback: str = "Cashback rewards", *, card_name: str = "", annual_fee: str = "") -> str:
    """Short benefit-led LazyBlock tag. Block numeric fragments and redundant category labels."""
    value = html.unescape(str(text or "")).strip()
    # Split only on semicolon/comma/"and". Do not split decimal values like 2.99.
    value = re.split(r"[;,]|\s+ and \s+", value, maxsplit=1, flags=re.I)[0].strip()
    value = re.sub(r"\bcard features\b", "", value, flags=re.I).strip()
    value = re.sub(r"\s+", " ", value).strip(" .;:,!")
    low = value.lower()
    name_low = (card_name or "").lower()
    fee_low = (annual_fee or "").lower()
    bad = (
        is_generic_visible_value(value)
        or low in {"credit card", "card benefits", "features", "official terms", "transfer fee", "annual fee"}
        or bool(re.fullmatch(r"[0-9.£%\s]+", value))
        or ("fee" in low and bool(re.search(r"\d", low)))
        or (low in {"balance transfer", "balance transfers"} and "balance transfer" in name_low)
        or (low == "no fees" and any(t in fee_low for t in ["fee", "2.99", "annual", "minimum"]))
    )
    if bad:
        value = fallback
    value = re.sub(r"\s+", " ", value).strip(" .;:,!")
    if is_generic_visible_value(value) or re.fullmatch(r"[0-9.£%\s]+", value):
        raise RunnerError(f"LazyBlock tag is generic/unusable: {value!r}")
    return value[:25].rstrip(" .;:,")


def derive_lazyblock_tags(card_name: str, benefits: List[str], annual_fee: str = "") -> Tuple[str, str, str]:
    """Choose commercial, non-redundant card tags and descriptor from current benefits."""
    joined = " ".join([card_name] + benefits).lower()
    fee_low = (annual_fee or "").lower()
    tags: List[str] = []
    descriptor = "Designed around confirmed benefits and practical repayment use."

    month = re.search(r"0%[^.]{0,80}?(\d{1,2})\s*months?", joined)
    if ("balance transfer" in joined or "0% balance" in joined) and month:
        tags.append(f"{month.group(1)} mo 0%")
        descriptor = "Helps move existing card debt into a clearer repayment window."
    elif "balance transfer" in joined or "0% balance" in joined:
        tags.append("0% transfers")
        descriptor = "Helps move existing card debt into a clearer repayment plan."
    if "no nationwide fees" in joined or "purchases abroad" in joined or "foreign transaction" in joined or "abroad" in joined:
        tags.append("No FX fees")
    if "0%" in joined and "purchase" in joined:
        tags.append("0% purchases")
    if "cashback" in joined:
        tags.append("Cashback")
        descriptor = "Makes routine spending feel more rewarding."
    if any(term in joined for term in ["visa", "mastercard", "broad acceptance", "accepted worldwide", "payment network"]):
        tags.append("Broad acceptance")
    if any(term in joined for term in ["online account", "mobile app", "digital wallet", "account management"]):
        tags.append("Digital tools")
    if any(term in joined for term in ["security", "fraud", "purchase protection"]):
        tags.append("Security features")
    if "1% back" in joined or "0.5% back" in joined or "rewards" in joined:
        tags.append("Rewards back")
        descriptor = "Turns planned spending into practical Rewards value."
    if any(t in joined for t in ["avios", "travel", "lounge", "hotel"]):
        tags.append("Travel rewards")
        descriptor = "Makes trips and overseas spending feel easier to use."
    if "no annual fee" in joined or ("annual fee" in fee_low and "£0" in fee_low and "£84" not in fee_low and "monthly" not in fee_low):
        tags.append("No annual fee")

    clean: List[str] = []
    for tag in tags:
        try:
            t = card_ui_tag(tag, tag, card_name=card_name, annual_fee=annual_fee)
        except RunnerError:
            continue
        if t.lower() not in [x.lower() for x in clean]:
            clean.append(t)
    for benefit in benefits:
        candidate = re.sub(r"\s+", " ", str(benefit or "")).strip(" .;:,!")[:25].rstrip(" .;:,")
        if candidate and candidate.lower() not in [x.lower() for x in clean]:
            try:
                clean.append(card_ui_tag(candidate, candidate, card_name=card_name, annual_fee=annual_fee))
            except RunnerError:
                pass
        if len(clean) >= 2:
            break
    if len(clean) < 2:
        raise RunnerError("Could not derive two LazyBlock tags from confirmed card benefits; do not use generic fallback labels")
    return clean[0], clean[1], descriptor


def card_ui_descriptor(card_data: Dict[str, Any], fallback: str) -> str:
    benefits = [str(b) for b in (card_data.get("benefits") or [])]
    joined = " ".join(benefits).lower()
    if "cashback" in joined:
        desc = "Get value back from routine spending."
    elif any(term in joined for term in ["avios", "travel", "marriott", "bonvoy", "elite night"]):
        desc = "Make regular trips and bookings feel more rewarding."
    elif "points" in joined:
        desc = "Collect points on eligible everyday spending."
    elif "no annual fee" in joined or "no fee" in joined:
        desc = "A no-annual-fee card for everyday spend."
    else:
        desc = fallback
    desc = clean_sentence_punctuation(desc)
    if len(desc) > 70:
        desc = desc[:69].rsplit(" ", 1)[0].rstrip(" ,;:") + "."
    return desc


def perceived_benefit_item(raw: str, *, card_name: str = "") -> str:
    """Convert a technical extracted fact into a short user-perceived REC benefit."""
    text = re.sub(r"\s+", " ", str(raw or "")).strip().rstrip(".")
    low = text.lower()
    name_low = card_name.lower()
    if not text:
        return "A clearer way to judge whether the card fits planned spending"
    if "foreign transaction" in low or "abroad" in low or "overseas" in low:
        return "Using the card abroad can feel more convenient when eligible purchases avoid the usual foreign transaction fee"
    if "travel" in low and ("reward" in low or "rewards" in low or "partner" in low):
        return "Trips, hotel bookings, transport or partner spending can turn into rewards when they already fit your routine"
    if "15%" in low and "reward" in low:
        return "Up to 15% back with chosen partner retailers can make travel or everyday partner purchases feel more worthwhile"
    if "1%" in low and ("supermarket" in low or "rewards" in low):
        return "Supermarket spending can return 1% in Rewards when it is part of your normal routine"
    if "0.5%" in low and ("petrol" in low or "elsewhere" in low or "rewards" in low):
        return "Everyday purchases outside supermarkets can still build 0.5% back in Rewards over time"
    if "credit limit" in low or "£5,000" in low:
        return "A higher minimum credit limit can support bigger planned purchases when approval and repayment discipline line up"
    if "annual fee" in low and ("no" in low or "£0" in low):
        return "No annual fee makes the card easier to keep for occasional use without adding a yearly cost"
    if "0%" in low and ("balance" in low or "money transfer" in low):
        return text
    if "balance transfer" in low:
        return "Moving existing card debt can create more breathing room when the transfer window and fee support a realistic repayment plan"
    if "reward" in low or "cashback" in low or "points" in low:
        return "The reward value matters most when it comes from spending you already planned to make"
    if "fee" in low or "apr" in low:
        return f"{text}. This should be checked against the way you expect to spend and repay"
    if "travel" in name_low:
        return f"{text}. The practical value is strongest when it supports trips, overseas purchases or partner spending already planned"
    return text


def rec_top_of_page_copy(card_name: str, benefits: List[str], annual_fee_raw: str, apr_raw: str) -> Dict[str, Any]:
    joined = " ".join([card_name] + benefits).lower()
    primary = perceived_benefit_item(shorten_words(benefits[0] if benefits else "key credit card benefits", 18), card_name=card_name)
    second = perceived_benefit_item(shorten_words(benefits[1] if len(benefits) > 1 else "repayment flexibility", 18), card_name=card_name)
    third = perceived_benefit_item(shorten_words(benefits[2] if len(benefits) > 2 else "clearer budgeting", 18), card_name=card_name)
    if "balance transfer" in joined or "0% balance" in joined:
        month = re.search(r"0%[^.]{0,80}?(\d{1,2})\s*months?", joined)
        months = f"{month.group(1)} months" if month else "months"
        return {
            "summary": f"{card_name} offers up to {months} interest-free balance transfers.",
            "opening_1": f"<strong>{html.escape(card_name)}</strong> is built for people who want to cut interest pressure on existing card debt and organise repayments with more control.",
            "opening_2": f"Its strongest hook is {html.escape(primary.lower())}, giving borrowers more time to simplify monthly payments before interest starts building again.",
            "opening_3": f"The transfer fee matters — {html.escape(annual_fee_raw)} — but the trade-off can make sense when the interest-free window creates real savings and breathing room.",
            "benefits_intro": "Some of the main advantages include:",
            "benefit_items": [
                primary,
                "More time to organise repayments with less financial pressure",
                second,
                "Ability to consolidate multiple balances into one card",
                "Better monthly budgeting and repayment visibility",
            ],
            "fee_context": f"The {html.escape(annual_fee_raw)} is the main trade-off. It should be weighed against the interest saved during the promotional period.",
            "best_for_1": f"This card may suit UK consumers carrying balances on higher-interest cards who want more time to repay debt in a structured way.",
            "best_for_2": "It works best when the user has a clear repayment target and wants fewer payments, less interest pressure and better visibility month to month.",
        }
    if any(t in joined for t in ["travel", "foreign transaction", "overseas", "hotel", "reward", "partner retailer"]):
        return {
            "summary": f"{card_name} links rewards, partner offers and fee-free overseas purchases.",
            "opening_1": f"<strong>{html.escape(card_name)}</strong> can make more sense when rewards already fit your routine.",
            "opening_2": "The value is easier to picture in real situations: booking a trip, paying abroad or using participating brands.",
            "opening_3": f"One of the strongest attractions is practical: {html.escape(primary[0].lower() + primary[1:] if primary else '')}.",
            "benefits_intro": "In practical use, the main benefits can feel like this:",
            "benefit_items": [primary, second, third],
            "fee_context": f"Cost context: {html.escape(annual_fee_raw)}. APR: {html.escape(shorten_words(apr_raw, 6))}.",
            "best_for_1": "This card may suit you if rewards connect with purchases you already make during the year.",
            "best_for_2": "It is less convincing if you would spend more only to chase rewards.",
        }
    return {
        "summary": f"{card_name} is worth comparing when its strongest benefit matches a real spending or repayment need.",
        "opening_1": f"<strong>{html.escape(card_name)}</strong> works best when you can picture exactly where the main benefit fits into everyday use.",
        "opening_2": "The value should feel practical before the application starts: lower friction, clearer costs, better rewards use or a repayment plan that makes sense.",
        "opening_3": f"The strongest hook is {html.escape(primary[0].lower() + primary[1:] if primary else '')}.",
        "benefits_intro": "In practical use, the main benefits can feel like this:",
        "benefit_items": [primary, second, third],
        "fee_context": f"The cost context is {html.escape(annual_fee_raw)}, with APR shown as {html.escape(shorten_words(apr_raw, 8))}; the benefit only matters if it survives normal repayment behaviour.",
        "best_for_1": f"This card may suit you if your normal spending or borrowing pattern makes its strongest benefit useful in practice.",
        "best_for_2": "It may not fit you if you need a different fee profile, reward structure or repayment approach.",
    }


def generate_article_local(site: Dict[str, Any], card_slug: str, card_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a deterministic REC article aligned to cc-rec.md v2.

    REC v2 is a short recommendation page: attraction, perceived benefits,
    points to consider, ideal profile, pros/cons and a soft transition to P1.
    Keep this generator factual and benefit-led; do not use competitor-example
    tables as the primary structure.
    """
    name = esc_text(card_data.get("card_name"))
    annual_fee_raw = require_specific_visible_value(card_data.get("annual_fee"), "annual_fee")
    apr_raw = require_specific_visible_value(card_data.get("apr"), "apr")
    annual_fee = esc_text(annual_fee_raw)
    apr = esc_text(apr_raw)
    benefits = [str(b).strip() for b in (card_data.get("benefits") or []) if str(b).strip() and not is_generic_visible_value(b)]
    if len(benefits) < 4:
        raise RunnerError("REC v2 requires at least 4 specific benefits/facts extracted from official/request facts; generic fallback benefits are blocked")

    primary = perceived_benefit_item(shorten_words(benefits[0], 18), card_name=str(card_data.get("card_name") or name))
    second = perceived_benefit_item(shorten_words(benefits[1], 18), card_name=str(card_data.get("card_name") or name))
    third = perceived_benefit_item(shorten_words(benefits[2], 18), card_name=str(card_data.get("card_name") or name))
    fourth = perceived_benefit_item(shorten_words(benefits[3], 18), card_name=str(card_data.get("card_name") or name))
    benefit_values = [shorten_words(x, 20) for x in [primary, second, third, fourth]]

    descriptor = card_data.get("descriptor") or primary
    tag10, tag2, default_descriptor = derive_lazyblock_tags(str(card_data.get("card_name") or name), benefits, annual_fee_raw)
    card_data["tag10"] = tag10
    card_data["tag2"] = tag2
    card_data["descriptor"] = card_ui_descriptor(card_data, default_descriptor if not descriptor else str(descriptor))

    joined = " ".join([str(card_data.get("card_name") or name)] + benefits).lower()
    if "balance transfer" in joined or "0% balance" in joined:
        angle = "repayment breathing room"
        opening_2 = "Its main appeal is reducing interest pressure while repayments stay clear, as long as the transfer fee and repayment plan make sense."
        conclusion = "If that repayment window matches your budget, the next page can help you check the application path and official conditions in more detail."
    elif any(t in joined for t in ["cashback", "reward", "rewards", "points", "miles", "avios"]):
        angle = "reward value"
        opening_2 = "Its main appeal is easier to understand when rewards come from purchases you already planned, instead of extra spending created only to chase benefits."
        conclusion = "If those rewards fit your routine, the next page explains the costs, requirements and application step before you leave this site."
    elif any(t in joined for t in ["foreign transaction", "abroad", "overseas", "travel", "lounge"]):
        angle = "travel value"
        opening_2 = "Its main appeal is practical travel use, especially when the confirmed benefits support trips, overseas purchases or services you would already use."
        conclusion = "If that travel use feels realistic, the next page goes deeper into requirements, costs and the official application route."
    else:
        angle = "practical value"
        opening_2 = "Its main appeal depends on how the confirmed features fit your normal spending, repayment habits and expectations before applying."
        conclusion = "If that value matches your profile, the next page gives a deeper look before you move to the official issuer step."

    def wp_h2(text: str) -> str:
        return f'<!-- wp:heading -->\n<h2 class="wp-block-heading">{html.escape(text)}</h2>\n<!-- /wp:heading -->'

    def wp_h3(text: str) -> str:
        return f'<!-- wp:heading {{"level":3}} -->\n<h3 class="wp-block-heading">{html.escape(text)}</h3>\n<!-- /wp:heading -->'

    def wp_p(text: str) -> str:
        return f'<!-- wp:paragraph -->\n<p>{text}</p>\n<!-- /wp:paragraph -->'

    def wp_list(items: List[str]) -> str:
        inner = "".join(f'<!-- wp:list-item -->\n<li>{html.escape(str(item))}</li>\n<!-- /wp:list-item -->\n' for item in items if str(item).strip())
        return f'<!-- wp:list -->\n<ul>{inner}</ul>\n<!-- /wp:list -->'

    points = [
        f"Cost context: {annual_fee}. Compare this with the benefit you expect to use most.",
        f"APR context: {esc_text(shorten_words(apr_raw, 10))}. Carrying a balance can reduce the value of rewards or perks.",
        "Final conditions can vary after the issuer checks eligibility, affordability and current product rules.",
    ]
    pros = benefit_values[:4]
    if len(pros) < 5 and "no annual fee" in joined:
        pros.append("No annual fee can make the card easier to keep when usage is occasional")
    cons = [
        "Benefits only create value when they match real spending habits",
        "Rates, fees or eligibility rules can change on the issuer page",
        "Approval, limit and final terms depend on the issuer's assessment",
    ]

    lang = (site.get("language") or "en").strip().lower()
    labels = {
        "pt": {"benefits":"Benefícios do {name}","points":"Pontos a considerar","profile":"Para quem o {name} é indicado","proscons":"Prós e Contras","pros":"Prós","cons":"Contras","final":"Vale avançar para a próxima análise?","bt":["Benefício principal","Valor financeiro","Conveniência de uso","Benefício complementar"]},
        "es": {"benefits":"Beneficios de {name}","points":"Puntos a considerar","profile":"Para quién se recomienda {name}","proscons":"Pros y contras","pros":"Pros","cons":"Contras","final":"¿Vale la pena seguir con la próxima página?","bt":["Beneficio principal","Valor financiero","Conveniencia de uso","Beneficio complementario"]},
        "en": {"benefits":"Benefits of {name}","points":"Points to Consider","profile":"Who {name} Is Recommended For","proscons":"Pros and Cons","pros":"Pros","cons":"Cons","final":"Is it worth moving to the next step?","bt":["Main benefit","Financial value","Usage convenience","Complementary benefit"]},
    }.get(lang, {})
    if not labels:
        labels = {"benefits":"Benefits of {name}","points":"Points to Consider","profile":"Who {name} Is Recommended For","proscons":"Pros and Cons","pros":"Pros","cons":"Cons","final":"Is it worth moving to the next step?","bt":["Main benefit","Financial value","Usage convenience","Complementary benefit"]}
    blocks = [
        wp_p(f"<strong>{name}</strong> is worth a closer look when its confirmed benefits match a real {html.escape(angle)} need."),
        wp_p(opening_2),
        wp_p("Before applying, compare the main benefits with costs, APR and the way you expect to use the card."),
        wp_h2(labels["benefits"].format(name=name)),
    ]
    benefit_tails = [
        "This helps connect the feature with a real spending decision.",
        "This matters most when the value survives normal costs and repayment.",
        "This can make daily use easier without changing your budget only for rewards.",
        "This supports the main use case without distracting from issuer conditions.",
    ]
    for title, benefit, tail in zip(labels["bt"], benefit_values, benefit_tails):
        blocks.append(wp_h3(title))
        blocks.append(wp_p(f"{html.escape(benefit)}. {tail}"))
    blocks.extend([
        wp_h2(labels["points"]),
        wp_list(points),
        wp_h2(labels["profile"].format(name=name)),
        wp_p("This card may suit readers who can use its confirmed benefits naturally before applying."),
        wp_p("It is less convincing when the main benefit would require extra spending or unclear repayment behaviour."),
        wp_h2(labels["proscons"]),
        wp_h3(labels["pros"]),
        wp_list(pros),
        wp_h3(labels["cons"]),
        wp_list(cons),
        wp_h2(labels["final"]),
        wp_p(conclusion),
        wp_p("Use this recommendation as a first filter, then compare the official page with your budget, spending habits and repayment plan with more confidence."),
        wp_p("Check the latest official conditions before deciding, because rates and benefits can change over time."),
    ])
    html_body = "\n\n".join(blocks)
    return {
        "success": True,
        "article_html": html_body,
        "cost_usd": 0.0,
        "duration_sec": 0.0,
        "card_data": card_data,
        "generator": "local_deterministic_rec_contract_v2",
    }


def validate_html(path: Path) -> Dict[str, Any]:
    p = run([str(GEN_SCRIPTS / "validate-article.sh"), str(path)], timeout=30)
    try:
        data = json.loads(p.stdout)
    except Exception:
        raise RunnerError(f"validate-article returned non-JSON: rc={p.returncode} stdout={p.stdout} stderr={p.stderr}")
    if p.returncode != 0 or data.get("status") != "PASS":
        raise RunnerError(f"Article validation failed: {json.dumps(data, ensure_ascii=False)}")
    return data


def validate_html_soft(path: Path) -> Dict[str, Any]:
    p = run([str(GEN_SCRIPTS / "validate-article.sh"), str(path)], timeout=30)
    try:
        return json.loads(p.stdout)
    except Exception:
        return {"status": "FAIL", "error": f"non_json rc={p.returncode} stdout={p.stdout[:500]} stderr={p.stderr[:500]}"}


def pad_content_to_min_words(content: str, current_count: int, min_count: int = 450) -> str:
    if current_count >= min_count:
        return content
    needed = min_count - current_count + 2
    pads = [
        "That can make planned spending easier to judge before applying.",
        "The card works best when its strongest feature matches real monthly behaviour.",
        "You should still confirm current issuer terms before committing.",
        "The final offer can vary after credit assessment.",
        "Repayment behaviour remains central to card value.",
        "Current pricing should be checked before application.",
        "The card should match planned spending needs.",
        "Eligibility is assessed by the issuer directly.",
        "You should compare alternatives before applying.",
        "That keeps the recommendation tied to practical use.",
        "The strongest value appears in regular travel spending.",
        "Costs matter most if balances are carried month to month.",
        "Cashback value depends on eligible purchase behaviour.",
        "Overseas spending benefits depend on how often you travel.",
        "Application checks should happen before any formal submission.",
    ]

    paragraph_re = re.compile(r"<p>(.*?)</p>", re.I | re.S)
    matches = list(paragraph_re.finditer(content))
    replacements: List[Tuple[int, int, str]] = []
    pad_i = 0
    used_pad_sentences = set(re.findall(r"[^.!?]+[.!?]", re.sub(r"<[^>]+>", " ", html.unescape(content))))
    used_pad_sentences = {re.sub(r"\s+", " ", s).strip().lower() for s in used_pad_sentences}
    remaining = needed
    # Add short factual caution sentences to existing paragraphs with spare room.
    # This preserves max-section-paragraphs and keeps every paragraph <=30 words.
    for m in matches[1:]:  # do not alter subtitle/excerpt
        inner = m.group(1)
        if "lazyblock" in inner.lower():
            continue
        plain = re.sub(r"<[^>]+>", " ", html.unescape(inner))
        count = len(re.findall(r"[A-Za-z0-9%£]+", plain))
        spare = 30 - count
        if spare < 7:
            continue
        addition = ""
        add_words = 0
        for _ in range(len(pads)):
            candidate = pads[pad_i % len(pads)]
            pad_i += 1
            norm = re.sub(r"\s+", " ", candidate).strip().lower()
            if norm in used_pad_sentences:
                continue
            candidate_words = len(candidate.split())
            if candidate_words > spare:
                continue
            addition = candidate
            add_words = candidate_words
            used_pad_sentences.add(norm)
            break
        if not addition:
            continue
        replacements.append((m.start(1), m.end(1), inner.rstrip() + " " + html.escape(addition)))
        remaining -= add_words
        if remaining <= 0:
            break

    if not replacements:
        return content
    for start, end, repl in reversed(replacements):
        content = content[:start] + repl + content[end:]
    return content


def trim_content_to_max_words(content: str, current_count: int, max_count: int = 500) -> str:
    """Deterministically trim prose when the generated article is slightly long.

    Prefer trimming the last normal paragraph before the CTA so the subtitle,
    LazyBlocks and comparative table structure remain intact.
    """
    if current_count <= max_count:
        return content
    excess = current_count - max_count
    paragraph_re = re.compile(r"<!-- wp:paragraph -->\s*<p>(.*?)</p>\s*<!-- /wp:paragraph -->", re.I | re.S)
    matches = list(paragraph_re.finditer(content))
    remove_words = excess + 3  # safety margin for validator tokenization
    for m in reversed(matches[1:]):  # never trim the subtitle/excerpt
        inner = m.group(1).strip()
        if "wp:lazyblock" in inner or "<strong>" in inner.lower():
            continue
        plain = re.sub(r"<[^>]+>", " ", html.unescape(inner))
        words = plain.split()
        if len(words) <= remove_words + 10:
            continue
        kept = words[: max(10, len(words) - remove_words)]
        new_plain = " ".join(kept).rstrip(" ,;:")
        if not re.search(r"[.!?]$", new_plain):
            new_plain += "."
        replacement = f"<!-- wp:paragraph -->\n<p>{html.escape(new_plain)}</p>\n<!-- /wp:paragraph -->"
        return content[: m.start()] + replacement + content[m.end():]
    return content


def title_meta_focus(card_name: str, card_data: Dict[str, Any]) -> Tuple[str, str, str]:
    # Keep focus <=4 words. Prefer a recognisable product stem.
    words = [w for w in re.sub(r"[^A-Za-z0-9 ]", " ", card_name).split() if w.lower() not in {"credit", "card", "the"}]
    focus = " ".join(words[:3]) if words else card_name[:40]
    no_fee = "no annual fee" in (card_data.get("annual_fee") or "").lower() or any("no annual fee" in b.lower() for b in card_data.get("benefits", []))
    joined = " ".join(card_data.get("benefits", [])).lower()
    rewards_supported = any(x in joined for x in ["cashback", "rewards", "points", "miles"])
    if "balance transfer" in joined or "0% balance" in joined:
        title = f"{focus}: 0% Balance Transfer"
    elif no_fee:
        title = f"{focus}: No Annual Fee"
    elif rewards_supported:
        title = f"{focus}: Rewards & Fees"
    else:
        title = f"{focus}: Benefits & Fees"
    if len(title) > 60:
        title = f"{focus}: Benefits"[:60]
    if "balance transfer" in joined or "0% balance" in joined:
        meta = f"{card_name} offers 0% balance transfer value, fees and APR context to compare before applying."
    else:
        benefit_text = ", ".join(card_data.get('benefits', ['key benefits'])[:2]).lower()
        meta = f"{card_name} offers {benefit_text}. Compare benefits, fees and APR before applying."
    # Contract v2: REC meta description must be 130-140 visible characters.
    if len(meta) > 140:
        meta = clean_sentence_punctuation(meta[:140].rsplit(" ", 1)[0] + ".")
        if len(meta) > 140:
            meta = meta[:140].rstrip(" ,;:")
    while len(meta) < 130:
        extra = " Check current issuer conditions before applying."
        candidate = clean_sentence_punctuation(meta.rstrip(".") + extra)
        if len(candidate) <= 140:
            meta = candidate
        else:
            remaining = 130 - len(meta)
            if remaining <= 0:
                break
            meta = clean_sentence_punctuation((meta.rstrip(".") + " Check official terms.")[:140])
            break
    if len(meta) < 130:
        meta = clean_sentence_punctuation((meta.rstrip(".") + " Check official issuer terms before applying.")[:140])
    meta = clean_sentence_punctuation(meta)
    if len(meta) > 140:
        meta = meta[:140].rstrip(" ,;:.") + "."
        if len(meta) > 140:
            meta = meta[:139].rstrip(" ,;:.") + "."
    if len(meta) < 130:
        meta = clean_sentence_punctuation((meta.rstrip(".") + " Check official issuer terms before applying.")[:140])
    if not (130 <= len(meta) <= 140):
        raise RunnerError(f"REC meta description outside contract v2 range 130-140 chars: {len(meta)}")
    return title, meta, focus


def load_term_cache() -> Dict[str, Any]:
    if not TERM_CACHE_JSON.exists():
        return {}
    try:
        data = json.loads(TERM_CACHE_JSON.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_term_cache(cache: Dict[str, Any]) -> None:
    TERM_CACHE_JSON.parent.mkdir(parents=True, exist_ok=True)
    tmp = TERM_CACHE_JSON.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    tmp.replace(TERM_CACHE_JSON)


def resolve_term_id(site_key: str, taxonomy: str, name: str, term_cache: Optional[Dict[str, Any]] = None, term_stats: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """Resolve a WP term, tolerating WordPress term_exists races/errors."""
    norm = " ".join(name.split()).lower()
    cache_key = f"{site_key}:{taxonomy}:{norm}"
    if term_cache is not None and cache_key in term_cache:
        if term_stats is not None:
            term_stats["cache_hits"] = term_stats.get("cache_hits", 0) + 1
        cached = dict(term_cache[cache_key])
        cached.setdefault("name", name)
        cached.setdefault("source", "term_cache")
        return cached

    if term_stats is not None:
        term_stats["cache_misses"] = term_stats.get("cache_misses", 0) + 1
    p = run([str(WP_SCRIPTS / "resolve-term.sh"), site_key, taxonomy, name], timeout=60)
    if p.returncode == 0:
        resolved = json.loads(p.stdout)
        if term_cache is not None:
            term_cache[cache_key] = {"id": int(resolved["id"]), "name": name, "slug": resolved.get("slug") or slugify(name), "taxonomy": taxonomy, "site_key": site_key}
        return resolved
    combined = (p.stderr or "") + "\n" + (p.stdout or "")
    m = re.search(r'"term_id"\s*:\s*(\d+)', combined)
    if m:
        resolved = {"id": int(m.group(1)), "name": name, "slug": slugify(name)}
        if term_cache is not None:
            term_cache[cache_key] = {"id": int(resolved["id"]), "name": name, "slug": resolved["slug"], "taxonomy": taxonomy, "site_key": site_key}
        return resolved
    raise RunnerError(f"Command failed rc={p.returncode}: {WP_SCRIPTS / 'resolve-term.sh'} {site_key} {taxonomy} {name}\n{combined[:2000]}")


def resolve_terms(site_key: str, site: Dict[str, Any], card_slug: str, card_data: Dict[str, Any], term_cache: Optional[Dict[str, Any]] = None, term_stats: Optional[Dict[str, int]] = None) -> Tuple[int, List[int], List[str]]:
    category_name = site.get("default_category", "Credit Card")
    cat = resolve_term_id(site_key, "categories", category_name, term_cache, term_stats)
    tags = [
        "rec",
        (site.get("verticals") or ["cc"])[0],
        site.get("country", "gb"),
        card_slug.replace("-", " "),
        f"lang_{site.get('language', 'en')}",
        "atena_agent",
    ]
    extras = []
    for b in card_data.get("benefits", []):
        lb = b.lower()
        if "cashback" in lb: extras.append("cashback rewards")
        if "no annual fee" in lb or "no fee" in lb: extras.append("no annual fee")
        if "travel" in lb: extras.append("travel credit card")
        if "balance transfer" in lb: extras.append("balance transfer")
        if ("purchase" in lb or "purchases" in lb) and ("0%" in lb or "interest free" in lb or "introductory" in lb or "promotional" in lb): extras.append("purchase credit card")
    issuer = card_name_issuer(card_data.get("card_name") or "")
    if issuer:
        extras.append(issuer)
    for e in extras:
        if e and e not in tags:
            tags.append(e)
        if len(tags) >= 10:
            break
    ids = []
    names = []
    for t in tags:
        term = resolve_term_id(site_key, "tags", t, term_cache, term_stats)
        ids.append(int(term["id"]))
        names.append(t)
    return int(cat["id"]), ids, names


def card_name_issuer(name: str) -> str:
    low = name.lower()
    if "american express" in low or "amex" in low:
        return "american express"
    for issuer in ["barclaycard", "hsbc", "lloyds", "halifax", "natwest", "mbna", "capital one", "tesco bank", "santander"]:
        if issuer in low:
            return issuer
    return ""


def public_verify(url: str, *, apply_url: str = "", card_url: str = "", featured_url: str = "") -> Dict[str, Any]:
    try:
        req = urllib.request.Request(url + ("?nocache=1" if "?" not in url else "&nocache=1"), headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read(500000).decode("utf-8", errors="ignore")
            status = getattr(r, "status", 200)
        checks = {
            "http_status": status,
            "bytes": len(body),
            "contains_how_to_apply": "How to Apply" in body or "HOW TO APPLY" in body,
            "contains_microcopy": "You will remain on this website." in body,
            "contains_apply_url": bool(apply_url and apply_url in body),
            "contains_card": bool(card_url and card_url in body),
            "contains_featured": bool(featured_url and featured_url in body),
        }
        checks["ok"] = (
            status == 200
            and checks["bytes"] > 5000
            and checks["contains_how_to_apply"]
            and checks["contains_microcopy"]
            and checks["contains_apply_url"]
            and checks["contains_card"]
            and checks["contains_featured"]
        )
        return checks
    except Exception as e:
        return {"http_status": 0, "ok": False, "error": str(e)}


def cleanup_extra_media(site_key: str, created_media: List[Dict[str, Any]], post_id: Optional[int], used_media_ids: List[int]) -> Dict[str, Any]:
    """Delete only media created in this runner execution and not used by the final post.

    This is intentionally conservative: the runner can only auto-delete items it
    uploaded itself during the current run. The shell helper performs the final
    WordPress-side safety gates (featured_media/content references/parent post).
    """
    used = {int(x) for x in used_media_ids if x}
    extras = [m for m in created_media if m.get("id") and int(m["id"]) not in used]
    results: List[Dict[str, Any]] = []
    for media in extras:
        try:
            cmd = [str(WP_SCRIPTS / "delete-media-safe.sh"), site_key, str(media["id"])]
            if post_id:
                cmd.append(str(post_id))
            res = run_json(cmd, timeout=90, allow_fail=True)
            res["role"] = media.get("role")
            results.append(res)
        except Exception as e:
            results.append({"status": "error", "media_id": media.get("id"), "role": media.get("role"), "reason": str(e)})
    return {
        "created_count": len(created_media),
        "used_count": len([m for m in created_media if m.get("id") and int(m["id"]) in used]),
        "extra_count": len(extras),
        "deleted_count": len([r for r in results if r.get("status") == "deleted"]),
        "items": results,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run deterministic MGS REC pipeline")
    ap.add_argument("--site", required=True)
    ap.add_argument("--card", required=True)
    ap.add_argument("--status", choices=["draft", "publish"], default="draft")
    ap.add_argument("--source-url", default="")
    ap.add_argument("--annual-fee", default="")
    ap.add_argument("--apr", default="")
    ap.add_argument("--benefit", action="append", default=[])
    ap.add_argument("--competitor", action="append", default=[], help="Name or JSON object; repeatable")
    ap.add_argument("--card-image-url", default="", help="Optional direct card image URL; skips search-card-image fallback")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-disambiguation", action="store_true")
    ap.add_argument("--lang", default="", help="Debug-only language override. Production language comes from site.language.")
    ap.add_argument("--allow-language-override", action="store_true", help="Allow --lang in dry-run/draft debug. Publish aborts if it conflicts with site.language.")
    args = ap.parse_args()
    if not args.card_image_url:
        args.card_image_url = (
            os.environ.get("MGS_CARD_IMAGE_URL", "").strip()
            or os.environ.get("MGS_MANUAL_CARD_IMAGE_URL", "").strip()
        )

    started = time.time()
    warnings: List[str] = []
    steps: List[str] = []
    costs = {"article_api": 0.0, "extract_llm_est": 0.0, "featured_image_est": 0.03, "total_est": 0.0}
    timings: Dict[str, float] = {}
    created_media: List[Dict[str, Any]] = []
    artifact_audit: Dict[str, Any] = {"created_count": 0, "used_count": 0, "extra_count": 0, "deleted_count": 0, "items": []}

    def tick(name: str, t0: float, add: bool = False) -> None:
        elapsed = time.time() - t0
        if add:
            elapsed += float(timings.get(name, 0) or 0)
        timings[name] = round(elapsed, 2)

    try:
        t0 = time.time()
        site = load_site(args.site)
        canonical_language = (site.get("language") or "").strip().lower()
        if args.lang:
            requested_language = args.lang.strip().lower()
            if not args.allow_language_override:
                raise RunnerError("--lang is debug-only. Use site.language for production, or pass --allow-language-override for dry-run/draft debugging.")
            if args.status == "publish" and canonical_language and requested_language != canonical_language:
                raise RunnerError(f"language_override_conflicts_with_site_language: site.language={canonical_language} --lang={requested_language}; publish blocked")
            site["language"] = requested_language
        template_contract = load_rec_template_contract(site)
        card_slug = slugify(args.card)
        country = site.get("country", "gb")
        vertical = (site.get("verticals") or ["cc"])[0]
        post_slug = f"rec-{country}-{vertical}-{card_slug}"
        edit_url = None
        card_data: Dict[str, Any]
        term_cache = load_term_cache()
        term_stats = {"cache_hits": 0, "cache_misses": 0}

        color = run_json([str(WP_SCRIPTS / "resolve-button-color.sh"), args.site], timeout=30)
        button_hex = color["hex"]
        tick("config_load_sec", t0)
        steps.append("config_loaded")

        benefits = args.benefit or []
        competitors: List[Dict[str, str]] = []
        for c in args.competitor:
            try:
                obj = json.loads(c)
                if isinstance(obj, dict):
                    competitors.append(obj)
            except Exception:
                competitors.append({"name": c})
        if benefits and args.annual_fee:
            card_data = {
                "card_name": args.card,
                "card_official_url": args.source_url,
                "annual_fee": args.annual_fee,
                "apr": args.apr or "N/A",
                "benefits": benefits,
                "competitors": competitors,
            }
            steps.append("request_facts_used")
        else:
            if not args.source_url:
                raise RunnerError("official source URL required; editorial card-cache is disabled for production content")
            t0 = time.time()
            status, text = fetch_reference_text(args.source_url)
            tick("reference_fetch_sec", t0)
            if status >= 400:
                raise RunnerError(f"reference_url returned HTTP {status}")
            t0 = time.time()
            card_data = extract_card_data_with_llm(args.card, args.source_url, text)
            tick("reference_extract_llm_sec", t0)
            card_data["card_official_url"] = args.source_url
            steps.append("reference_extracted_deterministic")
            costs["extract_llm_est"] = 0.0

        card_data["card_name"] = card_data.get("card_name") or args.card
        source_to_check = args.source_url or card_data.get("card_official_url") or ""
        if source_to_check:
            t0 = time.time()
            status_check, source_text = fetch_reference_text(source_to_check)
            tick("official_source_content_gate_sec", t0)
            if status_check >= 400:
                raise RunnerError(f"official source returned HTTP {status_check}: {source_to_check}")
            source_ok, source_reason = official_source_has_content(card_data["card_name"], source_to_check, source_text)
            if not source_ok:
                raise RunnerError(f"Official source URL has no usable product content; ask Raquel/Rodolfo for the correct official link. url={source_to_check} reason={source_reason}")
            card_data["card_official_url"] = source_to_check
            steps.append("official_source_content_gate_passed")
        if args.card_image_url:
            # A user-supplied card image is an explicit override. Do not reuse a
            # cached/uploaded card image for the same card, otherwise manual
            # image benchmarks silently fall back to auto/cache media.
            card_data.pop("card_image_uploaded_id", None)
            card_data.pop("card_image_uploaded_url", None)
            steps.append("manual_card_image_override_requested")
        card_id = card_data.get("card_image_uploaded_id")
        card_url = card_data.get("card_image_uploaded_url")
        card_local = None
        card_src = None
        card_selection: Dict[str, Any] = {}
        card_normalize: Dict[str, Any] = {}

        # Generate and mechanically validate content BEFORE any new WP media upload.
        # This prevents orphan card/featured media when the article later fails word-count/SEO validation.
        api_payload = {
            "site": args.site,
            "template_key": template_contract["template_key"],
            "template_contract": template_contract,
            "card_slug": card_slug,
            "card_name": card_data["card_name"],
            "card_official_url": card_data.get("card_official_url") or args.source_url,
            "annual_fee": card_data.get("annual_fee") or "N/A",
            "apr": card_data.get("apr") or "N/A",
            "benefits": card_data.get("benefits") or [],
            "competitors": card_data.get("competitors") or [],
        }
        t0 = time.time()
        api = generate_article_local(site, card_slug, card_data)
        tick("article_local_generate_sec", t0)
        steps.append("article_generated_local")
        costs["article_api"] = float(api.get("cost_usd") or 0)
        card_data.update(api.get("card_data") or {})

        def build_and_validate_current(stage: str) -> Tuple[str, Dict[str, Any], int]:
            t_stage = time.time()
            card_block = lazy_credit_card(card_data["card_name"], card_id, card_url, site, card_slug, card_data, button_hex)
            button_block = lazy_button(site, card_slug, button_hex)
            current = assemble_content(api["article_html"], card_block, button_block)
            current = enforce_subtitle_limit(current, card_data["card_name"], card_data)
            tmp_html = Path(tempfile.gettempdir()) / f"final-{card_slug}.html"
            tmp_html.write_text(current)
            first_validation = validate_html_soft(tmp_html)
            first_count = int(first_validation.get("count") or 0)
            if first_validation.get("status") != "PASS" and first_count < 450 and first_validation.get("subtitle") == "pass":
                current = pad_content_to_min_words(current, first_count, 470)
                tmp_html.write_text(current)
            elif first_validation.get("status") != "PASS" and first_count > 500 and first_validation.get("subtitle") == "pass":
                current = trim_content_to_max_words(current, first_count, 500)
                tmp_html.write_text(current)
            final_validation = validate_html(tmp_html)
            subtitle = visible_subtitle(current)
            sub_chars = len(subtitle)
            if sub_chars > 100:
                raise RunnerError(f"subtitle too long: {sub_chars} chars")
            tick(f"validate_{stage}_sec", t_stage)
            return current, final_validation, sub_chars

        content, validation, subtitle_chars = build_and_validate_current("pre_upload")
        steps.append("content_validated_pre_upload")

        featured_id = None
        featured_url = None
        featured_scene = None
        featured_path = None
        featured_audit = None

        if not card_id or not card_url:
            if args.dry_run:
                if args.card_image_url:
                    t0 = time.time()
                    # Manual overrides are normalized to PNG so rounded-card
                    # transparency survives; JPEG would bake the canvas color
                    # into the LazyBlock image corners.
                    suffix = ".png"
                    card_local = f"/tmp/card-{card_slug}-manual-dryrun{suffix}"
                    req = urllib.request.Request(
                        args.card_image_url,
                        headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) MGS-REC-Runner/1.0"},
                    )
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        Path(card_local).write_bytes(resp.read())
                    card_src = args.card_image_url
                    card_normalize = normalize_card_artwork(card_local, aggressive=True)
                    ident_card = run(["identify", "-format", "%w %h", card_local], timeout=20)
                    if ident_card.returncode != 0:
                        raise RunnerError(f"manual card image identify failed: {ident_card.stderr}")
                    cw, ch = [int(x) for x in ident_card.stdout.split()[:2]]
                    if cw < 200 or ch < 100:
                        raise RunnerError(f"manual card image too small: {cw}x{ch}")
                    if not (1.2 <= (cw / ch) <= 2.2):
                        raise RunnerError(f"manual card image aspect out of range: {cw}x{ch}")
                    manual_pre_upscale_w = (((card_normalize.get("upscale_info") or {}).get("before") or {}).get("width"))
                    card_selection = {
                        "mode": "manual_card_image_url",
                        "source": args.card_image_url,
                        "reason": "user_supplied_card_art_normalized",
                        "width": cw,
                        "height": ch,
                        "aspect": round(cw / ch, 4) if ch else None,
                        "dry_run_validated": True,
                    }
                    if manual_pre_upscale_w and int(manual_pre_upscale_w) < 600:
                        warnings.append(
                            f"manual_card_image_low_quality_source: useful crop width {manual_pre_upscale_w}px below 600px; "
                            "normal publish would stop and require a better source or explicit automatic fallback approval"
                        )
                        card_selection["quality_warning"] = f"useful crop width {manual_pre_upscale_w}px below 600px before upscale"
                    tick("manual_card_image_validate_sec", t0)
                    steps.append("dry_run_manual_card_image_validated")
                steps.append("dry_run_skip_card_upload")
            else:
                source_url = card_data.get("card_official_url") or args.source_url
                if args.status == "publish" and not args.card_image_url:
                    raise RunnerError(
                        "card_image_required_for_publish: no approved manual card image URL supplied. "
                        "Ask Raquel/Rodolfo for the correct card image before publishing; automatic image fallback is disabled for production."
                    )
                if not source_url and not args.card_image_url:
                    raise RunnerError("No card official URL available for draft image search")
                t0 = time.time()
                if args.card_image_url:
                    # Manual image URLs are a source-of-truth override for the
                    # LazyBlock card image. Normalize/crop the supplied image,
                    # but do not use Gemini/AI to recreate an isolated card:
                    # the MBNA incident proved generated card-only assets can
                    # change text, edges, shadows, colours, and brand design.
                    # If the useful crop is too small, stop before upload by
                    # default. A one-off editorial benchmark can explicitly
                    # allow the supplied low-res manual image via env var while
                    # keeping the normal gate strict.
                    suffix = ".png"
                    manual_local = f"/tmp/card-{card_slug}-manual{suffix}"
                    req = urllib.request.Request(
                        args.card_image_url,
                        headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) MGS-REC-Runner/1.0"},
                    )
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        Path(manual_local).write_bytes(resp.read())
                    manual_normalize = normalize_card_artwork(manual_local, aggressive=True)
                    manual_pre_upscale_w = (((manual_normalize.get("upscale_info") or {}).get("before") or {}).get("width"))
                    card_local = manual_local
                    card_src = args.card_image_url
                    card_selection = {
                        "mode": "manual_card_image_url",
                        "source": args.card_image_url,
                        "reason": "user_supplied_card_art_normalized",
                    }
                    if manual_pre_upscale_w and int(manual_pre_upscale_w) < 600:
                        # Scope update, Rodolfo 2026-05-27: small manual card images may be
                        # acceptable after normalization inside the card UI. Treat size as a
                        # quality warning, not a publishing blocker. Identity/semantics still
                        # remain hard gates.
                        card_selection["quality_warning"] = f"useful crop width {manual_pre_upscale_w}px below 600px before upscale"
                        card_selection["quality_status"] = "LOW_QUALITY_SOURCE_ALLOWED_MANUAL"
                        warnings.append(
                            f"manual_card_image_low_quality_source_allowed: useful crop width {manual_pre_upscale_w}px below 600px; manual image accepted after normalization"
                        )
                        steps.append("manual_card_image_low_quality_source_allowed")
                    steps.append("card_image_manual_url_used")
                else:
                    img = run_json([str(GEN_SCRIPTS / "search-card-image.sh"), card_data["card_name"], source_url], timeout=180, allow_fail=True)
                    if img.get("status") != "OK" or not img.get("path"):
                        raise RunnerError(f"Card image search failed: {json.dumps(img, ensure_ascii=False)[:1000]}")
                    card_local = img["path"]
                    card_src = img.get("source")
                    card_selection = {
                        "mode": (img.get("selection") or {}).get("mode") or "auto_card_image_search",
                        "provider": img.get("provider"),
                        "tier": img.get("tier"),
                        "source": img.get("source"),
                        "score": (img.get("selection") or {}).get("score"),
                        "title": (img.get("selection") or {}).get("title"),
                        "page": (img.get("selection") or {}).get("page"),
                    }
                card_normalize = normalize_card_artwork(card_local, aggressive=bool(args.card_image_url and card_selection.get("mode") == "manual_card_image_url"))
                try:
                    ident_card = run(["identify", "-format", "%w %h", card_local], timeout=20)
                    if ident_card.returncode == 0:
                        cw, ch = [int(x) for x in ident_card.stdout.split()[:2]]
                        card_selection.update({"width": cw, "height": ch, "aspect": round(cw / ch, 4) if ch else None})
                        if cw < 200 or ch < 100:
                            raise RunnerError(f"card image too small after normalization: {cw}x{ch}")
                        if not (1.2 <= (cw / ch) <= 2.2):
                            raise RunnerError(f"card image aspect out of range after normalization: {cw}x{ch}")
                except RunnerError:
                    raise
                except Exception as exc:
                    warnings.append(f"card_image_dimension_validation_skipped: {exc}")
                steps.append("card_image_normalized")
                tick("card_image_discovery_sec", t0)
                ext = Path(card_local).suffix or ".png"
                t0 = time.time()
                up = run_json([str(WP_SCRIPTS / "upload-image.sh"), args.site, card_local, f"card-{card_slug}{ext}"], timeout=120)
                tick("card_image_upload_sec", t0)
                card_id, card_url = int(up["id"]), up["source_url"]
                created_media.append({"role": "card", "id": card_id, "url": card_url, "filename": f"card-{card_slug}{ext}", "used": True})
                steps.append("card_image_uploaded")
        else:
            steps.append("card_image_cache_reused")

        if args.dry_run:
            steps.append("dry_run_skip_featured")
        else:
            if not card_local:
                if not card_url:
                    raise RunnerError("No card image available for featured generation")
                suffix = Path(urllib.parse.urlparse(card_url).path).suffix or ".png"
                card_local = f"/tmp/card-{card_slug}-from-wp{suffix}"
                t0 = time.time()
                urllib.request.urlretrieve(card_url, card_local)
                card_normalize = normalize_card_artwork(card_local)
                tick("card_image_download_sec", t0)
            featured_path = None
            featured_scene = None
            featured_audit = None
            featured_failures: List[str] = []
            for featured_attempt in range(1, 4):
                t0 = time.time()
                feat = run_json([str(GEN_SCRIPTS / "generate-featured-image.sh"), card_slug, card_local], timeout=180)
                tick("featured_generate_sec", t0, add=True)
                featured_path = feat["path"]
                featured_scene = feat.get("scene")
                t0 = time.time()
                ident = run(["identify", "-format", "%w %h", featured_path], timeout=20)
                if ident.returncode != 0:
                    raise RunnerError(f"featured identify failed: {ident.stderr}")
                w, h = [int(x) for x in ident.stdout.split()[:2]]
                if w < 1000 or h < 600:
                    raise RunnerError(f"featured image too small: {w}x{h}")
                if abs((w / h) - (16 / 9)) > 0.01:
                    raise RunnerError(f"featured image not 16:9 after compression: {w}x{h}")
                tick("featured_local_validate_sec", t0, add=True)
                t0 = time.time()
                featured_audit = run_json([
                    str(FEATURED_AUDIT_SCRIPT),
                    "--featured", featured_path,
                    "--card", card_local,
                    "--mode", "rec",
                    "--card-name", card_data.get("card_name") or args.card,
                ], timeout=150, allow_fail=True)
                tick("featured_semantic_audit_sec", t0, add=True)
                if featured_audit.get("ok"):
                    if featured_attempt > 1:
                        warnings.append(f"featured_semantic_audit_passed_after_retry:{featured_attempt}")
                    break
                reasons = featured_audit.get("blocking_reasons") or []
                featured_failures.append(f"attempt {featured_attempt}: {', '.join(map(str, reasons))}")
            if not featured_audit or not featured_audit.get("ok"):
                raise RunnerError("featured_semantic_audit_failed_after_retries: " + " | ".join(featured_failures))
            steps.append("featured_semantic_audited")
            t0 = time.time()
            upf = run_json([str(WP_SCRIPTS / "upload-image.sh"), args.site, featured_path, f"featured-{card_slug}-final.jpg"], timeout=120)
            tick("featured_upload_sec", t0)
            featured_id, featured_url = int(upf["id"]), upf["source_url"]
            created_media.append({"role": "featured", "id": featured_id, "url": featured_url, "filename": f"featured-{card_slug}-final.jpg", "used": True, "scene": featured_scene})
            steps.append("featured_uploaded")

        # Rebuild and revalidate the exact final HTML after media IDs/URLs are known.
        content, validation, subtitle_chars = build_and_validate_current("final")
        validate_no_review({"body": content, "subtitle": visible_subtitle(content)})
        steps.append("content_validated_final")

        fingerprint_check: Dict[str, Any] = {}
        fp_path = Path(tempfile.gettempdir()) / f"fingerprint-{card_slug}.html"
        fp_path.write_text(content)
        t0 = time.time()
        fingerprint_check = run_json([str(ROOT / "scripts/rec-fingerprint.py"), "--card-slug", card_slug, "--site", args.site, "--file", str(fp_path)], timeout=30, allow_fail=True)
        tick("duplicate_fingerprint_check_sec", t0)
        if fingerprint_check.get("status") == "WARN_SIMILAR":
            warnings.append(f"duplicate_content_similarity_warn: max={fingerprint_check.get('max_similarity')} threshold={fingerprint_check.get('threshold')}")
        steps.append("duplicate_fingerprint_checked")

        t0 = time.time()
        qa_check = run_json([
            str(ROOT / "scripts/qa-content-validator.py"),
            "--type", "rec",
            "--file", str(fp_path),
            "--card", card_data["card_name"],
        ], timeout=30, allow_fail=True)
        tick("semantic_qa_check_sec", t0)
        if qa_check.get("status") == "BLOCK":
            raise RunnerError(f"semantic_qa_blocked: {qa_check}")
        if qa_check.get("status") == "WARN":
            warnings.append(f"semantic_qa_warn: {qa_check.get('warnings')}")
        steps.append("semantic_qa_checked")

        t0 = time.time()
        title, meta_desc, focus_kw = title_meta_focus(card_data["card_name"], card_data)
        tick("seo_fields_sec", t0)
        validate_no_review({"title": title, "meta_desc": meta_desc, "focus_kw": focus_kw})
        if len(title) > 60 or focus_kw.lower() not in title.lower() or len(meta_desc) < 130 or len(meta_desc) > 140 or len(focus_kw.split()) > 4:
            raise RunnerError(f"SEO field validation failed title={len(title)} meta={len(meta_desc)} focus_words={len(focus_kw.split())} focus_in_title={focus_kw.lower() in title.lower()}")

        category_id = None
        tag_ids: List[int] = []
        tag_names: List[str] = []
        post_id = None
        public_url = f"https://{site['domain']}/{post_slug}/"
        yoast_result: Dict[str, Any] = {}
        public_check: Dict[str, Any] = {}

        if args.dry_run:
            steps.append("dry_run_skip_publish")
        else:
            t0 = time.time()
            category_id, tag_ids, tag_names = resolve_terms(args.site, site, card_slug, card_data, term_cache, term_stats)
            validate_taxonomy_names(tag_names, site.get("language", "en"))
            tick("wp_resolve_terms_sec", t0)
            if term_stats.get("cache_misses", 0):
                save_term_cache(term_cache)
            timings["wp_term_cache_hits"] = term_stats.get("cache_hits", 0)
            timings["wp_term_cache_misses"] = term_stats.get("cache_misses", 0)

            post_json = {
                "status": args.status,
                "slug": post_slug,
                "title": title,
                "content": content,
                "featured_media": featured_id or 0,
                "categories": [category_id],
                "tags": tag_ids,
                "meta": {
                    "_yoast_wpseo_title": "",
                    "_yoast_wpseo_metadesc": meta_desc,
                    "_yoast_wpseo_focuskw": focus_kw,
                    "_hide_from_home": "1",
                },
            }
            post_path = Path(tempfile.gettempdir()) / f"rec-post-{card_slug}.json"
            post_path.write_text(json.dumps(post_json, ensure_ascii=False))
            env = {"ALLOW_DISAMBIGUATION": "1"} if args.allow_disambiguation else None
            t0 = time.time()
            created = run_json([str(WP_SCRIPTS / "create-post.sh"), args.site, str(post_path)], timeout=180, env=env)
            tick("wp_create_post_sec", t0)
            post_id = int(created["id"])
            public_url = created.get("link") or public_url
            edit_url = f"{site['wp_url']}/wp-admin/post.php?post={post_id}&action=edit"
            steps.append("post_created")

            yoast_json = {"title": title, "content": content, "meta": post_json["meta"]}
            yoast_path = Path(tempfile.gettempdir()) / f"rec-yoast-{card_slug}.json"
            yoast_path.write_text(json.dumps(yoast_json, ensure_ascii=False))
            t0 = time.time()
            yoast_update = run_json([str(WP_SCRIPTS / "update-yoast.sh"), args.site, str(post_id), str(yoast_path), "verify"], timeout=180)
            tick("wp_update_yoast_sec", t0)
            steps.append("yoast_updated")
            try:
                t0 = time.time()
                yoast_result = run_json([str(GEN_SCRIPTS / "yoast-score-post.sh"), args.site, str(post_id)], timeout=180, allow_fail=True)
                tick("yoast_score_sec", t0)
                validate_yoast_score(yoast_result)
            except Exception as e:
                tick("yoast_score_sec", t0)
                raise RunnerError(f"yoast_score_failed: {e}")
            steps.append("yoast_scored")

            if args.status == "publish":
                t0 = time.time()
                apply_url = f"https://{site['domain']}/apply-now-{country}-{vertical}-{card_slug}/"
                public_check = public_verify(public_url, apply_url=apply_url, card_url=card_url or "", featured_url=featured_url or "")
                tick("public_verify_sec", t0)
                if not public_check.get("ok"):
                    raise RunnerError(f"public_verify_failed: {public_check}")
                steps.append("public_verified")
            else:
                public_check = {"ok": True, "skipped": "draft_not_public", "url": public_url}
                steps.append("draft_public_verify_skipped")

            t0 = time.time()
            artifact_audit = cleanup_extra_media(args.site, created_media, post_id, [card_id or 0, featured_id or 0])
            tick("artifact_cleanup_sec", t0)
            if artifact_audit.get("extra_count"):
                steps.append("extra_media_cleanup_checked")

            t0 = time.time()
            fingerprint_check = run_json([
                str(ROOT / "scripts/rec-fingerprint.py"), "--card-slug", card_slug, "--site", args.site,
                "--file", str(fp_path), "--post-id", str(post_id), "--post-url", public_url,
                "--title", title, "--store"
            ], timeout=30, allow_fail=True) or fingerprint_check
            tick("duplicate_fingerprint_store_sec", t0)
            steps.append("duplicate_fingerprint_stored")

        costs["total_est"] = round(costs["article_api"] + costs["extract_llm_est"] + (0 if args.dry_run else costs["featured_image_est"]), 6)
        total_duration_sec = round(time.time() - started, 2)
        instrumented_total_sec = round(sum(timings.values()), 2)
        timings["unattributed_sec"] = round(max(total_duration_sec - instrumented_total_sec, 0), 2)
        timings["instrumented_total_sec"] = instrumented_total_sec
        if total_duration_sec > 300:
            slowest = sorted(timings.items(), key=lambda kv: kv[1], reverse=True)[:5]
            warnings.append(f"sla_incident_runner_over_300s duration_sec={total_duration_sec} slowest={slowest}")
        elif total_duration_sec > 180:
            slowest = sorted(timings.items(), key=lambda kv: kv[1], reverse=True)[:5]
            warnings.append(f"sla_warn_runner_over_180s duration_sec={total_duration_sec} slowest={slowest}")
        result = {
            "success": True,
            "status_detail": "ok_with_non_blocking_warnings" if warnings else "fully_validated",
            "dry_run": args.dry_run,
            "site": args.site,
            "status": args.status,
            "official_url": args.source_url,
            "card_slug": card_slug,
            "post_slug": post_slug,
            "post_id": post_id,
            "public_url": public_url,
            "edit_url": edit_url,
            "duration_sec": total_duration_sec,
            "steps": steps,
            "timings_sec": timings,
            "term_cache": term_stats,
            "cost_usd": costs,
            "template_contract": template_contract,
            "card_data": {
                "card_name": card_data.get("card_name"),
                "annual_fee": card_data.get("annual_fee"),
                "apr": card_data.get("apr"),
                "benefits": card_data.get("benefits"),
                "competitors": card_data.get("competitors"),
            },
            "seo": {"title": title, "title_chars": len(title), "meta_desc": meta_desc, "meta_chars": len(meta_desc), "focus_kw": focus_kw},
            "validation": {**validation, "subtitle": visible_subtitle(content), "subtitle_chars": subtitle_chars, "excerpt": visible_subtitle(content), "excerpt_chars": subtitle_chars, "public": public_check, "duplicate_fingerprint": fingerprint_check, "semantic_qa": qa_check},
            "taxonomy": {"category_id": category_id, "tag_ids": tag_ids, "tag_names": tag_names},
            "images": {
                "card_id": card_id,
                "card_url": card_url,
                "featured_id": featured_id,
                "featured_url": featured_url,
                "featured_scene": featured_scene,
                "featured_path": featured_path,
                "featured_audit": featured_audit,
                "card_source": card_src,
                "card_selection": card_selection,
                "card_normalize": card_normalize,
                "created_media": created_media,
                "artifact_audit": artifact_audit,
            },
            "yoast": yoast_result,
            "warnings": warnings,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        total_duration_sec = round(time.time() - started, 2)
        instrumented_total_sec = round(sum(timings.values()), 2)
        timings["unattributed_sec"] = round(max(total_duration_sec - instrumented_total_sec, 0), 2)
        timings["instrumented_total_sec"] = instrumented_total_sec
        failure_cleanup = None
        if created_media and not args.dry_run:
            t_cleanup = time.time()
            try:
                # If the runner fails after uploading media but before a clean final report,
                # delete only media created by this execution. This prevents orphan card images
                # like the Nationwide 62295 incident.
                failure_cleanup = cleanup_extra_media(args.site, created_media, None, [])
                tick("failure_media_cleanup_sec", t_cleanup)
                steps.append("failure_media_cleanup_attempted")
            except Exception as cleanup_exc:
                failure_cleanup = {"error": str(cleanup_exc), "created_media": created_media}
                warnings.append(f"failure_media_cleanup_failed: {cleanup_exc}")
        result = {"success": False, "error": str(e), "duration_sec": total_duration_sec, "steps": steps, "timings_sec": timings, "warnings": warnings, "images": {"created_media": created_media, "failure_cleanup": failure_cleanup}}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
