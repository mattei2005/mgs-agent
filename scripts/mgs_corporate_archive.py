#!/usr/bin/env python3
"""Corporate owner setup publisher/independent verifier. No production enqueue,
ACL mutation, source deletion or implicit bulk activation in this controller.
The immutable owner worker supports later bounded moves behind SA activation;
consumer/backup/retention gates must be implemented/verified before that phase.
"""
from __future__ import annotations
import argparse,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ares_archive_bridge as b
import ares_archive_backfill as h
import mgs_whole_drive_migration as m
APPROVAL='1562565746557456515'
STAGE=m.DATA/'corporate-stage.json'
PLAN=m.DATA/'corporate-plan.json'
RECOVERY_SHA='02d870020bf678c9da3485bac873c2bfbf17e99f1439877d24b3891a2f9fe4cb'

def load_plan():
    p=b.read_json(PLAN,{})
    s=b.read_json(STAGE,{})
    proposal=b.read_json(m.DATA/'corporate-acl-proposal-1562563383415406614.json',{})
    if not isinstance(p,dict) or not isinstance(s,dict) or not isinstance(proposal,dict):raise b.ArchiveError('CORPORATE_LOCAL_STATE')
    if p.get('schema')!='mgs.corporate.archive.plan.v1' or p.get('sharingConfirmationMessageId')!=APPROVAL or p.get('authorizationMessageId')!=m.AUTH or p.get('account')!=b.ACCOUNT or p.get('sourceDriveId')!=b.SOURCE_DRIVE or p.get('archiveCreativeRootId')!=b.ARCHIVE_ROOT or p.get('ownerRootId')!='0AET_Qs3G4VFwUk9PVA' or p.get('rootName')!='MGS-CORPORATIVO' or p.get('deleteSource') is not False or p.get('productionMovesEnabledByDefault') is not False or hashlib.sha256(b.canonical(p)).hexdigest()!=s.get('plan_sha256') or proposal.get('confirmation_message_id')!=APPROVAL or proposal.get('confirmed_by_user_id')!='344196393512075265' or proposal.get('status') not in ['authorized_not_yet_applied','applied_verified']:raise b.ArchiveError('CORPORATE_PLAN_AUTHORITY')
    expected={'03783617840924670288':(b.ACCOUNT,'owner'),'05050970695410771211':('mattei2005@gmail.com','writer'),'07414359829876449782':(b.CANONICAL_SA,'writer'),'11042037043902793495':('support@matteiservicesinc.com','writer')}
    actual={x.get('permission_id'):(x.get('email'),x.get('destination_role')) for x in p.get('principals',[])}
    if actual!=expected or len(p.get('principals',[]))!=4 or any(x.get('type')!='user' or x.get('source_role')!='organizer' for x in p['principals']):raise b.ArchiveError('CORPORATE_PRINCIPALS')
    return p,s

def acl_normal(acl):
    return sorted((str(x.get('id')),x.get('type'),x.get('role')) for x in acl)

def desired(p,source=False):
    return [{'id':x['permission_id'],'type':'user','role':x['source_role'] if source else x['destination_role'],'emailAddress':x['email']} for x in p['principals']]

def check_acl(acl,wanted):
    if acl_normal(acl)!=acl_normal(wanted):raise b.ArchiveError('CORPORATE_ACL_CLOSURE')
    names={x['id']:x['emailAddress'] for x in wanted}
    if any(x.get('emailAddress') is not None and x['emailAddress']!=names.get(x.get('id')) for x in acl):raise b.ArchiveError('CORPORATE_ACL_EMAIL_CONFLICT')

def validate_receipt(p,s,r):
    if r.get('schema')!='mgs.corporate.setup.receipt.v1' or r.get('status')!='completed' or r.get('sharingConfirmationMessageId')!=APPROVAL or r.get('authorizationMessageId')!=m.AUTH or r.get('planSha256')!=s['plan_sha256'] or r.get('deleteSource') is not False or r.get('productionMutation') is not False or r.get('productionContentMoved') is not False or r.get('infrastructureMutation') is not True:raise b.ArchiveError('CORPORATE_SETUP_RECEIPT_BINDING')
    root=r.get('root',{});rid=root.get('id')
    if not isinstance(rid,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,}',rid) or rid in [b.ARCHIVE_ROOT,b.SOURCE_DRIVE,p['ownerRootId']] or root.get('name')!=p['rootName'] or root.get('mimeType')!=b.FOLDER or root.get('parents')!=[p['ownerRootId']] or root.get('driveId') or root.get('trashed') is not False or not any(x.get('emailAddress')==p['account'] and x.get('permissionId')==p['ownerPermissionId'] for x in root.get('owners',[])):raise b.ArchiveError('CORPORATE_ROOT_BINDING')
    check_acl(r.get('rootPermissions',[]),desired(p))
    canary=r.get('canary',{});a=p['canary']
    if canary.get('sourceId')!=a['id'] or canary.get('restored') is not True:raise b.ArchiveError('CORPORATE_CANARY_NOT_RESTORED')
    for field,in_source in [('sourceBefore',True),('destinationAfter',False),('sourceAfter',True)]:
        side=canary.get(field) or {};meta=side.get('metadata',{})
        if meta.get('id')!=a['id'] or meta.get('name')!=a['name'] or meta.get('createdTime')!=a['createdTime'] or meta.get('mimeType')!=a['mimeType'] or meta.get('trashed') is not False or meta.get('properties',{}).get('validationOnly')!='true':raise b.ArchiveError('CORPORATE_CANARY_IDENTITY')
        if in_source:
            if meta.get('parents')!=[b.SOURCE_DRIVE] or meta.get('driveId')!=b.SOURCE_DRIVE:raise b.ArchiveError('CORPORATE_CANARY_SOURCE_PARENT')
        elif meta.get('parents')!=[rid] or meta.get('driveId') or not any(x.get('permissionId')==p['ownerPermissionId'] and x.get('emailAddress')==p['account'] for x in meta.get('owners',[])):raise b.ArchiveError('CORPORATE_CANARY_DESTINATION')
        check_acl(side.get('permissions',[]),desired(p,source=in_source))
    return rid

def verify_setup(d,c,apply=False):
    p,s=load_plan();key='corporate-setup:'+APPROVAL;f=d.one(c['receipts_folder_id'],key)
    if not f:return {'status':'awaiting_owner_corporate_setup','grants_applied':False,'production_moves_enabled':False}
    meta=d.meta(f['id']);b.require_publisher(meta,b.ACCOUNT)
    if meta.get('parents')!=[c['receipts_folder_id']] or meta.get('driveId')!=b.SOURCE_DRIVE or meta.get('properties',{}).get('mgsArchiveKey')!=key or meta.get('properties',{}).get('mgsArchiveType')!='corporate_setup_receipt':raise b.ArchiveError('CORPORATE_SETUP_REMOTE_SCOPE')
    receipt=json.loads(d.raw(f['id']));rid=validate_receipt(p,s,receipt);root=d.meta(rid)
    if root.get('id')!=rid or root.get('mimeType')!=b.FOLDER or root.get('name')!=p['rootName'] or root.get('driveId') or root.get('trashed') is not False or (root.get('parents') and root['parents']!=[p['ownerRootId']]) or root.get('properties',{}).get('mgsArchiveKey')!='corporate-root:'+APPROVAL or root.get('properties',{}).get('mgsArchiveType')!='corporate_root' or not any(x.get('emailAddress')==p['account'] for x in root.get('owners',[])):raise b.ArchiveError('CORPORATE_ROOT_LIVE')
    acl=h.permissions(d,rid);check_acl(acl,desired(p))
    canary=d.meta(p['canary']['id'])
    if canary.get('driveId')!=b.SOURCE_DRIVE or canary.get('parents')!=[b.SOURCE_DRIVE] or canary.get('trashed') is not False or canary.get('properties',{}).get('validationOnly')!='true':raise b.ArchiveError('CORPORATE_CANARY_RESTORE_LIVE')
    check_acl(h.permissions(d,canary['id']),desired(p,source=True))
    sheet=m.sheets_get(d,canary['id'],params={'includeGridData':'false','fields':'spreadsheetId'})
    if sheet.get('spreadsheetId')!=canary['id']:raise b.ArchiveError('CORPORATE_CANARY_SHEETS_LIVE')
    proof={'status':'corporate_setup_verified','sharing_confirmation_message_id':APPROVAL,'verified_at':b.now_iso(),'receipt_file_id':f['id'],'plan_sha256':s['plan_sha256'],'root_id':rid,'root_metadata':root,'root_permissions':acl,'canary_restored_live':True,'canary_sheets_http':200,'production_moves_enabled':s.get('production_moves_enabled',False),'source_deleted':False}
    if apply:
        b.atomic_json(m.DATA/'corporate-setup-verification.json',proof);s.update(status=proof['status'],root_id=rid,grants_applied=True,owner_setup_verified=True,setup_receipt_id=f['id']);b.atomic_json(STAGE,s)
        prop_path=m.DATA/'corporate-acl-proposal-1562563383415406614.json';proposal=b.read_json(prop_path,{});proposal.update(status='applied_verified',root_id=rid,verified_at=proof['verified_at'],setup_receipt_file_id=f['id']);b.atomic_json(prop_path,proposal)
    return proof

def build_source(p,s):
    folder=b.BASE/'integrations/creative-archive-30tb';base=(folder/'WorkerWholeDriveRecovery.js').read_bytes()
    if hashlib.sha256(base).hexdigest()!=RECOVERY_SHA:raise b.ArchiveError('CORPORATE_RECOVERY_BASE_DRIFT')
    pin=b'\nvar MGS_CORPORATE_PINS='+b.canonical({'planFileId':s['plan_file_id'],'planSha256':s['plan_sha256']})+b';\n'
    return base+pin+(folder/'CorporateArchiveExtension.js').read_bytes()+b'\n'+(folder/'CorporateMoveExtension.js').read_bytes()

def publish_worker():
    with b.queue_lock():
        p,s=load_plan();d=b.Drive(True);c=b.config_load();b.preflight(d,c);whole=m.read(m.DATA/'stage.json',{})
        if not isinstance(whole,dict) or c['worker_sha256'] not in [whole.get('previous_active_worker_sha256'),whole.get('worker_sha256')]:raise b.ArchiveError('CORPORATE_ACTIVE_PIN_DRIFT')
        plan_meta=d.meta(s['plan_file_id']);b.require_publisher(plan_meta,b.CANONICAL_SA)
        if plan_meta.get('parents')!=[c['control_folder_id']] or d.raw(s['plan_file_id'])!=b.canonical(p):raise b.ArchiveError('CORPORATE_PLAN_REMOTE_READBACK')
        source=b.BASE/'integrations/creative-archive-30tb/WorkerWholeDriveCorporate.js';raw=build_source(p,s)
        if not source.exists() or source.read_bytes()!=raw:raise b.ArchiveError('CORPORATE_COMPOSITE_BUILD_REQUIRED')
        digest=hashlib.sha256(raw).hexdigest();fid=d.upload_once(c['control_folder_id'],'worker-whole-drive-corporate-'+digest+'.js',raw,'application/javascript','worker:'+digest,'worker_source')
        meta=d.meta(fid);b.require_publisher(meta,b.CANONICAL_SA)
        if meta.get('parents')!=[c['control_folder_id']] or hashlib.sha256(d.raw(fid)).hexdigest()!=digest:raise b.ArchiveError('CORPORATE_WORKER_READBACK')
        prior=s.get('worker_file_id') or whole.get('worker_file_id')
        s.update(status='owner_repin_required_corporate_setup',worker_file_id=fid,worker_sha256=digest,worker_source_path=str(source.relative_to(b.BASE)),published_at=b.now_iso(),active_sa_pin_unchanged=True,production_moves_enabled=False,grants_applied=False);b.atomic_json(STAGE,s)
        whole.update(status=s['status'],superseded_recovery_worker_file_id=whole.get('superseded_recovery_worker_file_id') or prior,previous_active_worker_file_id=c['worker_file_id'],previous_active_worker_sha256=c['worker_sha256'],worker_file_id=fid,worker_sha256=digest,worker_source_path=s['worker_source_path'],owner_repin_confirmed=False,owner_probe_new_version_completed=False,corporate_acl_decision_required=False,corporate_acl_confirmed=True,corporate_acl_confirmation_message_id=APPROVAL,manual_mode='probe_and_approved_corporate_setup_no_production_content',updated_at=b.now_iso());b.atomic_json(m.DATA/'stage.json',whole)
        return s

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=['status','accept-setup','publish-worker']);args=ap.parse_args()
    if args.action=='publish-worker':out=publish_worker()
    else:
        with b.queue_lock():out=verify_setup(b.Drive(False),b.config_load(),apply=args.action=='accept-setup')
    print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
