#!/bin/bash
set -euo pipefail

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

normalize_card_image() {
  local img_path="$1"
  [ -f "$img_path" ] || return 1
  python3 - "$img_path" <<'PY' >>"$LOG" 2>&1 || return 1
from PIL import Image
import sys

path = sys.argv[1]
img = Image.open(path)
img.load()

rotated = False
if img.height > img.width:
    img = img.rotate(-90, expand=True)
    rotated = True

rgba = img.convert('RGBA')
pix = rgba.load()
w, h = rgba.size
left, right, top, bottom = w, -1, h, -1

for y in range(h):
    for x in range(w):
        r, g, b, a = pix[x, y]
        # Treat transparent and near-white border/padding as background.
        if a > 20 and not (r > 242 and g > 242 and b > 242):
            left = min(left, x)
            right = max(right, x)
            top = min(top, y)
            bottom = max(bottom, y)

cropped = False
if right >= left and bottom >= top:
    pad = 3
    box = (max(0, left-pad), max(0, top-pad), min(w, right+pad+1), min(h, bottom+pad+1))
    if box != (0, 0, w, h):
        img = img.crop(box)
        cropped = True

if img.mode not in ('RGB', 'RGBA'):
    img = img.convert('RGBA')
img.save(path)
print(f"search-card-image NORMALIZE path={path} rotated={rotated} cropped={cropped} size={img.width}x{img.height}")
PY
}

get_brave_api_key() {
  # Prefer explicit env var so cron/systemd can inject it without 1Password.
  if [ -n "${BRAVE_SEARCH_API_KEY:-}" ]; then
    printf '%s' "$BRAVE_SEARCH_API_KEY"
    return 0
  fi

  # MGS production default: key lives in 1Password. Source .env only for OP token;
  # never print the returned secret. Field label in 1P is "api key".
  if command -v op >/dev/null 2>&1; then
    if [ -f /root/mgs-agent/.env ]; then
      set +u
      set -a
      # shellcheck disable=SC1091
      source /root/mgs-agent/.env >/dev/null 2>&1 || true
      set +a
      set -u
    fi
    op item get "Brave Search API - MGS" \
      --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" \
      --fields "api key" \
      --reveal 2>/dev/null || true
  fi
}

download_and_validate_candidate() {
  local cand_url="$1"
  local cand_ext="$2"
  local cand_tmp="$3"
  local origin="$4"

  if ! curl -sS -L -A "Mozilla/5.0" -o "$cand_tmp" "$cand_url" 2>/dev/null; then
    echo "[$(date -Iseconds)] search-card-image REJECT download_failed origin=$origin url=$cand_url" >>"$LOG"
    return 1
  fi
  [ -s "$cand_tmp" ] || { echo "[$(date -Iseconds)] search-card-image REJECT download_empty origin=$origin url=$cand_url" >>"$LOG"; return 1; }

  if ! command -v identify >/dev/null 2>&1; then
    echo "[$(date -Iseconds)] search-card-image WARN identify_unavailable accepting_without_dim_check origin=$origin url=$cand_url" >>"$LOG"
    return 0
  fi

  dims=$(identify -format '%w %h' "$cand_tmp" 2>/dev/null || echo "")
  if [ -z "$dims" ]; then
    echo "[$(date -Iseconds)] search-card-image REJECT identify_failed origin=$origin url=$cand_url" >>"$LOG"
    return 1
  fi
  w=$(echo "$dims" | awk '{print $1}')
  h=$(echo "$dims" | awk '{print $2}')

  if [ "$w" -lt "$CARD_MIN_WIDTH" ] || [ "$h" -lt "$CARD_MIN_HEIGHT" ]; then
    echo "[$(date -Iseconds)] search-card-image REJECT too_small origin=$origin w=${w} h=${h} (min ${CARD_MIN_WIDTH}x${CARD_MIN_HEIGHT}) url=$cand_url" >>"$LOG"
    return 1
  fi

  aspect=$(awk -v w="$w" -v h="$h" 'BEGIN{ printf "%.3f", w/h }')
  in_range=$(awk -v a="$aspect" -v lo="$CARD_ASPECT_MIN" -v hi="$CARD_ASPECT_MAX" 'BEGIN{ print (a>=lo && a<=hi) ? "1" : "0" }')
  if [ "$in_range" != "1" ]; then
    echo "[$(date -Iseconds)] search-card-image REJECT aspect_out_of_range origin=$origin w=${w} h=${h} aspect=${aspect} (expected ${CARD_ASPECT_MIN}-${CARD_ASPECT_MAX}) url=$cand_url" >>"$LOG"
    return 1
  fi

  echo "[$(date -Iseconds)] search-card-image ACCEPT origin=$origin w=${w} h=${h} aspect=${aspect} url=$cand_url" >>"$LOG"
  return 0
}

run_brave_fallback() {
  # ── Tentativa 2: Brave Images API (sem browser) ────────────────────────
  echo "[$(date -Iseconds)] search-card-image FALLBACK brave_images card=$CARD_NAME" >>"$LOG"

  local brave_key brave_json brave_urls cand_url cand_ext cand_tmp
  brave_key="$(get_brave_api_key | tr -d '\r\n')"
  if [ -z "$brave_key" ]; then
    echo "[$(date -Iseconds)] search-card-image BRAVE_SKIP no_api_key" >>"$LOG"
    return 1
  fi

  brave_json=$(python3 - "$CARD_NAME" "$brave_key" "$OFFICIAL_URL" <<'PY' 2>>"$LOG" || true
import json, re, sys, urllib.parse, urllib.request

card_name, key, official_url = sys.argv[1], sys.argv[2], sys.argv[3]
query = f'{card_name} credit card image'
official_host = (urllib.parse.urlparse(official_url).hostname or '').lower()
brand = re.sub(r'[^a-z0-9]+', ' ', card_name.lower()).split()[0] if card_name else ''
terms = [t for t in re.sub(r'[^a-z0-9]+', ' ', card_name.lower()).split() if t not in {'card', 'credit'}]
exact_phrase = re.sub(r'[^a-z0-9]+', ' ', card_name.lower()).strip()
priority_hosts = {
    'finder.com': 35,
    'finder.com/uk': 35,
    'nerdwallet.com': 25,
    'moneysavingexpert.com': 25,
    'headforpoints.com': 25,
    'backtodefault.com': 25,
    'which.co.uk': 20,
}
hard_noise_hosts = ('play.google.com', 'youtube.com', 'youtu.be', 'facebook.com', 'ytimg.com')
noise_re = re.compile(
    r'(app|mobile|phone|screenshot|screen|google\s*play|play\s*store|youtube|ytimg|facebook|'
    r'hand|hands|person|people|woman|man|avatar|trustpilot|alien|loan|balance\s*transfer|'
    r'virtual\s*card|virtual-assistant|decline|call-us|support|apple\s*pay|google\s*pay|what-is-cc-balance|card-hand|hero|banner|background|illustration|landing)'
)
clean_card_re = re.compile(r'(credit\s*card\s*review|card\s*review|mastercard|contactless|front|card[-_ ].*\.(png|jpg|jpeg|webp))')
url = 'https://api.search.brave.com/res/v1/images/search?' + urllib.parse.urlencode({
    'q': query,
    'count': 20,
    'country': 'GB',
    'search_lang': 'en',
    'safesearch': 'strict',
})
req = urllib.request.Request(url, headers={
    'Accept': 'application/json',
    'X-Subscription-Token': key,
    'User-Agent': 'Hermes-Agent MGS card-image-search',
})
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode('utf-8', 'ignore'))
except Exception as exc:
    print(json.dumps({'status': 'ERROR', 'error': str(exc)}))
    raise SystemExit(0)

out = []
for pos, item in enumerate(data.get('results', []), 1):
    props = item.get('properties') or {}
    thumb = item.get('thumbnail') or {}
    src = props.get('url') or item.get('image') or thumb.get('src')
    page = item.get('url') or ''
    title = item.get('title') or ''
    if not src:
        continue
    src_host = (urllib.parse.urlparse(src).hostname or '').lower()
    page_host = (urllib.parse.urlparse(page).hostname or '').lower()
    hay = f'{title} {page} {src}'.lower()
    score = 100 - pos  # keep Brave order as tie-breaker
    if official_host and (official_host in src_host or official_host in page_host):
        score += 25
    elif brand and (src_host.startswith(brand) or page_host.startswith(brand) or f'.{brand}' in src_host or f'.{brand}' in page_host):
        score += 20
    for host, boost in priority_hosts.items():
        if host in page_host or host in src_host or host in hay:
            score += boost
            break
    term_hits = sum(1 for t in terms if t in hay)
    score += term_hits * 8
    if exact_phrase and exact_phrase in hay:
        score += 28
    if clean_card_re.search(hay):
        score += 24
    if re.search(r'(mastercard|contactless|chip|front|card-front)', hay):
        score += 12
    # A clean isolated card image is preferable to a technically valid promotional banner.
    # Review/comparison pages often host the isolated card artwork when issuers don't expose it.
    if re.search(r'(review|reviews)', hay) and brand and brand in hay:
        score += 12
    if re.search(r'(illustration|hero|banner|background|what-is-cc-balance|card-hand|hand|hands|phone|app|screenshot)', hay):
        score -= 18
    # LazyBlock card image should be product/card artwork, not a contextual scene.
    # Official issuer pages often rank payment/app lifestyle photos very high;
    # these are valid marketing assets but bad card images. Force them below the
    # acceptance threshold unless there is an explicit isolated-card signal.
    isolated_signal = re.search(r'(card[-_ ]?front|front[-_ ]?card|product|niche-builder|card[-_][a-z0-9_-]{0,80}\.(png|jpg|jpeg|webp))', hay)
    contextual_noise = re.search(r'(person|people|woman|man|hand|hands|phone|mobile|app|screenshot|screen|virtual-assistant|decline|call-us|support|apple\s*pay|google\s*pay)', hay)
    if contextual_noise and not isolated_signal:
        score = -999
    elif noise_re.search(hay) and not isolated_signal:
        score -= 90
    if 'business' in hay and 'business' not in card_name.lower():
        score -= 25
    if official_host.endswith('.co.uk') and (page_host.endswith('.ca') or src_host.endswith('.ca') or '.com.au' in page_host or '.com.au' in src_host):
        score -= 90
    if official_host.endswith('.co.uk') and brand == 'mbna' and ('mbna.ca' in page_host or 'mbna.ca' in src_host):
        score = -999
    if any(h in page_host or h in src_host for h in hard_noise_hosts):
        score -= 60
    if noise_re.search(hay):
        score -= 35
    if re.search(r'(logo|icon|sprite|favicon)', hay):
        score -= 25
    if re.search(r'(walletwisdoms|memivi)', hay):
        score -= 10
    out.append({'src': src, 'page': page, 'title': title, 'score': score})
out.sort(key=lambda x: x.get('score', 0), reverse=True)
print(json.dumps({'status': 'OK', 'results': out}, ensure_ascii=False))
PY
)

  brave_status=$(echo "$brave_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null || echo "")
  if [ "$brave_status" != "OK" ]; then
    echo "[$(date -Iseconds)] search-card-image BRAVE_ERROR status=${brave_status:-invalid_response}" >>"$LOG"
    return 1
  fi

  brave_urls=$(BRAVE_JSON="$brave_json" python3 - <<'PY'
import json, os
try:
    data = json.loads(os.environ.get('BRAVE_JSON', '{}'))
except Exception:
    raise SystemExit(0)
for r in data.get('results', []):
    src = r.get('src') or ''
    if src.startswith('http'):
        title = (r.get('title') or '').replace('\t', ' ')[:180]
        page = (r.get('page') or '').replace('\t', ' ')[:220]
        print(f"{int(r.get('score', 0))}\t{src}\t{title}\t{page}")
PY
)
  if [ -z "$brave_urls" ]; then
    echo "[$(date -Iseconds)] search-card-image BRAVE_NO_IMAGE_URLS" >>"$LOG"
    return 1
  fi

  while IFS=$'\t' read -r cand_score cand_url cand_title cand_page; do
    [ -z "$cand_url" ] && continue
    if [ "${cand_score:-0}" -lt 110 ]; then
      echo "[$(date -Iseconds)] search-card-image BRAVE_SKIP_LOW_SCORE score=${cand_score:-0} title=${cand_title:-} page=${cand_page:-} src=$cand_url" >>"$LOG"
      continue
    fi
    cand_ext="${cand_url##*.}"; cand_ext="${cand_ext%%\?*}"
    cand_ext=$(echo "$cand_ext" | tr '[:upper:]' '[:lower:]')
    case "$cand_ext" in png|jpg|jpeg|webp) ;; *) cand_ext="jpg" ;; esac
    cand_tmp="/tmp/card-candidate-brave-$slug-$$-$RANDOM.$cand_ext"
    TEMP_FILES+=("$cand_tmp")
    echo "[$(date -Iseconds)] search-card-image BRAVE_TRY score=${cand_score:-0} title=${cand_title:-} page=${cand_page:-} src=$cand_url" >>"$LOG"
    if download_and_validate_candidate "$cand_url" "$cand_ext" "$cand_tmp" "brave"; then
      final_out="/tmp/card-$slug.$cand_ext"
      mv "$cand_tmp" "$final_out"
      normalize_card_image "$final_out" || true
      mime=$(file -b --mime-type "$final_out" 2>/dev/null || echo "image/$cand_ext")
      echo "[$(date -Iseconds)] search-card-image BRAVE_OK path=$final_out score=${cand_score:-0} src=$cand_url" >>"$LOG"
      jq -n --arg p "$final_out" --arg m "$mime" --arg s "$cand_url" \
        --argjson sc "${cand_score:-0}" --arg title "${cand_title:-}" --arg page "${cand_page:-}" \
        '{path:$p, mime:$m, tier:4, source:$s, status:"OK", provider:"brave_images", selection:{mode:"auto_ranked_card_image", score:$sc, title:$title, page:$page}}'
      exit 0
    fi
  done <<<"$brave_urls"

  echo "[$(date -Iseconds)] search-card-image BRAVE_NO_VALID_IMAGES" >>"$LOG"
  return 1
}

run_bing_fallback() {
  # ── Tentativa 3: Bing Images via Playwright local ──────────────────────
  if run_brave_fallback; then
    exit 0
  fi

  echo "[$(date -Iseconds)] search-card-image FALLBACK bing_playwright card=$CARD_NAME" >>"$LOG"
  BING_SCRIPT="$(dirname "$0")/search-card-image-bing.py"
  if [ -f "$BING_SCRIPT" ]; then
    bing_result=$(python3 "$BING_SCRIPT" "$CARD_NAME" 2>>"$LOG") || true
    bing_status=$(echo "$bing_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null || echo "")
    if [ "$bing_status" = "OK" ]; then
      bing_path=$(echo "$bing_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('path',''))"   2>/dev/null || echo "")
      bing_mime=$(echo "$bing_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('mime',''))"   2>/dev/null || echo "")
      bing_src=$(echo  "$bing_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('source',''))" 2>/dev/null || echo "")
      [ -n "$bing_path" ] && normalize_card_image "$bing_path" || true
      [ -n "$bing_path" ] && bing_mime=$(file -b --mime-type "$bing_path" 2>/dev/null || echo "$bing_mime")
      echo "[$(date -Iseconds)] search-card-image BING_OK path=$bing_path src=$bing_src" >>"$LOG"
      jq -n --arg p "$bing_path" --arg m "$bing_mime" --arg s "$bing_src" \
        '{path:$p, mime:$m, tier:4, source:$s, status:"OK"}'
      exit 0
    fi
  fi
  emit_needs_manual "all_sources_failed"
}

# ── Tentativa 1: Fetch official page ──────────────────────────────────────
# Captura HTTP status junto com o body para detecção rápida de geo-IP/bot block
http_out=$(curl -sS -L -A "Mozilla/5.0" -w "\nHTTP_STATUS:%{http_code}" "$OFFICIAL_URL" 2>/dev/null) || true
http_status=$(echo "$http_out" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
html=$(echo "$http_out" | sed '/HTTP_STATUS:[0-9]*/d')

# Detectar bloqueio:
# - HTTP 4xx/5xx
# - Cloudflare "Error 1007/1020" ou página de erro genérica no body
_blocked=0
if [ -n "$http_status" ] && [ "$http_status" -ge 400 ] 2>/dev/null; then
  _blocked=1
fi
if echo "$html" | grep -qiE '(error 10[0-9]{2}|access denied|cf-mitigated|cf-ray|enable javascript and cookies|sorry.{0,40}error occurred|we are sorry an error)'; then
  _blocked=1
fi

if [ "$_blocked" = "1" ] || [ -z "$html" ]; then
  echo "[$(date -Iseconds)] search-card-image GEO_BLOCK_OR_EMPTY status=${http_status:-?} skipping_to_bing card=$CARD_NAME url=$OFFICIAL_URL" >>"$LOG"
  run_bing_fallback
fi

# ── Scraping do site oficial ──────────────────────────────────────────────
base_host=$(echo "$OFFICIAL_URL" | sed -E 's#^(https?://[^/]+).*#\1#')
candidates=$(echo "$html" | grep -oE '(src|data-src|data-lazy-src)="[^"]+\.(png|jpe?g|webp)"' \
  | sed -E 's/^[^"]+\"([^"]+)\".*/\1/' \
  | sort -u || true)

abs_candidates=$(while IFS= read -r u; do
  [ -z "$u" ] && continue
  case "$u" in
    http*) echo "$u" ;;
    //*)   echo "https:$u" ;;
    /*)    echo "$base_host$u" ;;
    *)     echo "$base_host/$u" ;;
  esac
done <<<"$candidates")

if [ -z "$abs_candidates" ]; then
  echo "[$(date -Iseconds)] search-card-image no_image_tags_on_page skipping_to_bing card=$CARD_NAME" >>"$LOG"
  run_bing_fallback
fi

kw=$(echo "$slug" | tr '-' '|')
scored=$(while IFS= read -r u; do
  [ -z "$u" ] && continue
  score=0
  low=$(echo "$u" | tr '[:upper:]' '[:lower:]')
  low_path=$(echo "$low" | sed -E 's#^https?://[^/]+/?##')
  echo "$low_path" | grep -qE "($kw)" && score=$((score+5))
  echo "$low_path" | grep -qE '(card|visa|mastercard|amex|gold|platinum|classic|credit)' && score=$((score+2))
  [[ "$low" == *.png ]] && score=$((score+3))
  [[ "$low" == *.webp ]] && score=$((score+1))
  echo "$low_path" | grep -qE '(logo|icon|sprite|favicon|hero|banner|couple|walking|shop|background|new-fscs)' && score=$((score-4))
  echo "$score $u"
done <<<"$abs_candidates" | sort -rn)

# Iterate scored candidates (score > 0) until one passes dimension + aspect filters
best=""
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
    best="$cand_url"; ext="$cand_ext"; out="$cand_tmp"
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
  best="$cand_url"; ext="$cand_ext"; out="$cand_tmp"
  break
done <<<"$scored"

# Se Tentativa 1 não encontrou nada → Bing fallback
if [ -z "$best" ]; then
  run_bing_fallback
fi

# Move accepted candidate to canonical output path
final_out="/tmp/card-$slug.$ext"
if [ "$out" != "$final_out" ]; then
  mv "$out" "$final_out"
  out="$final_out"
fi
normalize_card_image "$out" || true
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
