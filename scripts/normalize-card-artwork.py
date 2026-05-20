#!/usr/bin/env python3
"""Normalize credit-card artwork for REC LazyBlock/featured use.

Usage:
  normalize-card-artwork.py <input_image> <output_png> [--aggressive]

- Normal mode: rotate portrait to landscape and trim white/transparent padding.
- Aggressive mode: additionally crops flat thumbnail/background canvas when safe;
  it must preserve internal card colours/design and avoid transparency holes.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from PIL import Image

RUNNER = Path('/root/mgs-agent/scripts/mgs-rec-runner.py')


def load_runner():
    spec = importlib.util.spec_from_file_location('mgs_rec_runner', RUNNER)
    if not spec or not spec.loader:
        raise SystemExit(f'Cannot load runner: {RUNNER}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('input_image')
    ap.add_argument('output_png')
    ap.add_argument('--aggressive', action='store_true')
    ap.add_argument('--min-width', type=int, default=600, help='fail if normalized card is narrower than this; use 0 to disable')
    args = ap.parse_args()

    src = Path(args.input_image)
    dst = Path(args.output_png)
    if dst.suffix.lower() != '.png':
        raise SystemExit('output path must end in .png so transparency is preserved')
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())

    runner = load_runner()
    result = runner.normalize_card_artwork(str(dst), aggressive=args.aggressive)
    with Image.open(dst) as im:
        width, height = im.size
        mode = im.mode
        alpha_bbox = im.convert('RGBA').getchannel('A').getbbox()
    aspect = width / max(1, height)
    if width <= height or not (1.2 <= aspect <= 2.2):
        raise SystemExit(
            f"CARD_STANDARD_FAIL: normalized LazyBlock card must be horizontal/card-shaped; "
            f"got {width}x{height} aspect={aspect:.4f}. Rotate/crop the card-only artwork before upload."
        )
    if args.min_width and width < args.min_width:
        raise SystemExit(
            f"LOW_QUALITY_SOURCE: normalized card image is only {width}x{height}; "
            f"minimum width is {args.min_width}px. Use a higher-resolution card-only image or request approval before automatic fallback."
        )
    if alpha_bbox and alpha_bbox != (0, 0, width, height):
        ax0, ay0, ax1, ay1 = alpha_bbox
        alpha_area_ratio = ((ax1 - ax0) * (ay1 - ay0)) / max(1, width * height)
        if alpha_area_ratio < 0.78:
            raise SystemExit(
                f"CARD_STANDARD_FAIL: normalized card has too much empty transparent canvas "
                f"({alpha_area_ratio:.2%} useful area). Crop tighter so the card fills the image."
            )
    print(json.dumps({'status': 'ok', 'path': str(dst), 'normalize': result, 'width': width, 'height': height, 'aspect': round(aspect, 4), 'mode': mode}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
