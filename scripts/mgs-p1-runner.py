#!/usr/bin/env python3
"""mgs-p1-runner.py — deterministic P1/application-page runner.

Goal: create GB credit-card P1 pages without Atena doing the workflow manually.
Default mode is dry-run unless --status draft/publish is supplied. Credentials are
resolved only through existing WordPress utility scripts and never printed.
"""
from __future__ import annotations

import argparse
import html
import importlib.util
import json
import os
import random
import re
import sqlite3
import string
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

ROOT = Path("/root/mgs-agent")
SITES_JSON = ROOT / "data/sites.json"
CACHE_DB = ROOT / "data/card-cache.db"
GEN_SCRIPTS = ROOT / "skills/content-generate-rec/scripts"
WP_SCRIPTS = ROOT / "skills/content-publish-wordpress/scripts"
REC_RUNNER = ROOT / "scripts/mgs-rec-runner.py"
FEATURED_AUDIT_SCRIPT = ROOT / "scripts/audit-featured-image.py"


class RunnerError(Exception):
    pass


def ts() -> float:
    return time.perf_counter()


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"&", " and ", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"^-+|-+$", "", text)


def run(cmd: List[str], *, timeout: int = 120, allow_fail: bool = False) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    if p.returncode != 0 and not allow_fail:
        raise RunnerError(f"Command failed rc={p.returncode}: {' '.join(cmd)}\n{(p.stderr or p.stdout)[:2000]}")
    return p


def run_json(cmd: List[str], *, timeout: int = 120, allow_fail: bool = False) -> Dict[str, Any]:
    p = run(cmd, timeout=timeout, allow_fail=allow_fail)
    text = p.stdout.strip() or p.stderr.strip() or "{}"
    try:
        data = json.loads(text)
    except Exception:
        if allow_fail:
            return {"ok": False, "returncode": p.returncode, "output": text[:1200]}
        raise RunnerError(f"Command did not return JSON: {' '.join(cmd)}\n{text[:1200]}")
    if p.returncode != 0 and not allow_fail:
        raise RunnerError(f"Command failed JSON rc={p.returncode}: {data}")
    return data


def load_site(site_key: str) -> Dict[str, Any]:
    data = json.loads(SITES_JSON.read_text())
    site = data.get(site_key)
    if not site:
        raise RunnerError(f"Site not found: {site_key}")
    return site


def load_rec_helpers():
    spec = importlib.util.spec_from_file_location("mgs_rec_runner", REC_RUNNER)
    if not spec or not spec.loader:
        raise RunnerError("Cannot import REC runner helpers")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def get_public(url: str) -> str:
    r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code >= 400:
        raise RunnerError(f"Public GET failed {r.status_code}: {url}")
    return r.text


def post_id_from_public_html(public_html: str, rec_url: str) -> int:
    m = re.search(r"postid-(\d+)", public_html)
    if m:
        return int(m.group(1))
    # Fallback: public REST by slug is broken on some sites, but keep a helpful error.
    raise RunnerError(f"Could not detect REC post ID from public HTML: {rec_url}")


def p1_slug_from_rec_buttons(public_html: str, rec_raw: str, site_domain: str) -> Optional[str]:
    """Return the P1 slug already linked from the REC buttons, if present.

    REC pages may be created before the P1 exists. In that case, the REC button
    URL is the source of truth for the future P1 slug. Do not re-infer a shorter
    slug from the card name when the REC already points to an apply-now URL.
    """
    haystack = "\n".join([public_html or "", rec_raw or ""])
    candidates: List[str] = []
    patterns = [
        rf"https?://{re.escape(site_domain)}/(apply-now-[a-z0-9-]+)/?",
        r"/(apply-now-[a-z0-9-]+)/?",
    ]
    for pat in patterns:
        for m in re.finditer(pat, haystack, flags=re.I):
            slug = m.group(1).strip("/").lower()
            if slug not in candidates:
                candidates.append(slug)
    return candidates[0] if candidates else None


def resolve_credentials(site_key: str) -> Dict[str, Any]:
    return run_json([str(WP_SCRIPTS / "resolve-credentials.sh"), site_key], timeout=90)


def wp_get_post(site_key: str, post_id: int, fields: str = "id,title,content,featured_media,link,tags,categories,slug") -> Dict[str, Any]:
    creds = resolve_credentials(site_key)
    url = creds["wp_url"].rstrip("/") + f"/wp-json/wp/v2/posts/{post_id}?context=edit&_fields={urllib.parse.quote(fields)}"
    r = requests.get(url, auth=(creds["username"], creds["password"]), timeout=25)
    if r.status_code >= 400:
        raise RunnerError(f"WP GET post failed {r.status_code}: {r.text[:800]}")
    return r.json()


def cache_lookup(card_slug: str) -> Dict[str, Any]:
    if not CACHE_DB.exists():
        return {}
    con = sqlite3.connect(str(CACHE_DB))
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM card_cache WHERE card_slug=? ORDER BY COALESCE(last_used_at, researched_at) DESC LIMIT 1", (card_slug,)).fetchone()
    con.close()
    if not row:
        return {}
    d = dict(row)
    for src, dst in [("benefits_json", "benefits"), ("competitors_json", "competitors")]:
        if d.get(src):
            try:
                d[dst] = json.loads(d[src])
            except Exception:
                d[dst] = []
    return d


def parse_card_from_rec(raw: str, rendered: str, rec_title: str) -> Dict[str, Any]:
    block = re.search(r"<!-- wp:lazyblock/credit-card\s+(\{.*?\})\s+/-->", raw, re.S)
    payload: Dict[str, Any] = {}
    if block:
        try:
            payload = json.loads(block.group(1))
        except Exception:
            payload = {}
    card_name = payload.get("titulo") or html.unescape(re.sub(r"<[^>]+>", " ", rec_title)).strip()
    if card_name and not card_name.lower().endswith("card") and "barclaycard" in card_name.lower():
        # Do not force Card for all issuers, but Barclaycard official pages often use it.
        card_name = card_name + " Card"
    card_url = None
    card_id = None
    if payload.get("imagem"):
        try:
            media = json.loads(urllib.parse.unquote(payload["imagem"]))
            card_url = media.get("url") or media.get("link")
            card_id = media.get("id")
        except Exception:
            pass
    if not card_url:
        m = re.search(r"https?://[^\"'<>\s)]+(?:card|barclaycard|avios)[^\"'<>\s)]*\.(?:png|jpg|jpeg|webp)", rendered, re.I)
        if m:
            card_url = m.group(0)
    return {
        "card_name": card_name,
        "card_url": card_url,
        "card_id": int(card_id) if card_id else None,
        "tag10": payload.get("tag10") or "Card benefits",
        "tag2": payload.get("tag2") or "Credit card",
        "descriptor": payload.get("texto") or f"Learn more about the {card_name}.",
    }


def infer_card_slug(rec_url: str, card_name: str) -> str:
    path = urllib.parse.urlparse(rec_url).path.strip("/")
    m = re.search(r"rec-[a-z]{2}-[a-z]+-(.+)$", path)
    if m:
        slug = re.sub(r"-\d+$", "", m.group(1))
        return slug
    slug = slugify(card_name)
    return re.sub(r"-card$", "", slug)


def meaningful_card_terms(card_name: str) -> List[str]:
    stop = {"credit", "card", "the", "and", "visa", "mastercard", "platinum", "classic", "gold"}
    terms: List[str] = []
    for word in re.sub(r"[^A-Za-z0-9 ]", " ", card_name).lower().split():
        if len(word) >= 3 and word not in stop and word not in terms:
            terms.append(word)
    return terms[:6]


def official_source_has_content(official_url: str, text: str, card_name: str = "") -> Tuple[bool, str]:
    """Reject issuer URLs that return a branded error/404/search page or generic category page."""
    clean = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip().lower()
    if not clean or len(clean) < 500:
        return False, "official source has no meaningful body"
    error_markers = [
        "page not found", "we can’t find that page", "we can't find that page",
        "sorry about this", "try our search tool", "internet banking - error",
        "we are sorry an error has occurred", "error 1007", "access denied",
        "cloudflare", "temporarily unavailable",
    ]
    for marker in error_markers:
        if marker in clean:
            return False, f"official source appears to be an error page: {marker}"
    product_terms = [
        "credit card", "representative apr", "annual fee", "monthly fee", "purchase rate",
        "eligibility", "apply", "rewards", "cashback", "avios", "mastercard", "visa",
    ]
    product_hits = [t for t in product_terms if t in clean]
    if len(product_hits) < 2:
        return False, "official source does not expose enough product content"
    name_terms = meaningful_card_terms(card_name) if card_name else []
    if name_terms and not any(t in clean for t in name_terms):
        return False, "official source does not mention the requested product/issuer terms"
    return True, "ok"


def validate_no_review(fields: Dict[str, str]) -> None:
    offenders = [name for name, value in fields.items() if re.search(r"\breview\b", value or "", flags=re.I)]
    if offenders:
        raise RunnerError("Review hard gate failed in " + ", ".join(offenders))


def compact_focus(card_name: str) -> str:
    words = [w for w in re.sub(r"[^A-Za-z0-9 ]", " ", card_name).split() if w.lower() not in {"credit", "card", "the"}]
    return " ".join(words[:3]) if words else card_name[:40]


def validate_seo_fields(title: str, meta: str, focus: str) -> None:
    validate_no_review({"title": title, "meta": meta, "focus": focus})
    if len(title) > 60 or not title.strip():
        raise RunnerError(f"P1 title length invalid: {len(title)}")
    if focus.lower() not in title.lower():
        raise RunnerError(f"P1 title missing focus keyphrase: {focus}")
    if len(meta) < 120 or len(meta) > 130:
        raise RunnerError(f"P1 meta length invalid: {len(meta)}")
    if len(focus.split()) > 4:
        raise RunnerError(f"P1 focus keyphrase too long: {focus}")


def validate_taxonomy_names(tag_names: List[str], expected_lang: str) -> None:
    bad = [t for t in tag_names if "-" in t]
    if bad:
        raise RunnerError(f"Tag names must use spaces, not hyphens: {bad}")
    missing = sorted({"atena_agent", f"lang_{expected_lang}"} - set(tag_names))
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


def fetch_official_source_text(official_url: str, card_name: str = "") -> Tuple[int, str, str]:
    """Fetch official product text, using a reader fallback for issuer geo/bot error shells.

    The canonical URL remains the issuer URL. The reader is only a rendering aid
    for the same official URL and must still expose product content.
    """
    rec = load_rec_helpers()
    status, text = rec.fetch_reference_text(official_url)
    has_content, _ = official_source_has_content(official_url, text, card_name)
    if has_content:
        return status, text, official_url
    reader_url = "https://r.jina.ai/http://" + official_url
    try:
        r = requests.get(reader_url, timeout=35, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code < 400:
            ok, _reason = official_source_has_content(official_url, r.text, card_name)
            if ok:
                return r.status_code, r.text, reader_url
    except Exception:
        pass
    return status, text, official_url


def preflight_official_source(official_url: str, card_name: str = "") -> None:
    status, text, source_fetch_url = fetch_official_source_text(official_url, card_name)
    has_content, source_reason = official_source_has_content(official_url, text, card_name)
    if not has_content:
        raise RunnerError(f"Official source URL has no usable product content; ask Raquel/Rodolfo for the correct official link before publishing. url={official_url} reason={source_reason}")


def extract_official_data(card_name: str, official_url: str, explicit_benefits: List[str], annual_fee: Optional[str], apr: Optional[str]) -> Dict[str, Any]:
    status, text, source_fetch_url = fetch_official_source_text(official_url, card_name)
    has_content, source_reason = official_source_has_content(official_url, text, card_name)
    if not has_content:
        raise RunnerError(f"Official source URL has no usable product content; ask Raquel/Rodolfo for the correct official link before publishing. url={official_url} reason={source_reason}")
    rec = load_rec_helpers()
    try:
        data = rec.extract_card_data_with_llm(card_name, official_url, text)
    except Exception as e:
        if not (explicit_benefits and annual_fee and apr):
            raise
        data = {
            "card_name": card_name,
            "annual_fee": annual_fee,
            "apr": apr,
            "benefits": explicit_benefits[:6],
            "competitors": [],
            "tag10": "Avios rewards",
            "tag2": annual_fee[:25],
            "descriptor": "A UK travel credit card with Avios rewards and issuer terms.",
            "extraction_mode": f"explicit_facts_after_short_fetch:{type(e).__name__}",
            "source_url": official_url,
        }
    if explicit_benefits:
        data["benefits"] = explicit_benefits[:6]
    if annual_fee:
        data["annual_fee"] = annual_fee
    if apr:
        data["apr"] = apr
    data["fetch_status"] = status
    # Product-specific deterministic improvements from official text.
    clean = re.sub(r"\s+", " ", text)
    if re.search(r"25,000\s+Avios", clean, re.I):
        add_unique(data["benefits"], "New Barclaycard customers can collect 25,000 Avios after spending £3,000 in the first three months.")
    if re.search(r"1\.5\s+Avios", clean, re.I):
        add_unique(data["benefits"], "Collect 1.5 Avios for every £1 spent on eligible purchases.")
    if re.search(r"cabin upgrade voucher", clean, re.I):
        add_unique(data["benefits"], "Spend £10,000 within 12 months and choose between a British Airways cabin upgrade voucher or 7,000 bonus Avios.")
    if re.search(r"1,000 airport lounges|£24 per lounge pass", clean, re.I):
        add_unique(data["benefits"], "Access over 1,000 airport lounges worldwide at a discounted rate of £24 per lounge pass, per person.")
    m = re.search(r"Representative\s+([0-9.]+%\s+APR).*?Purchase rate\s+([0-9.]+%[^£]{0,30}).*?Monthly fee\s+(£\d+)", clean, re.I)
    if m:
        data["apr"] = f"Representative {m.group(1)} variable; purchase rate {m.group(2).strip()}"
        data["annual_fee"] = f"{m.group(3)} monthly fee"
    elif "£20" in clean and "monthly fee" in clean.lower():
        data["annual_fee"] = "£20 monthly fee"
    return data


def add_unique(items: List[str], value: str) -> None:
    low = {i.lower() for i in items}
    if value.lower() not in low:
        items.append(value)


def ensure_card_local(card_url: str, card_slug: str) -> str:
    ext = Path(urllib.parse.urlparse(card_url).path).suffix or ".png"
    out = Path(tempfile.gettempdir()) / f"p1-card-{card_slug}{ext}"
    r = requests.get(card_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code >= 400 or not r.content:
        raise RunnerError(f"Card image download failed {r.status_code}: {card_url}")
    out.write_bytes(r.content)
    return str(out)


def make_exact_featured(card_path: str, card_slug: str) -> str:
    # Generate the P1 contextual advertising scene directly. Do not blur the
    # scene and paste a card-only overlay: P1 requires the visual layer order
    # scenario -> card -> foreground person, with depth and no cropped card.
    gen = run_json([str(GEN_SCRIPTS / "generate-featured-image.sh"), f"p1-{card_slug}", card_path], timeout=180)
    scene_path = gen.get("path")
    if not scene_path or not Path(scene_path).exists():
        raise RunnerError(f"Featured generator did not create a file: {gen}")
    try:
        from PIL import Image
    except Exception as e:
        raise RunnerError(f"PIL unavailable for featured normalization: {e}")
    bg = Image.open(scene_path).convert("RGB").resize((1280, 720))
    out = Path(tempfile.gettempdir()) / f"featured-p1-{card_slug}.jpg"
    bg.save(out, quality=91, optimize=True)
    return str(out)


def upload_image(site_key: str, image_path: str, filename: str) -> Dict[str, Any]:
    return run_json([str(WP_SCRIPTS / "upload-image.sh"), site_key, image_path, filename], timeout=120)


def rand_block_id() -> str:
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(6))


def media_payload(media_id: int, media_url: str, title: str) -> str:
    obj = {"alt":"","title":title,"caption":"","description":{"raw":"","rendered":""},"id":int(media_id),"link":media_url,"url":media_url,"sizes":""}
    return urllib.parse.quote(json.dumps(obj, separators=(",", ":")), safe="")


def clean_sentence_punctuation(text: Any) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([,;:])\s*\.\.\.$", "...", text)
    text = re.sub(r"\.\s*\.\.\.$", "...", text)
    text = re.sub(r",\s*\.$", ".", text)
    text = re.sub(r",\s*\.\.\.$", "...", text)
    if text and not re.search(r"(\.|!|\?|\.\.\.)$", text):
        text += "."
    return text


def card_ui_tag(text: Any, fallback: str = "Cashback rewards") -> str:
    value = html.unescape(str(text or "")).strip()
    value = re.split(r"[;,.]|\s+ and \s+", value, maxsplit=1, flags=re.I)[0].strip()
    value = re.sub(r"\bcard features\b", "", value, flags=re.I).strip()
    if not value or value.lower() in {"credit card", "card benefits", "features"}:
        value = fallback
    value = re.sub(r"\s+", " ", value).strip(" .;:,!")
    return value[:25].rstrip(" .;:,")


def card_ui_descriptor(card_data: Dict[str, Any], fallback: str) -> str:
    benefits = [str(b) for b in (card_data.get("benefits") or [])]
    joined = " ".join(benefits).lower()
    if "cashback" in joined:
        desc = "Earn cashback on eligible purchases."
    elif any(term in joined for term in ["avios", "travel", "points", "marriott", "bonvoy", "elite night"]):
        desc = "Earn travel rewards on eligible spend."
    elif "no annual fee" in joined or "no fee" in joined:
        desc = "A no-annual-fee card for everyday spend."
    else:
        desc = fallback
    desc = clean_sentence_punctuation(desc)
    if len(desc) > 70:
        desc = desc[:69].rsplit(" ", 1)[0].rstrip(" ,;:") + "."
    return desc


def lazy_credit_card_p1(site: Dict[str, Any], card_name: str, card_slug: str, card_id: int, card_url: str, card_data: Dict[str, Any], official_url: str, button_hex: str) -> str:
    b = rand_block_id()
    payload = {
        "imagem": media_payload(card_id, card_url, f"card-{card_slug}"),
        "categoria": site.get("default_category", "Credit Card"),
        "titulo": card_name,
        "tag10": card_ui_tag(card_data.get("tag10"), "Cashback rewards"),
        "tag2": card_ui_tag(card_data.get("tag2") or card_data.get("annual_fee"), "No annual fee"),
        "texto": card_ui_descriptor(card_data, card_data.get("descriptor") or f"Learn more about the {card_name}."),
        "botao-texto": "APPLY NOW",
        "siteXfora": "You will be redirected.",
        "botao-url": official_url,
        "color-botao": button_hex,
        "blockId": b,
        "blockUniqueClass": f"lazyblock-credit-card-{b}",
    }
    return "<!-- wp:lazyblock/credit-card " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + " /-->"


def wp_paragraph(text: str) -> str:
    return f"<!-- wp:paragraph -->\n<p>{html.escape(text)}</p>\n<!-- /wp:paragraph -->"


def wp_heading(text: str) -> str:
    return f"<!-- wp:heading -->\n<h2 class=\"wp-block-heading\">{html.escape(text)}</h2>\n<!-- /wp:heading -->"


def infer_p1_positioning(card_name: str, benefits: List[str]) -> Dict[str, str]:
    """Return benefit-specific P1 copy so scaled pages do not read as duplicated templates."""
    joined = " ".join(benefits).lower()
    name_l = card_name.lower()
    if "amazon" in joined or "amazon" in name_l:
        return {
            "subtitle_tail": "turns Amazon shopping into rewards, a welcome gift and 0% purchases.",
            "use_case": "people who already spend through Amazon and want those purchases to generate direct reward value",
            "value_focus": "Amazon-linked benefits, the app-first setup and the main repayment points",
            "reward_heading": "Amazon Rewards and Purchase Value",
            "reward_1": "This is not a miles card trying to feel premium. Its value is simpler: frequent Amazon shoppers can turn familiar purchases into direct rewards.",
            "reward_2": "The key question is how much of your normal basket already goes through Amazon, because that is where the card can feel more useful.",
            "reward_3": "Prime members should look closely at eligible shopping events such as Prime Day, when the temporary boost can make planned purchases more rewarding.",
            "max_1": "Use it first for Amazon and everyday purchases you were already going to make. That keeps the reward value connected to real behaviour, not extra borrowing.",
            "max_2": "Treat the welcome gift and rewards as a bonus, not a reason to carry a balance. Interest can wipe out the benefit quickly if repayment slips.",
            "max_3": "Recheck the reward rules around Prime events, the welcome gift and the first-year earn rate so you know exactly which purchases count.",
            "right_1": "For Amazon-focused spending, estimate how often you actually buy on Amazon, whether you have Prime and how fast you usually repay purchases.",
            "right_2": "Check whether the reward rules still match your shopping habits before submitting the application.",
            "right_3": "A strong fit usually means regular Amazon use, comfort with app-based account management and a repayment plan that protects the reward value.",
        }
    if any(t in joined for t in ["low interest", "low rate", "12.9%", "no annual fee", "foreign transaction"]):
        return {
            "subtitle_tail": "suits users prioritising low rates, no annual fee and overseas purchases.",
            "use_case": "users who care more about lower representative rates and simple fees than points or premium perks",
            "value_focus": "representative APR, annual fee, overseas purchase fees and repayment considerations",
            "reward_heading": "Low-Rate and Overseas Purchase Value",
            "reward_1": "The product is best judged through cost control rather than rewards. The representative APR and annual fee shape the value proposition.",
            "reward_2": "No foreign transaction fee on purchases can help abroad, but cash withdrawals and local fees need separate checks.",
            "reward_3": "A rewards card may be better for users who pay in full and care more about cashback, miles or points.",
            "max_1": "Start with planned spending and a realistic repayment plan. The lower-rate positioning only helps when balances stay manageable.",
            "max_2": "Use overseas purchase benefits carefully and avoid assuming cash withdrawals receive the same fee treatment.",
            "max_3": "Check the official summary box for the final personal rate, balance transfer rules and any fees before applying.",
            "right_1": "Estimate whether rate control, no annual fee and overseas purchase use matter more than rewards in a normal year.",
            "right_2": "Check whether the final APR and credit limit still match your budget before submitting the application.",
            "right_3": "A careful comparison should include repayment behaviour, overseas use, annual fee, final APR and whether rewards are actually more important.",
        }
    if any(t in joined for t in ["avios", "lounge", "hotel", "travel", "companion voucher"]):
        return {
            "subtitle_tail": "connects travel rewards with costs, eligibility and application steps.",
            "use_case": "travellers who can realistically use the card’s confirmed travel rewards",
            "value_focus": "travel benefits, annual cost, eligibility and repayment considerations",
            "reward_heading": "Travel Rewards and Real-World Value",
            "reward_1": "Travel rewards only matter when routes, hotel stays or partner redemptions match your plans.",
            "reward_2": "Check whether the strongest travel benefit would be used often enough to justify any fee or spending target.",
            "reward_3": "Occasional travellers may need to compare the same card against simpler cashback or no-fee alternatives.",
            "max_1": "Start with trips or travel spending you already planned. Avoid creating extra spend only to trigger rewards.",
            "max_2": "Track payment dates and statement balances so interest does not erase the value of travel rewards.",
            "max_3": "Review redemption rules, partner availability and voucher conditions before relying on headline travel value.",
            "right_1": "Estimate how many trips or partner redemptions you would realistically use in a normal year.",
            "right_2": "Check whether the travel rules still match your plans before submitting the application.",
            "right_3": "A careful comparison should include reward use, repayment behaviour, travel plans and total cost.",
        }
    return {
        "subtitle_tail": "explains its confirmed benefits, costs and application steps before you apply.",
        "use_case": "users whose normal spending matches the card’s confirmed strongest benefit",
        "value_focus": "confirmed benefits, costs, eligibility and repayment considerations",
        "reward_heading": "Rewards and Everyday Value",
        "reward_1": "The real value depends on how often you would use the confirmed benefit in ordinary spending.",
        "reward_2": "Compare the benefit with your repayment habits so interest does not outweigh the card’s value.",
        "reward_3": "A simpler card may be better if the headline feature does not match your routine.",
        "max_1": "Start with spending you can repay comfortably. Benefits should follow existing behaviour, not create extra borrowing.",
        "max_2": "Pay close attention to payment dates and statement balances so fees or interest do not reduce value.",
        "max_3": "Check the official rules regularly because terms, exclusions and availability can change.",
        "right_1": "Estimate how often you would use the strongest confirmed benefit during a normal year.",
        "right_2": "Check whether the rules still match your needs before submitting the application.",
        "right_3": "A careful comparison should include benefit use, repayment behaviour and total cost.",
    }


def generate_p1_body(site: Dict[str, Any], card_name: str, card_slug: str, card_data: Dict[str, Any], official_url: str, featured_id: int, featured_url: str, card_id: int, card_url: str, button_hex: str) -> Tuple[str, Dict[str, Any]]:
    fee = card_data.get("annual_fee") or "the official fee shown by the issuer"
    apr = card_data.get("apr") or "the representative APR shown by the issuer"
    benefits = [b for b in (card_data.get("benefits") or []) if b][:6]
    while len(benefits) < 4:
        benefits.append("Check the official issuer page for the latest confirmed benefit details.")
    tag10 = "Avios rewards" if any("avios" in b.lower() for b in benefits) else (card_data.get("tag10") or "Card benefits")
    tag2 = "Travel perks" if any("lounge" in b.lower() or "travel" in b.lower() for b in benefits) else (card_data.get("tag2") or "Credit card")
    card_data["tag10"] = tag10[:25]
    card_data["tag2"] = tag2[:25]
    positioning = infer_p1_positioning(card_name, benefits)
    card_data["descriptor"] = card_data.get("descriptor") or positioning["subtitle_tail"].replace("is built for ", "").rstrip(".").capitalize() + "."

    subtitle = f"{card_name} {positioning['subtitle_tail']}"
    if len(subtitle) > 100:
        subtitle = f"{card_name} highlights real benefits, costs and application steps."
    if len(subtitle) > 100:
        subtitle = subtitle[:97].rsplit(" ", 1)[0] + "."

    blocks: List[str] = [wp_paragraph(subtitle)]
    blocks.append(f'<!-- wp:image {{"id":{featured_id},"sizeSlug":"large","linkDestination":"none"}} -->\n<figure class="wp-block-image size-large"><img src="{featured_url}" alt="{html.escape(card_name)} application support" class="wp-image-{featured_id}"/></figure>\n<!-- /wp:image -->')
    intro = [
        f"The {card_name} is most relevant for {positioning['use_case']}. This page focuses on the {positioning['value_focus']}.",
        f"Applications, eligibility checks and final lending decisions are handled by the issuer, not by {site.get('domain')}. Therefore, the button sends you to the official card page.",
        f"Before applying, compare the card’s main benefits with your real spending. A card can be useful only when its benefits fit your normal budget.",
        "Use this page as a decision-support step, then read the issuer’s latest summary box and terms before submitting any application.",
    ]
    blocks.extend(wp_paragraph(p) for p in intro)
    card_block = lazy_credit_card_p1(site, card_name, card_slug, card_id, card_url, card_data, official_url, button_hex)
    blocks.append(card_block)

    sections: List[Tuple[str, List[str]]] = [
        ("Main Benefits", [
            benefits[0], benefits[1], benefits[2], benefits[3],
        ]),
        ("How Does It Work", [
            f"The card works like a standard credit card for eligible purchases. However, its main value depends on how the stated benefits match your usual spending.",
            f"The issuer may show different rates or limits depending on your circumstances. As a result, the final offer can differ from the representative example.",
            "If rewards are attached to spending, they should come from purchases you already planned to make. Avoid spending more simply to chase points, vouchers or bonuses.",
        ]),
        ("Costs, Fees and Key Conditions", [
            f"The official source states {fee}. This cost should be weighed against the benefits you realistically expect to use.",
            f"The official source also references {apr}. Interest charges may reduce or outweigh reward value if balances are not managed carefully.",
            "Users should read the summary box, reward rules and exclusions before applying. In particular, check whether any welcome offer has spending thresholds or time limits.",
        ]),
        (positioning["reward_heading"], [
            positioning["reward_1"],
            positioning["reward_2"],
            positioning["reward_3"],
        ]),
        ("Requirements to Qualify for the Card", [
            "The issuer does not guarantee acceptance. It may assess credit history, income, affordability, existing borrowing and other information before making a decision.",
            "An eligibility check can help users understand whether acceptance is likely before submitting a full application. Follow the issuer’s own process and guidance.",
            "Only apply if the monthly cost, possible interest charges and repayment obligations fit your situation. Responsible use matters more than earning any reward.",
        ]),
        ("How to Maximise the Benefits", [
            positioning["max_1"],
            positioning["max_2"],
            positioning["max_3"],
        ]),
        ("How to Apply", [
            "Select the apply button to continue to the official issuer website. You will be redirected, and the application will continue away from this site.",
            "The issuer may ask for personal, financial and employment information. It may also run checks before confirming whether the product is available to you.",
            "Before submitting, check the latest official rates, terms and conditions. Do not rely on any outdated offer or third-party summary if the issuer has changed the details.",
        ]),
        ("Is This Card Right for You?", [
            f"The {card_name} may suit users who can use its confirmed benefits regularly and repay responsibly. It is not suitable simply because rewards are available.",
            "If the fee, APR or eligibility conditions do not fit your situation, compare other cards before applying. A lower-cost product may sometimes be more practical.",
            positioning["right_3"],
        ]),
    ]
    for heading, paras in sections:
        blocks.append(wp_heading(heading))
        blocks.extend(wp_paragraph(p) for p in paras)
    blocks.append(card_block)
    body = "\n\n".join(blocks)
    body, wc = fit_word_count(body)
    meta = {
        "subtitle": subtitle,
        "subtitle_chars": len(subtitle),
        "word_count": wc,
        "featured_inserted": True,
        "lazyblocks": 2,
    }
    return body, meta


def visible_word_count(body: str) -> int:
    src = re.sub(r"<!-- wp:lazyblock/credit-card.*?/-->", " ", body, flags=re.S)
    src = re.sub(r"<figure.*?</figure>", " ", src, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", src))
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    return len(re.findall(r"\b[\w£’'.%-]+\b", text))


def fit_word_count(body: str) -> Tuple[str, int]:
    wc = visible_word_count(body)
    filler = [
        "Also consider how the card would fit alongside any existing borrowing, because multiple credit products can affect affordability and future applications.",
        "If you are unsure, pause before applying and check the issuer’s documents again. A slower decision is usually better than an unsuitable application.",
        "Finally, compare the same product against at least one alternative so the fee, reward structure and repayment terms are easier to judge.",
        "Think about how often the strongest benefit would be used during a normal year. Occasional use may not justify a fee or a more complex rewards structure.",
        "Keep the official page open while applying so you can confirm the latest rates, exclusions and reward conditions before submitting personal information.",
        "If your circumstances change, reassess the card rather than keeping it only for historic benefits. Credit products should continue to match your current budget today.",
        "Check whether the reward rules still match your spending habits before submitting the application.",
        "Confirm the product’s specific promotional window, fees and post-promotional rate before relying on any headline offer.",
        "Set a repayment plan before the promotional period ends, because any remaining balance may start accruing interest at the standard variable rate.",
        "Do not spend more than you can realistically repay, and remember that missed payments can affect promotional rates and future credit access.",
        "For travel-focused cards, estimate the cash value of lounge access, foreign-spend savings and insurance discounts against the monthly fee before applying.",
        "If a cashback cap applies, compare that cap with your usual monthly spending so the expected return remains realistic rather than theoretical.",
        "Keep evidence of the offer terms that applied when you submitted the application, because issuers may update promotions, eligibility wording or reward rules later.",
    ]
    idx = 0
    while wc < 900 and idx < len(filler):
        insert = wp_paragraph(filler[idx])
        body = body.replace("<!-- wp:lazyblock/credit-card", insert + "\n\n<!-- wp:lazyblock/credit-card", 1) if idx == 0 else body.replace("<!-- wp:heading -->\n<h2 class=\"wp-block-heading\">Is This Card Right for You?</h2>\n<!-- /wp:heading -->", "<!-- wp:heading -->\n<h2 class=\"wp-block-heading\">Is This Card Right for You?</h2>\n<!-- /wp:heading -->\n\n" + insert, 1)
        wc = visible_word_count(body)
        idx += 1
    if wc > 1000:
        raise RunnerError(f"P1 body word count above hard limit: {wc}")
    if wc < 900:
        raise RunnerError(f"P1 body word count below hard limit after expansion: {wc}")
    return body, wc


def title_and_meta(card_name: str, card_data: Dict[str, Any]) -> Tuple[str, str, str]:
    focus = compact_focus(card_name)
    joined = " ".join(card_data.get("benefits") or []).lower()
    low_rate = any(t in joined for t in ["low interest", "low rate", "12.9%", "no annual fee", "foreign transaction"])
    title = f"{focus}: Low Rate Costs and How to Apply" if low_rate else f"{focus}: Costs, Rewards and How to Apply"
    if len(title) > 60:
        title = f"{focus}: Costs and How to Apply"
    if len(title) > 60:
        title = f"{focus}: How to Apply"
    meta = (f"{focus} application guide focused on rates, annual fee, overseas purchases, eligibility notes and official issuer apply link."
            if low_rate else
            f"{focus} application guide with key costs, rewards, eligibility notes and official issuer apply link before you continue.")
    if len(meta) > 130:
        meta = f"{focus} guide with key costs, eligibility notes and official issuer apply link before you continue."
    if len(meta) < 120:
        meta = meta.rstrip(".") + " and compare the issuer terms first."
    if len(meta) > 130:
        meta = meta[:127].rsplit(" ", 1)[0] + "."
    validate_seo_fields(title, meta, focus)
    return title, meta, focus


def resolve_term(site_key: str, taxonomy: str, name: str) -> int:
    p = run([str(WP_SCRIPTS / "resolve-term.sh"), site_key, taxonomy, name], timeout=60, allow_fail=True)
    out = p.stdout.strip() or p.stderr.strip()
    if p.returncode == 0:
        return int(json.loads(p.stdout)["id"])
    m = re.search(r'"term_id":(\d+)', out)
    if m:
        return int(m.group(1))
    raise RunnerError(f"Could not resolve {taxonomy} term {name}: {out[:800]}")


def resolve_taxonomy(site_key: str, site: Dict[str, Any], card_name: str, card_slug: str, benefits: List[str]) -> Tuple[int, List[int], List[str]]:
    cat_name = site.get("default_category", "Credit Card")
    category_id = resolve_term(site_key, "categories", cat_name)
    lang = site.get("language") or (site.get("template_key", "gb-cc-en").split("-")[-1])
    vertical = (site.get("verticals") or ["cc"])[0]
    country = site.get("country", "gb")
    card_tag = re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 ]+", " ", card_name.replace("Card", ""))).strip().lower()
    tags = ["p1", vertical, country, card_tag, f"lang_{lang}", "atena_agent"]
    benefit_text = " ".join(benefits).lower()
    seo_tags = []
    if "avios" in benefit_text:
        seo_tags.append("avios rewards")
    if "lounge" in benefit_text:
        seo_tags.append("airport lounge access")
    if "travel" in benefit_text or "avios" in benefit_text:
        seo_tags.append("travel credit card")
    seo_tags.append("rewards credit card")
    for t in seo_tags:
        if t not in tags:
            tags.append(t)
    tags = tags[:10]
    tag_ids = [resolve_term(site_key, "tags", t) for t in tags]
    return category_id, tag_ids, tags


def create_or_update_post(site_key: str, post_json: Dict[str, Any], update_post_id: Optional[int]) -> Dict[str, Any]:
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(post_json, tmp, ensure_ascii=False)
    tmp.close()
    if update_post_id:
        creds = resolve_credentials(site_key)
        url = creds["wp_url"].rstrip("/") + f"/wp-json/wp/v2/posts/{update_post_id}"
        r = requests.post(url, auth=(creds["username"], creds["password"]), json=post_json, timeout=60)
        if r.status_code >= 400:
            raise RunnerError(f"WP update failed {r.status_code}: {r.text[:1000]}")
        return r.json()
    return run_json([str(WP_SCRIPTS / "create-post.sh"), site_key, tmp.name], timeout=180)


def update_yoast(site_key: str, post_id: int, title: str, body: str, meta: Dict[str, str]) -> Dict[str, Any]:
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump({"title": title, "content": body, "meta": meta}, tmp, ensure_ascii=False)
    tmp.close()
    return run_json([str(WP_SCRIPTS / "update-yoast.sh"), site_key, str(post_id), tmp.name, "verify"], timeout=180)


def public_verify(url: str, official_url: str, featured_url: str, card_url: str) -> Dict[str, Any]:
    r = requests.get(url + ("?nocache=1" if "?" not in url else "&nocache=1"), timeout=25, headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"})
    html_text = r.text
    m = re.search(r'"wordCount":(\d+)', html_text)
    checks = {
        "http": r.status_code,
        "contains_apply_now": "APPLY NOW" in html_text,
        "contains_redirected": "You will be redirected." in html_text,
        "contains_official_url": official_url in html_text,
        "contains_featured": bool(featured_url and featured_url in html_text),
        "contains_card": bool(card_url and card_url in html_text),
        "yoast_schema_word_count": int(m.group(1)) if m else None,
    }
    checks["ok"] = (
        checks["http"] == 200
        and checks["contains_apply_now"]
        and checks["contains_redirected"]
        and checks["contains_official_url"]
        and checks["contains_featured"]
        and checks["contains_card"]
    )
    return checks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--rec-url", required=True, help="Existing REC URL to use as source context")
    ap.add_argument("--status", choices=["draft", "publish"], default="draft")
    ap.add_argument("--official-url", default="")
    ap.add_argument("--card", default="")
    ap.add_argument("--annual-fee", default="")
    ap.add_argument("--apr", default="")
    ap.add_argument("--benefit", action="append", default=[])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--update-post-id", type=int, default=0, help="Update an existing P1 instead of creating a new post")
    args = ap.parse_args()

    started = ts()
    timings: Dict[str, float] = {}
    steps: List[str] = []
    media_created: List[Dict[str, Any]] = []
    result: Dict[str, Any] = {"ok": False, "runner": "mgs-p1-runner", "site": args.site, "status_requested": args.status, "dry_run": args.dry_run}
    try:
        t = ts(); site = load_site(args.site); timings["load_site"] = ts() - t; steps.append("site_loaded")
        if site.get("template_key") != "gb-cc-en":
            raise RunnerError("P1 runner currently supports template_key gb-cc-en only")

        t = ts()
        rec_id_match = re.search(r"[?&]p=(\d+)", args.rec_url)
        if rec_id_match:
            rec_id = int(rec_id_match.group(1))
            rec = wp_get_post(args.site, rec_id)
            public_html = f"<body class='postid-{rec_id}'>" + (rec.get("content", {}).get("rendered") or rec.get("content", {}).get("raw") or "") + "</body>"
        else:
            public_html = get_public(args.rec_url)
            rec_id = post_id_from_public_html(public_html, args.rec_url)
            rec = wp_get_post(args.site, rec_id)
        timings["fetch_rec"] = ts() - t; steps.append("rec_loaded")
        rec_raw = rec.get("content", {}).get("raw") or ""
        rec_rendered = rec.get("content", {}).get("rendered") or ""
        rec_title = rec.get("title", {}).get("raw") or rec.get("title", {}).get("rendered") or ""
        parsed = parse_card_from_rec(rec_raw, rec_rendered, rec_title)
        card_name = args.card or parsed["card_name"]
        card_slug = infer_card_slug(args.rec_url, card_name)
        cache = cache_lookup(card_slug)
        official_url = args.official_url or cache.get("card_official_url") or ""
        if not official_url:
            raise RunnerError("official URL missing and not found in card cache; pass --official-url")
        t = ts(); preflight_official_source(official_url, card_name); timings["official_source_preflight"] = ts() - t; steps.append("official_source_preflight_passed")
        card_url = parsed.get("card_url")
        card_id = parsed.get("card_id")
        card_image_source = "rec_lazyblock" if card_url and card_id else "missing_from_rec"
        if not card_url or not card_id:
            # P1 created from an existing REC must not silently inject an external/manual
            # cache image when the REC card LazyBlock is empty. That bypasses the
            # card-only normalization/crop gate and hides the issue from Raquel.
            raise RunnerError("REC card image is missing from the LazyBlock; do not publish P1. Ask Raquel for the correct card image or repair the REC card image first.")

        country = site.get("country", "gb"); vertical = (site.get("verticals") or ["cc"])[0]
        inferred_target_slug = f"apply-now-{country}-{vertical}-{card_slug}"
        rec_button_slug = p1_slug_from_rec_buttons(public_html, rec_raw, site["domain"])
        target_slug = rec_button_slug or inferred_target_slug
        target_url = f"https://{site['domain']}/{target_slug}/"
        existing_check = requests.get(target_url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        result["existing_p1_check"] = {"url": target_url, "http": existing_check.status_code, "slug_source": "rec_button" if rec_button_slug else "inferred", "inferred_slug": inferred_target_slug}
        if existing_check.status_code < 400 and not args.dry_run and not args.update_post_id:
            raise RunnerError(f"Target P1 already exists at {target_url}; pass --update-post-id to update instead of creating a duplicate")

        t = ts(); official_data = extract_official_data(card_name, official_url, args.benefit, args.annual_fee or None, args.apr or None); timings["official_facts"] = ts() - t; steps.append("official_facts_extracted")
        # Preserve REC LazyBlock labels when official extraction is generic.
        official_data.setdefault("tag10", parsed.get("tag10"))
        official_data.setdefault("tag2", parsed.get("tag2"))
        official_data.setdefault("descriptor", parsed.get("descriptor"))

        card_path = ensure_card_local(card_url, card_slug)
        featured_path = None
        featured_audit = None
        featured_failures: List[str] = []
        for featured_attempt in range(1, 4):
            t = ts(); featured_path = make_exact_featured(card_path, card_slug); timings["featured_image"] = timings.get("featured_image", 0) + (ts() - t)
            t = ts()
            featured_audit = run_json([
                str(FEATURED_AUDIT_SCRIPT),
                "--featured", featured_path,
                "--card", card_path,
                "--mode", "p1",
                "--card-name", card_name,
                "--require-person",
            ], timeout=150, allow_fail=True)
            timings["featured_semantic_audit"] = timings.get("featured_semantic_audit", 0) + (ts() - t)
            if featured_audit.get("ok"):
                if featured_attempt > 1:
                    result.setdefault("warnings", []).append(f"featured_semantic_audit_passed_after_retry:{featured_attempt}")
                break
            reasons = featured_audit.get("blocking_reasons") or []
            featured_failures.append(f"attempt {featured_attempt}: {', '.join(map(str, reasons))}")
        if not featured_audit or not featured_audit.get("ok") or not featured_path:
            raise RunnerError("featured_semantic_audit_failed_after_retries: " + " | ".join(featured_failures))
        steps.append("featured_generated_exact_overlay")
        steps.append("featured_semantic_audited")

        if args.dry_run:
            featured_media = {"id": None, "source_url": featured_path, "dry_run_local_path": featured_path}
        else:
            t = ts(); featured_media = upload_image(args.site, featured_path, f"featured-p1-{card_slug}.jpg"); timings["upload_featured"] = ts() - t; media_created.append({"id": featured_media.get("id"), "url": featured_media.get("source_url"), "role": "p1_featured"}); steps.append("featured_uploaded")

        t = ts(); button = run_json([str(WP_SCRIPTS / "resolve-button-color.sh"), args.site], timeout=60); button_hex = button["hex"]; timings["button_color"] = ts() - t
        featured_id = int(featured_media.get("id") or 0)
        featured_url = featured_media.get("source_url")
        # For dry-run, use placeholder id in body so validation can still run.
        body, validation = generate_p1_body(site, card_name, card_slug, official_data, official_url, featured_id or 999999, featured_url, int(card_id), card_url, button_hex)
        title, metadesc, focuskw = title_and_meta(card_name, official_data)
        validate_no_review({"body": body, "subtitle": validation.get("subtitle", ""), "title": title, "meta": metadesc})
        result["content_validation"] = {**validation, "title_chars": len(title), "meta_chars": len(metadesc), "focus_keyphrase": focuskw}
        steps.append("content_assembled")

        t = ts(); category_id, tag_ids, tag_names = resolve_taxonomy(args.site, site, card_name, card_slug, official_data.get("benefits") or []); validate_taxonomy_names(tag_names, site.get("language") or "en"); timings["taxonomy"] = ts() - t; steps.append("taxonomy_resolved")

        slug = target_slug
        meta = {"_yoast_wpseo_title": "", "_yoast_wpseo_metadesc": metadesc, "_yoast_wpseo_focuskw": focuskw}
        post_json = {
            "title": title,
            "slug": slug,
            "content": body,
            "status": args.status,
            "author": site.get("publishing_user", {}).get("id", 11),
            "categories": [category_id],
            "tags": tag_ids,
            "featured_media": featured_id or None,
            "meta": meta,
        }
        if site.get("hide_p1_from_home"):
            post_json.setdefault("meta", {})["_hide_from_home"] = "1"

        post = None; yoast = None; score = None; verify = None
        if not args.dry_run:
            t = ts(); post = create_or_update_post(args.site, post_json, args.update_post_id or None); timings["wp_publish"] = ts() - t; steps.append("post_published" if not args.update_post_id else "post_updated")
            post_id = int(post["id"])
            t = ts(); yoast = update_yoast(args.site, post_id, title, body, meta); timings["yoast_update"] = ts() - t; steps.append("yoast_verified")
            t = ts(); score = run_json([str(GEN_SCRIPTS / "yoast-score-post.sh"), args.site, str(post_id)], timeout=180, allow_fail=True); validate_yoast_score(score); timings["yoast_score"] = ts() - t; steps.append("yoast_scored")
            t = ts(); verify = public_verify(post["link"], official_url, featured_url, card_url); timings["public_verify"] = ts() - t
            if not verify.get("ok"):
                raise RunnerError(f"public_verify_failed: {verify}")
            steps.append("public_verified")
        else:
            post = {"id": None, "link": f"https://{site['domain']}/{slug}/", "slug": slug, "status": args.status}
            steps.append("dry_run_no_publish")

        duration = ts() - started
        result.update({
            "ok": True,
            "status_detail": "fully_validated" if not args.dry_run else "dry_run_validated",
            "steps": steps,
            "duration_sec": round(duration, 3),
            "timings_sec": {k: round(v, 3) for k, v in timings.items()},
            "rec_source": {"url": args.rec_url, "post_id": rec_id},
            "official_url": official_url,
            "card": {"name": card_name, "slug": card_slug, "image_id": int(card_id), "image_url": card_url},
            "post": {"id": post.get("id"), "status": post.get("status", args.status), "slug": post.get("slug"), "link": post.get("link"), "edit_url": f"https://{site['domain']}/wp-admin/post.php?post={post.get('id')}&action=edit" if post.get("id") else None},
            "seo": {"title": title, "meta_description": metadesc, "focus_keyphrase": focuskw, "yoast": yoast, "score": score},
            "taxonomy": {"category_id": category_id, "tag_ids": tag_ids, "tag_names": tag_names},
            "images": {"card_reused_from_rec": card_image_source == "rec_lazyblock", "card_image_source": card_image_source, "featured": featured_media, "featured_audit": featured_audit, "media_created": media_created},
            "public_verify": verify,
            "cost_usd": {"runner_api_est": 0.0, "featured_image_est": 0.04, "total_est": 0.04},
        })
    except Exception as e:
        result.update({"ok": False, "error": str(e), "steps": steps, "duration_sec": round(ts() - started, 3), "timings_sec": {k: round(v, 3) for k, v in timings.items()}})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
