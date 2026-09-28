#!/usr/bin/env python3
from __future__ import annotations
import csv, importlib.util, json, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE = Path('/root/mgs-agent/data/ares/creative-ops/executions/20260922T001300Z-kelly-shein-us-en-thread-1551746943489806417')
CSV = Path('/root/mgs-agent/data/ares/creative-ops/intake/stability-20260922/upload-manual-inventory-20260922T001202Z.csv')
PRIOR = Path('/root/mgs-agent/data/ares/creative-ops/executions/20260915T202402Z-kelly-shein-us-en-thread-1549514259069927457/process_batch.py')
ROOT_ID = '0AEwt4Ye690ocUk9PVA'
EXPECTED_EMAIL = 'mgsagent@mgs-core-prod.iam.gserviceaccount.com'
EXPECTED_PROJECT = 'mgs-core-prod'

spec = importlib.util.spec_from_file_location('prior_shein', PRIOR)
if spec is None or spec.loader is None:
    raise RuntimeError('cannot load prior verified SHEIN executor')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
ex = mod.load_executor()
ex.load_env()
sa = ex.service_account()
if sa.get('client_email') != EXPECTED_EMAIL or sa.get('project_id') != EXPECTED_PROJECT:
    raise RuntimeError('canonical service-account identity mismatch')
token, mode = ex.build_access_token()
if mode != 'service_account':
    raise RuntimeError('non-service-account auth refused')
drive = ex.Drive(token)
root = drive.preflight_destination(mode)
shared = drive.request(f'https://www.googleapis.com/drive/v3/drives/{ROOT_ID}?fields=id,name') or {}
if root.get('driveId') != ROOT_ID or shared.get('name') != 'MGS-AGENTS':
    raise RuntimeError('Shared Drive identity mismatch')

rows = [r for r in csv.DictReader(CSV.open(encoding='utf-8')) if r.get('format') == 'VID']
if len(rows) != 20:
    raise RuntimeError(f'expected 20 videos, got {len(rows)}')
raw_dir = BASE / 'review' / 'raw'
frame_dir = BASE / 'review' / 'frames'
strip_dir = BASE / 'review' / 'strips'
sheet_dir = BASE / 'review' / 'sheets'
for d in (raw_dir, frame_dir, strip_dir, sheet_dir): d.mkdir(parents=True, exist_ok=True)
font = ImageFont.load_default()
tech = []
for idx, row in enumerate(rows, 1):
    raw = raw_dir / f'{idx:02d}.mp4'
    if not raw.exists() or raw.stat().st_size != int(row['size_bytes']):
        drive.download(row['drive_id'], raw)
    info = mod.ffprobe(raw)
    frames=[]
    for n, frac in enumerate((0.2, 0.5, 0.8, 0.95), 1):
        out=frame_dir / f'{idx:02d}-{n}.jpg'
        p=subprocess.run(['ffmpeg','-y','-ss',f"{info['duration']*frac:.3f}",'-i',str(raw),'-frames:v','1','-q:v','2',str(out)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=120)
        if p.returncode or not out.exists(): raise RuntimeError(f'frame extraction failed for {row["original_filename"]}: {p.stderr[-200:]}')
        frames.append(out)
    thumbs=[]
    for f in frames:
        im=Image.open(f).convert('RGB'); im.thumbnail((270,480)); thumbs.append(im.copy())
    label=f'{idx:02d} | {row["original_filename"]}'
    strip=Image.new('RGB',(270*4,520),(255,255,255)); dr=ImageDraw.Draw(strip); dr.text((6,4),label,fill=(0,0,0),font=font)
    for j,im in enumerate(thumbs): strip.paste(im,(j*270,40))
    strip_path=strip_dir/f'{idx:02d}.jpg'; strip.save(strip_path,quality=92)
    tech.append({'index':idx,'drive_id':row['drive_id'],'filename':row['original_filename'],'size':int(row['size_bytes']),'width':info['width'],'height':info['height'],'duration':info['duration'],'codec':info['codec'],'strip':str(strip_path)})
for batch in range(4):
    items=tech[batch*5:(batch+1)*5]
    sheet=Image.new('RGB',(1080,520*len(items)),(238,238,238))
    for y,item in enumerate(items): sheet.paste(Image.open(item['strip']).convert('RGB'),(0,y*520))
    sheet.save(sheet_dir/f'sheet-{batch+1}.jpg',quality=90)
(BASE/'technical.json').write_text(json.dumps({'auth_mode':mode,'shared_drive':shared.get('name'),'count':len(tech),'items':tech},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'done':True,'count':len(tech),'sheets':[str(sheet_dir/f'sheet-{i}.jpg') for i in range(1,5)],'technical':str(BASE/'technical.json')},ensure_ascii=False,indent=2))
