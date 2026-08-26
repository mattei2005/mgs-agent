#!/usr/bin/env python3
from __future__ import annotations
import csv, datetime as dt, fcntl, hashlib, importlib.util, json, mimetypes, os, shutil, subprocess, urllib.parse
from pathlib import Path
from typing import Any
from PIL import Image

BASE=Path('/root/mgs-agent/data/ares/creative-ops/executions/20260826T181047Z-kelly-cc-us-en-correction')
STAGE=BASE/'correction-stage.json'; STATE=BASE/'apply-state.json'; INVENTORY=Path('/root/mgs-agent/data/ares/creative-ops/inventory/assets.jsonl')
EXECUTOR=Path('/root/mgs-agent/scripts/ares-execute-creative-copy-clean.py'); SANITIZER=Path('/root/mgs-agent/scripts/clean-creative-metadata.sh')
ROOT_ID='0AEwt4Ye690ocUk9PVA'; OP='CC_US_EN'; THREAD_ID='1542195602643755139'
EXPECTED_EMAIL='mgsagent@mgs-core-prod.iam.gserviceaccount.com'; EXPECTED_PROJECT='mgs-core-prod'
CONFIRMATION='Kelly Nice confirmed sending 40 erroneous files to Drive trash and replacing them with 10 corrected videos.'

def now(): return dt.datetime.now(dt.UTC).isoformat()
def load_executor():
    spec=importlib.util.spec_from_file_location('ares_executor_apply_correction',EXECUTOR)
    if spec is None or spec.loader is None: raise RuntimeError('cannot load canonical Drive executor')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def jdump(path,data):
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8'); os.replace(tmp,path)

def api_get(drive,file_id):
    f='id,name,mimeType,parents,driveId,size,md5Checksum,createdTime,modifiedTime,trashed,webViewLink,capabilities(canDownload,canEdit,canMoveItemWithinDrive,canModifyContent,canTrash,canDelete)'
    u=f'https://www.googleapis.com/drive/v3/files/{file_id}?'+urllib.parse.urlencode({'supportsAllDrives':'true','fields':f})
    return drive.request(u) or {}

def list_children(drive,parent):
    q=f"'{parent}' in parents and trashed=false"; f='files(id,name,mimeType,parents,driveId,size,md5Checksum,trashed,webViewLink)'
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
        if not parent: raise RuntimeError(f'missing canonical folder {name}')
    return parent

def move_file(drive,file_id,old_parent,new_parent):
    p={'supportsAllDrives':'true','addParents':new_parent,'removeParents':old_parent,'fields':'id,name,parents,driveId,trashed'}
    u=f'https://www.googleapis.com/drive/v3/files/{file_id}?'+urllib.parse.urlencode(p)
    return drive.request(u,method='PATCH',data=b'',headers={'Content-Type':'application/json'}) or {}

def trash_file(drive,file_id):
    p={'supportsAllDrives':'true','fields':'id,name,parents,driveId,trashed'}
    u=f'https://www.googleapis.com/drive/v3/files/{file_id}?'+urllib.parse.urlencode(p)
    return drive.request(u,method='PATCH',data=json.dumps({'trashed':True}).encode(),headers={'Content-Type':'application/json'}) or {}

def sha256(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def verify_clean(p):
    x=subprocess.run([str(SANITIZER),'verify',str(p)],capture_output=True,text=True,timeout=300)
    if x.returncode or 'clean: true' not in x.stdout: raise RuntimeError(f'metadata verify failed: {(x.stdout+x.stderr)[-500:]}')

def dhash(path):
    with Image.open(path) as im: px=list(im.convert('L').resize((9,8)).getdata())
    val=0
    for y in range(8):
        for x in range(8): val=(val<<1)|int(px[y*9+x]>px[y*9+x+1])
    return f'{val:016x}'

def fingerprint(index):
    vals=[]
    for k in (1,2,3):
        p=BASE/'work'/'frames'/f'new-{index:02d}-{k}.jpg'
        if not p.exists(): raise RuntimeError(f'missing staged frame {p.name}')
        vals.append(dhash(p))
    return 'dhash64:'+'/'.join(vals)

def load_inventory(): return [json.loads(x) for x in INVENTORY.read_text(encoding='utf-8').splitlines() if x.strip()]

def main():
    stage=json.loads(STAGE.read_text(encoding='utf-8')); matches=stage['matches']; unmatched=stage['unmatched_erroneous']
    if len(matches)!=10 or len(unmatched)!=10 or stage.get('erroneous_lineages_count')!=20: raise RuntimeError('stage count mismatch')
    old_asset_ids={m['replaces_asset_id'] for m in matches}|{u['asset_id'] for u in unmatched}
    old_drive_ids={m['replaces_source_drive_id'] for m in matches}|{m['replaces_asset_drive_id'] for m in matches}|{u['source_drive_id'] for u in unmatched}|{u['asset_drive_id'] for u in unmatched}
    if len(old_asset_ids)!=20 or len(old_drive_ids)!=40: raise RuntimeError('critical delete target set mismatch')
    incoming_ids={m['incoming_drive_id'] for m in matches}
    batch_key=hashlib.sha256('|'.join(sorted(incoming_ids|old_drive_ids)).encode()).hexdigest()[:20]
    lock_path=Path('/root/mgs-agent/tmp/ares-intake-locks')/f'cc_us_en-correction-{batch_key}.lock'; lock_path.parent.mkdir(parents=True,exist_ok=True)
    with lock_path.open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        ex=load_executor(); ex.load_env(); sa=ex.service_account()
        if sa.get('client_email')!=EXPECTED_EMAIL or sa.get('project_id')!=EXPECTED_PROJECT: raise RuntimeError('service account identity mismatch')
        token,mode=ex.build_access_token()
        if mode!='service_account': raise RuntimeError('non-service-account auth refused')
        drive=ex.Drive(token); root=drive.preflight_destination(mode); shared=drive.request(f'https://www.googleapis.com/drive/v3/drives/{ROOT_ID}?fields=id,name') or {}
        if root.get('driveId')!=ROOT_ID or shared.get('name')!='MGS-AGENTS': raise RuntimeError('Shared Drive mismatch')
        upload=resolve(drive,['CRIATIVOS','UPLOAD MANUAL']); ready=resolve(drive,['CRIATIVOS',OP,'VID','01_READY']); legacy=resolve(drive,['CRIATIVOS',OP,'VID','99_LEGACY'])
        state={'batch_key':batch_key,'created_at':now(),'confirmed_by':'Kelly Nice','confirmation':CONFIRMATION,'uploads':{},'trashed':{},'moved':{},'inventory_updated':False}
        if STATE.exists():
            state=json.loads(STATE.read_text(encoding='utf-8'))
            if state.get('batch_key')!=batch_key: raise RuntimeError('state belongs to different batch')
        inv=load_inventory(); by_asset={x.get('asset_id'):x for x in inv}
        if not old_asset_ids.issubset(by_asset): raise RuntimeError('inventory old lineage set missing')
        live_upload={x['id']:x for x in descendants(drive,upload)}
        # On first run all sources are in upload; on resume they may already be in LEGACY.
        if not state['moved'] and set(live_upload)!=incoming_ids: raise RuntimeError(f'fresh upload mismatch expected=10 live={len(live_upload)}')
        # Preflight all deletion targets before any write. Already-trashed targets are accepted on resume.
        for file_id in sorted(old_drive_ids):
            meta=api_get(drive,file_id)
            if meta.get('driveId')!=ROOT_ID: raise RuntimeError(f'delete target outside canonical Drive {file_id}')
            if not meta.get('trashed'):
                caps=meta.get('capabilities') or {}
                if not caps.get('canTrash'): raise RuntimeError(f'delete target cannot be moved to trash: {meta.get("name")}')
        # Validate staged corrected files and incoming capabilities before uploads.
        for m in matches:
            clean=Path(m['clean_path']); verify_clean(clean)
            if sha256(clean)!=m['clean_sha256']: raise RuntimeError(f'staged clean hash drift {m["incoming_filename"]}')
            src=api_get(drive,m['incoming_drive_id'])
            if src.get('driveId')!=ROOT_ID or src.get('trashed'): raise RuntimeError(f'incoming source invalid {m["incoming_filename"]}')
            caps=src.get('capabilities') or {}
            if not caps.get('canDownload') or not caps.get('canMoveItemWithinDrive'): raise RuntimeError(f'incoming capability missing {m["incoming_filename"]}')
        # Upload and fully validate all corrected destinations BEFORE trashing any old file.
        readback_dir=BASE/'work'/'apply-readback'; readback_dir.mkdir(parents=True,exist_ok=True)
        for m in matches:
            key=m['incoming_drive_id']; st=state['uploads'].setdefault(key,{})
            clean=Path(m['clean_path'])
            if not st.get('destination_drive_id'):
                dest=drive.upload_resumable(ready,m['canonical_filename'],clean,mimetypes.guess_type(m['canonical_filename'])[0] or 'video/mp4')
                st.update({'destination_drive_id':dest,'name':m['canonical_filename'],'bytes':clean.stat().st_size,'sha256':m['clean_sha256'],'uploaded_at':now()}); jdump(STATE,state)
            dest=st['destination_drive_id']; meta=api_get(drive,dest)
            if meta.get('name')!=m['canonical_filename'] or meta.get('parents')!=[ready] or meta.get('driveId')!=ROOT_ID or meta.get('trashed') or int(meta.get('size') or 0)!=st['bytes']: raise RuntimeError(f'corrected destination metadata mismatch {m["canonical_filename"]}')
            rb=readback_dir/m['canonical_filename']; drive.download(dest,rb)
            if sha256(rb)!=m['clean_sha256']: raise RuntimeError(f'corrected destination SHA mismatch {m["canonical_filename"]}')
            verify_clean(rb); st['verified']=True; st['drive_md5']=meta.get('md5Checksum'); st['webViewLink']=meta.get('webViewLink'); jdump(STATE,state)
        if sum(bool(x.get('verified')) for x in state['uploads'].values())!=10: raise RuntimeError('not all corrected destinations verified')
        # Critical deletion confirmed: move exactly the 40 erroneous files to trash.
        for file_id in sorted(old_drive_ids):
            meta=api_get(drive,file_id)
            if not meta.get('trashed'):
                trash_file(drive,file_id)
            after=api_get(drive,file_id)
            if not after.get('trashed') or after.get('driveId')!=ROOT_ID: raise RuntimeError(f'trash readback failed {meta.get("name")}')
            state['trashed'][file_id]={'name':after.get('name') or meta.get('name'),'verified':True,'trashed_at':now()}; jdump(STATE,state)
        if len(state['trashed'])!=40: raise RuntimeError('trashed target count mismatch')
        # Move corrected RAW sources into LEGACY after all clean destinations passed.
        for m in matches:
            key=m['incoming_drive_id']; meta=api_get(drive,key); parents=meta.get('parents') or []
            if meta.get('trashed'): raise RuntimeError(f'incoming source unexpectedly trashed {m["incoming_filename"]}')
            if parents!=[legacy]:
                if len(parents)!=1: raise RuntimeError(f'incoming source parent ambiguity {m["incoming_filename"]}')
                move_file(drive,key,parents[0],legacy)
            after=api_get(drive,key)
            if after.get('parents')!=[legacy] or after.get('driveId')!=ROOT_ID or after.get('trashed'): raise RuntimeError(f'corrected LEGACY move readback failed {m["incoming_filename"]}')
            state['moved'][key]={'name':after.get('name'),'verified':True,'moved_at':now(),'createdTime':after.get('createdTime')}; jdump(STATE,state)
        # Reconcile inventory atomically, preserving every retired revision.
        if not state.get('inventory_updated'):
            stamp=dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ'); backup=Path('/root/mgs-agent/backups/ares-creative-ops')/f'assets-before-kelly-cc-us-en-correction-{stamp}.jsonl'; backup.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(INVENTORY,backup)
            match_by_asset={m['replaces_asset_id']:m for m in matches}; unmatched_ids={u['asset_id'] for u in unmatched}; changed=0; retired=0; ts=now()
            revision_fields=['original_filename','canonical_filename','source_drive_id','asset_drive_id','original_checksum','clean_checksum','perceptual_fingerprint','status','metadata_clean','notes','webViewLink','first_seen_at','last_reconciled_at']
            for row in inv:
                aid=row.get('asset_id')
                if aid in match_by_asset:
                    m=match_by_asset[aid]; old={k:row.get(k) for k in revision_fields}; old.update({'retired_at':ts,'retirement_reason':'WRONG_LANGUAGE_LABEL','old_source_trashed':True,'old_asset_trashed':True})
                    hist=list(row.get('revision_history') or []); hist.append(old); row['revision_history']=hist
                    dest_state=state['uploads'][m['incoming_drive_id']]; source_state=state['moved'][m['incoming_drive_id']]
                    row.update({'original_filename':m['incoming_filename'],'canonical_filename':m['canonical_filename'],'source_drive_id':m['incoming_drive_id'],'asset_drive_id':dest_state['destination_drive_id'],'original_checksum':m['incoming_raw_sha256'],'clean_checksum':m['clean_sha256'],'perceptual_fingerprint':fingerprint(int(m['incoming_index'])),'status':'01_READY','reservation_status':'RESERVADO_PELO_GESTOR','ares_eligible':False,'metadata_clean':True,'first_seen_at':source_state.get('createdTime') or row.get('first_seen_at'),'last_reconciled_at':ts,'performance_label':'UNKNOWN','notes':'Revisão corrigida por Kelly. Faixa visual validada em inglês: AVAILABLE LIMIT $14,760. Versão anterior com texto em espanhol enviada à lixeira após confirmação crítica. Original corrigido preservado em 99_LEGACY. Fail-closed até liberação/conciliação Meta × Drive.','webViewLink':dest_state.get('webViewLink'),'thread_id':THREAD_ID,'lineage_revision':len(hist)+1,'correction_reason':'WRONG_LANGUAGE_LABEL','previous_revision_trashed':True})
                    changed+=1
                elif aid in unmatched_ids:
                    row.update({'status':'DELETED_BY_MANAGER_REQUEST','ares_eligible':False,'deleted_at':ts,'drive_trashed':True,'deletion_reason':'WRONG_LANGUAGE_LABEL_NO_CORRECTED_REPLACEMENT','last_reconciled_at':ts,'notes':(row.get('notes') or '')+' Versão com texto incorreto enviada à lixeira por solicitação e confirmação de Kelly; sem substituição corrigida neste lote.'})
                    retired+=1
            if changed!=10 or retired!=10: raise RuntimeError(f'inventory reconciliation count mismatch changed={changed} retired={retired}')
            lock_inv=INVENTORY.with_suffix(INVENTORY.suffix+'.lock')
            with lock_inv.open('a+') as lk:
                fcntl.flock(lk,fcntl.LOCK_EX); tmp=INVENTORY.with_suffix(INVENTORY.suffix+'.tmp'); tmp.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in inv),encoding='utf-8'); os.replace(tmp,INVENTORY)
            state.update({'inventory_updated':True,'inventory_backup':str(backup),'inventory_updated_at':ts}); jdump(STATE,state)
        # Final reconciliation.
        upload_left=descendants(drive,upload)
        if upload_left: raise RuntimeError(f'UPLOAD MANUAL contains {len(upload_left)} file(s)')
        ready_live={x['id']:x for x in list_children(drive,ready)}; legacy_live={x['id']:x for x in list_children(drive,legacy)}
        for m in matches:
            if state['uploads'][m['incoming_drive_id']]['destination_drive_id'] not in ready_live or m['incoming_drive_id'] not in legacy_live: raise RuntimeError(f'final corrected Drive reconciliation failed {m["incoming_filename"]}')
        for file_id in old_drive_ids:
            if not api_get(drive,file_id).get('trashed'): raise RuntimeError('old erroneous file not trashed')
        final_inv=load_inventory(); final_by_asset={x.get('asset_id'):x for x in final_inv}
        for m in matches:
            x=final_by_asset[m['replaces_asset_id']]
            if x.get('source_drive_id')!=m['incoming_drive_id'] or x.get('asset_drive_id')!=state['uploads'][m['incoming_drive_id']]['destination_drive_id'] or x.get('status')!='01_READY' or x.get('metadata_clean') is not True or x.get('ares_eligible') is not False: raise RuntimeError(f'final matched inventory mismatch {m["canonical_filename"]}')
        for u in unmatched:
            x=final_by_asset[u['asset_id']]
            if x.get('status')!='DELETED_BY_MANAGER_REQUEST' or x.get('drive_trashed') is not True or x.get('ares_eligible') is not False: raise RuntimeError(f'final unmatched inventory mismatch {u["canonical_filename"]}')
        stamp=dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ'); csv_path=BASE/f'correction-execution-{stamp}.csv'; json_path=BASE/f'correction-execution-{stamp}.json'
        rows=[]
        for m in matches:
            st=state['uploads'][m['incoming_drive_id']]; rows.append({'incoming_filename':m['incoming_filename'],'canonical_filename':m['canonical_filename'],'incoming_drive_id':m['incoming_drive_id'],'destination_drive_id':st['destination_drive_id'],'replaced_source_drive_id':m['replaces_source_drive_id'],'replaced_asset_drive_id':m['replaces_asset_drive_id'],'clean_sha256':m['clean_sha256'],'metadata_clean':True,'reservation_status':'RESERVADO_PELO_GESTOR','ares_eligible':False})
        with csv_path.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        report={'generated_at_utc':now(),'operation':OP,'requested_by':'Kelly Nice','thread_id':THREAD_ID,'confirmation':CONFIRMATION,'corrected_ready':10,'corrected_raw_legacy':10,'erroneous_ready_trashed':20,'erroneous_legacy_trashed':20,'old_lineages_revised':10,'old_lineages_retired_without_replacement':10,'upload_manual_remaining_files':0,'metadata_clean_verified':10,'reservation_status':'RESERVADO_PELO_GESTOR','ares_eligible':False,'inventory_backup':state.get('inventory_backup'),'report_csv':str(csv_path),'items':[{'source_filename':r['incoming_filename'],'destination_filename':r['canonical_filename']} for r in rows],'retired_without_replacement':[u['canonical_filename'] for u in unmatched]}
        jdump(json_path,report); jdump(BASE/'correction-execution-latest.json',report)
        print(json.dumps({'done':True,'corrected_ready':10,'corrected_raw_legacy':10,'erroneous_files_trashed':40,'retired_without_replacement':10,'upload_manual_remaining_files':0,'report':str(json_path)},ensure_ascii=False,indent=2))
if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'done':False,'error':str(exc)},ensure_ascii=False,indent=2)); raise
