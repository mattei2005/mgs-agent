#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path("/root/mgs-agent")
WORK = ROOT / "work/ares-shein-onboarding-20260911"
SOURCE_MANIFEST = WORK / "visual-review-new/20260912T021146Z/video-frame-sample-manifest.json"
OUT = WORK / "visual-review-montages"
COLS = 3
ROWS = 4
PER_PAGE = COLS * ROWS
TILE_W = 1300
TILE_H = 630
LABEL_H = 42


def font(size: int, bold: bool = False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(name, size)
    except Exception:
        return ImageFont.load_default()


def load_products() -> dict[str, dict]:
    rows = []
    for line in (ROOT / "data/ares/creative-ops/inventory/assets.jsonl").read_text(
        encoding="utf-8", errors="replace"
    ).splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("vertical") == "SHEIN" and row.get("country") == "US" and row.get("language") == "EN":
            rows.append(row)
    return {row["original_filename"]: row for row in rows}


def main() -> int:
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("selected_count") != 168 or len(manifest.get("items", [])) != 168:
        raise RuntimeError("visual sampler did not cover exactly 168 videos")
    products = load_products()
    OUT.mkdir(parents=True, exist_ok=True)
    pages = []
    items = manifest["items"]
    page_total = math.ceil(len(items) / PER_PAGE)
    for page_index in range(page_total):
        batch = items[page_index * PER_PAGE : (page_index + 1) * PER_PAGE]
        canvas = Image.new("RGB", (COLS * TILE_W, ROWS * TILE_H), (255, 255, 255))  # type: ignore[arg-type]
        page_items = []
        for slot, item in enumerate(batch):
            source = Image.open(item["sheet"]).convert("RGB")
            if source.width != TILE_W:
                source.thumbnail((TILE_W, TILE_H - LABEL_H))
            row = products.get(item["original_filename"])
            if not row:
                raise RuntimeError(f"inventory row missing for {item['original_filename']}")
            tile = Image.new("RGB", (TILE_W, TILE_H), (255, 255, 255))  # type: ignore[arg-type]
            tile.paste(source, (0, LABEL_H))
            draw = ImageDraw.Draw(tile)
            absolute_index = page_index * PER_PAGE + slot + 1
            label = f"#{absolute_index:03d} | EXPECTED {row.get('product_type')} | {row.get('canonical_filename')}"
            draw.rectangle((0, 0, TILE_W, LABEL_H), fill=(20, 28, 45))
            draw.text((10, 8), label[:145], font=font(18, True), fill="white")
            x = (slot % COLS) * TILE_W
            y = (slot // COLS) * TILE_H
            canvas.paste(tile, (x, y))
            page_items.append(
                {
                    "index": absolute_index,
                    "expected_product": row.get("product_type"),
                    "canonical_filename": row.get("canonical_filename"),
                    "original_filename": item.get("original_filename"),
                    "source_sheet": item.get("sheet"),
                }
            )
        page_path = OUT / f"shein-video-review-{page_index + 1:02d}-of-{page_total:02d}.jpg"
        canvas.save(page_path, quality=88, optimize=True)
        pages.append({"page": page_index + 1, "path": str(page_path), "items": page_items})
    output = {
        "source_manifest": str(SOURCE_MANIFEST),
        "video_count": len(items),
        "page_count": len(pages),
        "layout": {"columns": COLS, "rows": ROWS, "videos_per_page": PER_PAGE},
        "pages": pages,
    }
    (OUT / "montage-manifest.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"video_count": len(items), "page_count": len(pages), "manifest": str(OUT / 'montage-manifest.json')}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
