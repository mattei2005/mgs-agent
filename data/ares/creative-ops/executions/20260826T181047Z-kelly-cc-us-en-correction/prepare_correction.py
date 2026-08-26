#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, importlib.util, json, math, os, subprocess, urllib.parse
from pathlib import Path
from typing import Any
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

BASE=Path('/root/mgs-agent/data/ares/creative-ops/executions/20260826T181047Z-kelly-cc-us-en-correction')
CSV=next((BASE/'stability-3').glob('*inventory*.csv'))
INVENTORY=Path('/root/mgs-agent/data/ares/creative-ops/inventory/assets.jsonl')
EXECUTOR=Path('/root/mgs-agent/scripts/ares-execute-creative-copy-clean.py')
SANITIZER=Path('/root/mgs-agent/scripts/clean-creative-metadata.sh')
ROOT_ID='0AEwt4Ye690ocUk9PVA'; OP='CC_US_EN'; THREAD_ID='1542195602643755139'
EXPECTED_EMAIL='mgsagent@mgs-core-prod.iam.gserviceaccount.com'; EXPECTED_PROJECT='mgs-core-prod'
WORK=BASE/'work'; NEW_RAW=WORK/'new-raw'; OLD_RAW=WORK/'old-raw'; FRAMES=WORK/'frames'; CLEAN=WORK/'clean'; REVIEW=BASE/'review'
for p in (NEW_RAW,OLD_RAW,FRAMES,CLEAN,REVIEW): p.mkdir(parents=True,exist_ok=True)

def load_executor():
    spec=importlib.util.spec_from_file_location('ares_executor_correction',EXECUTOR)
    if spec is None or spec.loader is None: raise RuntimeError('cannot load canonical Drive executor')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def api_get(drive,file_id):
    f='id,name,mimeType,parents,driveId,size,md5Checksum,trashed,capabilities(canDownload,canEdit,canMoveItemWithinDrive,canTrash,canDelete)'
    u=f'https://www.googleapis.com/drive/v3/files/{file_id}?'+urllib.parse.urlencode({'supportsAllDrives':'true','fields':f})
    return drive.request(u) or {}

def list_children(drive,parent):
    q=f"'{parent}' in parents and trashed=false"; f='files(id,name,mimeType,parents,driveId,size,md5Checksum,trashed)'
    u='https://www.googleapis.com/drive/v3/files?'+urllib.parse.urlencode({'q':q,'supportsAllDrives':'true','includeItemsFromAllDrives':'true','pageSize':'1000','fields':f,'orderBy':'name_natural'})
    return (drive.request(u) or {}).get('files',[])

def descendants(drive,parent):
    out=[]; stack=[parent]; seen=set()
    while stack:
        cur=stack.pop()
        if cur in seen: continue
        seen.add(cur)
        for x in list_children(drive,cur):
            if x.get('mimeType')=='application/vnd.google-apps.folder': stack.append(x['id'])
            else: out.append(x)
    return out

def resolve(drive,parts):
    parent=ROOT_ID
    for name in parts:
        parent=drive.find_child_folder(parent,name)
        if not parent: raise RuntimeError(f'missing folder {name}')
    return parent

def sha256(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def ffprobe(p):
    x=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,codec_name:format=duration','-of','json',str(p)],capture_output=True,text=True,check=True,timeout=120)
    d=json.loads(x.stdout); s=d['streams'][0]; return int(s['width']),int(s['height']),float(d['format']['duration']),s.get('codec_name')

def frame(p,dur,frac,out):
    subprocess.run(['ffmpeg','-y','-ss',f'{dur*frac:.3f}','-i',str(p),'-frames:v','1','-q:v','2',str(out)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=120)

def signature(paths):
    sig=[]
    for p in paths:
        im=Image.open(p).convert('L'); w,h=im.size
        # Exclude the corrected/wrong upper label and the lowest CTA strip.
        im=im.crop((int(w*.08),int(h*.20),int(w*.92),int(h*.78))).resize((64,64))
        stat=ImageStat.Stat(im); mean=stat.mean[0]; std=max(stat.stddev[0],1.0)
        vals=[max(0,min(255,int((v-mean)/std*40+128))) for v in im.getdata()]
        norm=Image.new('L',(64,64)); norm.putdata(vals); sig.append(norm)
    return sig

def cost(a,b):
    total=0.0
    for x,y in zip(a,b):
        total+=ImageStat.Stat(ImageChops.difference(x,y)).mean[0]
    return total/len(a)

def hungarian(a):
    n=len(a); m=len(a[0]); u=[0.0]*(n+1); v=[0.0]*(m+1); p=[0]*(m+1); way=[0]*(m+1)
    for i in range(1,n+1):
        p[0]=i; j0=0; minv=[math.inf]*(m+1); used=[False]*(m+1)
        while True:
            used[j0]=True; i0=p[j0]; delta=math.inf; j1=0
            for j in range(1,m+1):
                if used[j]: continue
                cur=a[i0-1][j-1]-u[i0]-v[j]
                if cur<minv[j]: minv[j]=cur; way[j]=j0
                if minv[j]<delta: delta=minv[j]; j1=j
            for j in range(m+1):
                if used[j]: u[p[j]]+=delta; v[j]-=delta
                else: minv[j]-=delta
            j0=j1
            if p[j0]==0: break
        while True:
            j1=way[j0]; p[j0]=p[j1]; j0=j1
            if j0==0: break
    ans=[-1]*n
    for j in range(1,m+1):
        if p[j]: ans[p[j]-1]=j-1
    return ans

def clean_verify(raw,out):
    x=subprocess.run([str(SANITIZER),'clean',str(raw),'--out',str(out),'--agent','ares'],capture_output=True,text=True,timeout=900)
    if x.returncode: raise RuntimeError(f'sanitizer clean failed: {(x.stdout+x.stderr)[-500:]}')
    y=subprocess.run([str(SANITIZER),'verify',str(out)],capture_output=True,text=True,timeout=300)
    if y.returncode or 'clean: true' not in y.stdout: raise RuntimeError(f'sanitizer verify failed: {(y.stdout+y.stderr)[-500:]}')
    return sha256(out)

def fit(src,w=300,h=533):
    im=Image.open(src).convert('RGB'); im.thumbnail((w,h)); c=Image.new('RGB',(w,h),'white'); c.paste(im,((w-im.width)//2,(h-im.height)//2)); return c

def main():
    incoming=list(csv.DictReader(CSV.open(encoding='utf-8')))
    if len(incoming)!=10 or any(r.get('format')!='VID' for r in incoming): raise RuntimeError('expected stable 10-video correction batch')
    inv=[json.loads(line) for line in INVENTORY.read_text(encoding='utf-8').splitlines() if line.strip()]
    old=[]
    for x in inv:
        n=x.get('canonical_filename','')
        if x.get('thread_id')==THREAD_ID and n.startswith('CC_US_EN_VID_AVAILABLE_LIMIT_PV_'):
            try: var=int(x.get('variant'))
            except: continue
            if 63<=var<=82: old.append(x)
    old.sort(key=lambda x:int(x['variant']))
    if len(old)!=20: raise RuntimeError(f'expected 20 erroneous lineages, got {len(old)}')
    ex=load_executor(); ex.load_env(); sa=ex.service_account()
    if sa.get('client_email')!=EXPECTED_EMAIL or sa.get('project_id')!=EXPECTED_PROJECT: raise RuntimeError('service account identity mismatch')
    token,mode=ex.build_access_token()
    if mode!='service_account': raise RuntimeError('non-service-account auth refused')
    drive=ex.Drive(token); root=drive.preflight_destination(mode); shared=drive.request(f'https://www.googleapis.com/drive/v3/drives/{ROOT_ID}?fields=id,name') or {}
    if root.get('driveId')!=ROOT_ID or shared.get('name')!='MGS-AGENTS': raise RuntimeError('Shared Drive mismatch')
    upload=resolve(drive,['CRIATIVOS','UPLOAD MANUAL']); ready=resolve(drive,['CRIATIVOS',OP,'VID','01_READY']); legacy=resolve(drive,['CRIATIVOS',OP,'VID','99_LEGACY'])
    live={x['id']:x for x in descendants(drive,upload)}; expected={r['drive_id'] for r in incoming}
    if set(live)!=expected: raise RuntimeError(f'fresh queue mismatch incoming={len(expected)} live={len(live)}')
    ready_live={x['id']:x for x in list_children(drive,ready)}; legacy_live={x['id']:x for x in list_children(drive,legacy)}
    for x in old:
        if x['asset_drive_id'] not in ready_live or x['source_drive_id'] not in legacy_live: raise RuntimeError(f'old lineage Drive state mismatch {x["canonical_filename"]}')
    new_items=[]; old_items=[]
    for i,r in enumerate(incoming,1):
        meta=api_get(drive,r['drive_id']); caps=meta.get('capabilities') or {}
        if meta.get('driveId')!=ROOT_ID or r['drive_id'] not in live or not caps.get('canDownload') or not caps.get('canMoveItemWithinDrive'): raise RuntimeError(f'incoming capability/state mismatch {r["original_filename"]}')
        raw=NEW_RAW/f'{i:02d}.mp4'; drive.download(r['drive_id'],raw); w,h,dur,codec=ffprobe(raw)
        if (w,h)!=(1080,1920) or dur<=0: raise RuntimeError(f'bad technical profile {r["original_filename"]}')
        fps=[]
        for k,frac in enumerate((.2,.5,.8),1):
            o=FRAMES/f'new-{i:02d}-{k}.jpg'; frame(raw,dur,frac,o); fps.append(o)
        new_items.append({'index':i,'drive_id':r['drive_id'],'filename':r['original_filename'],'source_parent_id':meta['parents'][0],'raw_path':str(raw),'raw_sha256':sha256(raw),'size':raw.stat().st_size,'duration':dur,'codec':codec,'frames':[str(x) for x in fps],'sig':signature(fps)})
    for i,x in enumerate(old,1):
        raw=OLD_RAW/f'{i:02d}.mp4'; drive.download(x['source_drive_id'],raw); w,h,dur,codec=ffprobe(raw)
        fps=[]
        for k,frac in enumerate((.2,.5,.8),1):
            o=FRAMES/f'old-{i:02d}-{k}.jpg'; frame(raw,dur,frac,o); fps.append(o)
        old_items.append({'index':i,'source_drive_id':x['source_drive_id'],'asset_drive_id':x['asset_drive_id'],'original_filename':x['original_filename'],'canonical_filename':x['canonical_filename'],'variant':x['variant'],'asset_id':x['asset_id'],'raw_path':str(raw),'frames':[str(z) for z in fps],'sig':signature(fps)})
    matrix=[[cost(n['sig'],o['sig']) for o in old_items] for n in new_items]
    assignment=hungarian(matrix); matches=[]
    for i,j in enumerate(assignment):
        ranked=sorted([(matrix[i][k],k) for k in range(len(old_items))])
        best=matrix[i][j]; second=min(v for v,k in ranked if k!=j); margin=second-best
        n=new_items[i]; o=old_items[j]
        clean=CLEAN/o['canonical_filename']; clean_sha=clean_verify(Path(n['raw_path']),clean)
        if clean_sha in {x.get('clean_checksum') for x in inv if x.get('clean_checksum')}: raise RuntimeError(f'corrected clean file duplicates existing inventory: {n["filename"]}')
        matches.append({'incoming_index':n['index'],'incoming_drive_id':n['drive_id'],'incoming_filename':n['filename'],'incoming_source_parent_id':n['source_parent_id'],'incoming_raw_sha256':n['raw_sha256'],'incoming_size':n['size'],'incoming_duration':n['duration'],'clean_path':str(clean),'clean_sha256':clean_sha,'replaces_asset_id':o['asset_id'],'replaces_source_drive_id':o['source_drive_id'],'replaces_asset_drive_id':o['asset_drive_id'],'replaces_original_filename':o['original_filename'],'canonical_filename':o['canonical_filename'],'variant':o['variant'],'visual_cost':round(best,3),'next_best_cost':round(second,3),'margin':round(margin,3)})
    # New batch review sheets.
    font=ImageFont.load_default()
    for start in range(0,len(new_items),5):
        batch=new_items[start:start+5]; sheet=Image.new('RGB',(920,len(batch)*610),'white'); draw=ImageDraw.Draw(sheet); y=0
        for item in batch:
            draw.text((10,y+5),f"{item['index']:02d} | {item['filename']} | {item['duration']:.2f}s",fill='black',font=font)
            for k,p in enumerate(item['frames']): sheet.paste(fit(Path(p)),(10+k*303,y+45))
            y+=610
        sheet.save(REVIEW/f'corrected-{start+1:02d}-{start+len(batch):02d}.jpg',quality=92)
    result={'generated_at_utc':__import__('datetime').datetime.now(__import__('datetime').UTC).isoformat(),'auth_mode':mode,'shared_drive':shared.get('name'),'incoming_count':len(new_items),'erroneous_lineages_count':len(old_items),'matched_replacements':len(matches),'unmatched_erroneous':[{'asset_id':o['asset_id'],'source_drive_id':o['source_drive_id'],'asset_drive_id':o['asset_drive_id'],'original_filename':o['original_filename'],'canonical_filename':o['canonical_filename'],'variant':o['variant']} for o in old_items if o['asset_drive_id'] not in {m['replaces_asset_drive_id'] for m in matches}],'matches':matches,'ready_parent_id':ready,'legacy_parent_id':legacy,'upload_parent_id':upload}
    (BASE/'correction-stage.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'staged':True,'incoming':len(new_items),'matched':len(matches),'unmatched_erroneous':len(result['unmatched_erroneous']),'matches':[{'incoming':m['incoming_filename'],'replaces':m['canonical_filename'],'cost':m['visual_cost'],'margin':m['margin']} for m in matches],'review_sheets':[str(p) for p in sorted(REVIEW.glob('*.jpg'))]},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
