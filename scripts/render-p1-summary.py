#!/usr/bin/env python3
"""Render Rodolfo-approved P1 Discord summary from mgs-p1-runner JSON.

This is intentionally deterministic: no LLM reordering, no compact variants.
Usage:
  python3 scripts/render-p1-summary.py /tmp/p1-runner.json
  cat /tmp/p1-runner.json | python3 scripts/render-p1-summary.py
"""
import json
import sys
from pathlib import Path

RODOLFO = "<@344196393512075265>"
RAQUEL = "<@1496254952501280974>"

def fmt_duration(seconds):
    try:
        seconds = int(round(float(seconds)))
    except Exception:
        return "n/a"
    if seconds >= 60:
        return f"{seconds//60}m{seconds%60:02d}s"
    return f"{seconds}s"

def score_emoji(score):
    try:
        s = int(score)
    except Exception:
        return ""
    if s >= 80:
        return "🟢"
    if s >= 60:
        return "🟡"
    return "🔴"

def get(d, path, default=None):
    cur = d
    for p in path.split('.'):
        if not isinstance(cur, dict) or p not in cur or cur[p] is None:
            return default
        cur = cur[p]
    return cur

def main():
    if len(sys.argv) > 1 and sys.argv[1] not in ("-", "--"):
        data = json.loads(Path(sys.argv[1]).read_text())
    else:
        data = json.load(sys.stdin)

    card = get(data, "card.name") or data.get("card") or ""
    site = data.get("site", "")
    post_id = get(data, "post.id")
    public_url = get(data, "post.link")
    edit_url = get(data, "post.edit_url")
    rec_url = get(data, "rec_source.url") or data.get("rec_url", "")
    status = get(data, "post.status") or data.get("status_requested", "")
    status_label = "Publicado" if status == "publish" else status
    slug = get(data, "post.slug")
    seo_score = get(data, "seo.score.seo_score")
    read_score = get(data, "seo.score.readability_score")
    public_words = get(data, "public_verify.yoast_schema_word_count")
    validation_words = get(data, "content_validation.word_count")
    title = get(data, "seo.title")
    title_chars = get(data, "content_validation.title_chars", len(title) if title else "")
    subtitle = get(data, "content_validation.subtitle")
    subtitle_chars = get(data, "content_validation.subtitle_chars", len(subtitle) if subtitle else "")
    focus = get(data, "seo.focus_keyphrase") or get(data, "content_validation.focus_keyphrase")
    meta = get(data, "seo.meta_description")
    meta_chars = len(meta) if meta else ""
    tags = get(data, "taxonomy.tag_names", [])
    tags_line = " ".join(f"`{t}`" for t in tags)
    official_url = data.get("official_url", "")
    featured_url = get(data, "images.featured.source_url")
    card_url = get(data, "card.image_url")
    duration = fmt_duration(data.get("duration_sec"))
    cost = get(data, "cost_usd.total_est")
    cost_str = f"US${float(cost):.2f}" if isinstance(cost, (int, float)) else (str(cost) if cost else "n/a")

    public_http = get(data, "public_verify.http")
    words = public_words or validation_words or "n/a"
    tags_line = ", ".join(str(t) for t in tags) if isinstance(tags, list) else str(tags or "")

    lines = [
        f"📄 P1 Post ID: {post_id}",
        f"🔗 P1 : {public_url}",
        f"✏️ Edit P1: {edit_url}",
        f"🔗 Slug: {slug}",
        f"📌 Status: {status}",
        "",
        "📄 P1",
        f"📊  Yoast: SEO {seo_score} / Readability {read_score}",
        f"• Validação: {words} palavras / subtitle {subtitle_chars} chars / público HTTP {public_http or 'n/a'}",
        f"• Title: {title} — {title_chars} chars",
        f"• Focus: {focus}",
        f"• Meta Description: {meta}- {meta_chars} chars",
        f"• Tags: {tags_line}",
        f"• Imagem Card: {card_url}",
        f"• Imagem Featured: {featured_url}",
        f"• Fonte oficial: {official_url}",
        "",
        f"⏱️ Tempo total dos runners: P1 {duration}",
        f"💰 Custo estimado: P1 {cost_str}",
    ]
    print("\n".join(lines))

if __name__ == "__main__":
    main()
