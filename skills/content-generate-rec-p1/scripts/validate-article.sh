#!/bin/bash
set -euo pipefail

HTML_FILE="${1:?usage: validate-article.sh <html_file>}"
MIN=450
MAX=500

[ -f "$HTML_FILE" ] || { echo "ERROR: file not found: $HTML_FILE" >&2; exit 1; }

# Count visible words in the article body.
# INCLUDES: subtitle (first paragraph), body paragraphs, H2 headings, table content.
# EXCLUDES: LazyBlock card block, LazyBlock CTA button, HTML tags, Gutenberg comments.
#
# Word token definition: any whitespace-separated token containing at least one
# letter or digit (matches human/WP word counter behaviour).
count=$(python3 - "$HTML_FILE" <<'PYEOF'
import sys, re

with open(sys.argv[1]) as f:
    content = f.read()

# Remove LazyBlock lines (single-line self-closing: <!-- wp:lazyblock/... /-->)
content = re.sub(r'<!--\s*wp:lazyblock/.*?/-->', '', content)

# Remove all Gutenberg block comments (<!-- wp:... --> and <!-- /wp:... -->)
content = re.sub(r'<!--.*?-->', ' ', content, flags=re.DOTALL)

# Remove HTML tags
content = re.sub(r'<[^>]+>', ' ', content)

# Decode common HTML entities
content = content.replace('&amp;', '&').replace('&nbsp;', ' ')
content = re.sub(r'&[a-zA-Z0-9#]+;', ' ', content)

# Normalise whitespace
content = re.sub(r'\s+', ' ', content).strip()

# Count tokens with at least one letter or digit — matches WP/human word count
# (includes numbers like 20,000 and £24, excludes pure punctuation like — or +)
tokens = [t for t in content.split() if re.search(r'[a-zA-Z0-9]', t)]
print(len(tokens))
PYEOF
)

# Extract subtitle (first visible paragraph — the excerpt)
subtitle=$(python3 - "$HTML_FILE" <<'PYEOF2'
import sys, re
with open(sys.argv[1]) as f:
    content = f.read()
# Remove LazyBlock lines
content = re.sub(r'<!--\s*wp:lazyblock/.*?/-->', '', content)
# Find first <p>...</p>
m = re.search(r'<p>(.*?)</p>', content, re.DOTALL)
if not m:
    print("")
else:
    text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    print(text)
PYEOF2
)

subtitle_len=${#subtitle}
SUBTITLE_MAX=100

# Editorial readability/style checks from Atena documentation:
# - Every paragraph should stay <=30 words (roughly max 3 visual lines)
# - Each section under one H2 should have max 4 paragraphs
# - No more than 20% of sentences may exceed 20 words
style_json=$(python3 - "$HTML_FILE" <<'PYEOF3'
import html, json, re, sys

with open(sys.argv[1], encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'<!--\s*wp:lazyblock/.*?/-->', '', content, flags=re.S)

blocks = re.findall(r'<h2\b[^>]*>.*?</h2>|<p>.*?</p>', content, flags=re.I|re.S)
sections = []
current = {"heading": "intro", "paragraphs": []}
paragraphs = []
sentences = []

def clean(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    s = html.unescape(s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

for b in blocks:
    if re.match(r'<h2\b', b, flags=re.I):
        sections.append(current)
        current = {"heading": clean(b), "paragraphs": []}
        continue
    p = clean(b)
    if not p:
        continue
    current["paragraphs"].append(p)
    paragraphs.append(p)
    sentences.extend([x.strip() for x in re.split(r'(?<=[.!?])\s+', p) if x.strip()])
sections.append(current)

def wc(s):
    return len([t for t in s.split() if re.search(r'[A-Za-z0-9]', t)])

para_counts = [wc(p) for p in paragraphs]
avg_para = round(sum(para_counts) / len(para_counts), 2) if para_counts else 0
max_para = max(para_counts) if para_counts else 0
section_counts = [{"heading": s["heading"], "paragraphs": len(s["paragraphs"])} for s in sections if s["paragraphs"]]
max_section_paragraphs = max([s["paragraphs"] for s in section_counts] or [0])
sent_counts = [wc(s) for s in sentences]
long_sentences = [n for n in sent_counts if n > 20]
long_ratio = round((len(long_sentences) / len(sent_counts)) if sent_counts else 0, 4)

ok = avg_para <= 30 and max_para <= 30 and max_section_paragraphs <= 4 and long_ratio <= 0.20
print(json.dumps({
    "avg_paragraph_words": avg_para,
    "max_paragraph_words": max_para,
    "paragraph_count": len(paragraphs),
    "max_section_paragraphs": max_section_paragraphs,
    "section_paragraphs": section_counts,
    "sentence_count": len(sent_counts),
    "long_sentence_count": len(long_sentences),
    "long_sentence_ratio": long_ratio,
    "style": "pass" if ok else "fail",
}))
PYEOF3
)

# Evaluate results
word_ok=false
subtitle_ok=false
style_ok=false

[ "$count" -ge "$MIN" ] && [ "$count" -le "$MAX" ] && word_ok=true
[ "$subtitle_len" -le "$SUBTITLE_MAX" ] && subtitle_ok=true
style_status=$(echo "$style_json" | jq -r '.style // "fail"')
[ "$style_status" = "pass" ] && style_ok=true

if $word_ok && $subtitle_ok && $style_ok; then
  jq -n --argjson c "$count" --argjson mn "$MIN" --argjson mx "$MAX"     --argjson sl "$subtitle_len" --argjson sm "$SUBTITLE_MAX" --argjson style "$style_json"    '{count:$c, min:$mn, max:$mx, subtitle_chars:$sl, subtitle_max:$sm, style:$style, status:"PASS"}'
  exit 0
else
  jq -n --argjson c "$count" --argjson mn "$MIN" --argjson mx "$MAX"     --argjson sl "$subtitle_len" --argjson sm "$SUBTITLE_MAX" --argjson style "$style_json"    --arg wok "$([ "$word_ok" = true ] && echo pass || echo fail)"     --arg sok "$([ "$subtitle_ok" = true ] && echo pass || echo fail)" --arg stok "$([ "$style_ok" = true ] && echo pass || echo fail)"    '{count:$c, min:$mn, max:$mx, word_count:$wok, subtitle_chars:$sl, subtitle_max:$sm, subtitle:$sok, editorial_style:$stok, style:$style, status:"FAIL"}'
  exit 1
fi
