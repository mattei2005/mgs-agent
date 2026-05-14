#!/bin/bash
set -e

CARD_NAME="${1:?usage: search-card-image.sh <card_name> <card_official_url>}"
OFFICIAL_URL="${2:?missing card_official_url}"
LOG="/root/mgs-agent/logs/generate-rec.log"

slug=$(echo "$CARD_NAME" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g')

# Dimension filter thresholds (env-overridable for calibration)
CARD_MIN_WIDTH="${CARD_MIN_WIDTH:-200}"
CARD_MIN_HEIGHT="${CARD_MIN_HEIGHT:-100}"
CARD_ASPECT_MIN="${CARD_ASPECT_MIN:-1.2}"
CARD_ASPECT_MAX="${CARD_ASPECT_MAX:-2.2}"

# Temp file tracking for unified cleanup
TEMP_FILES=()
cleanup_temps() {
  local f
  for f in "${TEMP_FILES[@]}"; do
    [ -n "$f" ] || continue
    rm -f "$f"
  done
}
trap 'cleanup_temps' EXIT

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

# Iterate scored candidates (score > 0) until one passes dimension + aspect filters
best=""
best_score=""
ext=""
out=""

while IFS= read -r line; do
  [ -z "$line" ] && continue
  cand_score=$(echo "$line" | awk '{print $1}')
  cand_url=$(echo "$line" | awk '{print $2}')
  [ "$cand_score" -le 0 ] && break   # scored list is sorted desc by score

  cand_ext="${cand_url##*.}"; cand_ext="${cand_ext%%\?*}"
  cand_ext=$(echo "$cand_ext" | tr '[:upper:]' '[:lower:]')
  case "$cand_ext" in png|jpg|jpeg|webp) ;; *) cand_ext="png" ;; esac
  cand_tmp="/tmp/card-candidate-$slug-$$-$RANDOM.$cand_ext"
  TEMP_FILES+=("$cand_tmp")

  if ! curl -sS -L -A "Mozilla/5.0" -o "$cand_tmp" "$cand_url" 2>/dev/null; then
    echo "[$(date -Iseconds)] search-card-image REJECT download_failed url=$cand_url" >>"$LOG"
    continue
  fi
  [ -s "$cand_tmp" ] || { echo "[$(date -Iseconds)] search-card-image REJECT download_empty url=$cand_url" >>"$LOG"; continue; }

  if ! command -v identify >/dev/null 2>&1; then
    echo "[$(date -Iseconds)] search-card-image WARN identify_unavailable accepting_without_dim_check url=$cand_url" >>"$LOG"
    best="$cand_url"; best_score="$cand_score"; ext="$cand_ext"; out="$cand_tmp"
    break
  fi

  dims=$(identify -format '%w %h' "$cand_tmp" 2>/dev/null || echo "")
  if [ -z "$dims" ]; then
    echo "[$(date -Iseconds)] search-card-image REJECT identify_failed url=$cand_url" >>"$LOG"
    continue
  fi
  w=$(echo "$dims" | awk '{print $1}')
  h=$(echo "$dims" | awk '{print $2}')

  if [ "$w" -lt "$CARD_MIN_WIDTH" ] || [ "$h" -lt "$CARD_MIN_HEIGHT" ]; then
    echo "[$(date -Iseconds)] search-card-image REJECT too_small w=${w} h=${h} (min ${CARD_MIN_WIDTH}x${CARD_MIN_HEIGHT}) url=$cand_url" >>"$LOG"
    continue
  fi

  aspect=$(awk -v w="$w" -v h="$h" 'BEGIN{ printf "%.3f", w/h }')
  in_range=$(awk -v a="$aspect" -v lo="$CARD_ASPECT_MIN" -v hi="$CARD_ASPECT_MAX" 'BEGIN{ print (a>=lo && a<=hi) ? "1" : "0" }')
  if [ "$in_range" != "1" ]; then
    echo "[$(date -Iseconds)] search-card-image REJECT aspect_out_of_range w=${w} h=${h} aspect=${aspect} (expected ${CARD_ASPECT_MIN}-${CARD_ASPECT_MAX}) url=$cand_url" >>"$LOG"
    continue
  fi

  echo "[$(date -Iseconds)] search-card-image ACCEPT w=${w} h=${h} aspect=${aspect} score=${cand_score} url=$cand_url" >>"$LOG"
  best="$cand_url"; best_score="$cand_score"; ext="$cand_ext"; out="$cand_tmp"
  break
done <<<"$scored"

if [ -z "$best" ]; then
  # ── Tentativa 2: Bing Images via Playwright local ───────────────────────
  echo "[$(date -Iseconds)] search-card-image FALLBACK bing_playwright card=$CARD_NAME" >>"$LOG"
  BING_SCRIPT="$(dirname "$0")/search-card-image-bing.py"
  if [ -f "$BING_SCRIPT" ]; then
    bing_result=$(python3 "$BING_SCRIPT" "$CARD_NAME" 2>>"$LOG") || true
    bing_status=$(echo "$bing_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null || echo "")
    if [ "$bing_status" = "OK" ]; then
      bing_path=$(echo   "$bing_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('path',''))"   2>/dev/null || echo "")
      bing_mime=$(echo   "$bing_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('mime',''))"   2>/dev/null || echo "")
      bing_src=$(echo    "$bing_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('source',''))" 2>/dev/null || echo "")
      echo "[$(date -Iseconds)] search-card-image BING_OK path=$bing_path src=$bing_src" >>"$LOG"
      jq -n --arg p "$bing_path" --arg m "$bing_mime" --arg s "$bing_src" \
        '{path:$p, mime:$m, tier:4, source:$s, status:"OK"}'
      exit 0
    fi
  fi
  emit_needs_manual "dimensions_filter_all_rejected_bing_also_failed"
fi

# Move accepted candidate to canonical output path
final_out="/tmp/card-$slug.$ext"
if [ "$out" != "$final_out" ]; then
  mv "$out" "$final_out"
  out="$final_out"
fi
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
