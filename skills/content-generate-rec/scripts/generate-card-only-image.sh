#!/bin/bash
set -euo pipefail
# Generate a clean, card-only product asset from a low-quality manual source.
# Used only when a user explicitly supplies a manual card image and the crop is
# too small/rough for LazyBlock. Never prints credentials.

[ -f /root/mgs-agent/.env ] && set -a && . /root/mgs-agent/.env && set +a

SLUG="${1:?usage: generate-card-only-image.sh <slug> <source_image>}"
SOURCE_IMG="${2:?missing source_image}"
OUT="/tmp/card-${SLUG}-enhanced.png"
LOG="/root/mgs-agent/logs/generate-rec.log"
[ -f "$SOURCE_IMG" ] || { echo "ERROR: source image not found: $SOURCE_IMG" >&2; exit 1; }

python3 - "$SOURCE_IMG" "$OUT" <<'PY'
import base64, json, pathlib, subprocess, sys, urllib.request
src, out = sys.argv[1], sys.argv[2]
api_key = subprocess.check_output([
    'op','item','get','Gemini API Key','--vault','MGS Conteúdo','--fields','api_key','--reveal'
], text=True).strip()
img_b64 = base64.b64encode(open(src,'rb').read()).decode()
prompt = '''Generate an isolated high-resolution product PNG of the credit card shown in the reference.

Frame/composition:
- Output ONLY the card, no person, no hand, no scene, no table, no phone, no payment terminal.
- The card must fill 90-95% of the image width.
- Tight crop around the card with only small transparent padding.
- Transparent background outside the rounded card corners.
- No large white canvas and no coloured halo around the edge.

Card fidelity:
- Preserve the issuer logo, payment network mark, chip, contactless icon, colour palette, rounded rectangle shape, placeholder digits and layout from the reference.
- Clean antialiased edges and sharp text/icons.
- No transparent holes inside the card artwork.
- Do not change it into a different issuer or card product.
- Keep placeholder digits generic; do not introduce real personal data.

Output: one clean horizontal card-only product asset suitable for a WordPress LazyBlock.'''
payload = {"contents":[{"parts":[{"text":prompt},{"inline_data":{"mime_type":"image/png" if src.lower().endswith('.png') else "image/jpeg","data":img_b64}}]}]}
req = urllib.request.Request(
    f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={api_key}',
    data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'}, method='POST')
with urllib.request.urlopen(req, timeout=120) as resp:
    data = json.loads(resp.read())
for part in data.get('candidates',[{}])[0].get('content',{}).get('parts',[]):
    inline = part.get('inlineData') or part.get('inline_data')
    if inline and inline.get('data'):
        pathlib.Path(out).write_bytes(base64.b64decode(inline['data']))
        print(json.dumps({'status':'OK','path':out,'mode':'manual_card_image_enhanced','model':'gemini-2.5-flash-image'}))
        sys.exit(0)
print(json.dumps({'status':'ERROR','error':'Gemini returned no image'}))
sys.exit(1)
PY

echo "[$(date -Iseconds)] generate-card-only-image OK slug=$SLUG out=$OUT" >>"$LOG"
