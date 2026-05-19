#!/usr/bin/env python3
"""Normalize credit-card artwork for REC LazyBlock/featured use.

Usage:
  normalize-card-artwork.py <input_image> <output_png> [--aggressive]

- Normal mode: rotate portrait to landscape and trim white/transparent padding.
- Aggressive mode: additionally crop flat thumbnail/background canvas and keep
  rounded-card corners transparent in the output PNG.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

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
    args = ap.parse_args()

    src = Path(args.input_image)
    dst = Path(args.output_png)
    if dst.suffix.lower() != '.png':
        raise SystemExit('output path must end in .png so transparency is preserved')
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())

    runner = load_runner()
    result = runner.normalize_card_artwork(str(dst), aggressive=args.aggressive)
    print(json.dumps({'status': 'ok', 'path': str(dst), 'normalize': result}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
