#!/usr/bin/env python3
"""Approved exact manager delivery after native archive/READY verification.

Canonical SA only. Moves the same verified stock shortcut, never provider bytes,
RAW, permissions or structure. All writes share the archive queue/inventory locks.
A durable CAS intent is reconciled before retry. No DELETE/POST media operations.
"""
from __future__ import annotations
import argparse,fcntl,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ares_archive_bridge as b
import ares_archive_locations as loc
import ares_archive_storage as storage
import ares_upload_context_layout as layout
POLICY=b.BASE/'data/ares/creative-ops/manager-delivery-policy.json'
RECEIPTS=b.DATA/'manager-delivery'
INVENTORY=b.BASE/'data/ares/creative-ops/inventory/assets.jsonl'
AUTHORITY='1565546229914411133'
class DeliveryError(b.ArchiveError):pass

def require(value,reason):
    if not value:raise DeliveryError(reason)

def policy():
    p=b.read_json(POLICY,{})
    require(p.get('schema')=='mgs.creative.manager.delivery.policy.v1' and p.get('status')=='active' and p.get('standing_approval') is True and p.get('authority_user_id')=='344196393512075265' and p.get('authority_message_id')==AUTHORITY,'MANAGER_DELIVERY_AUTHORITY')
    return p

def validate_identity(row,entry,request):
    policy()
    require(entry.get('role')=='clean' and entry.get('sourceId')==row.get('asset_drive_id') and entry.get('lineageId')==row.get('asset_id') and entry.get('sha256')==row.get('clean_checksum'),'MANAGER_CLEAN_LINEAGE_REQUIRED')
    require(row.get('metadata_clean') is True and row.get('source_drive_id')!=row.get('asset_drive_id') and row.get('source_manager') in layout.MANAGERS.values(),'MANAGER_CONTEXT')
    require(row.get('reservation_status') in ['RESERVADO_PELO_GESTOR','RESERVED_BY_MANAGER'] and row.get('ares_eligible') is False and not row.get('used_by'),'MANAGER_RESERVATION')
    require(entry.get('relativeParent')==[row.get('operation'),row.get('format'),'01_READY'] and entry.get('verified') is True and entry.get('stockTransferredToArchive') is True,'MANAGER_READY_TRANSFER_REQUIRED')
    require(all(re.fullmatch(r'[0-9]{17,20}',str(request.get(k,''))) for k in ['requester_id','thread_id','message_id']),'MANAGER_REQUEST_IDENTITY')
    registry=b.read_json(b.BASE/'data/authorized-users.json',{})
    require(request['requester_id'] in registry.get('agents',{}).get('ares',{}).get('authorized_user_discord_ids',[]),'MANAGER_REQUESTER_UNAUTHORIZED')
    require(row.get('requested_by_discord_id')==request['requester_id'],'MANAGER_REQUESTER_LINEAGE_MISMATCH')
    return True

def exact_folder(d,manager,target):
    require(manager in layout.MANAGERS.values(),'MANAGER_UNREGISTERED')
    expected=loc.stock_folder_for_path(d,[manager])
    require(expected==target,'MANAGER_DESTINATION_MISMATCH')
    m=storage.meta(d,target)
    native=d.meta(target)
    require(m.get('parents')==[loc.stock_root()] and m.get('name')==manager and m.get('mimeType')==b.FOLDER and loc.stock_metadata_allowed(m) and m.get('capabilities',{}).get('canEdit') and native.get('capabilities',{}).get('canAddChildren'),'MANAGER_DESTINATION_NATIVE_SCOPE')
    return m

def receipt_binding(row,entry,receipt):
    require(receipt.get('schema')=='mgs.manager.delivery.receipt.v1' and receipt.get('authority_message_id')==AUTHORITY,'MANAGER_RECEIPT_AUTHORITY')
    wanted={'asset_id':row['asset_id'],'logical_id':row['asset_drive_id'],'raw_source_id':row['source_drive_id'],'provider_id':entry['archiveId'],'stock_file_id':entry['stockShortcutId'],'sha256':row['clean_checksum'],'job_id':entry['jobId'],'manager':row['source_manager']}
    require(all(receipt.get(k)==v for k,v in wanted.items()),'MANAGER_RECEIPT_BINDING')
    validate_identity(row,entry,receipt['request'])
    return True

def verify_receipt(d,row,entry,receipt,*,allow_intent=False):
    receipt_binding(row,entry,receipt)
    require(receipt.get('status') in (['intent','verified'] if allow_intent else ['verified']),'MANAGER_RECEIPT_NOT_VERIFIED')
    exact_folder(d,row['source_manager'],receipt['destination_parent_id'])
    record=storage.media_record(entry,storage.meta(d,entry['archiveId']),storage.meta(d,entry['stockShortcutId']))
    require(record['parents']==[receipt['destination_parent_id']] and record['name']==row['canonical_filename'] and record['sha256Checksum']==row['clean_checksum'],'MANAGER_FINAL_READBACK')
    require(d.relative_parent(record['provider_metadata']['parents'][0],b.ARCHIVE_ROOT)==entry['relativeParent'],'MANAGER_PROVIDER_PATH_CHANGED')
    require(d.hashes(entry['archiveId'])=={'size':str(entry['size']),'md5':entry['md5'],'sha256':entry['sha256']},'MANAGER_DELIVERY_BYTES')
    return record

def verify_delivered(d,asset,entry):
    """Called by retirement only for non-status clean-stock destinations."""
    require(asset.get('role')=='clean' and asset.get('sourceId')==entry.get('sourceId'),'MANAGER_RAW_NEVER_MOVED')
    rows=[json.loads(x) for x in INVENTORY.read_text().splitlines() if x.strip()]
    found=[r for r in rows if r.get('asset_id')==entry.get('lineageId') and r.get('asset_drive_id')==asset['sourceId']]
    require(len(found)==1,'MANAGER_UNIQUE_INVENTORY')
    row=found[0];receipt=b.read_json(RECEIPTS/('delivery-'+asset['sourceId']+'.json'),{})
    record=verify_receipt(d,row,entry,receipt)
    require(row.get('manager_media_folder_id')==receipt['destination_parent_id'] and row.get('manager_delivery_receipt')==str((RECEIPTS/('delivery-'+asset['sourceId']+'.json')).relative_to(b.BASE)) and row.get('asset_path')=='MGS-AGENTS/CRIATIVOS/'+row['source_manager']+'/'+row['canonical_filename'],'MANAGER_INVENTORY_FINAL_PARENT')
    return record

def verify_plan(d,plan,rows,index):
    target=plan.get('requested_manager_final_parent')
    if not target:return True
    for item in plan['items']:
        selected=[r for r in rows if r.get('source_drive_id')==item['id']]
        require(len(selected)==1,'MANAGER_PLAN_UNIQUE_LINEAGE');row=selected[0]
        require(row.get('source_manager')==plan['manager'] and row.get('manager_media_folder_id')==target,'MANAGER_PLAN_TARGET')
        entry=index['mappings'][row['asset_drive_id']]
        verify_delivered(d,{'role':'clean','sourceId':row['asset_drive_id']},entry)
    return True

def deliver(asset_id,target,request,apply=False):
    policy()
    with b.queue_lock():
        with Path(str(INVENTORY)+'.lock').open('a+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            rows=[json.loads(x) for x in INVENTORY.read_text().splitlines() if x.strip()]
            matches=[r for r in rows if r.get('asset_id')==asset_id];require(len(matches)==1,'MANAGER_UNIQUE_LINEAGE');row=matches[0]
            index=b.read_json(b.DATA/'archive-index.json',{});entry=index.get('mappings',{}).get(row['asset_drive_id'],{})
            storage.require_registered_mapping(entry,index);validate_identity(row,entry,request)
            raw=index.get('mappings',{}).get(row['source_drive_id'],{})
            require(raw.get('jobId')==entry['jobId'] and raw.get('role')=='original' and raw.get('relativeParent')==[row['operation'],row['format'],'99_LEGACY'] and raw.get('sha256')==row['original_checksum'] and raw.get('stockTransferredToArchive') is True,'MANAGER_RAW_LEGACY_PAIR')
            d=b.Drive(apply);exact_folder(d,row['source_manager'],target)
            ack=d.one(b.config_load()['requests_folder_id'],'ack:'+entry['jobId'])
            if ack is None:raise DeliveryError('MANAGER_NATIVE_ACK_REQUIRED')
            b.require_publisher(d.meta(ack['id']),b.CANONICAL_SA)
            body=json.loads(d.raw(ack['id']));require(body.get('schema')=='mgs.archive.ack.v1' and body.get('status')=='verified' and body.get('kind')=='lineage' and body.get('validationOnly') is not True and body.get('jobId')==entry['jobId'] and {a.get('sourceId') for a in body.get('assets',[])}=={row['source_drive_id'],row['asset_drive_id']},'MANAGER_ACK_BINDING')
            current=storage.media_record(entry,storage.meta(d,entry['archiveId']),storage.meta(d,entry['stockShortcutId']))
            require(d.hashes(entry['archiveId'])=={'size':str(entry['size']),'md5':entry['md5'],'sha256':entry['sha256']},'MANAGER_PREMOVE_BYTES')
            raw_record=storage.media_record(raw,storage.meta(d,raw['archiveId']),storage.meta(d,raw['stockShortcutId']))
            require(loc.stock_parent(d,raw_record['parents'][0])==[row['operation'],row['format'],'99_LEGACY'],'MANAGER_RAW_NATIVE_LEGACY')
            require(all(any(a.get('sourceId')==v['sourceId'] and a.get('archiveId')==v['archiveId'] and a.get('sha256')==v['sha256'] for a in body['assets']) for v in [raw,entry]),'MANAGER_ACK_HASH_BINDING')
            path=RECEIPTS/('delivery-'+row['asset_drive_id']+'.json');receipt=b.read_json(path,{})
            if receipt:
                receipt_binding(row,entry,receipt);require(receipt['destination_parent_id']==target and receipt['request']==request,'MANAGER_REPLAY_SCOPE_CHANGED')
            else:
                old_parent=current['parents'][0];require(loc.stock_parent(d,old_parent)==[row['operation'],row['format'],'01_READY'],'MANAGER_VERIFIED_READY_STAGE_REQUIRED')
                receipt={'schema':'mgs.manager.delivery.receipt.v1','authority_message_id':AUTHORITY,'status':'intent','asset_id':asset_id,'logical_id':row['asset_drive_id'],'raw_source_id':row['source_drive_id'],'provider_id':entry['archiveId'],'stock_file_id':entry['stockShortcutId'],'sha256':entry['sha256'],'job_id':entry['jobId'],'manager':row['source_manager'],'source_parent_id':old_parent,'destination_parent_id':target,'request':request,'created_at':b.now_iso(),'copied':False,'deleted':False}
            if not apply:return {'status':'verified_plan','asset_id':asset_id,'destination':target,'same_stock_id':entry['stockShortcutId'],'remote_writes':0}
            if not path.exists():b.atomic_json(path,receipt)
            if current['parents']!=[target]:
                require(current['parents']==[receipt['source_parent_id']],'MANAGER_PARENT_CAS')
                import ares_autonomous_intake as intake
                intake.assert_source_writer(row['source_drive_id'])
                d.api('PATCH','files/'+entry['stockShortcutId'],{'supportsAllDrives':'true','addParents':target,'removeParents':receipt['source_parent_id'],'fields':'id,parents'}, {})
            verified=verify_receipt(d,row,entry,receipt,allow_intent=True)
            if receipt.get('status')!='verified':receipt.update(status='verified',verified_at=b.now_iso());b.atomic_json(path,receipt)
            row.update(manager_media_folder_id=target,manager_delivery_receipt=str(path.relative_to(b.BASE)),asset_path='MGS-AGENTS/CRIATIVOS/'+row['source_manager']+'/'+row['canonical_filename'],asset_stock_file_id=entry['stockShortcutId'],asset_provider_id=entry['archiveId'],webViewLink='https://drive.google.com/file/d/'+entry['stockShortcutId']+'/view',last_reconciled_at=b.now_iso())
            payload=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows);tmp=INVENTORY.with_suffix('.manager-delivery.new');tmp.write_text(payload);tmp.replace(INVENTORY)
            require(INVENTORY.read_text()==payload,'MANAGER_INVENTORY_WRITE_READBACK')
            verify_delivered(d,{'role':'clean','sourceId':row['asset_drive_id']},entry)
            return {'status':'delivered','asset_id':asset_id,'logical_id':row['asset_drive_id'],'stock_file_id':verified['stock_file_id'],'destination':target,'same_ids':True,'copied':False,'deleted':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--asset-id',required=True);p.add_argument('--destination',required=True);p.add_argument('--requester-id',required=True);p.add_argument('--thread-id',required=True);p.add_argument('--message-id',required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
    print(json.dumps(deliver(a.asset_id,a.destination,{'requester_id':a.requester_id,'thread_id':a.thread_id,'message_id':a.message_id},a.apply),ensure_ascii=False))
if __name__=='__main__':main()
