#!/bin/bash
set -e

CARD_NAME="${1:?usage: search-card-image.sh <card_name> <card_official_url>}"
OFFICIAL_URL="${2:?missing card_official_url}"
LOG="/root/mgs-agent/logs/generate-rec.log"

slug=$(echo "$CARD_NAME" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g')

emit_needs_manual() {
  local reason="$1"
  echo "[$(date -Iseconds)] search-card-image NEEDS-MANUAL card=$CARD_NAME url=$OFFICIAL_URL reason=$reason" >>"$LOG"
  jq -n --arg r "$reason" --arg c "$CARD_NAME" --arg u "$OFFICIAL_URL" \
    '{path:null, mime:null, tier:0, source:null, status:"NEEDS_MANUAL", reason:$r, card_name:$c, url:$u}'
  exit 1
}

# Fetch official page
html=$(curl -sS -L -A "Mozilla/5.0" "$OFFICIAL_URL" 2>/dev/null) || emit_needs_manual "fetch_failed"
[ -z "$html" ] && emit_needs_manual "empty_page"

base_host=$(echo "$OFFICIAL_URL" | sed -E 's#^(https?://[^/]+).*#\1#')
candidates=$(echo "$html" | grep -oE '(src|data-src|data-lazy-src)="[^"]+\.(png|jpe?g|webp)"' \
  | sed -E 's/^[^"]+"([^"]+)".*/\1/' \
  | sort -u)

abs_candidates=$(while IFS= read -r u; do
  [ -z "$u" ] && continue
  case "$u" in
    http*) echo "$u" ;;
    //*)   echo "https:$u" ;;
    /*)    echo "$base_host$u" ;;
    *)     echo "$base_host/$u" ;;
  esac
done <<<"$candidates")

[ -z "$abs_candidates" ] && emit_needs_manual "no_image_tags_on_page"

kw=$(echo "$slug" | tr '-' '|')
scored=$(while IFS= read -r u; do
  [ -z "$u" ] && continue
  score=0
  low=$(echo "$u" | tr '[:upper:]' '[:lower:]')
  echo "$low" | grep -qE "($kw)" && score=$((score+5))
  echo "$low" | grep -qE '(card|visa|mastercard|amex|gold|platinum|classic|credit)' && score=$((score+2))
  [[ "$low" == *.png ]] && score=$((score+3))
  [[ "$low" == *.webp ]] && score=$((score+1))
  echo "$low" | grep -qE '(logo|icon|sprite|favicon|hero|banner)' && score=$((score-4))
  echo "$score $u"
done <<<"$abs_candidates" | sort -rn)

best=$(echo "$scored" | head -n1 | awk '{print $2}')
best_score=$(echo "$scored" | head -n1 | awk '{print $1}')

if [ -z "$best" ] || [ "$best_score" -le 0 ]; then
  emit_needs_manual "scoring_no_match"
fi

ext="${best##*.}"
ext="${ext%%\?*}"
ext=$(echo "$ext" | tr '[:upper:]' '[:lower:]')
case "$ext" in png|jpg|jpeg|webp) ;; *) ext="png" ;; esac

out="/tmp/card-$slug.$ext"
curl -sS -L -A "Mozilla/5.0" -o "$out" "$best" || emit_needs_manual "download_failed"
[ -s "$out" ] || emit_needs_manual "download_empty"
mime=$(file -b --mime-type "$out" 2>/dev/null || echo "image/$ext")

# Classify tier:
#  1 = official + PNG with alpha
#  2 = official + PNG (no alpha / unknown)
#  3 = official + JPG/webp (has background)
#  4 = non-official source
best_host=$(echo "$best" | sed -E 's#^(https?://[^/]+).*#\1#')
is_official=0
[ "$best_host" = "$base_host" ] && is_official=1

if [ "$is_official" = "1" ]; then
  if [ "$ext" = "png" ]; then
    tier=2
    if command -v identify >/dev/null 2>&1; then
      alpha=$(identify -format '%[channels]' "$out" 2>/dev/null || echo "")
      [[ "$alpha" == *a* ]] && tier=1
    fi
  else
    tier=3
  fi
else
  tier=4
fi

if [ "$tier" -ge 3 ]; then
  echo "[$(date -Iseconds)] search-card-image WARN MANUAL REVIEW RECOMMENDED tier=$tier card=$CARD_NAME path=$out src=$best (image may have background or be off-brand)" >>"$LOG"
else
  echo "[$(date -Iseconds)] search-card-image OK tier=$tier card=$CARD_NAME path=$out src=$best" >>"$LOG"
fi

jq -n --arg p "$out" --arg m "$mime" --argjson t "$tier" --arg s "$best" \
  --arg st "OK" \
  '{path:$p, mime:$m, tier:$t, source:$s, status:$st}'
