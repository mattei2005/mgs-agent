#!/bin/bash
set -euo pipefail

# Load env vars (OP_DEFAULT_VAULT, etc.) — runs under systemd/cron too
[ -f /root/mgs-agent/.env ] && set -a && . /root/mgs-agent/.env && set +a

SLUG="${1:?usage: generate-featured-image.sh <slug> <card_image_path>}"
CARD_IMG="${2:?missing card_image_path}"
LOG="/root/mgs-agent/logs/generate-rec.log"

TEMP_FILES=()
cleanup_temps() {
  local f
  for f in "${TEMP_FILES[@]}"; do
    [ -n "$f" ] || continue
    echo "[$(date -Iseconds)] generate-featured-image CLEANUP tmp=$f slug=$SLUG" >>"$LOG"
    rm -f "$f"
  done
}
trap 'cleanup_temps' EXIT

[ -f "$CARD_IMG" ] || { echo "ERROR: card image not found: $CARD_IMG" >&2; exit 1; }

api_key=$(op item get "Gemini API Key" --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" --fields api_key --reveal 2>/dev/null) || {
  echo "ERROR: could not read Gemini API Key from 1Password" >&2
  exit 1
}

scenes=(
  "modern financial district"
  "upscale café"
  "luxury hotel lounge"
  "premium office"
  "elegant home interior"
  "rooftop with skyline"
  "airport lounge"
  "contemporary coworking"
  "urban street with cinematic blur"
  "city at sunset"
  "nighttime metropolis"
)
scene="${scenes[$RANDOM % ${#scenes[@]}]}"

mime=$(file -b --mime-type "$CARD_IMG" 2>/dev/null || echo "image/png")
b64_tmp=$(mktemp /tmp/gemini-b64-XXXXXX)
TEMP_FILES+=("$b64_tmp")
base64 -w0 "$CARD_IMG" | tr -d '\n' > "$b64_tmp"

prompt=$(cat <<PROMPT
You must compose a photo-realistic 16:9 (1920x1080) horizontal image using the
EXACT credit card provided as the reference image. Do NOT redesign, recolor,
or recreate the card — it must appear identical in colors, logo, layout and
proportions.

Scene: $scene.
Composition:
- ONE realistic person in the foreground (medium shot or bust shot).
- The card appears LARGE, floating BEHIND the person (never held or touched).
- Card centered or slightly to the right, in the midground, partially
  occluded by the person for depth.
- Premium background with cinematic bokeh.

Style: ultra-realistic commercial photography (full-frame camera), cinematic
key + soft fill + subtle rim light, realistic card reflections, soft natural
shadows, premium campaign color grading.

Negative: multiple people, person touching/holding the card, altered card
design, distorted anatomy, extra fingers, fake smile, cartoon, illustration,
CGI, 3D render, stock photo look, flat lighting.

Output: one image, 16:9, photo-realistic.
PROMPT
)

req_tmp=$(mktemp /tmp/gemini-req-XXXXXX)
TEMP_FILES+=("$req_tmp")
jq -n \
  --arg text "$prompt" \
  --arg mime "$mime" \
  --rawfile data "$b64_tmp" \
  '{contents:[{parts:[{text:$text},{inline_data:{mime_type:$mime,data:$data}}]}]}' \
  > "$req_tmp"

endpoint="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key=$api_key"
out="/tmp/featured-$SLUG.png"

max_attempts=3
attempt=1
while [ "$attempt" -le "$max_attempts" ]; do
  tmp_body=$(mktemp)
  http_code=$(curl -sS -o "$tmp_body" -w '%{http_code}' \
    -H "Content-Type: application/json" -X POST -d @"$req_tmp" "$endpoint" || echo "000")
  body=$(cat "$tmp_body")
  rm -f "$tmp_body"

  if [ "$http_code" = "429" ] || [ "$http_code" = "503" ]; then
    echo "[$(date -Iseconds)] generate-featured-image RETRY attempt=$attempt http=$http_code slug=$SLUG" >>"$LOG"
    if [ "$attempt" -lt "$max_attempts" ]; then
      sleep 5
      attempt=$((attempt+1))
      continue
    else
      echo "[$(date -Iseconds)] generate-featured-image ABORT slug=$SLUG after $max_attempts attempts (rate-limit)" >>"$LOG"
      echo "ERROR: Gemini rate-limited after $max_attempts attempts. Last HTTP=$http_code body head: $(echo "$body" | head -c 400)" >&2
      exit 1
    fi
  fi

  if [ "$http_code" != "200" ]; then
    echo "[$(date -Iseconds)] generate-featured-image FAIL http=$http_code slug=$SLUG body=$(echo "$body" | head -c 500)" >>"$LOG"
    echo "ERROR: Gemini returned HTTP $http_code. Body head: $(echo "$body" | head -c 500)" >&2
    exit 1
  fi

  img_b64=$(jq -r '.candidates[0].content.parts[]? | (.inlineData // .inline_data) | .data // empty' <<<"$body" | head -n1)
  if [ -z "$img_b64" ] || [ "$img_b64" = "null" ]; then
    echo "[$(date -Iseconds)] generate-featured-image NO-IMAGE slug=$SLUG body=$(echo "$body" | head -c 500)" >>"$LOG"
    echo "ERROR: Gemini returned no image. Response head: $(echo "$body" | head -c 500)" >&2
    exit 1
  fi

  echo "$img_b64" | base64 -d >"$out"

  # Comprimir PNG -> JPEG (reduz ~94%, qualidade visual mantida)
  SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
  out=$("$SCRIPT_DIR/compress-image.sh" "$out" featured)

  echo "[$(date -Iseconds)] generate-featured-image OK slug=$SLUG scene=$scene attempt=$attempt path=$out" >>"$LOG"
  jq -n --arg p "$out" --arg s "$scene" --argjson a "$attempt" '{path:$p, scene:$s, attempt:$a}'
  exit 0
done
