#!/usr/bin/env python3
"""Isolated owner lane: transfer verified SA stock shortcuts, preserving IDs.
No media copies, trash, DELETE or permission changes; canonical queue lease.
"""
import argparse,json
import ares_archive_bridge as b
import ares_archive_storage as storage
import ares_archive_locations as loc
import mgs_archive_owner_transport as t
import mgs_archive_layout_cutover as layout
HOME=t.HOME/'stock-lane'

def destination_folder(owner,sa,journal,entry):
    names=entry['relativeParent'];t.validate_path(names)
    context=b.read_json(b.DATA/'upload-context-layout.json',{});operations={x['operation'] for x in context.get('slots',[])}
    if len(names)!=3 or names[0] not in operations or names[1] not in ['IMG','VID'] or names[2] not in ['99_LEGACY','01_READY','02_TESTING','03_TESTED','04_WINNERS','05_REJECTED']:raise b.ArchiveError('STOCK_TRANSFER_REGISTERED_PATH_REQUIRED')
    parent=loc.stock_root();loc.verify_stock_root(sa);owner.parents.add(parent)
    for name in names:
        rows=[x for x in owner.listing(parent) if x.get('name')==name]
        if len(rows)>1 or (rows and rows[0].get('mimeType')!=b.FOLDER):raise b.ArchiveError('STOCK_TRANSFER_FOLDER_AMBIGUOUS')
        if rows:fid=rows[0]['id']
        else:
            key='stock-folder:'+layout.ba.sha([parent,name]);fid=journal.known_id(key)
            if not fid:
                journal.allow_create(key);journal.intent(key,{'parent':parent,'name':name,'stock_root':loc.stock_root()})
                try:fid=owner.api('POST','files',{'fields':'id'},{'name':name,'mimeType':b.FOLDER,'parents':[parent],'properties':{'mgsArchiveKey':key,'mgsArchiveType':'stock_folder'}})['id']
                except b.ArchiveError:
                    landed=owner.one(parent,key)
                    if not landed:raise b.ArchiveError('STOCK_TRANSFER_FOLDER_UNKNOWN_NO_REPLAY') from None
                    fid=landed['id']
                journal.landed(key,fid)
        actual=loc.assert_stock_file(sa,fid,parent)
        if actual.get('name')!=name or actual.get('mimeType')!=b.FOLDER:raise b.ArchiveError('STOCK_TRANSFER_FOLDER_READBACK')
        owner.parents.add(fid);parent=fid
    return parent

def check_ack(sa,c,entry,index):
    storage.require_registered_mapping(entry,index)
    found=sa.one(c['requests_folder_id'],'ack:'+entry['jobId'])
    if not found:raise b.ArchiveError('STOCK_TRANSFER_ACK_REQUIRED')
    metadata=sa.meta(found['id']);b.require_publisher(metadata,b.CANONICAL_SA);raw=sa.raw(found['id']);ack=json.loads(raw)
    if not b.control_object_scope(metadata,c['requests_folder_id']) or metadata.get('properties',{}).get('sha256')!=layout.ba.sha(raw) or ack.get('schema')!='mgs.archive.ack.v1' or ack.get('status')!='verified' or ack.get('validationOnly') is True:raise b.ArchiveError('STOCK_TRANSFER_NATIVE_ACK_SCOPE')
    matches=[x for x in ack.get('assets',[]) if x.get('sourceId')==entry['sourceId']]
    if len(matches)!=1 or any(matches[0].get(k)!=entry.get(k) for k in ['sourceId','archiveId','size','md5','sha256','jobId','lineageId']):raise b.ArchiveError('STOCK_TRANSFER_NATIVE_ACK_BYTES')
    return found['id']

def tick(max_files=4,defer_if_busy=False):
    if not 1<=max_files<=4:raise b.ArchiveError('STOCK_TRANSFER_BATCH_BOUND')
    if not loc.active():return {'status':'inactive','blocked':[],'transferred':[]}
    HOME.mkdir(parents=True,exist_ok=True)
    with b.queue_lock(blocking=not defer_if_busy) as lease:
        if lease is None:return {'status':'ok','blocked':[],'deferred_to_existing_writer':True}
        sa=b.Drive(True);owner=t.OwnerDrive();journal=t.Journal(HOME/'journal.json');c=b.config_load();index=b.read_json(b.DATA/'archive-index.json',{});snapshot=b.read_json(layout.SNAPSHOT,{});done=[]
        rows=[e for e in index.get('mappings',{}).values() if e.get('stockShortcutId') and e.get('stockTransferredToArchive') is not True and index['verified_jobs'].get(e.get('jobId'),{}).get('validationOnly') is not True]
        for entry in rows[:max_files]:
            ackid=check_ack(sa,c,entry,index);sid=entry['stockShortcutId'];stock=storage.meta(sa,sid);physical=storage.meta(sa,entry['archiveId'])
            if stock.get('mimeType')!=storage.SHORTCUT or stock.get('shortcutDetails',{}).get('targetId')!=entry['archiveId'] or stock.get('properties',{}).get('mgsArchiveLogicalSource')!=entry['sourceId'] or stock.get('trashed') is not False:raise b.ArchiveError('STOCK_TRANSFER_ALIAS_BINDING')
            if stock.get('driveId')==b.SOURCE_DRIVE:
                if loc.staging_relative_parent(sa,stock['parents'][0])!=entry['relativeParent']:raise b.ArchiveError('STOCK_TRANSFER_STAGING_PATH')
                destination=destination_folder(owner,sa,journal,entry)
                layout.move_once(owner,sa,journal,sid,stock['parents'][0],destination)
            else:
                frozen=snapshot.get('objects',{}).get(sid)
                if not journal.known_id('move:'+sid) and (not frozen or frozen.get('shortcutDetails',{}).get('targetId')!=entry['archiveId']):raise b.ArchiveError('STOCK_TRANSFER_UNEXPLAINED_LANDED_ALIAS')
            after=storage.meta(sa,sid);loc.stock_parent(sa,after['parents'][0]);storage.media_record(entry,physical,after)
            body={'schema':'mgs.archive.stock.transfer.receipt.v1','source_id':entry['sourceId'],'stock_shortcut_id':sid,'archive_id':entry['archiveId'],'stock_parent_id':after['parents'][0],'media_ack_id':ackid,'sha256':entry['sha256'],'same_id':True,'copied':False,'deleted':False,'completed_at':b.now_iso()}
            old=owner.one(c['receipts_folder_id'],'stock-transfer:'+entry['sourceId'])
            if old:
                prior=json.loads(owner.raw(old['id']))
                if any(prior.get(k)!=body[k] for k in body if k!='completed_at'):raise b.ArchiveError('STOCK_TRANSFER_RECEIPT_CONFLICT')
                body=prior
            rid=owner.write_json(c['receipts_folder_id'],'stock-transfer:'+entry['sourceId'],'stock_transfer_receipt',body,journal)
            b.require_publisher(sa.meta(rid),b.ACCOUNT)
            if sa.raw(rid)!=b.canonical(body):raise b.ArchiveError('STOCK_TRANSFER_SA_RECEIPT_READBACK')
            entry.update(stockTransferredToArchive=True,stockTransferReceiptId=rid,stockTransferVerifiedAt=b.now_iso());index['mappings'][entry['sourceId']]=entry;b.atomic_json(b.DATA/'archive-index.json',index);done.append(sid)
        out={'status':'ok','blocked':[],'transferred':done,'remaining':max(0,len(rows)-len(done)),'same_ids':True,'executed_at':b.now_iso()};b.atomic_json(HOME/'last-tick.json',out);return out

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');p.add_argument('--max-files',type=int,default=4);p.add_argument('--defer-if-busy',action='store_true');args=p.parse_args()
    if not args.apply:raise SystemExit('APPLY_REQUIRED')
    print(json.dumps(tick(args.max_files,args.defer_if_busy),ensure_ascii=False))
