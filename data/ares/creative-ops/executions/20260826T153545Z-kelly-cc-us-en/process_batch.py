#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from PIL import Image

EXECUTOR = Path('/root/mgs-agent/scripts/ares-execute-creative-copy-clean.py')
SANITIZER = Path('/root/mgs-agent/scripts/clean-creative-metadata.sh')
ROOT_ID = '0AEwt4Ye690ocUk9PVA'
EXPECTED_DRIVE = 'MGS-AGENTS'
EXPECTED_EMAIL = 'mgsagent@mgs-core-prod.iam.gserviceaccount.com'
EXPECTED_PROJECT = 'mgs-core-prod'
OPERATION = 'CC_US_EN'
THREAD_ID = '1542195602643755139'
INVENTORY = Path('/root/mgs-agent/data/ares/creative-ops/inventory/assets.jsonl')
REPORT_DIR = Path('/root/mgs-agent/data/ares/creative-ops/executions/20260826T153545Z-kelly-cc-us-en')
WORK_DIR = REPORT_DIR / 'work-process'
STATE_PATH = REPORT_DIR / 'state.json'

CLAIMS = {
    '1_3_us_cc_ig_26_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
    '2_4_us_cc_ig_26_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
    '3_6_us_cc_ig_26_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
    '4_9_us_cc_ig_26_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
    '5_3_us_cc_ig_26_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
    '6_7_us_cc_ig_26_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
    '7_5_us_cc_ig_26_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
    '8_8_us_cc_ig_26_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
    '9_10_us_cc_ig_26_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
    '10_1_us_cc_ig_26_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
    '1_2_us_cc_ig_25_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
    '2_8_us_cc_ig_25_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
    '3_10_us_cc_ig_25_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
    '4_1_us_cc_ig_25_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
    '5_4_us_cc_ig_25_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
    '6_9_us_cc_ig_25_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
    '7_6_us_cc_ig_25_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
    '8_7_us_cc_ig_25_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
    '9_2_us_cc_ig_25_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
    '10_5_us_cc_es_25_08.mp4': 'LÍMITE DISPONIBLE $14,760; English spoken captions',
}

DUPLICATE_SOURCE_TO_PRIMARY = {}


def utcnow() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def load_executor():
    spec = importlib.util.spec_from_file_location('ares_executor', EXECUTOR)
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load canonical Drive executor')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def jdump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)


def api_get(drive, file_id: str) -> dict[str, Any]:
    fields = 'id,name,mimeType,parents,driveId,size,md5Checksum,createdTime,modifiedTime,trashed,webViewLink,capabilities(canDownload,canEdit,canMoveItemWithinDrive,canModifyContent,canTrash,canDelete)'
    url = f'https://www.googleapis.com/drive/v3/files/{file_id}?' + urllib.parse.urlencode({'supportsAllDrives': 'true', 'fields': fields})
    return drive.request(url) or {}


def list_children(drive, parent_id: str) -> list[dict[str, Any]]:
    q = f"'{parent_id}' in parents and trashed=false"
    fields = 'files(id,name,mimeType,parents,driveId,size,md5Checksum,createdTime,modifiedTime,trashed,webViewLink)'
    url = 'https://www.googleapis.com/drive/v3/files?' + urllib.parse.urlencode({'q': q, 'supportsAllDrives': 'true', 'includeItemsFromAllDrives': 'true', 'pageSize': '1000', 'fields': fields, 'orderBy': 'name_natural'})
    return (drive.request(url) or {}).get('files', [])


def list_descendant_files(drive, parent_id: str) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    stack = [parent_id]
    seen = set()
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        for item in list_children(drive, current):
            if item.get('mimeType') == 'application/vnd.google-apps.folder':
                stack.append(item['id'])
            else:
                files.append(item)
    return files


def resolve_existing_path(drive, parts: list[str]) -> str:
    parent = ROOT_ID
    for name in parts:
        child = drive.find_child_folder(parent, name)
        if not child:
            raise RuntimeError(f'missing canonical folder: {name}')
        parent = child
    return parent


def move_file(drive, file_id: str, old_parent: str, new_parent: str) -> dict[str, Any]:
    params = {'supportsAllDrives': 'true', 'addParents': new_parent, 'removeParents': old_parent, 'fields': 'id,name,parents,driveId,trashed'}
    url = f'https://www.googleapis.com/drive/v3/files/{file_id}?' + urllib.parse.urlencode(params)
    return drive.request(url, method='PATCH', data=b'', headers={'Content-Type': 'application/json'}) or {}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def ffprobe(path: Path) -> dict[str, Any]:
    p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,codec_name:format=duration', '-of', 'json', str(path)], capture_output=True, text=True, check=False, timeout=120)
    if p.returncode != 0:
        raise RuntimeError(f'ffprobe failed: {p.stderr[-300:]}')
    d = json.loads(p.stdout)
    if not d.get('streams'):
        raise RuntimeError('video has no visual stream')
    s = d['streams'][0]
    width, height = int(s['width']), int(s['height'])
    duration = float(d.get('format', {}).get('duration') or 0)
    if width != 1080 or height != 1920 or duration <= 0:
        raise RuntimeError(f'unexpected technical profile {width}x{height} duration={duration}')
    return {'width': width, 'height': height, 'duration': duration, 'codec': s.get('codec_name')}


def dhash(path: Path) -> str:
    with Image.open(path) as im:
        pixels = list(im.convert('L').resize((9, 8)).getdata())
    value = 0
    for y in range(8):
        for x in range(8):
            value = (value << 1) | int(pixels[y * 9 + x] > pixels[y * 9 + x + 1])
    return f'{value:016x}'


def fingerprint_video(path: Path, duration: float, frame_dir: Path, stem: str) -> str:
    frame_dir.mkdir(parents=True, exist_ok=True)
    hashes = []
    for i, frac in enumerate((0.2, 0.5, 0.8), 1):
        out = frame_dir / f'{stem}-{i}.jpg'
        p = subprocess.run(['ffmpeg', '-y', '-ss', f'{duration * frac:.3f}', '-i', str(path), '-frames:v', '1', '-q:v', '2', str(out)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=120)
        if p.returncode != 0 or not out.exists():
            raise RuntimeError('failed to extract fingerprint frame')
        hashes.append(dhash(out))
    return 'dhash64:' + '/'.join(hashes)


def clean_and_verify(raw: Path, out: Path) -> tuple[str, str]:
    p = subprocess.run([str(SANITIZER), 'clean', str(raw), '--out', str(out), '--agent', 'ares'], capture_output=True, text=True, check=False, timeout=900)
    if p.returncode != 0:
        raise RuntimeError(f'sanitizer clean failed: {(p.stdout + p.stderr)[-500:]}')
    v = subprocess.run([str(SANITIZER), 'verify', str(out)], capture_output=True, text=True, check=False, timeout=300)
    if v.returncode != 0 or 'clean: true' not in v.stdout:
        raise RuntimeError(f'sanitizer verify failed: {(v.stdout + v.stderr)[-500:]}')
    return sha256_file(out), v.stdout


def verify_clean(path: Path) -> None:
    v = subprocess.run([str(SANITIZER), 'verify', str(path)], capture_output=True, text=True, check=False, timeout=300)
    if v.returncode != 0 or 'clean: true' not in v.stdout:
        raise RuntimeError(f'readback sanitizer verify failed: {(v.stdout + v.stderr)[-500:]}')


def load_inventory() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    rows = []
    by_source = {}
    by_raw_sha = {}
    if INVENTORY.exists():
        for line in INVENTORY.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            rows.append(row)
            if row.get('source_drive_id'):
                by_source[row['source_drive_id']] = row
            if row.get('original_checksum'):
                by_raw_sha[row['original_checksum']] = row
    return rows, by_source, by_raw_sha


def append_inventory(row: dict[str, Any]) -> None:
    INVENTORY.parent.mkdir(parents=True, exist_ok=True)
    lock_path = INVENTORY.with_suffix(INVENTORY.suffix + '.lock')
    with lock_path.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        existing_ids = set()
        if INVENTORY.exists():
            for line in INVENTORY.read_text(encoding='utf-8').splitlines():
                if line.strip():
                    existing_ids.add(json.loads(line).get('source_drive_id'))
        if row['source_drive_id'] in existing_ids:
            return
        with INVENTORY.open('a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
            f.flush()
            os.fsync(f.fileno())


def attach_duplicate_source(primary_source_id: str, duplicate_source_id: str, duplicate_filename: str) -> None:
    lock_path = INVENTORY.with_suffix(INVENTORY.suffix + '.lock')
    with lock_path.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        rows = [json.loads(line) for line in INVENTORY.read_text(encoding='utf-8').splitlines() if line.strip()]
        matched = 0
        for row in rows:
            if row.get('source_drive_id') != primary_source_id:
                continue
            matched += 1
            duplicate_ids = list(row.get('duplicate_source_drive_ids') or [])
            if duplicate_source_id not in duplicate_ids:
                duplicate_ids.append(duplicate_source_id)
            row['duplicate_source_drive_ids'] = duplicate_ids
            note = f' Fonte adicional {duplicate_filename} conciliada como duplicata exata após sanitização; nenhum candidato independente foi criado.'
            if note.strip() not in (row.get('notes') or ''):
                row['notes'] = (row.get('notes') or '') + note
        if matched != 1:
            raise RuntimeError(f'primary inventory row not uniquely found: {primary_source_id} matches={matched}')
        tmp = INVENTORY.with_suffix(INVENTORY.suffix + '.tmp')
        tmp.write_text(''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n' for row in rows), encoding='utf-8')
        os.replace(tmp, INVENTORY)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ['index','status','disposition','source_drive_id','source_filename','destination_drive_id','destination_filename','source_sha256','clean_sha256','drive_md5','bytes_clean','metadata_clean','drive_readback_verified','sha256_readback_verified','person','p_orient','angle','variant','claim','perceptual_fingerprint','webViewLink']
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, '') for k in fields})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('inventory_csv')
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    input_rows = list(csv.DictReader(open(args.inventory_csv, encoding='utf-8')))
    input_rows = [r for r in input_rows if r.get('format') == 'VID']
    if len(input_rows) != 20:
        raise RuntimeError(f'expected 20 videos, found {len(input_rows)}')
    if set(r['original_filename'] for r in input_rows) != set(CLAIMS):
        raise RuntimeError('live batch filenames do not match the visually reviewed batch')

    batch_key = hashlib.sha256('|'.join(sorted(r['drive_id'] for r in input_rows)).encode()).hexdigest()[:20]
    lock_path = Path('/root/mgs-agent/tmp/ares-intake-locks') / f'cc_mx_es-{batch_key}.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)

        ex = load_executor()
        ex.load_env()
        sa = ex.service_account()
        if sa.get('client_email') != EXPECTED_EMAIL or sa.get('project_id') != EXPECTED_PROJECT:
            raise RuntimeError('canonical service account identity validation failed')
        token, auth_mode = ex.build_access_token()
        if auth_mode != 'service_account':
            raise RuntimeError('non-service-account auth refused')
        drive = ex.Drive(token)
        root = drive.preflight_destination(auth_mode)
        if root.get('driveId') != ROOT_ID:
            raise RuntimeError('canonical Shared Drive root mismatch')
        shared = drive.request(f'https://www.googleapis.com/drive/v3/drives/{ROOT_ID}?fields=id,name') or {}
        if shared.get('name') != EXPECTED_DRIVE:
            raise RuntimeError('Shared Drive name mismatch')

        creatives_id = resolve_existing_path(drive, ['CRIATIVOS'])
        upload_id = resolve_existing_path(drive, ['CRIATIVOS', 'UPLOAD MANUAL'])
        ready_id = resolve_existing_path(drive, ['CRIATIVOS', OPERATION, 'VID', '01_READY'])
        legacy_id = resolve_existing_path(drive, ['CRIATIVOS', OPERATION, 'VID', '99_LEGACY'])

        live_sources = {x['id']: x for x in list_descendant_files(drive, upload_id)}
        expected_ids = {r['drive_id'] for r in input_rows}
        if set(live_sources) != expected_ids:
            raise RuntimeError(f'fresh queue mismatch expected={len(expected_ids)} live_files={len(live_sources)}')

        for row in input_rows:
            live = api_get(drive, row['drive_id'])
            caps = live.get('capabilities') or {}
            if live.get('driveId') != ROOT_ID or row['drive_id'] not in live_sources:
                raise RuntimeError(f'source not in canonical upload parent: {row["original_filename"]}')
            if not caps.get('canDownload') or not caps.get('canMoveItemWithinDrive'):
                raise RuntimeError(f'missing required source capability: {row["original_filename"]}')
            if str(live.get('size')) != str(row['size_bytes']):
                raise RuntimeError(f'source size drift: {row["original_filename"]}')

        existing_rows, by_source, by_raw_sha = load_inventory()
        already = expected_ids.intersection(by_source)
        if already:
            raise RuntimeError(f'source IDs already inventoried: {len(already)}')

        live_ready = list_children(drive, ready_id)
        rx = re.compile(r'^CC_US_EN_VID_AVAILABLE_LIMIT_PV_(\d{3})\.mp4$')
        used_variants = {int(m.group(1)) for x in live_ready if (m := rx.match(x['name']))}
        for x in existing_rows:
            m = rx.match(x.get('canonical_filename') or '')
            if m:
                used_variants.add(int(m.group(1)))
        next_variant = max(used_variants, default=0) + 1

        WORK_DIR.mkdir(parents=True, exist_ok=True)
        raws = WORK_DIR / 'raw'
        frames = WORK_DIR / 'frames'
        clean_dir = WORK_DIR / 'clean'
        readback_dir = WORK_DIR / 'readback'
        for d in [raws, frames, clean_dir, readback_dir]:
            d.mkdir(parents=True, exist_ok=True)

        plan = []
        duplicate_matches = []
        existing_by_clean_sha = {r.get('clean_checksum'): r for r in existing_rows if r.get('clean_checksum')}
        batch_by_clean_sha: dict[str, dict[str, Any]] = {}
        primary_plan_by_filename: dict[str, dict[str, Any]] = {}
        unique_offset = 0
        preclean_dir = WORK_DIR / 'dedupe-clean'
        preclean_dir.mkdir(parents=True, exist_ok=True)
        for idx, row in enumerate(input_rows, 1):
            raw = raws / f'{idx:02d}.mp4'
            if not raw.exists() or raw.stat().st_size != int(row['size_bytes']):
                drive.download(row['drive_id'], raw)
            raw_sha = sha256_file(raw)
            if raw_sha in by_raw_sha:
                duplicate_matches.append({'match_type': 'existing_raw_sha256', 'source_drive_id': row['drive_id'], 'existing_asset_id': by_raw_sha[raw_sha].get('asset_id'), 'filename': row['original_filename']})
            tech = ffprobe(raw)
            fp = fingerprint_video(raw, tech['duration'], frames, f'{idx:02d}')
            preclean = preclean_dir / f'{idx:02d}.mp4'
            if not preclean.exists():
                preclean_sha, _ = clean_and_verify(raw, preclean)
            else:
                verify_clean(preclean)
                preclean_sha = sha256_file(preclean)
            if preclean_sha in existing_by_clean_sha:
                existing = existing_by_clean_sha[preclean_sha]
                duplicate_matches.append({'match_type': 'existing_clean_sha256', 'source_drive_id': row['drive_id'], 'existing_asset_id': existing.get('asset_id'), 'filename': row['original_filename']})

            primary_filename = DUPLICATE_SOURCE_TO_PRIMARY.get(row['original_filename'])
            if primary_filename:
                primary = primary_plan_by_filename.get(primary_filename)
                if not primary:
                    raise RuntimeError(f'declared duplicate primary not processed first: {primary_filename}')
                if primary['clean_sha256'] != preclean_sha:
                    raise RuntimeError(f'declared duplicate clean hash mismatch: {row["original_filename"]}')
                variant = int(primary['variant'])
                final_name = primary['destination_filename']
                disposition = 'DUPLICATE_SOURCE'
                primary_source_drive_id = primary['source_drive_id']
            else:
                if preclean_sha in batch_by_clean_sha:
                    prior = batch_by_clean_sha[preclean_sha]
                    raise RuntimeError(f'undeclared within-batch clean duplicate: {row["original_filename"]} == {prior["source_filename"]}')
                variant = next_variant + unique_offset
                unique_offset += 1
                final_name = f'CC_US_EN_VID_AVAILABLE_LIMIT_PV_{variant:03d}.mp4'
                if any(x['name'] == final_name for x in live_ready):
                    raise RuntimeError(f'live READY collision: {final_name}')
                disposition = 'UNIQUE_READY'
                primary_source_drive_id = row['drive_id']

            item = {
                'index': idx,
                'source_drive_id': row['drive_id'],
                'source_filename': row['original_filename'],
                'source_sha256': raw_sha,
                'clean_sha256': preclean_sha,
                'preclean_path': str(preclean),
                'raw_path': str(raw),
                'destination_filename': final_name,
                'variant': f'{variant:03d}',
                'disposition': disposition,
                'primary_source_drive_id': primary_source_drive_id,
                'claim': CLAIMS[row['original_filename']],
                'person': 'PERSON',
                'p_orient': 'PV',
                'angle': 'AVAILABLE_LIMIT',
                'width': tech['width'],
                'height': tech['height'],
                'duration_seconds': tech['duration'],
                'codec': tech['codec'],
                'perceptual_fingerprint': fp,
                'source_created_time': live_sources[row['drive_id']].get('createdTime'),
            }
            plan.append(item)
            if disposition == 'UNIQUE_READY':
                batch_by_clean_sha[preclean_sha] = item
                primary_plan_by_filename[row['original_filename']] = item

        dry = {
            'generated_at_utc': utcnow(),
            'mode': 'apply' if args.apply else 'dry-run',
            'operation': OPERATION,
            'auth_mode': auth_mode,
            'shared_drive_validated': shared.get('name') == EXPECTED_DRIVE and root.get('driveId') == ROOT_ID,
            'source_count': len(plan),
            'unique_ready_assets': sum(1 for x in plan if x['disposition'] == 'UNIQUE_READY'),
            'duplicate_sources': sum(1 for x in plan if x['disposition'] == 'DUPLICATE_SOURCE'),
            'ready_existing_group_count': len(used_variants),
            'next_variant': f'{next_variant:03d}',
            'duplicate_checksum_matches': duplicate_matches,
            'plan': [{k: v for k, v in x.items() if k not in {'raw_path', 'preclean_path'}} for x in plan],
        }
        dry_path = REPORT_DIR / 'dry-run.json'
        jdump(dry_path, dry)
        if duplicate_matches:
            raise RuntimeError(f'exact duplicate matches against existing inventory require reconciliation: {len(duplicate_matches)}')
        if not args.apply:
            unique_count = dry['unique_ready_assets']
            print(json.dumps({'done': True, 'dry_run': str(dry_path), 'source_count': len(plan), 'unique_ready_assets': unique_count, 'duplicate_sources': dry['duplicate_sources'], 'next_variant': f'{next_variant:03d}', 'last_variant': f'{next_variant+unique_count-1:03d}'}, ensure_ascii=False, indent=2))
            return 0

        backup_stamp = dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ')
        backup_dir = Path('/root/mgs-agent/backups/ares-creative-ops')
        backup_dir.mkdir(parents=True, exist_ok=True)
        inventory_backup = backup_dir / f'assets-before-kelly-cc-us-en-{backup_stamp}.jsonl'
        shutil.copy2(INVENTORY, inventory_backup)

        state = {'generated_at_utc': utcnow(), 'operation': OPERATION, 'batch_key': batch_key, 'items': {}}
        if STATE_PATH.exists():
            state = json.loads(STATE_PATH.read_text(encoding='utf-8'))
            if state.get('batch_key') != batch_key:
                raise RuntimeError('state belongs to another batch')
        results = []
        for item in plan:
            key = item['source_drive_id']
            st = state['items'].setdefault(key, {})
            print(json.dumps({'processing': item['index'], 'source_filename': item['source_filename'], 'destination_filename': item['destination_filename'], 'disposition': item['disposition']}), flush=True)
            raw = Path(item['raw_path'])
            clean = Path(item['preclean_path'])

            if item['disposition'] == 'DUPLICATE_SOURCE':
                primary_key = item['primary_source_drive_id']
                primary_st = state['items'].get(primary_key) or {}
                dest_id = primary_st.get('destination_drive_id')
                if not dest_id or not primary_st.get('destination_verified') or not primary_st.get('inventory_verified'):
                    raise RuntimeError(f'duplicate primary not fully verified: {item["source_filename"]}')
                if primary_st.get('clean_sha256') != item['clean_sha256']:
                    raise RuntimeError(f'duplicate clean SHA mismatch at apply: {item["source_filename"]}')
                dest_meta = api_get(drive, dest_id)
                if dest_meta.get('name') != item['destination_filename'] or dest_meta.get('parents') != [ready_id] or dest_meta.get('driveId') != ROOT_ID or dest_meta.get('trashed'):
                    raise RuntimeError(f'duplicate active destination readback failed: {item["destination_filename"]}')
                rb = readback_dir / f'duplicate-{item["index"]:02d}.mp4'
                drive.download(dest_id, rb)
                if sha256_file(rb) != item['clean_sha256']:
                    raise RuntimeError(f'duplicate destination SHA-256 readback failed: {item["source_filename"]}')
                verify_clean(rb)
                source_meta = api_get(drive, key)
                source_parent = (source_meta.get('parents') or [None])[0]
                if not source_parent:
                    raise RuntimeError(f'source has no parent: {item["source_filename"]}')
                if source_parent != legacy_id:
                    move_file(drive, key, source_parent, legacy_id)
                source_after = api_get(drive, key)
                if source_after.get('parents') != [legacy_id] or source_after.get('driveId') != ROOT_ID or source_after.get('trashed'):
                    raise RuntimeError(f'duplicate LEGACY source readback failed: {item["source_filename"]}')
                attach_duplicate_source(primary_key, key, item['source_filename'])
                st.update({'destination_drive_id': dest_id, 'clean_sha256': item['clean_sha256'], 'bytes_clean': int(dest_meta.get('size') or 0), 'destination_verified': True, 'legacy_verified': True, 'inventory_verified': True, 'disposition': 'DUPLICATE_SOURCE'})
                jdump(STATE_PATH, state)
                results.append({
                    'index': item['index'], 'status': '01_READY', 'disposition': 'DUPLICATE_SOURCE', 'source_drive_id': key, 'source_filename': item['source_filename'],
                    'destination_drive_id': dest_id, 'destination_filename': item['destination_filename'], 'source_sha256': item['source_sha256'],
                    'clean_sha256': item['clean_sha256'], 'drive_md5': dest_meta.get('md5Checksum'), 'bytes_clean': int(dest_meta.get('size') or 0),
                    'metadata_clean': True, 'drive_readback_verified': True, 'sha256_readback_verified': True, 'person': 'PERSON',
                    'p_orient': 'PV', 'angle': 'AVAILABLE_LIMIT', 'variant': item['variant'], 'claim': item['claim'],
                    'perceptual_fingerprint': item['perceptual_fingerprint'], 'webViewLink': dest_meta.get('webViewLink'),
                })
                continue

            if not clean.exists():
                raise RuntimeError(f'preclean asset missing: {item["source_filename"]}')
            verify_clean(clean)
            if sha256_file(clean) != item['clean_sha256']:
                raise RuntimeError(f'preclean SHA drift: {item["source_filename"]}')

            if not st.get('destination_drive_id'):
                clean_sha = item['clean_sha256']
                dest_id = drive.upload_resumable(ready_id, item['destination_filename'], clean, mimetypes.guess_type(item['destination_filename'])[0] or 'video/mp4')
                st.update({'destination_drive_id': dest_id, 'clean_sha256': clean_sha, 'bytes_clean': clean.stat().st_size, 'uploaded_at_utc': utcnow()})
                jdump(STATE_PATH, state)
            else:
                dest_id = st['destination_drive_id']
                clean_sha = st['clean_sha256']
                if not clean.exists():
                    clean_sha_now, _ = clean_and_verify(raw, clean)
                    if clean_sha_now != clean_sha:
                        raise RuntimeError('recreated clean asset hash drift')

            dest_meta = api_get(drive, dest_id)
            if dest_meta.get('name') != item['destination_filename'] or dest_meta.get('parents') != [ready_id] or dest_meta.get('driveId') != ROOT_ID or dest_meta.get('trashed'):
                raise RuntimeError(f'destination Drive readback failed: {item["destination_filename"]}')
            if int(dest_meta.get('size') or 0) != int(st['bytes_clean']):
                raise RuntimeError(f'destination size readback failed: {item["destination_filename"]}')
            rb = readback_dir / item['destination_filename']
            drive.download(dest_id, rb)
            if sha256_file(rb) != st['clean_sha256']:
                raise RuntimeError(f'destination SHA-256 readback failed: {item["destination_filename"]}')
            verify_clean(rb)
            st['destination_verified'] = True
            jdump(STATE_PATH, state)

            source_meta = api_get(drive, key)
            source_parent = (source_meta.get('parents') or [None])[0]
            if source_parent != legacy_id:
                move_file(drive, key, source_parent, legacy_id)
            source_after = api_get(drive, key)
            if source_after.get('parents') != [legacy_id] or source_after.get('driveId') != ROOT_ID or source_after.get('trashed'):
                raise RuntimeError(f'LEGACY source readback failed: {item["source_filename"]}')
            st['legacy_verified'] = True
            jdump(STATE_PATH, state)

            asset_id = 'asset_' + hashlib.sha256((key + ':' + dest_id).encode()).hexdigest()[:20]
            inventory_row = {
                'asset_id': asset_id,
                'original_filename': item['source_filename'],
                'canonical_filename': item['destination_filename'],
                'source_manager': 'KELLY',
                'requested_by': 'Kelly Nice',
                'created_by': 'KELLY',
                'vertical': 'CC',
                'country': 'US',
                'language': 'EN',
                'strategy': None,
                'ad_account_id': None,
                'source_drive_id': key,
                'asset_drive_id': dest_id,
                'original_checksum': item['source_sha256'],
                'clean_checksum': st['clean_sha256'],
                'perceptual_fingerprint': item['perceptual_fingerprint'],
                'format': 'VID',
                'angle': 'AVAILABLE_LIMIT',
                'person': 'PERSON',
                'orientation': 'VERTICAL',
                'p_orient': 'PV',
                'variant': item['variant'],
                'status': '01_READY',
                'reservation_status': 'RESERVADO_PELO_GESTOR',
                'ares_eligible': False,
                'used_by': None,
                'campaign_owner': 'Kelly',
                'meta_ad_id': None,
                'meta_creative_id': None,
                'meta_image_hash': None,
                'meta_video_id': None,
                'effective_object_story_id': None,
                'width': item['width'],
                'height': item['height'],
                'aspect_ratio': '9:16',
                'placement_fit': 'STORY',
                'metadata_clean': True,
                'first_seen_at': item['source_created_time'] or utcnow(),
                'last_reconciled_at': None,
                'performance_label': 'UNKNOWN',
                'notes': f"Upload humano tratado por Ares. Claim visual dominante: {item['claim']}. Apresentadora é elemento principal. Original preservado em 99_LEGACY. Fail-closed até liberação/conciliação Meta × Drive.",
                'source_path': 'MGS-AGENTS/CRIATIVOS/CC_US_EN/VID/99_LEGACY',
                'asset_path': 'MGS-AGENTS/CRIATIVOS/CC_US_EN/VID/01_READY',
                'webViewLink': dest_meta.get('webViewLink'),
                'local_clean_path': None,
                'thread_id': THREAD_ID,
            }
            append_inventory(inventory_row)
            st['inventory_verified'] = True
            jdump(STATE_PATH, state)
            results.append({
                'index': item['index'], 'status': '01_READY', 'disposition': 'UNIQUE_READY', 'source_drive_id': key, 'source_filename': item['source_filename'],
                'destination_drive_id': dest_id, 'destination_filename': item['destination_filename'], 'source_sha256': item['source_sha256'],
                'clean_sha256': st['clean_sha256'], 'drive_md5': dest_meta.get('md5Checksum'), 'bytes_clean': st['bytes_clean'],
                'metadata_clean': True, 'drive_readback_verified': True, 'sha256_readback_verified': True, 'person': 'PERSON',
                'p_orient': 'PV', 'angle': 'AVAILABLE_LIMIT', 'variant': item['variant'], 'claim': item['claim'],
                'perceptual_fingerprint': item['perceptual_fingerprint'], 'webViewLink': dest_meta.get('webViewLink'),
            })

        final_upload = list_descendant_files(drive, upload_id)
        if final_upload:
            raise RuntimeError(f'UPLOAD MANUAL still contains {len(final_upload)} file item(s)')
        ready_live = {x['id']: x for x in list_children(drive, ready_id)}
        legacy_live = {x['id']: x for x in list_children(drive, legacy_id)}
        final_inventory_rows, final_by_source, _ = load_inventory()
        final_duplicate_source_ids = {
            duplicate_id
            for row in final_inventory_rows
            for duplicate_id in (row.get('duplicate_source_drive_ids') or [])
        }
        for r in results:
            if r['destination_drive_id'] not in ready_live or r['source_drive_id'] not in legacy_live:
                raise RuntimeError('final Drive reconciliation failed')
            if r['disposition'] == 'UNIQUE_READY' and r['source_drive_id'] not in final_by_source:
                raise RuntimeError('final primary inventory reconciliation failed')
            if r['disposition'] == 'DUPLICATE_SOURCE' and r['source_drive_id'] not in final_duplicate_source_ids:
                raise RuntimeError('final duplicate inventory reconciliation failed')

        stamp = dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ')
        csv_path = REPORT_DIR / f'ready-execution-{stamp}.csv'
        manifest_path = REPORT_DIR / f'ready-execution-{stamp}.json'
        latest_path = REPORT_DIR / 'ready-execution-latest.json'
        write_csv(csv_path, results)
        unique_results = [r for r in results if r['disposition'] == 'UNIQUE_READY']
        duplicate_results = [r for r in results if r['disposition'] == 'DUPLICATE_SOURCE']
        manifest = {
            'generated_at_utc': utcnow(), 'operation': OPERATION, 'requested_by': 'Kelly Nice', 'thread_id': THREAD_ID,
            'source_lineages': len(results), 'unique_ready_assets': len(unique_results), 'duplicate_sources': len(duplicate_results),
            'metadata_clean_verified': len(unique_results), 'raw_legacy_verified': len(results), 'upload_manual_remaining_files': 0,
            'reservation_status': 'RESERVADO_PELO_GESTOR', 'ares_eligible': False, 'inventory_backup': str(inventory_backup),
            'ready_parent_id': ready_id, 'legacy_parent_id': legacy_id, 'report_csv': str(csv_path),
            'items': [{'source_filename': r['source_filename'], 'destination_filename': r['destination_filename'], 'disposition': r['disposition'], 'claim': r['claim'], 'angle': r['angle'], 'person': r['person'], 'p_orient': r['p_orient']} for r in results],
        }
        jdump(manifest_path, manifest)
        jdump(latest_path, manifest)
        if WORK_DIR.exists():
            shutil.rmtree(WORK_DIR)
        print(json.dumps({'done': True, 'source_lineages': len(results), 'unique_ready_assets': len(unique_results), 'duplicate_sources': len(duplicate_results), 'upload_manual_remaining_files': 0, 'report_csv': str(csv_path), 'manifest': str(manifest_path), 'first': unique_results[0]['destination_filename'], 'last': unique_results[-1]['destination_filename']}, ensure_ascii=False, indent=2))
        return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'done': False, 'error': str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise
