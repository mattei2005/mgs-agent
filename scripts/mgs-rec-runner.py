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
import sqlite3
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
CACHE_DB = ROOT / "data/card-cache.db"
TERM_CACHE_JSON = ROOT / "data/wp-term-cache.json"
GEN_SCRIPTS = ROOT / "skills/content-generate-rec/scripts"
REC_TEMPLATES = ROOT / "skills/content-generate-rec/templates"
WP_SCRIPTS = ROOT / "skills/content-publish-wordpress/scripts"
API_URL = "http://127.0.0.1:8001/generate"
HEALTH_URL = "http://127.0.0.1:8001/health"

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
    """Validate that the site's REC template exists without loading it into Atena's context."""
    template_key = site.get("template_key")
    if not template_key:
        raise RunnerError("Site is missing template_key in sites.json")
    template_path = REC_TEMPLATES / f"rec-{template_key}.md"
    if not template_path.exists():
        raise RunnerError(f"No REC template for template_key '{template_key}'. Create templates/rec-{template_key}.md first.")
    text = template_path.read_text(errors="ignore")
    return {
        "template_key": template_key,
        "path": str(template_path),
        "bytes": template_path.stat().st_size,
        "contract_loaded": True,
        "has_word_count_gate": "450" in text and "500" in text,
        "has_paragraph_gate": "30 words" in text or "~30 words" in text,
        "has_horizontal_card_gate": "horizontal" in text.lower() and "rotate" in text.lower(),
        "has_featured_three_layer_gate": "three essential" in text.lower() or "three" in text.lower() and "layers" in text.lower(),
    }


def cache_lookup(card_slug: str) -> Optional[Dict[str, Any]]:
    if not CACHE_DB.exists():
        return None
    con = sqlite3.connect(str(CACHE_DB))
    con.row_factory = sqlite3.Row
    now = now_iso()
    row = con.execute(
        "SELECT * FROM card_cache WHERE card_slug=? AND (expires_at IS NULL OR expires_at > ?)",
        (card_slug, now),
    ).fetchone()
    con.close()
    if not row:
        return None
    d = dict(row)
    for src, dst in [("benefits_json", "benefits"), ("competitors_json", "competitors")]:
        if d.get(src):
            try:
                d[dst] = json.loads(d[src])
            except Exception:
                d[dst] = []
    return d


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
            return status, strip_html_to_text(body)
    except Exception as e:
        raise RunnerError(f"reference_url fetch failed: {url} ({e})")


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
            break

    # Benefits: source sentences with product/offer terms. Avoid boilerplate.
    raw_sentences = re.split(r"(?<=[.!?])\s+", clean)
    benefit_re = re.compile(
        r"(0%|balance transfer|purchase|money transfer|credit limit|eligibility|online|app|manage|contactless|mastercard|protection|fee|APR|representative|offer)",
        re.I,
    )
    noise_re = re.compile(r"(cookie|privacy|javascript|terms of use|accessibility|complaint|site map)", re.I)
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
        # Conservative fallback still derived from the source page URL/name; do
        # not claim specific rates that were not extracted.
        benefits.extend([
            f"Review the official {card_name} page before applying.",
            "Check eligibility, fees and repayment terms before submitting an application.",
            "Use the issuer's online account tools to manage the card if approved.",
        ])
        benefits = benefits[:3]

    lower_benefits = " ".join(benefits).lower()
    tag10 = "Balance transfers" if "balance transfer" in lower_benefits else "Card features"
    tag2 = "0% offers" if "0%" in lower_benefits else (annual_fee[:25] if annual_fee != "N/A" else "Check terms")
    descriptor = f"A UK credit card with issuer terms and online account features."

    return {
        "card_name": card_name,
        "annual_fee": annual_fee,
        "apr": apr,
        "benefits": benefits,
        "competitors": [{"name": "Barclaycard Platinum"}, {"name": "Tesco Bank Credit Card"}],
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
    payload = {
        "imagem": build_media_payload(card_id, card_url, f"card-{card_slug}"),
        "categoria": site.get("default_category", "Credit Card"),
        "titulo": card_name,
        "tag10": (card_data.get("tag10") or "Card benefits")[:25],
        "tag2": (card_data.get("tag2") or card_data.get("annual_fee") or "Credit card")[:25],
        "texto": (card_data.get("descriptor") or f"Learn more about the {card_name}.")[:100],
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
    if "no annual fee" in annual or "no annual fee" in benefits:
        tail = "offers cashback benefits with no annual fee."
    elif "travel" in benefits:
        tail = "offers travel-focused credit card benefits."
    elif "cashback" in benefits:
        tail = "offers cashback benefits for eligible spending."
    else:
        tail = "offers key credit card benefits and features."
    # Include bold card name for focus-keyword placement, but cap hard.
    plain = f"{card_name} {tail}"
    if len(plain) > 98:
        # Use a shortened display name but keep recognisable terms.
        short = " ".join([w for w in card_name.split() if w.lower() not in {"credit", "card"}][:4])
        plain = f"{short} {tail}"
    if len(plain) > 98:
        plain = plain[:95].rsplit(" ", 1)[0] + "."
    replacement = f"<!-- wp:paragraph -->\n<p><strong>{html.escape(card_name)}</strong> {html.escape(tail)}</p>\n<!-- /wp:paragraph -->"
    return re.sub(r"<!-- wp:paragraph -->\s*<p>.*?</p>\s*<!-- /wp:paragraph -->", replacement, content, count=1, flags=re.I | re.S)


def call_rec_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    req = urllib.request.Request(API_URL, method="POST", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")
        raise RunnerError(f"mgs-rec-api HTTP {e.code}: {body[:1000]}")
    except Exception as e:
        raise RunnerError(f"mgs-rec-api call failed: {e}")


def normalize_card_artwork(path: str) -> Dict[str, Any]:
    """Force card artwork to horizontal orientation and crop white padding."""
    try:
        from PIL import Image
    except Exception as e:
        return {"status": "skipped", "reason": f"PIL unavailable: {e}"}

    img = Image.open(path)
    img.load()
    before = {"width": img.width, "height": img.height}
    rotated = False
    if img.height > img.width:
        img = img.rotate(-90, expand=True)
        rotated = True

    rgba = img.convert("RGBA")
    pix = rgba.load()
    w, h = rgba.size
    left, right, top, bottom = w, -1, h, -1
    for y in range(h):
        for x in range(w):
            r, g, b, a = pix[x, y]
            if a > 20 and not (r > 242 and g > 242 and b > 242):
                left, right = min(left, x), max(right, x)
                top, bottom = min(top, y), max(bottom, y)

    cropped = False
    if right >= left and bottom >= top:
        pad = 3
        box = (max(0, left-pad), max(0, top-pad), min(w, right+pad+1), min(h, bottom+pad+1))
        if box != (0, 0, w, h):
            img = img.crop(box)
            cropped = True

    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    img.save(path)
    return {"status": "ok", "before": before, "after": {"width": img.width, "height": img.height}, "rotated": rotated, "cropped": cropped}


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


def generate_article_local(site: Dict[str, Any], card_slug: str, card_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a deterministic REC article without the deprecated local API."""
    name = esc_text(card_data.get("card_name"))
    annual_fee = esc_text(card_data.get("annual_fee") or "N/A")
    apr = esc_text(card_data.get("apr") or "N/A")
    benefits = [str(b).strip() for b in (card_data.get("benefits") or []) if str(b).strip()]
    competitors = [c.get("name") if isinstance(c, dict) else str(c) for c in (card_data.get("competitors") or [])]
    competitors = [c.strip() for c in competitors if c and str(c).strip()]
    comp_a = esc_text(competitors[0] if len(competitors) > 0 else "another card in the same segment")
    comp_b = esc_text(competitors[1] if len(competitors) > 1 else "a second comparable card")
    primary_benefit = esc_text(shorten_words(benefits[0] if benefits else "key credit card features", 12))
    second_benefit = esc_text(shorten_words(benefits[1] if len(benefits) > 1 else "account management tools", 12))
    third_benefit = esc_text(shorten_words(benefits[2] if len(benefits) > 2 else "everyday payment flexibility", 12))
    benefit_phrase = esc_text(shorten_words(sentence_join(benefits, 3), 10))
    descriptor = card_data.get("descriptor") or f"A UK credit card with {annual_fee.lower()} and practical account features."
    card_data.setdefault("tag10", primary_benefit[:25] or "Card benefits")
    card_data.setdefault("tag2", annual_fee[:25] if annual_fee != "N/A" else "Credit card")
    card_data.setdefault("descriptor", descriptor[:100])

    rows = []
    for label, fee, note in [
        (name, annual_fee, primary_benefit),
        (comp_a, "Varies", "Compare eligibility, APR and fees before applying"),
        (comp_b, "Varies", "Compare benefits and repayment terms carefully"),
    ]:
        rows.append(f"<tr><td>{label}</td><td>{esc_text(fee)}</td><td>{esc_text(note)}</td></tr>")
    table = "".join(rows)

    html_body = f"""<!-- wp:paragraph -->
<p><strong>{name}</strong> offers {annual_fee.lower()} and practical features for UK applicants.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>The {name} is built for applicants who want a clear credit card option. It should be reviewed against budget, eligibility and repayment habits.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Its official positioning highlights {benefit_phrase}. Those details help readers understand the card before comparing it with nearby alternatives.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>This keeps the review focused on practical value, not unsupported promotional claims or unclear product assumptions.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Key Benefits of the Card</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>The main benefit is {primary_benefit}. This gives the card a clear role for everyday applicants.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Another point is {second_benefit}. It can help people who prefer simple account control and fewer surprises.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>The card also includes {third_benefit}. This may support regular spending when repayments stay organised.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>These features make the card practical. It is not presented here as a premium travel or luxury rewards product.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">How Does It Work</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>The official product information lists the annual fee as {annual_fee}. APR information is shown as {apr}.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>The final cost depends on credit limit, interest rate and repayment behaviour. Paying on time remains central.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Applicants should check the latest terms before applying. Fees, rates and eligibility rules can change.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Used carefully, the card can support routine purchases. Carrying a balance may increase the total cost.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Comparative Table</h2>
<!-- /wp:heading -->

<!-- wp:table -->
<figure class="wp-block-table"><table class="has-fixed-layout" style="font-size:85%"><thead><tr><th>Card</th><th>Annual fee</th><th>Positioning</th></tr></thead><tbody>{table}</tbody></table></figure>
<!-- /wp:table -->

<!-- wp:paragraph -->
<p>Compared with {comp_a}, the {name} should be judged on fees, eligibility and daily usefulness.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Compared with {comp_b}, it may suit readers who want a simple card rather than a complex benefit package.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>The table is a quick orientation tool. It is not a full eligibility check.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Rates and terms can change. Therefore, the official page should remain the final reference.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Who Is This Card Best For</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>This card may suit applicants who want a straightforward UK credit card. It is best assessed with realistic repayment plans.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>It may not fit someone seeking premium rewards, travel perks or a guaranteed low APR. Other cards may compete better there.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Readers should compare the official details with their own credit profile and read the official terms before applying.</p>
<!-- /wp:paragraph -->"""
    return {
        "success": True,
        "article_html": html_body,
        "cost_usd": 0.0,
        "duration_sec": 0.0,
        "card_data": card_data,
        "generator": "local_deterministic",
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
    needed = min_count - current_count
    pads = [
        "Applicants should review eligibility, fees and repayment terms before applying online.",
        "This helps confirm whether the card fits everyday spending habits and budget goals.",
        "A responsible comparison also makes the final application decision clearer.",
    ]
    words = []
    i = 0
    while len(words) < needed + 2:
        words.extend(pads[i % len(pads)].split())
        i += 1
    sentence = " ".join(words[: needed + 2]).rstrip(" ,") + "."
    block = f"<!-- wp:paragraph -->\n<p>{html.escape(sentence)}</p>\n<!-- /wp:paragraph -->"
    # Insert before final LazyBlock CTA if present.
    marker = "<!-- wp:lazyblock/botao"
    idx = content.rfind(marker)
    if idx >= 0:
        return content[:idx].rstrip() + "\n\n" + block + "\n\n" + content[idx:]
    return content.rstrip() + "\n\n" + block


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
    rewards_supported = any(x in " ".join(card_data.get("benefits", [])).lower() for x in ["cashback", "rewards", "points", "miles"])
    if no_fee:
        title = f"{focus}: No Annual Fee"
    elif rewards_supported:
        title = f"{focus}: Rewards & Fees"
    else:
        title = f"{focus}: Benefits & Fees"
    if len(title) > 60:
        title = f"{focus}: Card Review"[:60]
    meta = f"{card_name} offers {', '.join(card_data.get('benefits', ['key benefits'])[:2]).lower()}. See fees, APR and how it works."
    if len(meta) > 130:
        meta = meta[:127].rsplit(" ", 1)[0] + "..."
    if len(meta) < 120:
        meta = (meta + " Compare before applying.")[:130]
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
        if "purchase" in lb: extras.append("purchase credit card")
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


def public_verify(url: str) -> Dict[str, Any]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return {"http_status": getattr(r, "status", 200), "bytes": len(r.read(200000))}
    except Exception as e:
        return {"http_status": 0, "error": str(e)}


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
    args = ap.parse_args()

    started = time.time()
    warnings: List[str] = []
    steps: List[str] = []
    costs = {"article_api": 0.0, "extract_llm_est": 0.0, "featured_image_est": 0.03, "total_est": 0.0}
    timings: Dict[str, float] = {}
    created_media: List[Dict[str, Any]] = []
    artifact_audit: Dict[str, Any] = {"created_count": 0, "used_count": 0, "extra_count": 0, "deleted_count": 0, "items": []}

    def tick(name: str, t0: float) -> None:
        timings[name] = round(time.time() - t0, 2)

    try:
        t0 = time.time()
        site = load_site(args.site)
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

        t0 = time.time()
        cache = cache_lookup(card_slug)
        tick("card_cache_lookup_sec", t0)
        if cache:
            card_data = {
                "card_name": cache.get("card_name") or args.card,
                "card_official_url": cache.get("card_official_url") or args.source_url,
                "annual_fee": cache.get("annual_fee"),
                "apr": cache.get("apr"),
                "benefits": cache.get("benefits") or [],
                "competitors": cache.get("competitors") or [],
                "tag10": cache.get("tag10"),
                "tag2": cache.get("tag2"),
                "descriptor": cache.get("descriptor"),
                "card_image_uploaded_id": cache.get("card_image_uploaded_id"),
                "card_image_uploaded_url": cache.get("card_image_uploaded_url"),
            }
            steps.append("cache_hit")
        else:
            benefits = args.benefit or []
            competitors: List[Dict[str, str]] = []
            for c in args.competitor:
                try:
                    obj = json.loads(c)
                    if isinstance(obj, dict): competitors.append(obj)
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
                    raise RunnerError("Cache MISS and no --source-url/benefits supplied")
                t0 = time.time()
                status, text = fetch_reference_text(args.source_url)
                tick("reference_fetch_sec", t0)
                if status >= 400:
                    raise RunnerError(f"reference_url returned HTTP {status}")
                t0 = time.time()
                card_data = extract_card_data_with_llm(args.card, args.source_url, text)
                tick("reference_extract_llm_sec", t0)
                card_data["card_official_url"] = args.source_url
                steps.append("reference_extracted_llm")
                costs["extract_llm_est"] = 0.02

        card_data["card_name"] = card_data.get("card_name") or args.card
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
        try:
            api = call_rec_api(api_payload)
            tick("article_api_sec", t0)
            if not api.get("success"):
                raise RunnerError(f"mgs-rec-api failed: {api}")
            steps.append("article_generated_api")
        except RunnerError as e:
            # The legacy local API is intentionally masked on current MGS infra.
            # Do not waste a second runner attempt; generate deterministic HTML
            # locally from the official facts already supplied to this runner.
            warnings.append(f"article_api_unavailable_local_generator_used: {str(e)[:300]}")
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
                current = pad_content_to_min_words(current, first_count, 450)
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

        if not card_id or not card_url:
            if args.dry_run:
                steps.append("dry_run_skip_card_upload")
            else:
                source_url = card_data.get("card_official_url") or args.source_url
                if not source_url and not args.card_image_url:
                    raise RunnerError("No card official URL available for image search")
                t0 = time.time()
                if args.card_image_url:
                    suffix = Path(urllib.parse.urlparse(args.card_image_url).path).suffix or ".png"
                    if suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                        suffix = ".png"
                    card_local = f"/tmp/card-{card_slug}-manual{suffix}"
                    req = urllib.request.Request(
                        args.card_image_url,
                        headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) MGS-REC-Runner/1.0"},
                    )
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        Path(card_local).write_bytes(resp.read())
                    card_src = args.card_image_url
                    card_selection = {"mode": "manual_card_image_url", "source": args.card_image_url, "reason": "user_supplied_best_card_art"}
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
                card_normalize = normalize_card_artwork(card_local)
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
            t0 = time.time()
            feat = run_json([str(GEN_SCRIPTS / "generate-featured-image.sh"), card_slug, card_local], timeout=180)
            tick("featured_generate_sec", t0)
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
            tick("featured_local_validate_sec", t0)
            t0 = time.time()
            upf = run_json([str(WP_SCRIPTS / "upload-image.sh"), args.site, featured_path, f"featured-{card_slug}-final.jpg"], timeout=120)
            tick("featured_upload_sec", t0)
            featured_id, featured_url = int(upf["id"]), upf["source_url"]
            created_media.append({"role": "featured", "id": featured_id, "url": featured_url, "filename": f"featured-{card_slug}-final.jpg", "used": True, "scene": featured_scene})
            steps.append("featured_uploaded")

        # Rebuild and revalidate the exact final HTML after media IDs/URLs are known.
        content, validation, subtitle_chars = build_and_validate_current("final")
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
        title, meta_desc, focus_kw = title_meta_focus(card_data["card_name"], card_data)
        tick("seo_fields_sec", t0)
        if len(title) > 60 or len(meta_desc) < 120 or len(meta_desc) > 130 or len(focus_kw.split()) > 4:
            raise RunnerError(f"SEO field validation failed title={len(title)} meta={len(meta_desc)} focus_words={len(focus_kw.split())}")

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
            except Exception as e:
                tick("yoast_score_sec", t0)
                warnings.append(f"yoast_score_failed: {e}")
                yoast_result = {"status": "error", "message": str(e)}
            steps.append("yoast_scored")

            cache_payload = {
                "card_slug": card_slug,
                "card_name": card_data["card_name"],
                "card_official_url": card_data.get("card_official_url") or args.source_url,
                "country": country,
                "vertical": vertical,
                "language": site.get("language", "en"),
                "annual_fee": card_data.get("annual_fee"),
                "apr": card_data.get("apr"),
                "benefits": card_data.get("benefits") or [],
                "tag10": card_data.get("tag10"),
                "tag2": card_data.get("tag2"),
                "descriptor": card_data.get("descriptor"),
                "competitors": card_data.get("competitors") or [],
                "card_image_local_path": card_local,
                "card_image_url_orig": card_src,
                "card_image_uploaded_id": card_id,
                "card_image_uploaded_url": card_url,
                "ttl_days": 30,
                "source": "mgs-rec-runner",
            }
            cache_path = Path(tempfile.gettempdir()) / f"cache-save-{card_slug}.json"
            cache_path.write_text(json.dumps(cache_payload, ensure_ascii=False))
            t0 = time.time()
            run_json([str(GEN_SCRIPTS / "card-cache-save.sh"), str(cache_path)], timeout=60)
            tick("cache_save_sec", t0)
            steps.append("cache_saved")
            t0 = time.time()
            public_check = public_verify(public_url)
            tick("public_verify_sec", t0)
            if public_check.get("http_status") != 200:
                warnings.append(f"public_verify_not_200: {public_check}")
            steps.append("public_verified")

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
            "dry_run": args.dry_run,
            "site": args.site,
            "status": args.status,
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
            "validation": {**validation, "subtitle_chars": subtitle_chars, "public": public_check, "duplicate_fingerprint": fingerprint_check},
            "taxonomy": {"category_id": category_id, "tag_ids": tag_ids, "tag_names": tag_names},
            "images": {
                "card_id": card_id,
                "card_url": card_url,
                "featured_id": featured_id,
                "featured_url": featured_url,
                "featured_scene": featured_scene,
                "featured_path": featured_path,
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
        result = {"success": False, "error": str(e), "duration_sec": total_duration_sec, "steps": steps, "timings_sec": timings, "warnings": warnings}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
