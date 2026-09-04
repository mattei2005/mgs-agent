#!/usr/bin/env python3
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

base = Path('/root/mgs-agent/data/ares/creative-ops/executions/20260904T204908Z-kelly-shein-us-en-thread-1545536009595261079/frame-samples/20260904T205103Z')
manifest = json.loads((base / 'video-frame-sample-manifest.json').read_text(encoding='utf-8'))
out_dir = base / 'review-montages'
out_dir.mkdir(parents=True, exist_ok=True)
try:
    font = ImageFont.truetype('DejaVuSans-Bold.ttf', 26)
except Exception:
    font = ImageFont.load_default()
index = []
for batch_no, start in enumerate(range(0, len(manifest['items']), 4), 1):
    items = manifest['items'][start:start+4]
    opened = [Image.open(item['sheet']).convert('RGB') for item in items]
    width = max(im.width for im in opened)
    blocks = []
    for idx, (item, im) in enumerate(zip(items, opened), start+1):
        block = Image.new('RGB', (width, im.height + 46), (255, 255, 255))
        draw = ImageDraw.Draw(block)
        draw.text((10, 8), f'ITEM {idx:02d}: {item["original_filename"]}', fill='black', font=font)
        block.paste(im, ((width-im.width)//2, 46))
        blocks.append(block)
    canvas = Image.new('RGB', (width, sum(b.height for b in blocks)), 'white')
    y = 0
    for block in blocks:
        canvas.paste(block, (0, y)); y += block.height
    path = out_dir / f'batch-{batch_no:02d}.jpg'
    canvas.save(path, quality=94)
    index.append({'batch': batch_no, 'path': str(path), 'items': [x['original_filename'] for x in items]})
(out_dir / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'montages': len(index), 'index': str(out_dir / 'index.json')}, indent=2))
