#!/bin/bash
set -euo pipefail

# Load env vars (OP_DEFAULT_VAULT, etc.) — runs under systemd/cron too
# shellcheck source=/dev/null
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

api_key=$(op item get "Gemini API Key - MGS Core" --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" --fields api_key --reveal 2>/dev/null) || {
  echo "ERROR: could not read Gemini API Key - MGS Core from 1Password" >&2
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
  "supermarket checkout"
  "restaurant payment moment"
  "home budgeting desk"
  "travel desk with passport and luggage tag"
)
scene="${scenes[$RANDOM % ${#scenes[@]}]}"

# Visual variation prevents category pages from looking repetitive. These are
# generic finance/lifestyle compositions inspired by common editorial patterns,
# not by any competitor's branded overlays, logos, or corner graphics.
visual_briefs=(
  "large centered card floating in front of one confident person, premium editorial composition"
  "close-up hand holding the card toward the camera, shallow depth of field, fingers do not cover issuer logo or payment network mark"
  "contactless payment moment with the card near a generic payment terminal, no merchant logos, card remains readable"
  "card partially entering or leaving a wallet or jacket pocket, lifestyle banking moment, card brand still visible"
  "flat lay desk scene with card beside smartphone, receipts and coffee, clean budgeting context"
  "online shopping context with laptop and parcel in background, card in foreground, no visible retailer logos"
  "travel context with passport, boarding-pass-like generic paper and card, no airline logos"
  "cashback/rewards context with shopping bag, hotel loyalty vibe and premium lifestyle props, no graphic icons, badges or text overlays"
)
visual_brief="${visual_briefs[$RANDOM % ${#visual_briefs[@]}]}"
mode_label="REC featured image"
mode_distinction="This is the REC featured image: it should feel like a quick commercial recommendation hook, lifestyle/payment/rewards oriented, not an application explainer."

if [[ "$SLUG" == p1-* ]]; then
  # P1 must not look like a reused REC hero. Force a different intent and
  # composition family: application/deep-dive support, more explanatory and
  # decision-oriented, with distinct background/framing from the REC image.
  mode_label="P1 featured image"
  scene="application review desk or modern advisory office"
  visual_brief="P1 application/deep-dive support scene: realistic person reviewing card details on a desk or in an advisory setting, exact card centred but not in the same lifestyle/payment composition as REC, different background and framing, calm decision-oriented mood"
  mode_distinction="This is the P1 featured image. It must be visually distinct from the REC featured image for the same card: different scene, framing, background/foreground treatment and editorial intent. Do not recreate the REC lifestyle/payment hook."
fi

mime=$(file -b --mime-type "$CARD_IMG" 2>/dev/null || echo "image/png")
b64_tmp=$(mktemp /tmp/gemini-b64-XXXXXX)
TEMP_FILES+=("$b64_tmp")
base64 -w0 "$CARD_IMG" | tr -d '\n' > "$b64_tmp"

prompt=$(cat <<PROMPT
You must compose a photo-realistic 16:9 (1920x1080) horizontal lifestyle/finance
background scene. The exact credit card will be composited separately by the
pipeline after generation. Do NOT generate, draw, recreate, duplicate, or place
any credit card, debit card, payment card, bank card, card-shaped mockup, badge,
or card-like rectangle in the scene.

Scene: $scene.
Image role: $mode_label.
Visual variation for this run: $visual_brief.
Role-specific distinction: $mode_distinction.

Composition rules:
- Leave a clean natural central foreground area where the pipeline can later
  place the exact card. Do not put any object shaped like a payment card there.
- For P1 images, follow this intent: realistic full-scene background with depth,
  calm decision-oriented desk/advisory mood, and no generated card object.
- Do not add borders, frames, moulding, stickers, badges, glow outlines, or
  external graphic effects.
- Use the selected visual variation naturally; do not force the same centered-card
  layout every time.
- Acceptable variations include: generic payment terminal in the background,
  smartphone, receipts, coffee, budgeting desk, wallet, shopping/rewards context,
  travel context, or one person in a realistic finance/lifestyle setting.
- If a hand is present, it must not hold a card or card-like object.
- Use only generic props. No competitor logo, no site logo, no branded corner
  overlay, no blue corner effect copied from another site, no retailer/airline/
  merchant logos.
- Keep the scene clean: no cards, no duplicate cards, no extra card designs, no UI overlay,
  no stickers, no badges, no text labels.

Style: ultra-realistic commercial photography (full-frame camera), cinematic
key + soft fill + subtle rim light, realistic card reflections, soft natural
shadows, premium editorial color grading. Vary camera angle and distance across
runs: close-up, flat lay, over-the-shoulder, payment moment, lifestyle portrait,
or product-focused foreground.

Negative: credit card, debit card, payment card, bank card, card-like rectangle,
competitor branding, Memivi logo, blue corner overlay, picture frame, mockup frame,
extra card, duplicate card, phone screen with readable UI, badge, sticker,
unnecessary objects, altered card design, vertical card orientation, distorted
anatomy, extra fingers, fake smile, cartoon, illustration, CGI, 3D render, stock
photo look, flat lighting.

Output: one image, 16:9, photo-realistic.
PROMPT
)

req_tmp=$(mktemp /tmp/gemini-req-XXXXXX)
TEMP_FILES+=("$req_tmp")
jq -n \
  --arg text "$prompt" \
  --arg mime "$mime" \
  --rawfile data "$b64_tmp" \
  '{contents:[{parts:[{text:$text},{inline_data:{mime_type:$mime,data:$data}}]}],generationConfig:{responseModalities:["TEXT","IMAGE"],imageConfig:{aspectRatio:"16:9"}}}' \
  > "$req_tmp"

endpoint="https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key=$api_key"
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

  # Preserve card identity deterministically: Gemini may alter small card text,
  # so compose the exact provided card artwork over the generated scene before
  # compression/semantic audit.
  composite_card=$(mktemp /tmp/featured-card-overlay-XXXXXX.png)
  composite_shadow=$(mktemp /tmp/featured-card-shadow-XXXXXX.png)
  composite_out=$(mktemp /tmp/featured-composite-XXXXXX.png)
  TEMP_FILES+=("$composite_card" "$composite_shadow" "$composite_out")
  convert "$CARD_IMG" -resize '760x430>' "$composite_card"
  convert "$composite_card" -background black -shadow 35x18+0+18 "$composite_shadow"
  convert "$out" -resize 1920x1080^ -gravity center -extent 1920x1080 \
    "$composite_shadow" -gravity center -geometry +0+34 -compose over -composite \
    "$composite_card" -gravity center -geometry +0+0 -compose over -composite \
    "$composite_out"
  cp "$composite_out" "$out"

  # Comprimir PNG -> JPEG (reduz ~94%, qualidade visual mantida)
  SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
  out=$("$SCRIPT_DIR/compress-image.sh" "$out" featured)

  echo "[$(date -Iseconds)] generate-featured-image OK slug=$SLUG scene=$scene visual_brief=$visual_brief attempt=$attempt path=$out" >>"$LOG"
  jq -n --arg p "$out" --arg s "$scene" --arg v "$visual_brief" --argjson a "$attempt" '{path:$p, scene:$s, visual_brief:$v, attempt:$a}'
  exit 0
done
