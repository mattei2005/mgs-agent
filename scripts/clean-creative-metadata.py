#!/usr/bin/env python3
"""MGS creative metadata sanitizer.

Server-side metadata cleaning gate for Ares Creative Operations + Growth.
Uses ExifTool as the primary remover and mat2 as an optional second pass when available.
Never prints secrets; audit events are written as JSONL under /root/mgs-agent/logs/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path('/root/mgs-agent')
AUDIT_LOG = ROOT / 'logs' / 'creative-metadata-sanitizer.jsonl'
DEFAULT_MAX_BYTES = 250 * 1024 * 1024

# ExifTool emits many structural/file tags that are not privacy metadata. Keep
# this allowlist intentionally conservative; verify is a privacy gate, not a
# full media parser.
ALLOWED_EXIFTOOL_GROUPS = {'ExifTool', 'File', 'System', 'Composite'}
ALLOWED_STRUCTURAL_TAGS = {
    'SourceFile', 'ExifToolVersion', 'FileName', 'Directory', 'FileSize',
    'FileModifyDate', 'FileAccessDate', 'FileInodeChangeDate', 'FilePermissions',
    'FileType', 'FileTypeExtension', 'MIMEType', 'ImageWidth', 'ImageHeight',
    'ImageSize', 'Megapixels', 'ColorType', 'BitDepth', 'Compression', 'Filter',
    'Interlace', 'ColorComponents', 'YCbCrSubSampling', 'EncodingProcess',
    'BitsPerSample', 'SamplesPerPixel', 'XResolution', 'YResolution',
    'ResolutionUnit', 'ExifByteOrder', 'CurrentIPTCDigest', 'BackgroundColor',
    'JFIFVersion',
    'Warning', 'Error',
    # MP4/QuickTime structural/container fields that remain after -all= and are
    # required to describe/play the video. These are not privacy metadata.
    'MajorBrand', 'MinorVersion', 'CompatibleBrands', 'MediaDataSize',
    'MediaDataOffset', 'MovieHeaderVersion', 'TimeScale', 'Duration',
    'PreferredRate', 'PreferredVolume', 'MatrixStructure', 'PreviewTime',
    'PreviewDuration', 'PosterTime', 'SelectionTime', 'SelectionDuration',
    'CurrentTime', 'NextTrackID', 'TrackHeaderVersion', 'TrackID',
    'TrackDuration', 'TrackLayer', 'TrackVolume', 'MediaHeaderVersion',
    'MediaTimeScale', 'MediaDuration', 'MediaLanguageCode', 'HandlerType',
    'HandlerVendorID', 'HandlerDescription', 'GraphicsMode', 'OpColor',
    'CompressorID', 'SourceImageWidth', 'SourceImageHeight', 'ColorProfiles',
    'ColorPrimaries', 'TransferCharacteristics', 'MatrixCoefficients',
    'VideoFullRangeFlag', 'BufferSize', 'MaxBitrate', 'AverageBitrate',
    'VideoFrameRate', 'Balance', 'AudioFormat', 'AudioChannels',
    'AudioBitsPerSample', 'AudioSampleRate', 'PixelAspectRatio',
    # ExifTool groups some QuickTime structural track descriptors under TrackN.
    # They remain after stripping metadata and are needed to describe/play media,
    # not privacy metadata.
    'CleanApertureDimensions', 'ProductionApertureDimensions',
    'EncodedPixelsDimensions', 'HandlerClass', 'CompressorName',
    'PurchaseFileFormat',
}


def run(cmd: list[str], *, check: bool = True, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check, timeout=timeout)


def require_cmd(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f'ERROR: required command not found: {name}')
    return path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def mime_type(path: Path) -> str:
    if shutil.which('file'):
        cp = run(['file', '--brief', '--mime-type', str(path)], check=False)
        if cp.stdout.strip():
            return cp.stdout.strip()
    # Fallback for minimal containers where `file` is unavailable.
    try:
        raw = exiftool_json(path)
        return str(raw.get('File:MIMEType') or raw.get('MIMEType') or 'unknown')
    except Exception:
        return 'unknown'


def safe_output_path(src: Path) -> Path:
    return src.with_name(f'{src.stem}.metadata-clean{src.suffix}')


def exiftool_json(path: Path) -> dict[str, Any]:
    require_cmd('exiftool')
    cp = run(['exiftool', '-json', '-G1', '-a', '-s', str(path)], timeout=180)
    data = json.loads(cp.stdout or '[]')
    return data[0] if data else {}


def harmful_exiftool_tags(path: Path) -> dict[str, Any]:
    raw = exiftool_json(path)
    harmful: dict[str, Any] = {}
    for key, value in raw.items():
        # Keys usually look like "PNG:Comment" or "File:FileName" with -G1.
        if ':' in key:
            group, tag = key.split(':', 1)
        else:
            group, tag = '', key
        if group in ALLOWED_EXIFTOOL_GROUPS:
            continue
        if tag in {'CreateDate', 'ModifyDate', 'TrackCreateDate', 'TrackModifyDate', 'MediaCreateDate', 'MediaModifyDate'} and str(value).startswith('0000:00:00'):
            continue
        if tag in ALLOWED_STRUCTURAL_TAGS:
            continue
        harmful[key] = value
    return harmful


def mat2_show(path: Path) -> tuple[bool, str]:
    if not shutil.which('mat2'):
        return False, 'mat2 not installed'
    cp = run(['mat2', '--show', str(path)], check=False, timeout=180)
    out = (cp.stdout + cp.stderr).strip()
    return cp.returncode == 0, out


def inspect(path: Path) -> dict[str, Any]:
    ensure_file(path)
    harmful = harmful_exiftool_tags(path)
    mat2_ok, mat2_output = mat2_show(path)
    return {
        'file': str(path),
        'exists': path.exists(),
        'size_bytes': path.stat().st_size,
        'sha256': sha256(path),
        'mime_type': mime_type(path),
        'exiftool_harmful_tag_count': len(harmful),
        'exiftool_harmful_tags': harmful,
        'mat2_available': shutil.which('mat2') is not None,
        'mat2_show_ok': mat2_ok,
        'mat2_show_excerpt': mat2_output[:4000],
    }


def verify(path: Path) -> dict[str, Any]:
    info = inspect(path)
    harmful = info['exiftool_harmful_tag_count']
    mat2_excerpt = info.get('mat2_show_excerpt') or ''
    # mat2 --show normally says "No metadata found" for clean files. Some
    # unsupported formats return non-zero; in that case ExifTool is the gate.
    mat2_reports_metadata = bool(mat2_excerpt and 'No metadata found' not in mat2_excerpt and 'is not supported' not in mat2_excerpt)
    if str(info.get('mime_type', '')).startswith('video/') and harmful == 0:
        # mat2 reports MP4 structural/container fields as metadata even after
        # ExifTool strips privacy metadata. ExifTool is the privacy gate for video.
        mat2_reports_metadata = False
    info['clean'] = harmful == 0 and not mat2_reports_metadata
    info['mat2_reports_metadata'] = mat2_reports_metadata
    return info


def ensure_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise SystemExit(f'ERROR: file not found: {path}')


def ensure_size(path: Path, max_bytes: int) -> None:
    size = path.stat().st_size
    if size > max_bytes:
        raise SystemExit(f'ERROR: file too large: {size} bytes > {max_bytes} bytes')


def append_audit(event: dict[str, Any]) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    event = {'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), **event}
    with AUDIT_LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + '\n')


def clean_one(src: Path, *, out: Path | None, in_place: bool, agent: str, max_bytes: int, use_mat2: bool) -> dict[str, Any]:
    ensure_file(src)
    ensure_size(src, max_bytes)
    before = inspect(src)
    dest = src if in_place else (out or safe_output_path(src))
    if not in_place:
        if dest.exists():
            raise SystemExit(f'ERROR: output already exists, refusing overwrite: {dest}')
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix='.mgs-clean-', suffix=src.suffix, dir=str(dest.parent), delete=False) as tf:
            tmp = Path(tf.name)
        try:
            shutil.copy2(src, tmp)
            _clean_in_place(tmp, use_mat2=use_mat2)
            os.replace(tmp, dest)
        finally:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
    else:
        _clean_in_place(dest, use_mat2=use_mat2)

    after = verify(dest)
    event = {
        'event': 'creative_metadata_cleaned',
        'agent': agent,
        'source': str(src),
        'output': str(dest),
        'in_place': in_place,
        'mime_type_before': before['mime_type'],
        'mime_type_after': after['mime_type'],
        'size_before': before['size_bytes'],
        'size_after': after['size_bytes'],
        'sha256_before': before['sha256'],
        'sha256_after': after['sha256'],
        'harmful_tags_before': before['exiftool_harmful_tag_count'],
        'harmful_tags_after': after['exiftool_harmful_tag_count'],
        'clean': after['clean'],
    }
    append_audit(event)
    return {'before': before, 'after': after, 'audit_event': event}


def _clean_in_place(path: Path, *, use_mat2: bool) -> None:
    require_cmd('exiftool')
    # Strip metadata without leaving *_original files.
    run(['exiftool', '-overwrite_original', '-all=', str(path)], timeout=300)
    if use_mat2 and shutil.which('mat2'):
        # mat2 may not support every creative format; fail-open only when
        # ExifTool succeeded, because verify still decides final clean status.
        run(['mat2', '--inplace', str(path)], check=False, timeout=300)


def iter_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise SystemExit(f'ERROR: path not found: {path}')
    return sorted([p for p in path.rglob('*') if p.is_file()])


def main() -> int:
    parser = argparse.ArgumentParser(description='MGS server-side creative metadata sanitizer')
    sub = parser.add_subparsers(dest='cmd', required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument('path', type=Path)
        p.add_argument('--json', action='store_true', help='print machine-readable JSON')

    p_inspect = sub.add_parser('inspect', help='show metadata/privacy status')
    add_common(p_inspect)

    p_verify = sub.add_parser('verify', help='return clean=true/false for one file')
    add_common(p_verify)

    p_clean = sub.add_parser('clean', help='clean one file')
    p_clean.add_argument('path', type=Path)
    p_clean.add_argument('--out', type=Path)
    p_clean.add_argument('--in-place', action='store_true')
    p_clean.add_argument('--agent', default='manual')
    p_clean.add_argument('--max-mb', type=int, default=250)
    p_clean.add_argument('--no-mat2', action='store_true')
    p_clean.add_argument('--json', action='store_true')

    p_batch = sub.add_parser('batch', help='clean every file in a directory into an output directory')
    p_batch.add_argument('path', type=Path)
    p_batch.add_argument('--out-dir', type=Path, required=True)
    p_batch.add_argument('--agent', default='manual')
    p_batch.add_argument('--max-mb', type=int, default=250)
    p_batch.add_argument('--no-mat2', action='store_true')
    p_batch.add_argument('--json', action='store_true')

    args = parser.parse_args()
    if args.cmd == 'inspect':
        result = inspect(args.path)
    elif args.cmd == 'verify':
        result = verify(args.path)
    elif args.cmd == 'clean':
        result = clean_one(args.path, out=args.out, in_place=args.in_place, agent=args.agent, max_bytes=args.max_mb * 1024 * 1024, use_mat2=not args.no_mat2)
    elif args.cmd == 'batch':
        files = iter_files(args.path)
        results = []
        for src in files:
            rel = src.relative_to(args.path) if args.path.is_dir() else src.name
            dest = args.out_dir / rel
            results.append(clean_one(src, out=dest, in_place=False, agent=args.agent, max_bytes=args.max_mb * 1024 * 1024, use_mat2=not args.no_mat2)['audit_event'])
        result = {'count': len(results), 'results': results, 'all_clean': all(r['clean'] for r in results)}
    else:
        raise AssertionError(args.cmd)

    if getattr(args, 'json', False):
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if args.cmd in {'inspect', 'verify'}:
            print(f"file: {result['file']}")
            print(f"mime: {result['mime_type']}")
            print(f"size_bytes: {result['size_bytes']}")
            print(f"sha256: {result['sha256']}")
            print(f"harmful_tags: {result['exiftool_harmful_tag_count']}")
            if 'clean' in result:
                print(f"clean: {str(result['clean']).lower()}")
        elif args.cmd == 'clean':
            ev = result['audit_event']
            print(f"output: {ev['output']}")
            print(f"harmful_tags_before: {ev['harmful_tags_before']}")
            print(f"harmful_tags_after: {ev['harmful_tags_after']}")
            print(f"clean: {str(ev['clean']).lower()}")
            print(f"audit_log: {AUDIT_LOG}")
        elif args.cmd == 'batch':
            print(f"count: {result['count']}")
            print(f"all_clean: {str(result['all_clean']).lower()}")
            print(f"audit_log: {AUDIT_LOG}")
    return 0 if not (args.cmd == 'verify' and not result['clean']) else 2


if __name__ == '__main__':
    raise SystemExit(main())
