#!/bin/bash
# Comprime imagens antes do upload pra WordPress
# Uso: compress-image.sh <input_path> <type>
#   type: "card" (PNG transparente otimizado) | "featured" (JPEG comprimido)
#
# Output:
#   - card:     mesmo path .png (otimizado in-place)
#   - featured: novo path .jpg (PNG original deletado)
#
# Stdout: caminho final do arquivo (pra ser capturado pelo caller)

set -euo pipefail

INPUT="${1:?usage: compress-image.sh <path> <card|featured>}"
TYPE="${2:?usage: compress-image.sh <path> <card|featured>}"

if [ ! -f "$INPUT" ]; then
  echo "ERROR: file not found: $INPUT" >&2
  exit 1
fi

case "$TYPE" in
  card)
    # PNG transparente — só otimiza (mantém transparência)
    python3 - "$INPUT" << 'PYEOF'
import sys
from PIL import Image

path = sys.argv[1]
img = Image.open(path)

# Sempre salva como PNG otimizado (preserva transparência se RGBA)
img.save(path, 'PNG', optimize=True, compress_level=9)
PYEOF
    echo "$INPUT"
    ;;

  featured)
    # PNG → JPEG quality 88, forced 16:9 final (center crop), max 1280px wide
    OUTPUT="${INPUT%.png}.jpg"
    python3 - "$INPUT" "$OUTPUT" << 'PYEOF'
import sys
from PIL import Image, ImageOps

src, dst = sys.argv[1], sys.argv[2]
img = Image.open(src)

# Convert RGBA → RGB (descarta transparência)
if img.mode in ('RGBA', 'LA', 'P'):
    bg = Image.new('RGB', img.size, (255, 255, 255))
    if img.mode == 'P':
        img = img.convert('RGBA')
    bg.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
    img = bg
elif img.mode != 'RGB':
    img = img.convert('RGB')

# Featured images must be strict 16:9. Gemini sometimes returns 16:10/8:5
# despite the prompt; enforce here before upload so WordPress never receives
# 1280x800-style outputs. Center crop is preferred over padding for REC hero art.
target_aspect = 16 / 9
w, h = img.size
current_aspect = w / h if h else target_aspect
if abs(current_aspect - target_aspect) > 0.01:
    if current_aspect > target_aspect:
        # Too wide: crop left/right.
        new_w = int(h * target_aspect)
        left = max(0, (w - new_w) // 2)
        img = img.crop((left, 0, left + new_w, h))
    else:
        # Too tall: crop top/bottom.
        new_h = int(w / target_aspect)
        top = max(0, (h - new_h) // 2)
        img = img.crop((0, top, w, top + new_h))

# Resize to standard width when possible. This yields 1280x720 for normal heroes.
if img.width != 1280:
    new_h = int(round(img.height * 1280 / img.width))
    img = img.resize((1280, new_h), Image.LANCZOS)

# Final guard: exact 16:9 after rounding.
if img.size != (1280, 720):
    img = ImageOps.fit(img, (1280, 720), method=Image.LANCZOS, centering=(0.5, 0.5))

# Save JPEG quality 88
img.save(dst, 'JPEG', quality=88, optimize=True, progressive=True)
PYEOF
    # Remove PNG original (já temos o JPEG)
    rm -f "$INPUT"
    echo "$OUTPUT"
    ;;

  *)
    echo "ERROR: type must be 'card' or 'featured'" >&2
    exit 1
    ;;
esac
