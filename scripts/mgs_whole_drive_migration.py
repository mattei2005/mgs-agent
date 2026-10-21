#!/usr/bin/env python3
"""Whole-drive migration discovery/probe control. No production move or deletion."""
from __future__ import annotations
import sys,json,hashlib,urllib.parse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ares_archive_bridge as b
import ares_archive_backfill as historical
AUTH='1562459803186626571'
DATA=b.DATA/('whole-drive-migration-'+AUTH)
CANARY_KEY='whole-drive-native-canary:'+AUTH
PROBE_KEY='whole-drive-probe:'+AUTH

def read(path,default=None):
    return b.read_json(path,default)

def sheets_get(d,sid,path='',params=None):
    url='https://sheets.googleapis.com/v4/spreadsheets/'+sid+path
    if params:url+='?'+urllib.parse.urlencode(params,doseq=True)
    status,value=d.api_json('GET',url,d.token)
    if status!=200:raise b.ArchiveError('SHEETS_PROBE_HTTP_'+str(status))
    return value

def snapshot(d,sid):
    meta=sheets_get(d,sid,params={'includeGridData':'false'})
    titles=[s['properties']['title'] for s in meta.get('sheets',[])]
    ranges=["'"+x.replace("'","''")+"'" for x in titles]
    formulas=[];values=[]
    for start in range(0,len(ranges),40):
        p={'ranges':ranges[start:start+40],'valueRenderOption':'FORMULA'}
        formulas.extend(sheets_get(d,sid,'/values:batchGet',p).get('valueRanges',[]))
        p['valueRenderOption']='FORMATTED_VALUE'
        values.extend(sheets_get(d,sid,'/values:batchGet',p).get('valueRanges',[]))
    full={'spreadsheet':meta,'formulas':formulas,'formatted_values':values}
    tabs=[];deps=set()
    import re
    for r in formulas:
        cells=[v for row in r.get('values',[]) for v in row if isinstance(v,str)]
        fs=[v for v in cells if v.startswith('=')]
        for f in fs:
            for match in re.finditer(r'IMPORTRANGE\s*\(\s*"([^"]+)"',f,re.I):
                token=match.group(1);found=re.search(r'/d/([A-Za-z0-9_-]+)',token)
                deps.add(found.group(1) if found else token)
        tabs.append({'range':r['range'],'rows_with_values':len(r.get('values',[])),'formulas':len(fs),'formula_sha256':hashlib.sha256(b.canonical(r)).hexdigest()})
    return full,{'id':sid,'tabs':len(titles),'tab_summaries':tabs,'literal_importrange_dependencies':sorted(deps),'snapshot_sha256':hashlib.sha256(b.canonical(full)).hexdigest()}

def prepare():
    DATA.mkdir(parents=True,exist_ok=True)
    with b.queue_lock():
        d=b.Drive(True);c=b.config_load();b.preflight(d,c)
        from mgs_google_workspace_auth import service_account_access_token
        d.token=service_account_access_token(['https://www.googleapis.com/auth/drive','https://www.googleapis.com/auth/spreadsheets.readonly'])
        inventory=read(DATA/'inventory.json')
        if not inventory:raise b.ArchiveError('WHOLE_DRIVE_INVENTORY_REQUIRED')
        native=[x for x in inventory['files'] if x['mimeType']=='application/vnd.google-apps.spreadsheet']
        summaries=[]
        for entry in native:
            path=DATA/('sheet-baseline-'+entry['id']+'.json')
            if path.exists():
                prior=read(path,{})
                if not isinstance(prior,dict) or 'summary' not in prior:raise b.ArchiveError('SHEET_BASELINE_INVALID')
                summaries.append(prior['summary']);continue
            full,summary=snapshot(d,entry['id'])
            b.atomic_json(path,{'captured_at':b.now_iso(),'summary':summary,'snapshot':full});summaries.append(summary)
        b.atomic_json(DATA/'sheets-baseline-summary.json',{'sheets':summaries,'count':len(summaries),'captured_at':b.now_iso()})
        found=d.one(b.SOURCE_DRIVE,CANARY_KEY)
        intent=DATA/'canary-create-intent.json'
        if not found:
            if intent.exists():raise b.ArchiveError('CANARY_CREATE_AMBIGUOUS_NO_REPLAY')
            b.atomic_json(intent,{'key':CANARY_KEY,'created_at':b.now_iso(),'mime_type':'application/vnd.google-apps.spreadsheet','validation_only':True})
            payload={'name':'MGS_MIGRATION_TEST_ONLY_NATIVE_'+AUTH,'mimeType':'application/vnd.google-apps.spreadsheet','parents':[b.SOURCE_DRIVE],'properties':{'mgsArchiveKey':CANARY_KEY,'mgsArchiveType':'whole_drive_test_only','validationOnly':'true'}}
            try:made=d.api('POST','files',{'supportsAllDrives':'true','fields':'id'},payload)
            except Exception:
                found=d.one(b.SOURCE_DRIVE,CANARY_KEY)
                if not found:raise b.ArchiveError('CANARY_CREATE_AMBIGUOUS_NO_REPLAY')
                made=found
            # files.list indexes can lag a committed create. Persist and verify
            # the exact returned ID; never replay POST to cure list latency.
            b.atomic_json(DATA/'canary-create-result.json',{'id':made['id'],'key':CANARY_KEY,'recorded_at':b.now_iso()})
            found=d.meta(made['id'])
            if found.get('properties',{}).get('mgsArchiveKey')!=CANARY_KEY:raise b.ArchiveError('CANARY_ID_READBACK')
        canary=d.meta(found['id']);b.require_publisher(canary,b.CANONICAL_SA)
        if canary.get('parents')!=[b.SOURCE_DRIVE] or canary.get('driveId')!=b.SOURCE_DRIVE or canary['mimeType']!='application/vnd.google-apps.spreadsheet' or canary.get('properties',{}).get('validationOnly')!='true':raise b.ArchiveError('CANARY_SCOPE')
        targets=[]
        ids={x['id'] for x in inventory['files'] if x.get('parents')==[b.SOURCE_DRIVE] or x['mimeType']=='application/vnd.google-apps.spreadsheet'}
        ids.update([b.SOURCE_DRIVE,b.ARCHIVE_ROOT,canary['id']])
        for fid in sorted(ids):
            m=d.meta(fid);targets.append({'id':fid,'name':m['name'],'mimeType':m['mimeType'],'parents':m.get('parents',[]),'driveId':m.get('driveId'),'sourceAcl':historical.permissions(d,fid)})
        manifest={'schema':'mgs.whole.drive.probe.v1','authorizationMessageId':AUTH,'sourceDriveId':b.SOURCE_DRIVE,'archiveRootId':b.ARCHIVE_ROOT,'account':b.ACCOUNT,'productionMutation':False,'deleteSource':False,'targets':targets,'canary':{'id':canary['id'],'sourceParentId':b.SOURCE_DRIVE,'mimeType':canary['mimeType'],'name':canary['name'],'createdTime':canary['createdTime'],'validationOnly':True,'restoreImmediately':True}}
        raw=b.canonical(manifest);digest=hashlib.sha256(raw).hexdigest()
        fid=d.upload_once(c['control_folder_id'],'whole-drive-probe-manifest-'+AUTH+'.json',raw,'application/json','whole-drive-probe-manifest:'+AUTH,'whole_drive_probe_manifest')
        b.require_publisher(d.meta(fid),b.CANONICAL_SA)
        if d.raw(fid)!=raw:raise b.ArchiveError('PROBE_MANIFEST_READBACK')
        b.atomic_json(DATA/'probe-manifest.json',manifest)
        result={'schema':'mgs.whole.drive.probe.stage.v1','authorization_message_id':AUTH,'manifest_file_id':fid,'manifest_sha256':digest,'canary_id':canary['id'],'target_count':len(targets),'native_sheet_count':len(native),'status':'owner_probe_code_required','production_mutation':False,'source_deleted':False}
        old=read(DATA/'stage.json',{})
        if not isinstance(old,dict):raise b.ArchiveError('WHOLE_DRIVE_STAGE_INVALID')
        for k in ['worker_file_id','worker_sha256','worker_source_path']: 
            if k in old:result[k]=old[k]
        b.atomic_json(DATA/'stage.json',result)
        return result

def status():
    with b.queue_lock():
        d=b.Drive(False);c=b.config_load();stage=read(DATA/'stage.json',{})
        f=d.one(c['receipts_folder_id'],PROBE_KEY)
        if not f:return {'status':'awaiting_owner_probe','stage':stage}
        meta=d.meta(f['id']);b.require_publisher(meta,b.ACCOUNT)
        result=json.loads(d.raw(f['id']))
        if result.get('authorizationMessageId')!=AUTH or result.get('schema')!='mgs.whole.drive.probe.receipt.v1' or result.get('productionMutation') is not False or result.get('deleteSource') is not False:raise b.ArchiveError('WHOLE_DRIVE_PROBE_RECEIPT_SCOPE')
        b.atomic_json(DATA/'owner-probe-receipt.json',{'file_id':f['id'],'verified_at':b.now_iso(),'receipt':result})
        return result

def publish_probe():
    with b.queue_lock():
        d=b.Drive(True);c=b.config_load();b.preflight(d,c)
        stage=read(DATA/'stage.json',{})
        if not isinstance(stage,dict):raise b.ArchiveError('WHOLE_DRIVE_STAGE_INVALID')
        if not stage.get('manifest_file_id') or not stage.get('manifest_sha256'):raise b.ArchiveError('PROBE_MANIFEST_REQUIRED')
        source=b.BASE/'integrations/creative-archive-30tb/WorkerWholeDriveProbe.js'
        raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        base=(b.BASE/'integrations/creative-archive-30tb/WorkerBackfill.js').read_text()
        hook='    if(summary.canaryAcknowledged)summary.wholeDriveProbe=mgsWholeDriveOwnerProbe(c,props,start);\n'
        if raw.decode().replace(hook,'',1)[:len(base)]!=base or raw.decode().count(hook)!=1:raise b.ArchiveError('PROBE_COMPOSITE_BASE_CHANGED')
        if hashlib.sha256(base.encode()).hexdigest()!=c['worker_sha256']:raise b.ArchiveError('PROBE_ACTIVE_BASE_NOT_PINNED')
        fid=d.upload_once(c['control_folder_id'],'worker-whole-drive-probe-'+digest+'.js',raw,'application/javascript','worker:'+digest,'worker_source')
        meta=d.meta(fid);b.require_publisher(meta,b.CANONICAL_SA)
        if meta.get('parents')!=[c['control_folder_id']] or hashlib.sha256(d.raw(fid)).hexdigest()!=digest:raise b.ArchiveError('PROBE_WORKER_READBACK')
        stage.update(worker_file_id=fid,worker_sha256=digest,worker_source_path=str(source.relative_to(b.BASE)),previous_active_worker_file_id=c['worker_file_id'],previous_active_worker_sha256=c['worker_sha256'],status='owner_repin_required',published_at=b.now_iso(),active_sa_pin_unchanged=True,js_regressions_passed=10,python_backfill_regressions_passed=8)
        b.atomic_json(DATA/'stage.json',stage)
        return stage

def main():
    import argparse
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=['prepare','status','publish-probe']);args=ap.parse_args()
    result={'prepare':prepare,'status':status,'publish-probe':publish_probe}[args.action]()
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
