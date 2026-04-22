#!/bin/bash
set -e

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

if [ "$count" -ge "$MIN" ] && [ "$count" -le "$MAX" ]; then
  jq -n --argjson c "$count" --argjson mn "$MIN" --argjson mx "$MAX" \
    '{count:$c, min:$mn, max:$mx, status:"PASS"}'
  exit 0
else
  jq -n --argjson c "$count" --argjson mn "$MIN" --argjson mx "$MAX" \
    '{count:$c, min:$mn, max:$mx, status:"FAIL"}'
  exit 1
fi
