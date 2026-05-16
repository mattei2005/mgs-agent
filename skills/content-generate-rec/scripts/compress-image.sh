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
    # PNG → JPEG quality 88, max 1280px wide
    OUTPUT="${INPUT%.png}.jpg"
    python3 - "$INPUT" "$OUTPUT" << 'PYEOF'
import sys
from PIL import Image

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

# Resize se largura > 1280
if img.width > 1280:
    new_h = int(img.height * 1280 / img.width)
    img = img.resize((1280, new_h), Image.LANCZOS)

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
