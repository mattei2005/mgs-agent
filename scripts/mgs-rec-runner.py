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
GEN_SCRIPTS = ROOT / "skills/content-generate-rec/scripts"
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
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip().strip('"').strip("'")
    if key.startswith("sk-ant-"):
        return key
    for env_path in [ROOT / ".env", Path("/root/.hermes/profiles/atena/.env")]:
        if not env_path.exists():
            continue
        for line in env_path.read_text(errors="ignore").splitlines():
            if line.strip().startswith("ANTHROPIC_API_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val.startswith("sk-ant-"):
                    return val
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
    key = load_anthropic_key()
    if not key:
        raise RunnerError("ANTHROPIC_API_KEY unavailable for reference extraction")
    import anthropic  # local import so --dry-run env checks stay lightweight

    client = anthropic.Anthropic(api_key=key)
    prompt = f"""Extract verified credit-card facts from the reference text.
Return ONLY compact JSON with this schema:
{{
  "card_name": "exact product name",
  "annual_fee": "fee as stated, or No annual fee",
  "apr": "representative APR as stated, or N/A",
  "benefits": ["3-5 factual benefits"],
  "tag10": "short benefit tag <=25 chars",
  "tag2": "short benefit tag <=25 chars",
  "descriptor": "50-100 char card descriptor",
  "competitors": [{{"name":"real comparable UK credit card","apr":"if known"}}, {{"name":"real comparable UK credit card","apr":"if known"}}]
}}
Rules: never invent card benefits. If a fact is absent, use N/A. Competitors may use generally known UK cards in the same segment.

Requested card: {card_name}
Source URL: {source_url}
Reference text:
{text[:12000]}
"""
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system="You extract structured financial product facts. Output JSON only.",
        messages=[{"role": "user", "content": prompt}],
    )
    out = msg.content[0].text.strip()
    out = re.sub(r"^```json\s*|\s*```$", "", out, flags=re.I | re.S).strip()
    try:
        data = json.loads(out)
    except Exception as e:
        raise RunnerError(f"reference extraction returned invalid JSON: {e}; output={out[:1000]}")
    if not data.get("benefits") or len(data.get("benefits", [])) < 3:
        raise RunnerError("reference extraction produced fewer than 3 benefits")
    return data


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


def validate_html(path: Path) -> Dict[str, Any]:
    p = run([str(GEN_SCRIPTS / "validate-article.sh"), str(path)], timeout=30)
    try:
        data = json.loads(p.stdout)
    except Exception:
        raise RunnerError(f"validate-article returned non-JSON: rc={p.returncode} stdout={p.stdout} stderr={p.stderr}")
    if p.returncode != 0 or data.get("status") != "PASS":
        raise RunnerError(f"Article validation failed: {json.dumps(data, ensure_ascii=False)}")
    return data


def title_meta_focus(card_name: str, card_data: Dict[str, Any]) -> Tuple[str, str, str]:
    # Keep focus <=4 words. Prefer a recognisable product stem.
    words = [w for w in re.sub(r"[^A-Za-z0-9 ]", " ", card_name).split() if w.lower() not in {"credit", "card", "the"}]
    focus = " ".join(words[:3]) if words else card_name[:40]
    no_fee = "no annual fee" in (card_data.get("annual_fee") or "").lower() or any("no annual fee" in b.lower() for b in card_data.get("benefits", []))
    benefit = "No Fee" if no_fee else "Key Benefits"
    title = f"{focus}: {benefit} & Rewards"
    if len(title) > 60:
        title = f"{focus}: Benefits & Fees"[:60]
    meta = f"{card_name} offers {', '.join(card_data.get('benefits', ['key benefits'])[:2]).lower()}. See fees, APR and how it works."
    if len(meta) > 130:
        meta = meta[:127].rsplit(" ", 1)[0] + "..."
    if len(meta) < 120:
        meta = (meta + " Compare before applying.")[:130]
    return title, meta, focus


def resolve_terms(site_key: str, site: Dict[str, Any], card_slug: str, card_data: Dict[str, Any]) -> Tuple[int, List[int], List[str]]:
    category_name = site.get("default_category", "Credit Card")
    cat = run_json([str(WP_SCRIPTS / "resolve-term.sh"), site_key, "categories", category_name], timeout=60)
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
        term = run_json([str(WP_SCRIPTS / "resolve-term.sh"), site_key, "tags", t], timeout=60)
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
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-disambiguation", action="store_true")
    args = ap.parse_args()

    started = time.time()
    warnings: List[str] = []
    steps: List[str] = []
    costs = {"article_api": 0.0, "extract_llm_est": 0.0, "featured_image_est": 0.03, "total_est": 0.0}

    try:
        site = load_site(args.site)
        card_slug = slugify(args.card)
        country = site.get("country", "gb")
        vertical = (site.get("verticals") or ["cc"])[0]
        post_slug = f"rec-{country}-{vertical}-{card_slug}"
        edit_url = None
        card_data: Dict[str, Any]

        color = run_json([str(WP_SCRIPTS / "resolve-button-color.sh"), args.site], timeout=30)
        button_hex = color["hex"]
        steps.append("config_loaded")

        cache = cache_lookup(card_slug)
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
                status, text = fetch_reference_text(args.source_url)
                if status >= 400:
                    raise RunnerError(f"reference_url returned HTTP {status}")
                card_data = extract_card_data_with_llm(args.card, args.source_url, text)
                card_data["card_official_url"] = args.source_url
                steps.append("reference_extracted_llm")
                costs["extract_llm_est"] = 0.02

        card_data["card_name"] = card_data.get("card_name") or args.card
        card_id = card_data.get("card_image_uploaded_id")
        card_url = card_data.get("card_image_uploaded_url")
        card_local = None
        card_src = None

        if not card_id or not card_url:
            if args.dry_run:
                steps.append("dry_run_skip_card_upload")
            else:
                source_url = card_data.get("card_official_url") or args.source_url
                if not source_url:
                    raise RunnerError("No card official URL available for image search")
                img = run_json([str(GEN_SCRIPTS / "search-card-image.sh"), card_data["card_name"], source_url], timeout=180, allow_fail=True)
                if img.get("status") != "OK" or not img.get("path"):
                    raise RunnerError(f"Card image search failed: {json.dumps(img, ensure_ascii=False)[:1000]}")
                card_local = img["path"]
                card_src = img.get("source")
                ext = Path(card_local).suffix or ".png"
                up = run_json([str(WP_SCRIPTS / "upload-image.sh"), args.site, card_local, f"card-{card_slug}{ext}"], timeout=120)
                card_id, card_url = int(up["id"]), up["source_url"]
                steps.append("card_image_uploaded")

        featured_id = None
        featured_url = None
        featured_scene = None
        featured_path = None
        if args.dry_run:
            steps.append("dry_run_skip_featured")
        else:
            # Need local card image for Gemini; if cache only has uploaded URL, download it to tmp.
            if not card_local:
                if not card_url:
                    raise RunnerError("No card image available for featured generation")
                suffix = Path(urllib.parse.urlparse(card_url).path).suffix or ".png"
                card_local = f"/tmp/card-{card_slug}-from-wp{suffix}"
                urllib.request.urlretrieve(card_url, card_local)
            feat = run_json([str(GEN_SCRIPTS / "generate-featured-image.sh"), card_slug, card_local], timeout=180)
            featured_path = feat["path"]
            featured_scene = feat.get("scene")
            # Cheap deterministic validation before upload.
            ident = run(["identify", "-format", "%w %h", featured_path], timeout=20)
            if ident.returncode != 0:
                raise RunnerError(f"featured identify failed: {ident.stderr}")
            w, h = [int(x) for x in ident.stdout.split()[:2]]
            if w < 1000 or h < 600:
                raise RunnerError(f"featured image too small: {w}x{h}")
            upf = run_json([str(WP_SCRIPTS / "upload-image.sh"), args.site, featured_path, f"featured-{card_slug}-final.jpg"], timeout=120)
            featured_id, featured_url = int(upf["id"]), upf["source_url"]
            steps.append("featured_uploaded")

        api_payload = {
            "site": args.site,
            "card_slug": card_slug,
            "card_name": card_data["card_name"],
            "card_official_url": card_data.get("card_official_url") or args.source_url,
            "annual_fee": card_data.get("annual_fee") or "N/A",
            "apr": card_data.get("apr") or "N/A",
            "benefits": card_data.get("benefits") or [],
            "competitors": card_data.get("competitors") or [],
        }
        api = call_rec_api(api_payload)
        if not api.get("success"):
            raise RunnerError(f"mgs-rec-api failed: {api}")
        costs["article_api"] = float(api.get("cost_usd") or 0)
        card_data.update(api.get("card_data") or {})
        steps.append("article_generated")

        card_block = lazy_credit_card(card_data["card_name"], card_id, card_url, site, card_slug, card_data, button_hex)
        button_block = lazy_button(site, card_slug, button_hex)
        content = assemble_content(api["article_html"], card_block, button_block)
        tmp_html = Path(tempfile.gettempdir()) / f"final-{card_slug}.html"
        tmp_html.write_text(content)
        validation = validate_html(tmp_html)
        subtitle = visible_subtitle(content)
        subtitle_chars = len(subtitle)
        if subtitle_chars > 100:
            raise RunnerError(f"subtitle too long: {subtitle_chars} chars")
        steps.append("content_validated")

        title, meta_desc, focus_kw = title_meta_focus(card_data["card_name"], card_data)
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
            category_id, tag_ids, tag_names = resolve_terms(args.site, site, card_slug, card_data)
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
            created = run_json([str(WP_SCRIPTS / "create-post.sh"), args.site, str(post_path)], timeout=180, env=env)
            post_id = int(created["id"])
            public_url = created.get("link") or public_url
            edit_url = f"{site['wp_url']}/wp-admin/post.php?post={post_id}&action=edit"
            steps.append("post_created")

            yoast_json = {"title": title, "content": content, "meta": post_json["meta"]}
            yoast_path = Path(tempfile.gettempdir()) / f"rec-yoast-{card_slug}.json"
            yoast_path.write_text(json.dumps(yoast_json, ensure_ascii=False))
            yoast_update = run_json([str(WP_SCRIPTS / "update-yoast.sh"), args.site, str(post_id), str(yoast_path), "verify"], timeout=180)
            steps.append("yoast_updated")
            try:
                yoast_result = run_json([str(GEN_SCRIPTS / "yoast-score-post.sh"), args.site, str(post_id)], timeout=180, allow_fail=True)
            except Exception as e:
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
            run_json([str(GEN_SCRIPTS / "card-cache-save.sh"), str(cache_path)], timeout=60)
            steps.append("cache_saved")
            public_check = public_verify(public_url)
            if public_check.get("http_status") != 200:
                warnings.append(f"public_verify_not_200: {public_check}")
            steps.append("public_verified")

        costs["total_est"] = round(costs["article_api"] + costs["extract_llm_est"] + (0 if args.dry_run else costs["featured_image_est"]), 6)
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
            "duration_sec": round(time.time() - started, 2),
            "steps": steps,
            "cost_usd": costs,
            "card_data": {
                "card_name": card_data.get("card_name"),
                "annual_fee": card_data.get("annual_fee"),
                "apr": card_data.get("apr"),
                "benefits": card_data.get("benefits"),
                "competitors": card_data.get("competitors"),
            },
            "seo": {"title": title, "title_chars": len(title), "meta_desc": meta_desc, "meta_chars": len(meta_desc), "focus_kw": focus_kw},
            "validation": {**validation, "subtitle_chars": subtitle_chars, "public": public_check},
            "taxonomy": {"category_id": category_id, "tag_ids": tag_ids, "tag_names": tag_names},
            "images": {
                "card_id": card_id,
                "card_url": card_url,
                "featured_id": featured_id,
                "featured_url": featured_url,
                "featured_scene": featured_scene,
                "featured_path": featured_path,
            },
            "yoast": yoast_result,
            "warnings": warnings,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        result = {"success": False, "error": str(e), "duration_sec": round(time.time() - started, 2), "steps": steps, "warnings": warnings}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
