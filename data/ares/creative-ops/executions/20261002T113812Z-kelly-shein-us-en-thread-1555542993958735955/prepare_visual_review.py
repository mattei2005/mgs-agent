#!/usr/bin/env python3
from __future__ import annotations
import csv, importlib.util, json, subprocess, urllib.parse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

CSV_PATH=Path('/root/mgs-agent/data/ares/creative-ops/intake/20261002-kelly-shein-us-en/poll-3/upload-manual-inventory-20261002T113812Z.csv')
BASE=Path('/root/mgs-agent/data/ares/creative-ops/executions/20261002T113812Z-kelly-shein-us-en-thread-1555542993958735955')
RAW=BASE/'visual-review'/'raw'
FRAMES=BASE/'visual-review'/'frames'
SHEETS=BASE/'visual-review'/'contact-sheets'
EXECUTOR=Path('/root/mgs-agent/scripts/ares-execute-creative-copy-clean.py')
ROOT_ID='0AEwt4Ye690ocUk9PVA'
EXPECTED_EMAIL='mgsagent@mgs-core-prod.iam.gserviceaccount.com'
EXPECTED_PROJECT='mgs-core-prod'

spec=importlib.util.spec_from_file_location('ares_executor',EXECUTOR)
if spec is None or spec.loader is None: raise RuntimeError('cannot load executor')
ex=importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)
ex.load_env(); sa=ex.service_account()
if sa.get('client_email')!=EXPECTED_EMAIL or sa.get('project_id')!=EXPECTED_PROJECT: raise RuntimeError('service account mismatch')
token,auth_mode=ex.build_access_token()
if auth_mode!='service_account': raise RuntimeError('auth mode mismatch')
drive=ex.Drive(token); root=drive.preflight_destination(auth_mode)
if root.get('driveId')!=ROOT_ID: raise RuntimeError('drive mismatch')
for d in (RAW,FRAMES,SHEETS): d.mkdir(parents=True,exist_ok=True)
rows=[r for r in csv.DictReader(open(CSV_PATH,encoding='utf-8')) if r.get('format')=='VID']
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',24)
small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
items=[]
for idx,row in enumerate(rows,1):
    raw=RAW/f'{idx:02d}.mp4'
    if not raw.exists() or raw.stat().st_size!=int(row['size_bytes']): drive.download(row['drive_id'],raw)
    p=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height:format=duration','-of','json',str(raw)],capture_output=True,text=True,timeout=120,check=True)
    meta=json.loads(p.stdout); stream=meta['streams'][0]; duration=float(meta['format']['duration'])
    if int(stream['width'])!=1080 or int(stream['height'])!=1920 or duration<=0: raise RuntimeError(f'bad media {row["original_filename"]}')
    frame_paths=[]
    for j,frac in enumerate((0.2,0.5,0.8,0.95),1):
        out=FRAMES/f'{idx:02d}-{j}.jpg'
        subprocess.run(['ffmpeg','-y','-ss',f'{duration*frac:.3f}','-i',str(raw),'-frames:v','1','-q:v','2',str(out)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=120,check=True)
        frame_paths.append(out)
    items.append({'index':idx,'filename':row['original_filename'],'drive_id':row['drive_id'],'duration':duration,'frames':[str(x) for x in frame_paths]})

for start in range(0,len(items),4):
    chunk=items[start:start+4]
    fw,fh=405,720; label_h=76
    sheet=Image.new('RGB',(fw*4,(fh+label_h)*len(chunk)),(20,20,20)); draw=ImageDraw.Draw(sheet)
    for r,item in enumerate(chunk):
        y=r*(fh+label_h)
        label=f"#{item['index']:02d} {item['filename']}"
        draw.text((8,y+4),label[:105],fill='white',font=font)
        draw.text((8,y+38),'Frames: 20% | 50% | 80% | 95%',fill=(180,220,255),font=small)
        for c,fp in enumerate(item['frames']):
            im=Image.open(fp).convert('RGB'); im.thumbnail((fw,fh))
            x=c*fw+(fw-im.width)//2; yy=y+label_h+(fh-im.height)//2
            sheet.paste(im,(x,yy))
    out=SHEETS/f'sheet-{start//4+1:02d}.jpg'; sheet.save(out,quality=92)
manifest={'auth_mode':auth_mode,'shared_drive_id':ROOT_ID,'source_count':len(items),'csv':str(CSV_PATH),'items':items,'sheets':[str(x) for x in sorted(SHEETS.glob('*.jpg'))]}
(BASE/'visual-review'/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'source_count':len(items),'sheets':manifest['sheets'],'manifest':str(BASE/'visual-review'/'manifest.json')},ensure_ascii=False,indent=2))
