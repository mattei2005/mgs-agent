#!/usr/bin/env python3
"""Render Rodolfo-approved final Discord summaries for REC, P1 and REC+P1.

Deterministic formatter: no intro sentence, no tables, no extra fields.
It fills the exact 2026-05-26 templates from runner JSON.

Usage:
  python3 scripts/render-article-summary.py --type rec rec.json
  python3 scripts/render-article-summary.py --type p1 p1.json
  python3 scripts/render-article-summary.py --type rec-p1 rec.json p1.json
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


def load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def get(d: Mapping[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, Mapping) or part not in cur or cur[part] is None:
            return default
        cur = cur[part]
    return cur


def first(d: Mapping[str, Any], *paths: str, default: Any = "") -> Any:
    for path in paths:
        value = get(d, path) if "." in path else d.get(path)
        if value is not None and value != "":
            return value
    return default


def duration(seconds: Any) -> str:
    try:
        total = int(round(float(seconds)))
    except Exception:
        return "n/a"
    if total > 60:
        return f"{total // 60}m{total % 60:02d}s"
    return f"{total}s"


def operation_duration(data: Mapping[str, Any], override_seconds: Any = None) -> str:
    """User-perceived elapsed time. Prefer explicit operation elapsed seconds.

    Runner duration is only a fallback for older JSON; final summaries should pass
    --operation-seconds or include operation_duration_sec/operation_elapsed_sec.
    """
    value = override_seconds
    if value in (None, ""):
        value = first(data, "operation_duration_sec", "operation_elapsed_sec", "total_elapsed_sec", "duration_sec")
    return duration(value)


def operation_duration_from_started(started_at: str | None) -> float | None:
    if not started_at:
        return None
    text = started_at.strip()
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return max(0.0, time.time() - datetime.fromisoformat(text).timestamp())
    except Exception:
        try:
            return max(0.0, time.time() - float(started_at))
        except Exception:
            return None


def cost(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"US${value:.2f}"
    return str(value) if value not in (None, "") else "n/a"


def no_embed_url(value: Any) -> str:
    """Wrap Discord URLs in angle brackets to suppress embeds/previews."""
    if value in (None, ""):
        return ""
    text = str(value)
    if text.startswith("<") and text.endswith(">"):
        return text
    if text.startswith("http://") or text.startswith("https://"):
        return f"<{text}>"
    return text


def tags(data: Mapping[str, Any]) -> str:
    raw = first(data, "taxonomy.tag_names", default=[])
    if isinstance(raw, list):
        return ", ".join(str(x) for x in raw)
    return str(raw or "")


def article_type(data: Mapping[str, Any], forced: str) -> str:
    if forced == "rec":
        return "REC"
    if forced == "p1":
        return "P1"
    return str(first(data, "type", "article_type", default=forced.upper()))


def post_id(data: Mapping[str, Any]) -> Any:
    return first(data, "post.id", "post_id")


def public_url(data: Mapping[str, Any]) -> Any:
    return first(data, "post.link", "public_url")


def edit_url(data: Mapping[str, Any]) -> Any:
    return first(data, "post.edit_url", "edit_url")


def slug(data: Mapping[str, Any]) -> Any:
    return first(data, "post.slug", "post_slug", "card_slug")


def status(data: Mapping[str, Any]) -> Any:
    return first(data, "post.status", "status")


def seo_score(data: Mapping[str, Any]) -> Any:
    return first(data, "seo.score.seo_score", "yoast.seo_score")


def readability_score(data: Mapping[str, Any]) -> Any:
    return first(data, "seo.score.readability_score", "yoast.readability_score")


def word_count(data: Mapping[str, Any]) -> Any:
    return first(data, "public_verify.yoast_schema_word_count", "content_validation.word_count", "validation.word_count")


def subtitle_chars(data: Mapping[str, Any]) -> Any:
    subtitle = first(data, "content_validation.subtitle", "validation.subtitle", default="")
    return first(data, "content_validation.subtitle_chars", "validation.subtitle_chars", default=(len(subtitle) if subtitle else ""))


def public_http(data: Mapping[str, Any]) -> Any:
    return first(data, "public_verify.http", "public_verify.http_status", "validation.public.http", "validation.public.http_status")


def title(data: Mapping[str, Any]) -> Any:
    return first(data, "seo.title")


def title_chars(data: Mapping[str, Any]) -> Any:
    t = title(data)
    return first(data, "content_validation.title_chars", "validation.title_chars", "seo.title_chars", default=(len(t) if t else ""))


def focus(data: Mapping[str, Any]) -> Any:
    return first(data, "seo.focus_keyphrase", "content_validation.focus_keyphrase", "seo.focus_kw")


def meta(data: Mapping[str, Any]) -> Any:
    return first(data, "seo.meta_description", "seo.meta_desc")


def meta_chars(data: Mapping[str, Any]) -> Any:
    m = meta(data)
    return first(data, "content_validation.meta_chars", "validation.meta_chars", "seo.meta_chars", default=(len(m) if m else ""))


def card_image(data: Mapping[str, Any]) -> Any:
    return first(data, "card.image_url", "images.card_url", "card_data.card_image_uploaded_url")


def featured_image(data: Mapping[str, Any]) -> Any:
    return first(data, "images.featured.source_url", "images.featured_url")


def official_url(data: Mapping[str, Any]) -> Any:
    return first(data, "official_url", "source_url", "card_data.card_official_url")


def render_block(data: Mapping[str, Any], kind: str) -> list[str]:
    return [
        f"📄 {article_type(data, kind)}",
        f"📊  Yoast: SEO {seo_score(data)} / Readability {readability_score(data)}",
        f"• Validação: {word_count(data)} palavras / subtitle {subtitle_chars(data)} chars / público HTTP {public_http(data)}",
        f"• Title: {title(data)} — {title_chars(data)} chars",
        f"• Focus: {focus(data)}",
        f"• Meta Description: {meta(data)}- {meta_chars(data)} chars",
        f"• Tags: {tags(data)}",
        f"• Imagem Card: {no_embed_url(card_image(data))}",
        f"• Imagem Featured: {no_embed_url(featured_image(data))}",
        f"• Fonte oficial: {no_embed_url(official_url(data))}",
    ]


def render_rec(data: Mapping[str, Any], operation_seconds: Any = None) -> str:
    lines = [
        f"📄 REC Post ID: {post_id(data)}",
        f"🔗 REC: {no_embed_url(public_url(data))}",
        f"✏️ Edit REC: {no_embed_url(edit_url(data))}",
        f"🔗 Slug: {slug(data)}",
        f"📌 Status: {status(data)}",
        "",
        *render_block(data, "rec"),
        "",
        f"⏱️ Tempo total da operação: {operation_duration(data, operation_seconds)}",
        f"💰 Custo estimado: REC {cost(first(data, 'cost_usd.total_est'))}",
    ]
    return "\n".join(lines)


def render_p1(data: Mapping[str, Any], operation_seconds: Any = None) -> str:
    lines = [
        f"📄 P1 Post ID: {post_id(data)}",
        f"🔗 P1 : {no_embed_url(public_url(data))}",
        f"✏️ Edit P1: {no_embed_url(edit_url(data))}",
        f"🔗 Slug: {slug(data)}",
        f"📌 Status: {status(data)}",
        "",
        *render_block(data, "p1"),
        "",
        f"⏱️ Tempo total da operação: {operation_duration(data, operation_seconds)}",
        f"💰 Custo estimado: P1 {cost(first(data, 'cost_usd.total_est'))}",
    ]
    return "\n".join(lines)


def render_rec_p1(rec: Mapping[str, Any], p1: Mapping[str, Any], operation_seconds: Any = None) -> str:
    rec_cost = first(rec, "cost_usd.total_est")
    p1_cost = first(p1, "cost_usd.total_est")
    try:
        total_cost = cost(float(rec_cost or 0) + float(p1_cost or 0))
    except Exception:
        total_cost = "n/a"
    lines = [
        f"📄 REC Post ID: {post_id(rec)}",
        f"🔗 REC: {no_embed_url(public_url(rec))}",
        f"✏️ Edit REC: {no_embed_url(edit_url(rec))}",
        f"🔗 Slug: {slug(rec)}",
        f"📌 Status: {status(rec)}",
        "",
        f"📄 P1 Post ID: {post_id(p1)}",
        f"🔗 P1 : {no_embed_url(public_url(p1))}",
        f"✏️ Edit P1: {no_embed_url(edit_url(p1))}",
        f"🔗 Slug: {slug(p1)}",
        f"📌 Status: {status(p1)}",
        "",
        *render_block(rec, "rec"),
        "",
        *render_block(p1, "p1"),
        "",
        f"⏱️ Tempo total da operação: {duration(operation_seconds) if operation_seconds not in (None, '') else duration((float(first(rec, 'duration_sec', default=0) or 0) + float(first(p1, 'duration_sec', default=0) or 0)))}",
        f"💰 Custo estimado: REC {cost(rec_cost)} + P1 {cost(p1_cost)} = {total_cost}",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--type", choices=["rec", "p1", "rec-p1"], required=True)
    parser.add_argument("--operation-seconds", type=float, default=None, help="User-perceived elapsed seconds from request receipt to final summary")
    parser.add_argument("--started-at", default=None, help="ISO timestamp or epoch captured when the user request was received")
    args = parser.parse_args()
    operation_seconds = args.operation_seconds
    if operation_seconds is None:
        operation_seconds = operation_duration_from_started(args.started_at)

    if args.type == "rec":
        if len(args.paths) != 1:
            parser.error("--type rec requires exactly 1 JSON path")
        print(render_rec(load_json(args.paths[0]), operation_seconds))
    elif args.type == "p1":
        if len(args.paths) != 1:
            parser.error("--type p1 requires exactly 1 JSON path")
        print(render_p1(load_json(args.paths[0]), operation_seconds))
    else:
        if len(args.paths) != 2:
            parser.error("--type rec-p1 requires REC JSON path and P1 JSON path")
        print(render_rec_p1(load_json(args.paths[0]), load_json(args.paths[1]), operation_seconds))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
