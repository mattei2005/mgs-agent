#!/usr/bin/env python3
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

exec_dir = Path(Path('/root/mgs-agent/tmp/ares-current-exec-path').read_text().strip())
manifest_path = next((exec_dir / 'timelines').glob('*/video-frame-sample-manifest.json'))
base = manifest_path.parent
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
out_dir = base / 'review-montages'
out_dir.mkdir(parents=True, exist_ok=True)
font = ImageFont.truetype('DejaVuSans-Bold.ttf', 26)
index = []
for batch_no, start in enumerate(range(0, len(manifest['items']), 4), 1):
    items = manifest['items'][start:start + 4]
    opened = [Image.open(item['sheet']).convert('RGB') for item in items]
    width = max(image.width for image in opened)
    blocks = []
    for item_no, (item, image) in enumerate(zip(items, opened), start + 1):
        block = Image.new('RGB', (width, image.height + 46), (255, 255, 255))
        draw = ImageDraw.Draw(block)
        draw.text((10, 8), f"ITEM {item_no:02d}: {item['original_filename']}", fill='black', font=font)
        block.paste(image, ((width - image.width) // 2, 46))
        blocks.append(block)
    canvas = Image.new('RGB', (width, sum(block.height for block in blocks)), (255, 255, 255))
    y = 0
    for block in blocks:
        canvas.paste(block, (0, y))
        y += block.height
    path = out_dir / f'batch-{batch_no:02d}.jpg'
    canvas.save(path, quality=94)
    index.append({'batch': batch_no, 'path': str(path), 'items': [item['original_filename'] for item in items]})
(out_dir / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'montages': len(index), 'index': str(out_dir / 'index.json')}))
