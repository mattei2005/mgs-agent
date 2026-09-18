#!/usr/bin/env python3
from pathlib import Path
import json
from PIL import Image, ImageDraw

run = Path('/root/mgs-agent/data/ares/creative-ops/review/current-1550626790299664487/20260918T215946Z')
manifest = json.loads((run / 'video-frame-sample-manifest.json').read_text(encoding='utf-8'))
out = run / 'montages'
out.mkdir(exist_ok=True)
for page_no in range(6):
    items = manifest['items'][page_no * 4:(page_no + 1) * 4]
    images = []
    for item_no, item in enumerate(items, page_no * 4 + 1):
        image = Image.open(item['sheet']).convert('RGB')
        canvas = Image.new('RGB', (image.width, image.height + 36), 'white')
        canvas.paste(image, (0, 36))
        ImageDraw.Draw(canvas).text(
            (10, 10), f"ITEM {item_no:02d}: {item['original_filename']}", fill='black'
        )
        images.append(canvas)
    width = max(image.width for image in images)
    height = max(image.height for image in images)
    page = Image.new('RGB', (width * 2, height * 2), (235, 235, 235))
    for index, image in enumerate(images):
        page.paste(image, ((index % 2) * width, (index // 2) * height))
    output = out / f'montage-{page_no + 1:02d}.jpg'
    page.save(output, quality=90)
    print(output)
