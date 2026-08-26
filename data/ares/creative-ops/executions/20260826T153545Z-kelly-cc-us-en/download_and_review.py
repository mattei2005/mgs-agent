#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, importlib.util, json, subprocess, urllib.parse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE=Path('/root/mgs-agent/data/ares/creative-ops/executions/20260826T153545Z-kelly-cc-us-en')
CSV=next((BASE/'stability-3').glob('*inventory*.csv'))
EXECUTOR=Path('/root/mgs-agent/scripts/ares-execute-creative-copy-clean.py')
ROOT_ID='0AEwt4Ye690ocUk9PVA'
EXPECTED_EMAIL='mgsagent@mgs-core-prod.iam.gserviceaccount.com'
EXPECTED_PROJECT='mgs-core-prod'
RAW=BASE/'work'/'raw'; FRAMES=BASE/'work'/'frames'; SHEETS=BASE/'review'
for p in (RAW,FRAMES,SHEETS): p.mkdir(parents=True,exist_ok=True)

def load_executor():
    spec=importlib.util.spec_from_file_location('ares_executor_review',EXECUTOR)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def get(drive,file_id):
    fields='id,name,mimeType,parents,driveId,size,md5Checksum,trashed,capabilities(canDownload,canEdit,canMoveItemWithinDrive)'
    u=f'https://www.googleapis.com/drive/v3/files/{file_id}?'+urllib.parse.urlencode({'supportsAllDrives':'true','fields':fields})
    return drive.request(u) or {}

def sha256(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def ffprobe(p):
    x=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,codec_name:format=duration','-of','json',str(p)],capture_output=True,text=True,check=True,timeout=120)
    d=json.loads(x.stdout); s=d['streams'][0]
    return int(s['width']),int(s['height']),float(d['format']['duration']),s.get('codec_name')

def fit_frame(src,w=300,h=533):
    im=Image.open(src).convert('RGB'); im.thumbnail((w,h))
    canvas=Image.new('RGB',(w,h),'white'); canvas.paste(im,((w-im.width)//2,(h-im.height)//2)); return canvas

def main():
    rows=list(csv.DictReader(CSV.open(encoding='utf-8')))
    if len(rows)!=20: raise RuntimeError(f'expected 20 videos, got {len(rows)}')
    ex=load_executor(); ex.load_env(); sa=ex.service_account()
    if sa.get('client_email')!=EXPECTED_EMAIL or sa.get('project_id')!=EXPECTED_PROJECT: raise RuntimeError('service account identity mismatch')
    token,mode=ex.build_access_token()
    if mode!='service_account': raise RuntimeError('non-service-account auth refused')
    drive=ex.Drive(token); root=drive.preflight_destination(mode)
    shared=drive.request(f'https://www.googleapis.com/drive/v3/drives/{ROOT_ID}?fields=id,name') or {}
    if root.get('driveId')!=ROOT_ID or shared.get('name')!='MGS-AGENTS': raise RuntimeError('Shared Drive validation failed')
    manifest=[]
    for i,r in enumerate(rows,1):
        meta=get(drive,r['drive_id']); caps=meta.get('capabilities') or {}
        if meta.get('driveId')!=ROOT_ID or meta.get('trashed') or not caps.get('canDownload') or not caps.get('canMoveItemWithinDrive'): raise RuntimeError(f'bad source/capability {r["original_filename"]}')
        raw=RAW/f'{i:02d}.mp4'
        if not raw.exists() or raw.stat().st_size!=int(r['size_bytes']): drive.download(r['drive_id'],raw)
        if raw.stat().st_size!=int(r['size_bytes']): raise RuntimeError(f'size mismatch {r["original_filename"]}')
        w,h,dur,codec=ffprobe(raw)
        if (w,h)!=(1080,1920) or dur<=0: raise RuntimeError(f'technical profile mismatch {r["original_filename"]}: {w}x{h} {dur}')
        fpaths=[]
        for j,frac in enumerate((0.2,0.5,0.8),1):
            out=FRAMES/f'{i:02d}-{j}.jpg'
            subprocess.run(['ffmpeg','-y','-ss',f'{dur*frac:.3f}','-i',str(raw),'-frames:v','1','-q:v','2',str(out)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=120)
            fpaths.append(str(out))
        manifest.append({'index':i,'drive_id':r['drive_id'],'filename':r['original_filename'],'source_parent_id':meta['parents'][0],'size':int(r['size_bytes']),'drive_md5':r['md5_checksum'],'sha256':sha256(raw),'width':w,'height':h,'duration':dur,'codec':codec,'frames':fpaths})
    (BASE/'review-manifest.json').write_text(json.dumps({'auth_mode':mode,'shared_drive':shared.get('name'),'items':manifest},ensure_ascii=False,indent=2),encoding='utf-8')
    font=ImageFont.load_default()
    for start in range(0,len(manifest),5):
        batch=manifest[start:start+5]; sheet=Image.new('RGB',(920,len(batch)*610),'white'); draw=ImageDraw.Draw(sheet)
        y=0
        for item in batch:
            label=f"{item['index']:02d} | {item['filename']} | {item['duration']:.2f}s"
            draw.text((10,y+5),label,fill='black',font=font)
            for j,p in enumerate(item['frames']): sheet.paste(fit_frame(Path(p)),(10+j*303,y+45))
            y+=610
        out=SHEETS/f'review-{start+1:02d}-{start+len(batch):02d}.jpg'; sheet.save(out,quality=92)
    print(json.dumps({'auth_mode':mode,'shared_drive':shared.get('name'),'videos':len(manifest),'sheets':[str(p) for p in sorted(SHEETS.glob('review-*.jpg'))]},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
