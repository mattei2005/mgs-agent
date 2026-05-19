#!/bin/bash
set -euo pipefail

# Generate a clean card-only asset from a user-supplied manual card image.
# Use only when crop/trim leaves a low-quality small card crop but the same
# source worked well as a reference for Gemini featured generation.

[ -f /root/mgs-agent/.env ] && set -a && . /root/mgs-agent/.env && set +a

SLUG="${1:?usage: generate-clean-card-image.sh <slug> <manual_card_image_path>}"
CARD_IMG="${2:?missing manual_card_image_path}"
LOG="/root/mgs-agent/logs/generate-rec.log"
OUT="/tmp/card-clean-${SLUG}.png"

TEMP_FILES=()
cleanup_temps() {
  local f
  for f in "${TEMP_FILES[@]:-}"; do
    [ -n "$f" ] || continue
    echo "[$(date -Iseconds)] generate-clean-card-image CLEANUP tmp=$f slug=$SLUG" >>"$LOG"
    rm -f "$f"
  done
}
trap 'cleanup_temps' EXIT

[ -f "$CARD_IMG" ] || { echo "ERROR: card image not found: $CARD_IMG" >&2; exit 1; }

api_key=$(op item get "Gemini API Key" --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" --fields api_key --reveal 2>/dev/null) || {
  echo "ERROR: could not read Gemini API Key from 1Password" >&2
  exit 1
}

mime=$(file -b --mime-type "$CARD_IMG" 2>/dev/null || echo "image/png")
b64_tmp=$(mktemp /tmp/gemini-card-b64-XXXXXX)
TEMP_FILES+=("$b64_tmp")
base64 -w0 "$CARD_IMG" | tr -d '\n' > "$b64_tmp"

prompt=$(cat <<'PROMPT'
Create a clean, high-resolution, card-only PNG asset from the reference image.

Critical requirements:
- Output only the credit card artwork itself, centered and horizontal.
- Remove all outside background/canvas, borders, shadows, people, scenery, video thumbnail padding, and promotional layout.
- Preserve the exact issuer/card design from the reference as much as possible: colors, logo placement, VISA mark, chip, contactless symbol, number layout, text placement, and proportions.
- Do not invent a different card design, do not change brand, do not add hands, phones, app screens, badges, text labels, frames, or decorative panels.
- Make the card sharp and suitable for a WordPress credit-card LazyBlock.
- Keep rounded corners clean.
- Prefer transparent background. If transparency is not possible, use a plain white background tightly cropped to the card bounds.

Output: one high-resolution horizontal card-only image, no scene, no person.
PROMPT
)

req_tmp=$(mktemp /tmp/gemini-card-req-XXXXXX)
TEMP_FILES+=("$req_tmp")
jq -n \
  --arg text "$prompt" \
  --arg mime "$mime" \
  --rawfile data "$b64_tmp" \
  '{contents:[{parts:[{text:$text},{inline_data:{mime_type:$mime,data:$data}}]}]}' \
  > "$req_tmp"

endpoint="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key=${api_key}"

max_attempts=3
attempt=1
while [ "$attempt" -le "$max_attempts" ]; do
  tmp_body=$(mktemp)
  http_code=$(curl -sS -o "$tmp_body" -w '%{http_code}' \
    -H "Content-Type: application/json" -X POST -d @"$req_tmp" "$endpoint" || echo "000")
  body=$(cat "$tmp_body")
  rm -f "$tmp_body"

  if [ "$http_code" = "429" ] || [ "$http_code" = "503" ]; then
    echo "[$(date -Iseconds)] generate-clean-card-image RETRY attempt=$attempt http=$http_code slug=$SLUG" >>"$LOG"
    if [ "$attempt" -lt "$max_attempts" ]; then
      sleep 5
      attempt=$((attempt+1))
      continue
    fi
  fi

  if [ "$http_code" != "200" ]; then
    echo "[$(date -Iseconds)] generate-clean-card-image FAIL http=$http_code slug=$SLUG body=$(echo "$body" | head -c 500)" >>"$LOG"
    echo "ERROR: Gemini returned HTTP $http_code. Body head: $(echo "$body" | head -c 500)" >&2
    exit 1
  fi

  img_b64=$(jq -r '.candidates[0].content.parts[]? | (.inlineData // .inline_data) | .data // empty' <<<"$body" | head -n1)
  if [ -z "$img_b64" ] || [ "$img_b64" = "null" ]; then
    echo "[$(date -Iseconds)] generate-clean-card-image NO-IMAGE slug=$SLUG body=$(echo "$body" | head -c 500)" >>"$LOG"
    echo "ERROR: Gemini returned no image. Response head: $(echo "$body" | head -c 500)" >&2
    exit 1
  fi

  echo "$img_b64" | base64 -d >"$OUT"
  /root/mgs-agent/scripts/normalize-card-artwork.py "$OUT" "$OUT" --aggressive --min-width 0 >/tmp/normalize-card-clean-${SLUG}.json || true
  echo "[$(date -Iseconds)] generate-clean-card-image OK slug=$SLUG attempt=$attempt path=$OUT" >>"$LOG"
  jq -n --arg p "$OUT" --argjson a "$attempt" '{path:$p, attempt:$a, mode:"gemini_clean_card_asset"}'
  exit 0
done
