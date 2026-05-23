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
    public_check = f"HTTP {public_http}" if public_http else "Verificado"
    redirect_ok = "Verificado" if get(data, "public_verify.contains_redirected") and get(data, "public_verify.contains_official_url") else "Verificar"
    media_audit = "P1 OK / card reutilizado do REC / featured presente / card presente na página pública" if get(data, "images.card_reused_from_rec") else "P1 OK / featured presente / card presente na página pública"

    lines = [
        f"{RODOLFO} ✅ P1 do **{card}** publicada no {site}.",
        "",
        f"📄 **Post ID:** `{post_id}`",
        f"🔗 **Artigo:** <{public_url}>",
        f"✏️ **Edit:** <{edit_url}>",
    ]
    if rec_url:
        lines.append(f"↩️ **REC de origem:** <{rec_url}>")
    lines += [
        "",
        f"📌 **Site:** `{site}` | **Vertical:** `GB / CC / EN` | **Status:** `{status_label}`",
        f"🔗 **Slug:** `{slug}`",
        "",
        f"📊 **Yoast:** SEO **{seo_score}** {score_emoji(seo_score)} | Readability **{read_score}** {score_emoji(read_score)}",
        f"📝 **Palavras:** **{public_words}** schema público / **{validation_words}** validação interna",
        f"🏷️ **Title:** {title}",
        f"🔢 **Title — caracteres:** `{title_chars}`",
        f"💬 **Sub-title:** {subtitle}",
        f"🔢 **Sub-title — caracteres:** `{subtitle_chars}`",
        f"🔍 **Focus:** `{focus}`",
        f"🧾 **Meta:** {meta}",
        f"🔢 **Meta description — caracteres:** `{meta_chars}`",
        "",
        f"🏷️ **Tags:** {tags_line}",
        "",
        "🟢 **CTA:** `APPLY NOW` | **Microcopy:** `You will be redirected.`",
        f"🏦 **Fonte oficial:** <{official_url}>",
        f"✅ **Página pública:** {public_check} | **Redirect/URL oficial:** {redirect_ok}",
        "",
        "🖼️ **Imagens:**",
        f"• **Imagem P1:** <{featured_url}>",
        f"• **Card image:** <{card_url}>",
        f"• **Auditoria:** {media_audit}",
        "",
        f"⏱️ **Tempo total:** `{duration}` | 💰 **Custo:** `{cost_str}`",
        "",
        f"{RAQUEL} P1 publicada e validada.",
    ]
    print("\n".join(lines))

if __name__ == "__main__":
    main()
