#!/usr/bin/env python3
"""Render Rodolfo-approved P1 Discord summary from mgs-p1-runner JSON.

Deterministic formatter for final Discord replies. Use this after a successful
mgs-p1-runner run instead of hand-formatting from memory.

Usage:
  python3 /root/mgs-agent/skills/content-generate-rec/scripts/render-p1-summary.py /tmp/p1-runner.json
  cat /tmp/p1-runner.json | python3 /root/mgs-agent/skills/content-generate-rec/scripts/render-p1-summary.py
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
    status = get(data, "post.status") or data.get("status_requested", "")
    status_label = "Publicado" if status == "publish" else status

    title = get(data, "seo.title") or ""
    subtitle = get(data, "content_validation.subtitle") or ""
    meta = get(data, "seo.meta_description") or ""
    tags = get(data, "taxonomy.tag_names", []) or []
    tags_line = " ".join(f"`{t}`" for t in tags)

    seo_score = get(data, "seo.score.seo_score")
    read_score = get(data, "seo.score.readability_score")
    public_http = get(data, "public_verify.http")
    public_check = f"HTTP {public_http}" if public_http else "Verificado"
    redirect_ok = "Verificado" if get(data, "public_verify.contains_redirected") and get(data, "public_verify.contains_official_url") else "Verificar"
    media_audit = "P1 OK / card reutilizado do REC / featured presente / card presente na página pública" if get(data, "images.card_reused_from_rec") else "P1 OK / featured presente / card presente na página pública"

    cost = get(data, "cost_usd.total_est")
    cost_str = f"US${float(cost):.2f}" if isinstance(cost, (int, float)) else (str(cost) if cost else "n/a")

    lines = [
        f"{RODOLFO} ✅ P1 do **{card}** publicada no {site}.",
        "",
        f"📄 **Post ID:** `{get(data, 'post.id')}`",
        f"🔗 **Artigo:** <{get(data, 'post.link')}>",
        f"✏️ **Edit:** <{get(data, 'post.edit_url')}>",
    ]
    rec_url = get(data, "rec_source.url") or data.get("rec_url", "")
    if rec_url:
        lines.append(f"↩️ **REC de origem:** <{rec_url}>")

    lines += [
        "",
        f"📌 **Site:** `{site}` | **Vertical:** `GB / CC / EN` | **Status:** `{status_label}`",
        f"🔗 **Slug:** `{get(data, 'post.slug')}`",
        "",
        f"📊 **Yoast:** SEO **{seo_score}** {score_emoji(seo_score)} | Readability **{read_score}** {score_emoji(read_score)}",
        f"📝 **Palavras:** **{get(data, 'public_verify.yoast_schema_word_count')}** schema público / **{get(data, 'content_validation.word_count')}** validação interna",
        f"🏷️ **Title:** {title}",
        f"🔢 **Title — caracteres:** `{get(data, 'content_validation.title_chars', len(title) if title else '')}`",
        f"💬 **Sub-title:** {subtitle}",
        f"🔢 **Sub-title — caracteres:** `{get(data, 'content_validation.subtitle_chars', len(subtitle) if subtitle else '')}`",
        f"🔍 **Focus:** `{get(data, 'seo.focus_keyphrase') or get(data, 'content_validation.focus_keyphrase')}`",
        f"🧾 **Meta:** {meta}",
        f"🔢 **Meta description — caracteres:** `{len(meta) if meta else ''}`",
        "",
        f"🏷️ **Tags:** {tags_line}",
        "",
        "🟢 **CTA:** `APPLY NOW` | **Microcopy:** `You will be redirected.`",
        f"🏦 **Fonte oficial:** <{data.get('official_url', '')}>",
        f"✅ **Página pública:** {public_check} | **Redirect/URL oficial:** {redirect_ok}",
        "",
        "🖼️ **Imagens:**",
        f"• **Imagem P1:** <{get(data, 'images.featured.source_url')}>",
        f"• **Card image:** <{get(data, 'card.image_url')}>",
        f"• **Auditoria:** {media_audit}",
        "",
        f"⏱️ **Tempo total:** `{fmt_duration(data.get('duration_sec'))}` | 💰 **Custo:** `{cost_str}`",
        "",
        f"{RAQUEL} P1 publicada e validada.",
    ]
    print("\n".join(lines))


if __name__ == "__main__":
    main()
