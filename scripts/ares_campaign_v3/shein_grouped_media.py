"""SHEIN explicit campaign groups and manager-folder media preparation.

Separate maintenance/pre-stage layer; campaign writes remain solely Engine v3.
No Google identity fallback, Drive move, public URL or credential persistence.
"""
from __future__ import annotations
import concurrent.futures
import copy
import fcntl
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def validate_groups(request):
    groups=request.get('campaign_groups')
    valid_mode = request.get('mode') == 'clone_prestaged' or (request.get('mode') == 'from_zero_prestaged' and bool(request.get('source_account')))
    if not valid_mode or not isinstance(groups,list) or len(groups)!=int(request.get('quantity',1)) or not groups:
        raise ValueError('explicit groups require clone_prestaged and exact quantity')
    files=[]
    for g in groups:
        required = {'files','product_label','primary_text'}
        if not isinstance(g,dict) or not required <= set(g) or set(g) - (required | {'headline'}):
            raise ValueError('group requires files, product_label, primary_text and permits optional headline only')
        if 'headline' in g and (not isinstance(g['headline'],str) or not g['headline'].strip()):
            raise ValueError('optional group headline must be a nonempty literal string')
        if not isinstance(g['files'],list) or not 1<=len(g['files'])<=5:
            raise ValueError('group requires one through five media files')
        if not all(isinstance(g[k],str) and g[k].strip() for k in ['product_label','primary_text']):
            raise ValueError('literal product and Primary text required for each group')
        for f in g['files']:
            if not isinstance(f,str) or not re.fullmatch(r'SHEIN_US_(EN|ES)_VID_[A-Z0-9_]+_(PV|NV|PH|NH)_[0-9]{3}\.mp4',f):
                raise ValueError('exact canonical SHEIN video filename required')
        files.extend(g['files'])
    if len(files)!=len(set(files)):
        raise ValueError('one asset lineage cannot be duplicated across campaign groups')
    return files


def manager_folder(request, profile, base, ops, drive_token):
    policy=json.loads((base/'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json').read_text()).get('grouped_manager_media_policy') or {}
    if policy.get('enabled') is not True or policy.get('approved_by')!='344196393512075265':
        raise ValueError('approved grouped manager media policy unavailable')
    fid=request.get('manager_media_folder_id')
    folder=ops.drive_file_readback(drive_token,fid)
    names={str(x.get('manager_name')).casefold() for x in json.loads((base/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-accounts.json').read_text())['accounts'] if x.get('manager_code')==profile['manager_code']}
    if request.get('source_account'):
        names |= {name + ' - usados' for name in names}
    if folder.get('trashed') or folder.get('driveId')!='0AEwt4Ye690ocUk9PVA' or folder.get('name','').casefold() not in names or len(folder.get('parents') or [])!=1:
        raise ValueError('manager folder identity, partition or Shared Drive mismatch')
    parent=ops.drive_file_readback(drive_token,folder['parents'][0])
    if request.get('source_account') and folder['name'].casefold().endswith(' - usados'):
        drive = json.loads((base/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-v3.json').read_text()).get('drive') or {}
        vid = (drive.get('folders') or {}).get('VID') or {}
        if (parent.get('id') != vid.get('folder_id') or parent.get('name') != 'VID'
                or parent.get('parents') != [drive.get('pool_id')] or parent.get('trashed')
                or parent.get('driveId') != '0AEwt4Ye690ocUk9PVA'):
            raise ValueError('manager USED folder must belong to canonical operation VID')
        pool = ops.drive_file_readback(drive_token, drive['pool_id'])
        if (pool.get('name') != 'SHEIN_US_' + profile['language'] or pool.get('trashed')
                or pool.get('driveId') != '0AEwt4Ye690ocUk9PVA' or len(pool.get('parents') or []) != 1):
            raise ValueError('manager USED pool language/Shared Drive mismatch')
        parent = ops.drive_file_readback(drive_token, pool['parents'][0])
    if parent.get('name')!='CRIATIVOS' or parent.get('driveId')!='0AEwt4Ye690ocUk9PVA' or parent.get('trashed'):
        raise ValueError('manager folder must be direct child of canonical CRIATIVOS')
    return folder


def prepare(request, *, base=Path('/root/mgs-agent'), work_dir=None):
    from .shein_single_clone import lookup_account
    account = lookup_account(request['account'])
    locks = base/'data/ares/meta-ads/state/shein-campaigns/single-clone'
    locks.mkdir(parents=True, exist_ok=True)
    with (locks/('account-'+account['account_id']+'.lock')).open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('account has another in-flight request; no media writes') from None
        return _prepare_locked(request, base=base, work_dir=work_dir)


def _prepare_locked(request, *, base=Path('/root/mgs-agent'), work_dir=None):
    """Explicit selected media -> download/verify/reserve -> existing pre-stage.

    Reads live authority/account/folder, preserves history and requested reuse,
    never declares historical/unknown-use assets new. Repeated invocation keeps
    the same reservation and uses the canonical registry/title reconciliation.
    """
    from . import shein_single_clone as driver
    from .shein_general import authorize
    from .shein_media_handoff import _ops
    from .prestage import AdAccountVideoUploader, PrestageService, OnDemandMediaPipeline
    from .media_registry import MediaRegistry
    files=validate_groups(request);driver.validate_request(request)
    account=driver.lookup_account(request['account'])
    cfg=json.loads((base/'data/ares/meta-ads/engine-v3/config.json').read_text())
    profile=copy.deepcopy(cfg['accounts'][account['account_id']]['shein_profile'])
    op=json.loads((base/'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json').read_text())
    profile['channel_authorization_policy']=op['channel_authorization_policy'];authorize(request,profile,force=True)
    reference = {}
    if request.get('source_account'):
        from .shein_reference import configure
        profiles = json.loads((base/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json').read_text())['profiles']
        profile, reference = configure(request, profile, profiles, op, driver.lookup_account)
        profile['reference_profile'] = reference
    scope=subprocess.run(['python3',str(base/'scripts/mgs-domain-scope.py'),'check','--agent','ares',profile['destination_base']],capture_output=True,timeout=20)
    if scope.returncode!=0:raise ValueError('operational domain scope rejected')
    if request.get('source_account'):
        scope=subprocess.run(['python3',str(base/'scripts/mgs-domain-scope.py'),'check','--agent','ares',reference['destination_base']],capture_output=True,timeout=20)
        if scope.returncode!=0:raise ValueError('operational domain scope rejected')
    common=driver._load_common();token,_=common.get_token_from_1password(cfg['accounts'][account['account_id']]['token_item'])
    if request.get('source_account'):
        marker = driver.CURRENT_PROFILE.set(profile)
        try:
            driver._prepare(request, cfg, driver.ReadOnlyClient(common), token, reference_only=True)
        finally:
            driver.CURRENT_PROFILE.reset(marker)
    h,live,_=common.graph_get('act_'+account['account_id'],token,{'fields':'id,name,currency,timezone_name,account_status,disable_reason,user_tasks'})
    if h!=200 or live.get('name')!=profile['account_name'] or live.get('currency')!='USD' or live.get('timezone_name')!=profile['timezone'] or live.get('account_status')!=1 or live.get('disable_reason')!=0 or 'ADVERTISE' not in live.get('user_tasks',[]):
        raise ValueError('exact account live identity/access/health mismatch')
    ops=_ops(base);dt,_=ops.drive_runtime_token();folder=manager_folder(request,profile,base,ops,dt)
    inv=base/'data/ares/creative-ops/inventory/assets.jsonl'
    rows=[json.loads(l) for l in inv.read_text().splitlines() if l.strip()]
    selected=[]
    for filename in files:
        matches=[r for r in rows if r.get('canonical_filename')==filename]
        if len(matches)!=1:raise ValueError('canonical filename missing or ambiguous')
        row=matches[0]
        if row.get('language')!=profile['language'] or row.get('vertical')!='SHEIN' or row.get('metadata_clean') is not True:
            raise ValueError('selected media language/sanitization mismatch')
        if row.get('reservation_request_id') not in {None,request['request_id']}:
            raise ValueError('selected lineage reserved by another request')
        selected.append(row)
    if len({r['asset_id'] for r in selected})!=len(selected):raise ValueError('duplicate selected lineage')
    if work_dir is None:work_dir=Path(os.environ.get('TMPDIR','/root/.hermes/profiles/ares/cache/scratch'))/request['request_id']/'media'
    work_dir=Path(work_dir);work_dir.mkdir(parents=True,exist_ok=True)
    proof_dir=base/'data/ares/meta-ads/audit/shein/campaigns/intake'/request['request_id'];proof_dir.mkdir(parents=True,exist_ok=True)
    def download(row):
        f=ops.drive_file_readback(dt,row['asset_drive_id'])
        if f.get('driveId')!='0AEwt4Ye690ocUk9PVA' or f.get('trashed') or f.get('name')!=row['canonical_filename'] or f.get('parents')!=[folder['id']]:raise ValueError('selected file live identity/folder mismatch')
        path=work_dir/row['canonical_filename']
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=row['clean_checksum']:
            with urlopen(Request('https://www.googleapis.com/drive/v3/files/'+row['asset_drive_id']+'?alt=media&supportsAllDrives=true',headers={'Authorization':'Bearer '+dt}),timeout=180) as response:
                with path.open('wb') as handle:
                    while chunk:=response.read(1024*1024):handle.write(chunk)
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=row['clean_checksum'] or hashlib.md5(raw).hexdigest()!=f.get('md5Checksum') or len(raw)!=int(f.get('size') or 0):raise ValueError('selected file checksum/size mismatch')
        check=subprocess.run(['python3',str(base/'scripts/clean-creative-metadata.py'),'verify',str(path)],capture_output=True,text=True,timeout=60)
        if check.returncode!=0:raise ValueError('selected file failed metadata-clean verification')
        if not re.search(r'^clean:\s*true\s*$', check.stdout, re.MULTILINE):
            raise ValueError('selected file metadata not clean')
        return {'asset_id':row['asset_id'],'checksum':row['clean_checksum'],'vertical_file':str(path),'canonical_filename':row['canonical_filename'],'drive_id':f['id'],'drive_md5':f['md5Checksum'],'drive_parent_id':folder['id'],'metadata_clean':True}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:assets=list(pool.map(download,selected))
    # Reconcile scoped Meta usage by exact known media IDs and deterministic
    # lineage titles; requested reuse is explicit, never a claim of novelty.
    params={'fields':'id,title','limit':500};videos=[];seen=set()
    while True:
        h,page,_=common.graph_get('act_'+account['account_id']+'/advideos',token,params)
        if h!=200:raise ValueError('account media reconciliation unavailable')
        videos.extend(page.get('data') or [])
        if not page.get('paging',{}).get('next'):break
        cursor=page.get('paging',{}).get('cursors',{}).get('after')
        if not cursor or cursor in seen:raise ValueError('account media reconciliation pagination invalid')
        seen.add(cursor);params['after']=cursor
    observed={a['asset_id']:[v['id'] for v in videos if a['asset_id'] in str(v.get('title')) and a['checksum'][:10] in str(v.get('title'))] for a in assets}
    with inv.with_suffix(inv.suffix+'.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        current=[json.loads(l) for l in inv.read_text().splitlines() if l.strip()];ids={r['asset_id'] for r in selected};stamp=datetime.now(timezone.utc).isoformat()
        for row in current:
            if row['asset_id'] not in ids:continue
            if row.get('reservation_request_id') not in {None,request['request_id']}:raise ValueError('reservation changed during pre-stage')
        backup=proof_dir/'inventory-before.jsonl'
        if not backup.exists():backup.write_bytes(inv.read_bytes());os.chmod(backup,0o600)
        for row in current:
            if row['asset_id'] not in ids:continue
            history=row.setdefault('reservation_history',[])
            if not any(x.get('request_id')==request['request_id'] for x in history):history.append({'request_id':request['request_id'],'previous_status':row.get('status'),'previous_used_by':row.get('used_by'),'previous_reservation_status':row.get('reservation_status'),'at':stamp,'authority':request['authorized_by']})
            row.update(reservation_request_id=request['request_id'],reservation_status='RESERVADO_PELO_REQUEST',ares_eligible=False,manager_media_folder_id=folder['id'],explicit_asset_request=True,reservation_authority=request['authorized_by'],last_reconciled_at=stamp)
            row['request_media_reconciliation']={'account_id':account['account_id'],'known_video_ids':observed[row['asset_id']],'requested_reuse':True,'no_novelty_claim':True,'drive_live':True}
        ops.atomic_inventory(current)
    driver.atomic_json(proof_dir/'media-preparation.json',{'request_id':request['request_id'],'account_id':account['account_id'],'folder_id':folder['id'],'assets':assets,'reconciliation':observed,'drive_moves':0,'novelty_claim':False})
    if cfg.get('media_upload_enabled') is not True:raise ValueError('media upload gate disabled')
    uploader=AdAccountVideoUploader(common=common,user_token=token,account_id=account['account_id'],graph_version=cfg.get('graph_version','v26.0'))
    result=OnDemandMediaPipeline(PrestageService(MediaRegistry(base/'data/ares/meta-ads/engine-v3/media-registry.json'),uploader),max_workers=5).run(account_id=account['account_id'],assets=assets,prepare_asset=lambda a:{'vertical_path':a['vertical_file'],'square_path':None},required_variants=('vertical',))
    out=copy.deepcopy(request);out['asset_refs']=[{'asset_id':a['asset_id'],'checksum':a['checksum']} for a in assets]
    driver.atomic_json(proof_dir/'request-ready.json',out)
    driver.atomic_json(proof_dir/'prestage-summary.json',{'request_id':request['request_id'],'assets':len(result['assets']),'ready':all(a['registry']['ready'] for a in result['assets']),'registry_hits':result['registry_hits']})
    return out
