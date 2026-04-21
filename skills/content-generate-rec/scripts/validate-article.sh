#!/bin/bash
set -e

HTML_FILE="${1:?usage: validate-article.sh <html_file>}"
MIN=450
MAX=500

[ -f "$HTML_FILE" ] || { echo "ERROR: file not found: $HTML_FILE" >&2; exit 1; }

# Strip Gutenberg comments + HTML tags + entities, then count alphanumeric tokens
count=$(sed -E '
  s/<!--[^>]*-->//g
  s/<[^>]+>/ /g
  s/&nbsp;/ /g
  s/&[a-zA-Z]+;/ /g
' "$HTML_FILE" | tr -s '[:space:]' ' ' | tr ' ' '\n' | grep -cE "^[[:alnum:]'’-]+$")

if [ "$count" -ge "$MIN" ] && [ "$count" -le "$MAX" ]; then
  jq -n --argjson c "$count" --argjson mn "$MIN" --argjson mx "$MAX" \
    '{count:$c, min:$mn, max:$mx, status:"PASS"}'
  exit 0
else
  jq -n --argjson c "$count" --argjson mn "$MIN" --argjson mx "$MAX" \
    '{count:$c, min:$mn, max:$mx, status:"FAIL"}'
  exit 1
fi
